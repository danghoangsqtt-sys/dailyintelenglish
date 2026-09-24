"""Checkpointed script generation pipeline (Phase 13, Task 13.4).

Replaces one long synchronous Gemini call with outline -> validated 1-2 minute
sections -> global merge, checkpointing each valid section so an interrupted job
resumes instead of restarting. Runs as an `ai_worker` "script" operation handler;
`app/main.py` wiring is deferred to Task 13.6 (not in this task's allowed files —
see task-13.4.md).
"""

from __future__ import annotations

import asyncio
import difflib
import hashlib
import json
import logging
import re
from collections import Counter
from datetime import datetime, timezone
from typing import NamedTuple, TYPE_CHECKING

from jinja2 import Environment, FileSystemLoader, StrictUndefined, TemplateNotFound
from pydantic import BaseModel, Field, TypeAdapter

from app.core.config import settings
from app.core.constants import (
    CEFR_WORDS_PER_MINUTE,
    SCRIPT_GLOBAL_WORD_TOLERANCE,
    SCRIPT_LAST_SECTION_CARRY_CAP,
    SCRIPT_MAX_CONSECUTIVE_LINES_PER_SPEAKER,
    SCRIPT_MAX_REPEATED_8GRAM_RATIO,
    SCRIPT_PIPELINE_MAX_GLOBAL_BUDGET_REPAIRS,
    SCRIPT_PIPELINE_MAX_LENGTH_REPAIRS,
    SCRIPT_PIPELINE_MAX_REPETITION_REPAIRS,
    SCRIPT_PIPELINE_MAX_STRUCTURAL_FIXES,
    SCRIPT_SECTION_AVOID_PHRASES_MAX,
    SCRIPT_SECTION_CARRY_CAP,
    SCRIPT_SECTION_TARGET_MINUTES,
    SCRIPT_SECTION_WORD_TOLERANCE,
    SCRIPT_SPEAKER_BALANCE_MAX_SHARE,
    SCRIPT_SPEAKER_BALANCE_MIN_SHARE,
    SCRIPT_SPEAKER_ID_MATCH_MIN_RATIO,
)
from app.core.exceptions import ProviderError, SchemaValidationError
from app.core.prompt_loader import SCRIPT_PROMPTS_DIR, load_cefr_block, load_genre_block
from app.db.transactions import read_transaction, write_transaction
from app.services import ai_job_service, project_service, script_service
from app.services.ai.contracts import GenerationRequest, GenerationResult
from app.services.ai.validation import parse_and_validate
from app.services.script_service import LanguageNotesOut

if TYPE_CHECKING:
    from app.services.ai.router import AIRouter
    from app.services.ai_worker import AIWorker, JobHandler

logger = logging.getLogger(__name__)

_env = Environment(
    loader=FileSystemLoader(str(SCRIPT_PROMPTS_DIR)),
    undefined=StrictUndefined,
    trim_blocks=True,
    lstrip_blocks=True,
)
_WORD_RE = re.compile(r"\S+")
# Task 17.1: the exact prefix validate_global() emits for a whole-episode word-count
# failure, shared with the global stage's own error-type check so the two can never
# silently drift apart again (found drifted once already during design review).
_GLOBAL_BUDGET_ERROR_PREFIX = "total word count"


class OutlineSectionSpec(BaseModel):
    """One planned section of the episode, as proposed by the outline call."""

    index: int = Field(ge=1)
    objective: str = Field(min_length=8)
    target_words: int = Field(ge=1)


class ScriptOutline(BaseModel):
    """The episode-level plan sections are generated against."""

    title: str = Field(min_length=1)
    sections: list[OutlineSectionSpec] = Field(min_length=1)


class SectionLineOut(BaseModel):
    """One generated line, before server-side ID assignment.

    Deliberately has no `id` field -- line IDs are always server-owned in this
    pipeline (unlike the legacy `script_service.ScriptLineOut`, which still
    expects the model to echo an `id` for single-line regeneration).
    """

    speaker_id: str
    text: str = Field(min_length=1)
    language_notes: LanguageNotesOut = Field(default_factory=LanguageNotesOut)


class SectionLineWire(BaseModel):
    """Task 15.1: the model's raw response shape -- `speaker` is a short alias
    (`S1`, `S2`, ...), never assumed to already be a real speaker UUID. Every
    call that talks to the model parses/schemas against this type; the result
    is resolved into `SectionLineOut` (`resolve_section_lines`) before any
    validation runs. `SectionLineOut` itself, and everything downstream of it
    (validators, checkpoints, `script_service.save_script`), is unaware this
    type exists."""

    speaker: str
    text: str = Field(min_length=1)
    language_notes: LanguageNotesOut = Field(default_factory=LanguageNotesOut)


_OUTLINE_ADAPTER = TypeAdapter(ScriptOutline)
_SECTION_LINES_ADAPTER = TypeAdapter(list[SectionLineOut])
# Task 15.1: the model-facing schema/parse target -- SectionLineOut/_SECTION_LINES_ADAPTER
# above stay the checkpoint (resolved-shape) adapter, untouched.
_SECTION_LINES_WIRE_ADAPTER = TypeAdapter(list[SectionLineWire])
_UUID_SHAPED_RE = re.compile(r"^[0-9a-f-]{8,}$", re.IGNORECASE)


# --- pure functions (no I/O -- unit-testable directly) -------------------------------


def compute_target_words(cefr_level: str, duration_minutes: float) -> int:
    """Total spoken-word target for the whole episode."""
    wpm = CEFR_WORDS_PER_MINUTE[cefr_level.upper()]
    return round(wpm * duration_minutes)


def plan_sections(target_words: int, cefr_level: str) -> list[int]:
    """Split `target_words` into `SCRIPT_SECTION_TARGET_MINUTES`-sized budgets.

    Returns a list of per-section word budgets summing exactly to `target_words`
    -- used only to tell the outline prompt how many sections to propose and
    roughly how big each should be; the outline call's own returned
    `target_words` per section (not this function's numbers) are what section
    generation and validation actually target.
    """
    wpm = CEFR_WORDS_PER_MINUTE[cefr_level.upper()]
    section_size = max(1, round(wpm * SCRIPT_SECTION_TARGET_MINUTES))
    num_sections = max(1, round(target_words / section_size))
    base, remainder = divmod(target_words, num_sections)
    return [base + 1 if i < remainder else base for i in range(num_sections)]


def normalize_text(text: str) -> str:
    """Casefold + collapse whitespace, for duplicate/repetition comparisons."""
    return re.sub(r"\s+", " ", text.strip().casefold())


def section_word_count(lines: list[SectionLineOut]) -> int:
    """Total spoken-word count across `lines` (Task 14.2 checkpoint telemetry)."""
    return sum(len(_WORD_RE.findall(line.text)) for line in lines)


def clamp(value: float, low: float, high: float) -> float:
    """Bound `value` to `[low, high]`."""
    return max(low, min(high, value))


def compute_section_effective_target(nominal: int, carry: float) -> int:
    """Effective word target for a non-last section (Task 14.3, plan §4.3 item 2).

    `carry` is the running surplus/deficit from prior sections (positive =
    prior sections undershot and owe words to this one). Clamped to
    `nominal * (1 ± SCRIPT_SECTION_CARRY_CAP)` -- any part of `nominal + carry`
    outside that band is not applied *this* section, but `carry` itself is never
    reset by the clamp (see `carry` update below), so it is not lost either.
    """
    low = nominal * (1 - SCRIPT_SECTION_CARRY_CAP)
    high = nominal * (1 + SCRIPT_SECTION_CARRY_CAP)
    return round(clamp(nominal + carry, low, high))


def compute_last_section_effective_target(nominal_last: int, target_words: int, words_so_far: int) -> int:
    """Effective target for the episode's final section (Task 14.3, plan §4.3
    item 3) -- aims directly at landing the whole-episode total instead of
    accumulating carry further, clamped to `nominal_last * (1 ±
    SCRIPT_LAST_SECTION_CARRY_CAP)`."""
    low = nominal_last * (1 - SCRIPT_LAST_SECTION_CARRY_CAP)
    high = nominal_last * (1 + SCRIPT_LAST_SECTION_CARRY_CAP)
    return round(clamp(target_words - words_so_far, low, high))


def repeated_8gram_ratio(words: list[str]) -> float:
    """Fraction of 8-word sliding windows that repeat elsewhere in `words`."""
    if len(words) < 8:
        return 0.0
    grams = [tuple(words[i : i + 8]) for i in range(len(words) - 7)]
    counts = Counter(grams)
    repeated = sum(count for count in counts.values() if count > 1)
    return repeated / len(grams)


def find_repeated_8grams_by_section(
    sections: list[tuple[int, list[SectionLineOut]]],
) -> tuple[list[tuple[str, ...]], dict[int, int]]:
    """Task 14.13: repeated 8-word windows across the whole episode, attributed
    to whichever section each occurrence *starts* in -- lets the pipeline pick
    the single worst section to regenerate rather than a flat re-roll. A repeat
    spanning a section boundary is still found (the whole episode's words are
    concatenated in order first) and attributed to the section its first word
    falls in. Returns `(distinct repeated grams, {section_index: occurrence
    count starting there})` -- both empty if nothing repeats."""
    all_words: list[str] = []
    word_section: list[int] = []
    for section_index, lines in sections:
        for line in lines:
            for word in _WORD_RE.findall(line.text):
                all_words.append(normalize_text(word))
                word_section.append(section_index)

    if len(all_words) < 8:
        return [], {}

    grams = [tuple(all_words[i : i + 8]) for i in range(len(all_words) - 7)]
    counts = Counter(grams)
    repeated_gram_set = {gram for gram, count in counts.items() if count > 1}
    if not repeated_gram_set:
        return [], {}

    per_section_counts: dict[int, int] = {}
    for index, gram in enumerate(grams):
        if gram in repeated_gram_set:
            section_index = word_section[index]
            per_section_counts[section_index] = per_section_counts.get(section_index, 0) + 1

    return sorted(repeated_gram_set), per_section_counts


def frequent_repeated_phrases(words: list[str], limit: int = SCRIPT_SECTION_AVOID_PHRASES_MAX) -> list[str]:
    """Task 14.13: the most-repeated 8-word phrases seen so far (already-
    normalized `words`), for the *next* section's prompt to proactively avoid
    reusing -- a heads-up before generation, not the reactive repair above."""
    if len(words) < 8:
        return []
    grams = [tuple(words[i : i + 8]) for i in range(len(words) - 7)]
    counts = Counter(grams)
    repeated = sorted((gram for gram, count in counts.items() if count > 1), key=lambda gram: -counts[gram])
    return [" ".join(gram) for gram in repeated[:limit]]


def resolve_speaker(raw: str, speakers: list[dict]) -> tuple[str, str | None]:
    """Task 15.1: maps a wire-format `speaker` value (normally an `S{n}` alias)
    to a real speaker UUID, deterministically. Returns `(resolved_or_original,
    kind)` -- `kind` names which rule matched (for logging), or `None` if
    nothing matched, in which case the *original* `raw` value is returned
    unchanged so the existing unknown-speaker-id validation catches it exactly
    as it does today (no separate "unresolved" error path).

    Rule order: exact alias -> alias case/whitespace-insensitive -> the
    speaker's display name (only when unique in the project, case-insensitive
    -- two same-named speakers means this rule contributes nothing for either)
    -> an exact known-UUID match -> a UUID-*shaped* value matching exactly one
    known id at >= SCRIPT_SPEAKER_ID_MATCH_MIN_RATIO similarity (two or more
    ids tying above the threshold is unresolved, never a guess)."""
    value = raw.strip()
    normalized = value.casefold()
    exact_alias = {f"S{index}": speaker["id"] for index, speaker in enumerate(speakers, start=1)}
    normalized_alias = {f"s{index}": speaker["id"] for index, speaker in enumerate(speakers, start=1)}

    if value in exact_alias:
        return exact_alias[value], "alias_exact"
    if normalized in normalized_alias:
        return normalized_alias[normalized], "alias_normalized"

    name_counts = Counter(speaker["name"].strip().casefold() for speaker in speakers)
    for speaker in speakers:
        speaker_name = speaker["name"].strip().casefold()
        if speaker_name == normalized and name_counts[speaker_name] == 1:
            return speaker["id"], "display_name"

    known_ids = {speaker["id"] for speaker in speakers}
    if value in known_ids:
        return value, "uuid_exact"

    if _UUID_SHAPED_RE.match(value):
        matches = [
            known_id
            for known_id in known_ids
            if difflib.SequenceMatcher(None, value.lower(), known_id.lower()).ratio()
            >= SCRIPT_SPEAKER_ID_MATCH_MIN_RATIO
        ]
        if len(matches) == 1:
            return matches[0], "uuid_near_miss"

    return raw, None


def resolve_section_lines(wire_lines: list[SectionLineWire], speakers: list[dict]) -> list[SectionLineOut]:
    """Task 15.1: resolves every wire line's alias/near-miss `speaker` value to
    a real speaker id, logging each successful resolution
    (`script_speaker_resolved`). An unresolved value is *not* logged here --
    it passes through unchanged into `SectionLineOut.speaker_id`, and the
    existing unknown-speaker-id validation reports it exactly as today."""
    resolved_lines = []
    for wire_line in wire_lines:
        resolved, kind = resolve_speaker(wire_line.speaker, speakers)
        if kind is not None:
            logger.info(
                "script_speaker_resolved kind=%s original=%r resolved=%s", kind, wire_line.speaker, resolved
            )
        resolved_lines.append(
            SectionLineOut(speaker_id=resolved, text=wire_line.text, language_notes=wire_line.language_notes)
        )
    return resolved_lines


def _lines_to_wire_json(lines: list[SectionLineOut], speakers: list[dict]) -> str:
    """Task 15.1: renders already-resolved section lines back into the
    alias-shaped wire format for the repair prompt's "your previous answer"
    echo -- keeps that echo self-consistent with the alias contract. A line
    whose `speaker_id` was never resolved (exactly the case that triggers a
    repair) falls back to showing the literal original value, which is more
    useful for a repair prompt than hiding it or fabricating an alias."""
    id_to_alias = {speaker["id"]: f"S{index}" for index, speaker in enumerate(speakers, start=1)}
    wire = [
        {
            "speaker": id_to_alias.get(line.speaker_id, line.speaker_id),
            "text": line.text,
            "language_notes": line.language_notes.model_dump(),
        }
        for line in lines
    ]
    return json.dumps(wire)


def validate_section_structure(lines: list[SectionLineOut], known_speaker_ids: set[str]) -> list[str]:
    """Structural hard checks for one generated section (Task 14.3 split --
    these always hard-fail the job even after a repair; see
    `validate_section_word_budget` for the check that now instead triggers
    accept-and-carry). Empty list means structurally valid."""
    if not lines:
        return ["section has no lines"]

    errors: list[str] = []
    unknown = {line.speaker_id for line in lines} - known_speaker_ids
    if unknown:
        errors.append(f"unknown speaker_id(s): {sorted(unknown)}")

    if len(known_speaker_ids) > 1:
        consecutive = 1
        run_start = 0
        for index, (previous, current) in enumerate(zip(lines, lines[1:], strict=False), start=1):
            if previous.speaker_id == current.speaker_id:
                consecutive += 1
                if consecutive > SCRIPT_MAX_CONSECUTIVE_LINES_PER_SPEAKER:
                    errors.append(
                        f"more than {SCRIPT_MAX_CONSECUTIVE_LINES_PER_SPEAKER} consecutive lines "
                        f"from speaker {previous.speaker_id} (lines {run_start + 1}-{index + 1})"
                    )
                    break
            else:
                consecutive = 1
                run_start = index

    return errors


def _merge_group(group: list[SectionLineOut]) -> SectionLineOut:
    """Task 15.2: joins one group of same-speaker lines into a single line --
    text concatenated with a space, word order preserved exactly. `language_notes`
    (PM review note): `collocations`/`idioms` are unioned across the group,
    deduplicated in first-seen order (nothing any merged line carried is
    dropped); `grammar_point` keeps the first line's value."""
    if len(group) == 1:
        return group[0]
    collocations = list(dict.fromkeys(item for line in group for item in line.language_notes.collocations))
    idioms = list(dict.fromkeys(item for line in group for item in line.language_notes.idioms))
    return SectionLineOut(
        speaker_id=group[0].speaker_id,
        text=" ".join(line.text for line in group),
        language_notes=LanguageNotesOut(
            collocations=collocations, idioms=idioms, grammar_point=group[0].language_notes.grammar_point
        ),
    )


def _chunk_run(run: list[SectionLineOut], limit: int) -> list[list[SectionLineOut]]:
    """Splits one same-speaker `run` into exactly `limit` contiguous groups,
    sized as evenly as possible (the same `divmod` distribution `plan_sections`
    already uses elsewhere in this file), preserving line order."""
    base, remainder = divmod(len(run), limit)
    groups: list[list[SectionLineOut]] = []
    index = 0
    for group_index in range(limit):
        size = base + 1 if group_index < remainder else base
        if size == 0:
            continue
        groups.append(run[index : index + size])
        index += size
    return groups


def merge_consecutive_lines(lines: list[SectionLineOut], limit: int) -> list[SectionLineOut] | None:
    """Task 15.2: merges every run of more than `limit` consecutive same-speaker
    lines into `limit` (or fewer) lines, splitting the run as evenly as possible
    and joining each group's text with a space -- words and their order are
    never changed, and no line is ever re-attributed to a different speaker
    (invariants 20/21).

    Returns `None`, not a merged list, when the *entire* section is one
    speaker (zero lines from any other speaker) -- merging that down to
    `limit` giant paragraphs would still not be a dialogue, just a
    numerically-passing monologue, which the plan explicitly calls out as
    unfixable: the caller falls through to the existing hard-fail unchanged."""
    if len({line.speaker_id for line in lines}) < 2:
        return None

    merged: list[SectionLineOut] = []
    run: list[SectionLineOut] = [lines[0]]
    for line in lines[1:]:
        if line.speaker_id == run[-1].speaker_id:
            run.append(line)
        else:
            merged.extend([_merge_group(group) for group in _chunk_run(run, limit)] if len(run) > limit else run)
            run = [line]
    merged.extend([_merge_group(group) for group in _chunk_run(run, limit)] if len(run) > limit else run)
    return merged


def validate_section_word_budget(lines: list[SectionLineOut], target_words: int) -> list[str]:
    """Word-deviation check against `target_words` (Task 14.3: the caller passes
    the *effective*, not nominal, target). Empty `lines` returns no error here --
    that case is `validate_section_structure`'s "section has no lines", not a
    budget miss, so it is never double-reported."""
    if not lines:
        return []
    total_words = section_word_count(lines)
    tolerance = target_words * SCRIPT_SECTION_WORD_TOLERANCE
    if not (target_words - tolerance <= total_words <= target_words + tolerance):
        return [
            f"section word count {total_words} is outside "
            f"±{int(SCRIPT_SECTION_WORD_TOLERANCE * 100)}% of target {target_words}"
        ]
    return []


def validate_section(
    lines: list[SectionLineOut], target_words: int, known_speaker_ids: set[str]
) -> list[str]:
    """Combined structural + word-budget checks -- kept for existing pure-function
    callers; the pipeline itself (Task 14.3) calls the two split functions above
    separately, since a word-budget-only failure and a structural failure are no
    longer treated the same way after a repair. Semantically identical to the
    pre-14.3 combined function (same errors, different internal composition)."""
    return validate_section_structure(lines, known_speaker_ids) + validate_section_word_budget(lines, target_words)


def validate_global(
    lines: list[SectionLineOut],
    target_words: int,
    known_speaker_ids: set[str],
    num_speakers: int,
    topic: str,
) -> tuple[list[str], list[str]]:
    """Whole-episode hard checks (word budget, balance, duplicates, repetition)
    plus soft warnings (topic relevance). Returns `(hard_errors, warnings)`."""
    hard_errors: list[str] = []
    warnings: list[str] = []

    if not lines:
        return ["merged script has no lines"], warnings

    normalized_words: list[str] = []
    words_by_speaker: dict[str, int] = {}
    for line in lines:
        line_words = _WORD_RE.findall(line.text)
        normalized_words.extend(normalize_text(word) for word in line_words)
        words_by_speaker[line.speaker_id] = words_by_speaker.get(line.speaker_id, 0) + len(line_words)

    total_words = sum(words_by_speaker.values())
    tolerance = target_words * SCRIPT_GLOBAL_WORD_TOLERANCE
    if not (target_words - tolerance <= total_words <= target_words + tolerance):
        hard_errors.append(
            f"{_GLOBAL_BUDGET_ERROR_PREFIX} {total_words} is outside "
            f"±{int(SCRIPT_GLOBAL_WORD_TOLERANCE * 100)}% of target {target_words}"
        )

    # Speaker-balance is only well-defined for exactly two speakers (matches the
    # controlling plan's own "no worse than 65/35 for two speakers" wording).
    if num_speakers == 2 and total_words > 0:
        for speaker_id, count in words_by_speaker.items():
            share = count / total_words
            if not (SCRIPT_SPEAKER_BALANCE_MIN_SHARE <= share <= SCRIPT_SPEAKER_BALANCE_MAX_SHARE):
                hard_errors.append(
                    f"speaker {speaker_id} word share {share:.0%} outside "
                    f"{SCRIPT_SPEAKER_BALANCE_MIN_SHARE:.0%}-{SCRIPT_SPEAKER_BALANCE_MAX_SHARE:.0%}"
                )

    normalized_lines = [normalize_text(line.text) for line in lines]
    if len(normalized_lines) != len(set(normalized_lines)):
        hard_errors.append("exact duplicate line(s) found")

    ratio = repeated_8gram_ratio(normalized_words)
    if ratio >= SCRIPT_MAX_REPEATED_8GRAM_RATIO:
        hard_errors.append(
            f"repeated 8-gram ratio {ratio:.2%} >= {SCRIPT_MAX_REPEATED_8GRAM_RATIO:.0%}"
        )

    # Topic relevance stays a warning, never a hard reject (low-precision keyword
    # heuristic, per the controlling plan's explicit instruction).
    topic_keywords = {normalize_text(word) for word in _WORD_RE.findall(topic) if len(word) > 3}
    if topic_keywords and not (topic_keywords & set(normalized_words)):
        warnings.append("no topic keyword found anywhere in the script (heuristic, may be a false positive)")

    return hard_errors, warnings


def _has_budget_error(errors: list[str]) -> bool:
    return any(error.startswith(_GLOBAL_BUDGET_ERROR_PREFIX) for error in errors)


def _has_repetition_error(errors: list[str]) -> bool:
    return any(error.startswith("repeated 8-gram ratio") for error in errors)


class _BudgetRepairTarget(NamedTuple):
    """One global-stage budget repair's chosen section and computed target
    (Task 17.1)."""

    section_index: int
    lines: list[SectionLineOut]
    new_target: int
    direction: str  # "over" or "under"
    deviation: int  # always >= 0, in the `direction` sense
    nominal: int


async def _load_section_checkpoints(db, job_id: str) -> dict[int, dict]:
    """Fresh `stage == "section"` checkpoints for a job, keyed by section_index --
    shared by the global stage's budget and repetition repair paths (Task 17.1) so
    each sees whatever the other one just changed."""
    async with read_transaction():
        fresh_checkpoints = await ai_job_service.get_valid_checkpoints(db, job_id)
    return {
        checkpoint["section_index"]: checkpoint
        for checkpoint in fresh_checkpoints
        if checkpoint["stage"] == "section"
    }


def _worst_budget_section(
    section_checkpoints: dict[int, dict],
    outline: ScriptOutline,
    total_words: int,
    target_words: int,
) -> _BudgetRepairTarget | None:
    """Picks the section whose actual words deviate most from its own NOMINAL
    target -- never its effective one (Task 17.1, C2). Effective targets already
    have carry baked in from earlier sections' own undershoot/overshoot, which
    hides where an overshoot or undershoot actually originated; nominal targets
    are what the whole-episode `target_words` is the sum of. Direction follows
    whichever way the episode total is wrong. Ties broken by lowest
    `section_index` (sections are scanned in outline order; only a *strictly*
    larger deviation replaces the current pick).

    Returns `None` if no section has a checkpoint yet (defensive -- should not
    happen once every section is checkpointed, mirrors the repetition-repair
    path's own `if per_section_counts:` guard)."""
    direction = "over" if total_words > target_words else "under"
    worst: _BudgetRepairTarget | None = None
    for section_spec in outline.sections:
        checkpoint = section_checkpoints.get(section_spec.index)
        if checkpoint is None:
            continue
        lines = _SECTION_LINES_ADAPTER.validate_json(checkpoint["result_json"])
        words = section_word_count(lines)
        nominal = section_spec.target_words
        deviation = (words - nominal) if direction == "over" else (nominal - words)
        if worst is None or deviation > worst.deviation:
            # Lands the whole-episode total exactly on target_words, given every
            # other section's words stay as they are (generalizes the single
            # last-section formula this replaces).
            new_target = max(1, target_words - (total_words - words))
            worst = _BudgetRepairTarget(section_spec.index, lines, new_target, direction, deviation, nominal)
    return worst


def summarize_section(lines: list[SectionLineOut]) -> str:
    """A short, bounded continuity note for the next section's prompt -- never
    the full prior transcript, so prompt size stays flat as sections accumulate."""
    if not lines:
        return ""
    return f'{len(lines)} lines; started with "{lines[0].text[:80]}"; ended with "{lines[-1].text[:80]}"'


def compute_config_hash(project: dict, operation: str) -> str:
    """Mirrors `ai_job_service._canonical_hash`'s exact algorithm.

    Duplicated intentionally rather than imported: `app/services/ai_job_service.py`
    is not in this task's allowed files, and this is 3 lines, not worth a
    cross-module private-function coupling for.
    """
    canonical = json.dumps({"project": project, "operation": operation}, sort_keys=True, default=str)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


# --- prompt rendering (this module's own Jinja env -- app/core/prompt_loader.py
# is not in this task's allowed files, so its render_* wrappers aren't extended) --


def _render_sync(template_name: str, **context: object) -> str:
    try:
        template = _env.get_template(template_name)
    except TemplateNotFound as exc:
        raise SchemaValidationError(f"Prompt template not found: {exc}") from exc
    return template.render(**context)


async def _render(template_name: str, **context: object) -> str:
    return await asyncio.to_thread(_render_sync, template_name, **context)


# --- provider calls --------------------------------------------------------------------


async def _generate_outline(
    router: "AIRouter", project: dict, target_words: int, num_sections: int, db, job_id: str
) -> ScriptOutline:
    genre_instructions = await load_genre_block(project["genre"])
    cefr_constraints = await load_cefr_block(project["cefr_level"])
    prompt = await _render(
        "outline.txt",
        topic=project["topic"],
        genre=project["genre"],
        cefr_level=project["cefr_level"],
        duration_minutes=project["duration_minutes"],
        num_speakers=len(project["speakers"]),
        accent=project["accent"],
        speakers=project["speakers"],
        target_words=target_words,
        num_sections=num_sections,
        genre_instructions=genre_instructions,
        cefr_constraints=cefr_constraints,
    )
    result = await _call_router(
        db, job_id, router,
        GenerationRequest(
            prompt=prompt,
            json_schema=ScriptOutline.model_json_schema(),
            deadline_seconds=settings.AI_REQUEST_DEADLINE_SECONDS,
            purpose="script_outline",
        ),
        section_index=None, is_repair=False, adapter=_OUTLINE_ADAPTER,
    )
    return parse_and_validate(result.text, _OUTLINE_ADAPTER)


async def _generate_section(
    router: "AIRouter",
    project: dict,
    outline: ScriptOutline,
    section_spec: OutlineSectionSpec,
    prior_summary: str,
    known_speaker_ids: set[str],
    is_last_section: bool,
    db,
    job_id: str,
    avoid_phrases: list[str] | None = None,
) -> tuple[list[SectionLineOut], list[str], list[str]]:
    """Returns `(lines, structural_errors, budget_errors)`. `section_spec.target_words`
    is the *effective* target the caller wants this section validated against --
    the orchestrator passes a `model_copy`'d spec with `target_words` already
    overridden (Task 14.3), so this function itself needs no separate parameter.
    `avoid_phrases` (Task 14.13) is the episode-so-far's most-repeated 8-grams,
    a proactive heads-up so this section doesn't reuse them -- optional, empty
    by default, since the outline call has no prior sections to avoid yet."""
    cefr_constraints = await load_cefr_block(project["cefr_level"])
    # Task 14.8-b (CR-02): the ±tolerance range shown in the prompt is computed
    # here, from the one real constant, instead of the template hard-coding its
    # own copy of SCRIPT_SECTION_WORD_TOLERANCE as 0.85/1.15 literals.
    min_words = round(section_spec.target_words * (1 - SCRIPT_SECTION_WORD_TOLERANCE))
    max_words = round(section_spec.target_words * (1 + SCRIPT_SECTION_WORD_TOLERANCE))
    prompt = await _render(
        "section.txt",
        topic=project["topic"],
        genre=project["genre"],
        cefr_level=project["cefr_level"],
        outline_title=outline.title,
        section_index=section_spec.index,
        section_count=len(outline.sections),
        objective=section_spec.objective,
        min_words=min_words,
        max_words=max_words,
        prior_summary=prior_summary,
        is_last_section=is_last_section,
        avoid_phrases=avoid_phrases or [],
        speakers=project["speakers"],
        num_speakers=len(project["speakers"]),
        max_consecutive_lines=SCRIPT_MAX_CONSECUTIVE_LINES_PER_SPEAKER,
        cefr_constraints=cefr_constraints,
        language_features=project["language_features"],
    )
    result = await _call_router(
        db, job_id, router,
        GenerationRequest(
            prompt=prompt,
            json_schema=_SECTION_LINES_WIRE_ADAPTER.json_schema(),
            deadline_seconds=settings.AI_REQUEST_DEADLINE_SECONDS,
            purpose="script_section",
        ),
        section_index=section_spec.index, is_repair=False, adapter=_SECTION_LINES_WIRE_ADAPTER,
    )
    try:
        wire_lines = parse_and_validate(result.text, _SECTION_LINES_WIRE_ADAPTER)
    except SchemaValidationError as exc:
        return [], [str(exc)], []
    lines = resolve_section_lines(wire_lines, project["speakers"])
    return (
        lines,
        validate_section_structure(lines, known_speaker_ids),
        validate_section_word_budget(lines, section_spec.target_words),
    )


async def _repair_section(
    router: "AIRouter",
    project: dict,
    section_spec: OutlineSectionSpec,
    previous_lines: list[SectionLineOut],
    errors: list[str],
    known_speaker_ids: set[str],
    db,
    job_id: str,
    *,
    purpose: str = "script_section_repair",
) -> tuple[list[SectionLineOut], list[str], list[str]]:
    """Returns `(lines, structural_errors, budget_errors)` -- see `_generate_section`
    for why `section_spec.target_words` is already the effective target.

    `purpose` (Task 14.8) distinguishes the one semantic repair
    (`script_section_repair`, the default) from the length-only pass
    (`script_section_length_repair`) in telemetry -- both call this same
    function, since the length-only pass is a second, narrower repair, not a
    different code path."""
    previous_output = _lines_to_wire_json(previous_lines, project["speakers"]) if previous_lines else "[]"
    measured_words = section_word_count(previous_lines)
    prompt = await _render(
        "repair.txt",
        objective=section_spec.objective,
        target_words=section_spec.target_words,
        measured_words=measured_words,
        delta=measured_words - section_spec.target_words,
        speakers=project["speakers"],
        errors=errors,
        previous_output=previous_output,
    )
    result = await _call_router(
        db, job_id, router,
        GenerationRequest(
            prompt=prompt,
            json_schema=_SECTION_LINES_WIRE_ADAPTER.json_schema(),
            deadline_seconds=settings.AI_REQUEST_DEADLINE_SECONDS,
            purpose=purpose,
        ),
        section_index=section_spec.index, is_repair=True, adapter=_SECTION_LINES_WIRE_ADAPTER,
    )
    try:
        wire_lines = parse_and_validate(result.text, _SECTION_LINES_WIRE_ADAPTER)
    except SchemaValidationError as exc:
        return [], [str(exc)], []
    lines = resolve_section_lines(wire_lines, project["speakers"])
    return (
        lines,
        validate_section_structure(lines, known_speaker_ids),
        validate_section_word_budget(lines, section_spec.target_words),
    )


async def _run_section_pipeline(
    router: "AIRouter",
    project: dict,
    outline: ScriptOutline,
    section_spec: OutlineSectionSpec,
    effective_target: int,
    prior_summary: str,
    avoid_phrases: list[str],
    known_speaker_ids: set[str],
    is_last: bool,
    db,
    job_id: str,
) -> tuple[list[SectionLineOut], dict] | None:
    """One section's full generate-and-repair path: generate -> one semantic
    repair if structurally/budget invalid -> one bounded consecutive-lines merge
    fix if still failing on exactly that -> one length-only repair if still far
    over budget -> the checkpoint-metrics dict for whichever result survives.

    Extracted from the main per-section loop (Task 17.1, C4) so the global
    stage's targeted budget repair (the "over" direction) can rerun a section
    through this *exact same, calibrated* path at a new target, instead of a
    bare fresh generation alone. Evidence across 118 B-6+B-7 section checkpoints
    (plan Amendment B, read-only): a bare first-pass generation alone lands at a
    median 0.60x its target (only 15/118 within +/-15%), while this full path
    (generation through the in-loop length repair) lands at a median 1.02x
    (65/118 within +/-15%) -- the calibrated tool, not a new one.

    Returns `(lines, checkpoint_metrics)` on success, matching exactly the
    `metrics_json` shape the main loop has always saved. Returns `None` if the
    job has already been marked failed (`_fail`/`_fail_provider` already ran
    inside this function) -- the caller must return immediately and do nothing
    else, identical to how the main loop already behaves today (behaviour-
    preserving: this function's body is the main loop's own per-section body,
    moved, not rewritten).
    """
    effective_spec = section_spec.model_copy(update={"target_words": effective_target})
    idx = section_spec.index

    try:
        section_lines, structural_errors, budget_errors = await _generate_section(
            router, project, outline, effective_spec, prior_summary, known_speaker_ids,
            is_last, db, job_id, avoid_phrases,
        )
    except ProviderError as exc:
        await _fail_provider(db, job_id, exc)
        return None

    repaired = False
    words_before_repair: int | None = None
    errors_before_repair = 0
    if structural_errors or budget_errors:
        errors_before_repair = len(structural_errors) + len(budget_errors)
        words_before_repair = section_word_count(section_lines)
        try:
            section_lines, structural_errors, budget_errors = await _repair_section(
                router, project, effective_spec, section_lines,
                structural_errors + budget_errors, known_speaker_ids, db, job_id,
            )
        except ProviderError as exc:
            await _fail_provider(db, job_id, exc)
            return None
        repaired = True

    # Task 15.2: a section still failing structural validation after the one
    # semantic repair, where that failure is *exactly* the consecutive-lines
    # one (never mixed with an unknown-speaker error, and never a second
    # attempt beyond this one), gets one bounded merge fix instead of
    # hard-failing outright.
    structural_fix_applied = False
    lines_before_fix: int | None = None
    lines_after_fix: int | None = None
    if (
        structural_errors
        and len(structural_errors) == 1
        and structural_errors[0].startswith("more than ")
        and SCRIPT_PIPELINE_MAX_STRUCTURAL_FIXES > 0
    ):
        merged_lines = merge_consecutive_lines(section_lines, SCRIPT_MAX_CONSECUTIVE_LINES_PER_SPEAKER)
        if merged_lines is not None:
            lines_before_fix = len(section_lines)
            section_lines = merged_lines
            lines_after_fix = len(section_lines)
            structural_fix_applied = True
            structural_errors = validate_section_structure(section_lines, known_speaker_ids)

    if structural_errors:
        await _fail(db, job_id, "section_validation_failed", structural_errors)
        return None

    words = section_word_count(section_lines)

    # Task 14.8: a section still far over budget after its one semantic
    # repair gets one more, length-only pass -- narrower than the semantic
    # repair (SCRIPT_SECTION_CARRY_CAP, not the ±15% tolerance, is the
    # trigger) and never fires for an under-length miss, which keeps
    # 14.3's accept-and-carry for those exactly as it was.
    length_repaired = False
    words_before_length_repair: int | None = None
    if (
        repaired
        and budget_errors
        and words > effective_target * (1 + SCRIPT_SECTION_CARRY_CAP)
        and SCRIPT_PIPELINE_MAX_LENGTH_REPAIRS > 0
    ):
        words_before_length_repair = words
        try:
            section_lines, structural_errors, budget_errors = await _repair_section(
                router, project, effective_spec, section_lines,
                budget_errors, known_speaker_ids, db, job_id,
                purpose="script_section_length_repair",
            )
        except ProviderError as exc:
            await _fail_provider(db, job_id, exc)
            return None
        length_repaired = True
        if structural_errors:
            await _fail(db, job_id, "section_validation_failed", structural_errors)
            return None
        words = section_word_count(section_lines)

    if (repaired or length_repaired) and budget_errors:
        # Task 14.3 item 4: a word-deviation-only failure survives the one
        # repair pass -- accept and carry the drift instead of failing the
        # job (the ±15% check is now a repair trigger/drift signal, not a
        # job-killing gate; the product's only hard word-count gate stays
        # the ±10% total, checked below via validate_global).
        logger.info(
            "script_section_accepted_off_target job_id=%s section=%d effective=%d actual=%d",
            job_id, idx, effective_target, words,
        )

    checkpoint_metrics = {
        "target_nominal": section_spec.target_words,
        "target_effective": effective_target,
        "words": words,
        "deviation_pct": round((words - effective_target) / effective_target, 4) if effective_target else 0.0,
        "repaired": repaired,
        "words_before_repair": words_before_repair,
        "errors_before_repair": errors_before_repair,
        "length_repaired": length_repaired,
        "words_before_length_repair": words_before_length_repair,
        "structural_fix": "merged_consecutive_lines" if structural_fix_applied else None,
        "lines_before_fix": lines_before_fix,
        "lines_after_fix": lines_after_fix,
    }
    return section_lines, checkpoint_metrics


# --- orchestration -----------------------------------------------------------------------


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _call_record(
    request: GenerationRequest,
    *,
    section_index: int | None,
    is_repair: bool,
    result: GenerationResult | None = None,
    exc: ProviderError | None = None,
) -> dict:
    """Build one Task 14.2 telemetry call record -- safe fields only, never
    prompt/response text or a key (plan §4.2's call record shape)."""
    if result is not None:
        return {
            "purpose": request.purpose,
            "section_index": section_index,
            "provider": result.provider,
            "model": result.model,
            "attempt": result.attempt,
            "attempts": result.attempts,
            "backoff_seconds": result.backoff_seconds,
            "latency_ms": result.latency_ms,
            "fallback_used": result.fallback_used,
            "fallback_reason": result.fallback_reason,
            "circuit_open": result.circuit_open,
            "providers_tried": result.providers_tried,
            "is_repair": is_repair,
            "outcome": "ok",
            "error_type": None,
            "at": _now_iso(),
        }
    return {
        "purpose": request.purpose,
        "section_index": section_index,
        "provider": None,
        "model": None,
        "attempt": None,
        "attempts": None,
        "backoff_seconds": None,
        "latency_ms": None,
        "fallback_used": False,
        "fallback_reason": None,
        "circuit_open": False,
        "providers_tried": [],
        "is_repair": is_repair,
        "outcome": "error",
        "error_type": type(exc).__name__ if exc is not None else None,
        "at": _now_iso(),
    }


async def _call_router(
    db,
    job_id: str,
    router: "AIRouter",
    request: GenerationRequest,
    *,
    section_index: int | None,
    is_repair: bool,
    adapter: TypeAdapter | None = None,
) -> GenerationResult:
    """Call `router.generate`, then record Task 14.2 telemetry for it inside a
    short `write_transaction` of its own -- the transaction never spans the
    actual inference call itself (task-14.2.md: "Holding any transaction across a
    router call" is explicitly forbidden). On a `ProviderError`, the call is
    still recorded (`outcome="error"`) before re-raising, so the orchestrator's
    `except ProviderError` handler can fail the job with a specific error_code.

    Task 18.6 item 4 (rename to `is_cloud_result` in 18.8): when `adapter` is
    given, a cloud-served result (`router.is_cloud_result(result)`) that fails
    validation against it gets one local retry (`router.generate_on_fallback`)
    before being recorded --
    marked `fallback_used=True, fallback_reason="SchemaValidationError"`, the
    same shape the router's own internal primary-failure fallback already
    produces. This is a look-ahead pre-check only: the caller's own existing
    post-call `parse_and_validate(result.text, adapter)` is unchanged and
    still runs afterward to get the actual parsed value."""
    try:
        result = await router.generate(request)
    except ProviderError as exc:
        async with write_transaction(db):
            await ai_job_service.record_generation_call(
                db, job_id,
                _call_record(request, section_index=section_index, is_repair=is_repair, exc=exc),
                commit=False,
            )
        raise

    if adapter is not None and router.is_cloud_result(result):
        try:
            parse_and_validate(result.text, adapter)
        except SchemaValidationError:
            try:
                result = await router.generate_on_fallback(request)
            except ProviderError as exc:
                async with write_transaction(db):
                    await ai_job_service.record_generation_call(
                        db, job_id,
                        _call_record(request, section_index=section_index, is_repair=is_repair, exc=exc),
                        commit=False,
                    )
                raise
            result.fallback_used = True
            result.fallback_reason = "SchemaValidationError"

    async with write_transaction(db):
        await ai_job_service.record_generation_call(
            db, job_id,
            _call_record(request, section_index=section_index, is_repair=is_repair, result=result),
            commit=False,
        )
    return result


async def _update_progress(db, job_id: str, stage: str, progress: int) -> None:
    async with write_transaction(db):
        await ai_job_service.update_progress(db, job_id, stage, progress, commit=False)


async def _fail(db, job_id: str, error_code: str, errors: list[str]) -> None:
    async with write_transaction(db):
        await ai_job_service.transition_status(
            db, job_id, "error", error_code=error_code, error_message="; ".join(errors)[:200], commit=False
        )


async def _fail_provider(db, job_id: str, exc: ProviderError) -> None:
    """Fail the job with a specific `provider_*` error_code (Task 14.2) instead of
    letting a `ProviderError` propagate to the worker's blanket `except` and land
    as an indistinguishable `handler_exception`."""
    error_code = ai_job_service.provider_error_code(exc)
    message = f"{type(exc).__name__}: {exc}"[:200]
    async with write_transaction(db):
        await ai_job_service.transition_status(
            db, job_id, "error", error_code=error_code, error_message=message, commit=False
        )


async def _cancel(db, job_id: str) -> None:
    async with write_transaction(db):
        await ai_job_service.transition_status(db, job_id, "cancelled", commit=False)


async def _is_cancelled(db, job_id: str, project_id: str) -> bool:
    fresh = await ai_job_service.get_job(db, job_id, project_id)
    return bool(fresh["cancel_requested"])


def make_handler(router: "AIRouter") -> "JobHandler":
    """Build the `ai_worker.register_handler("script", ...)` handler for `router`."""

    async def _handler(job: dict, worker: "AIWorker") -> None:
        await _run_script_job(job, worker, router)

    return _handler


async def _run_script_job(job: dict, worker: "AIWorker", router: "AIRouter") -> None:
    """Implements the controlling plan's 8-step checkpointed script pipeline."""
    db = worker.get_db()
    job_id = job["id"]
    project_id = job["project_id"]

    async with read_transaction():
        project = await project_service.get_project(db, project_id)

    if compute_config_hash(project, job["operation"]) != job["config_hash"]:
        async with write_transaction(db):
            await ai_job_service.mark_stale(db, job_id, commit=False)
        return
    if await _is_cancelled(db, job_id, project_id):
        await _cancel(db, job_id)
        return

    known_speaker_ids = {speaker["id"] for speaker in project["speakers"]}
    num_speakers = len(project["speakers"])
    target_words = compute_target_words(project["cefr_level"], project["duration_minutes"])
    section_budgets = plan_sections(target_words, project["cefr_level"])

    async with read_transaction():
        existing = await ai_job_service.get_valid_checkpoints(db, job_id)
    checkpoints_by_index = {checkpoint["section_index"]: checkpoint for checkpoint in existing}

    await _update_progress(db, job_id, "outline", 5)

    if 0 in checkpoints_by_index:
        outline = ScriptOutline.model_validate_json(checkpoints_by_index[0]["result_json"])
    else:
        try:
            outline = await _generate_outline(router, project, target_words, len(section_budgets), db, job_id)
        except ProviderError as exc:
            await _fail_provider(db, job_id, exc)
            return
        async with write_transaction(db):
            await ai_job_service.save_checkpoint(
                db, job_id, 0, "outline", "valid",
                compute_config_hash(project, "outline"),
                result_json=outline.model_dump_json(), commit=False,
            )

    all_lines: list[SectionLineOut] = []
    prior_summary = ""
    total_sections = len(outline.sections)

    # Task 14.3 item 7 (resume): recompute carry/words_so_far from already-
    # checkpointed sections -- a no-op loop for a fresh job. Reads each
    # checkpoint's stored `target_effective` rather than replaying nominal
    # targets, so a resumed run reaches the exact same carry (and therefore the
    # same total) an uninterrupted run would have -- see task-14.3.md's
    # "Resume/carry" decision for the equivalence argument (PM-reviewed).
    carry = 0.0
    words_so_far = 0
    for position, section_spec in enumerate(outline.sections, start=1):
        idx = section_spec.index
        if idx == 0 or idx not in checkpoints_by_index:
            continue
        checkpoint = checkpoints_by_index[idx]
        cp_lines = _SECTION_LINES_ADAPTER.validate_json(checkpoint["result_json"])
        cp_words = section_word_count(cp_lines)
        try:
            cp_metrics = json.loads(checkpoint["metrics_json"])
        except (TypeError, ValueError):
            cp_metrics = {}
        cp_effective = cp_metrics.get("target_effective", section_spec.target_words)
        carry += cp_effective - cp_words
        words_so_far += cp_words

    for position, section_spec in enumerate(outline.sections, start=1):
        idx = section_spec.index
        is_last = position == total_sections
        if idx != 0 and idx in checkpoints_by_index:
            section_lines = _SECTION_LINES_ADAPTER.validate_json(checkpoints_by_index[idx]["result_json"])
            all_lines.extend(section_lines)
            prior_summary = summarize_section(section_lines)
            continue

        if await _is_cancelled(db, job_id, project_id):
            await _cancel(db, job_id)
            return

        nominal = section_spec.target_words
        effective_target = (
            compute_last_section_effective_target(nominal, target_words, words_so_far)
            if is_last
            else compute_section_effective_target(nominal, carry)
        )

        # Task 14.13: episode-so-far's most-repeated 8-grams, computed fresh each
        # iteration from everything generated up to this point, so the model gets
        # a proactive heads-up before generating -- not just the reactive repair.
        avoid_phrases = frequent_repeated_phrases(
            [normalize_text(word) for line in all_lines for word in _WORD_RE.findall(line.text)]
        )

        result = await _run_section_pipeline(
            router, project, outline, section_spec, effective_target, prior_summary,
            avoid_phrases, known_speaker_ids, is_last, db, job_id,
        )
        if result is None:
            return
        section_lines, checkpoint_metrics = result

        async with write_transaction(db):
            await ai_job_service.save_checkpoint(
                db, job_id, idx, "section", "valid",
                compute_config_hash({"section": section_spec.model_dump()}, "section"),
                result_json=_SECTION_LINES_ADAPTER.dump_json(section_lines).decode("utf-8"),
                metrics_json=json.dumps(checkpoint_metrics),
                commit=False,
            )
        all_lines.extend(section_lines)
        prior_summary = summarize_section(section_lines)
        if not is_last:
            carry += effective_target - checkpoint_metrics["words"]
        words_so_far += checkpoint_metrics["words"]
        await _update_progress(db, job_id, f"section_{idx}", 10 + round(80 * position / total_sections))
        await worker.heartbeat(job_id)

    async with write_transaction(db):
        await ai_job_service.transition_status(db, job_id, "validating", commit=False)

    hard_errors, _warnings = validate_global(
        all_lines, target_words, known_speaker_ids, num_speakers, project["topic"]
    )

    # Task 17.1 (ENH-010): one shared, ordered, two-slot loop. Budget is checked
    # before repetition on every pass, but each repair type can only ever fire
    # once (its own existing cap constant) -- this reproduces both Gate B-7
    # failure shapes from one mechanism: a mixed-from-the-start failure gets
    # budget-then-repetition (in that order); a repetition-only failure whose
    # own repair inflates length afterward (the actual B-7 run-1 bug) finds the
    # budget slot still unused on the next pass, since its condition never
    # matched while the failure was still repetition-only. Worst case: one
    # budget-repair attempt (a generate + in-loop repair(s) via
    # `_run_section_pipeline`, both directions -- Task 17.4) plus one
    # repetition-repair attempt -- see task-17.1.md's design for the exact
    # worst-case model-call accounting (unchanged at 4 by Task 17.4).
    budget_repair_used = False
    repetition_repair_used = False

    for _ in range(2):
        if not hard_errors:
            break

        if _has_budget_error(hard_errors) and not budget_repair_used and SCRIPT_PIPELINE_MAX_GLOBAL_BUDGET_REPAIRS > 0:
            budget_repair_used = True
            total_words = section_word_count(all_lines)
            section_checkpoints = await _load_section_checkpoints(db, job_id)
            target = _worst_budget_section(section_checkpoints, outline, total_words, target_words)
            if target is not None:
                worst_spec = next(spec for spec in outline.sections if spec.index == target.section_index)

                # Task 17.1, C3/C4, extended to "under" by Task 17.4: a bare
                # fresh regeneration alone lands at a median 0.60x its target
                # (evidence: plan Amendment B); rerunning the *full*
                # per-section path (generate -> repair -> in-loop length
                # repair) lands at a median 1.02x -- the calibrated tool, not
                # a new one, and it's exactly the main loop's own per-section
                # pipeline, reused via `_run_section_pipeline`. Gate B-8 found
                # "under"'s old plain-repair path overshooting to 2.1x target
                # (91 -> 505 words against a 238 target, task-17.4.md) --
                # the in-loop length repair this path already has is exactly
                # what self-corrects that kind of overshoot for "over", so it
                # applies unconditionally now, not just when direction == "over".
                position = next(
                    i for i, spec in enumerate(outline.sections, start=1) if spec.index == target.section_index
                )
                is_last_target = position == total_sections
                if position == 1:
                    prior_summary_for_target = ""
                else:
                    preceding_spec = outline.sections[position - 2]
                    preceding_checkpoint = section_checkpoints.get(preceding_spec.index)
                    preceding_lines = (
                        _SECTION_LINES_ADAPTER.validate_json(preceding_checkpoint["result_json"])
                        if preceding_checkpoint is not None
                        else []
                    )
                    prior_summary_for_target = summarize_section(preceding_lines)
                # Task 17.1, C4: computed from the OTHER sections, never [].
                avoid_phrases_for_target = frequent_repeated_phrases([
                    normalize_text(word)
                    for other_index, other_checkpoint in section_checkpoints.items()
                    if other_index != target.section_index
                    for other_line in _SECTION_LINES_ADAPTER.validate_json(other_checkpoint["result_json"])
                    for word in _WORD_RE.findall(other_line.text)
                ])
                rerun = await _run_section_pipeline(
                    router, project, outline, worst_spec, target.new_target, prior_summary_for_target,
                    avoid_phrases_for_target, known_speaker_ids, is_last_target, db, job_id,
                )
                if rerun is None:
                    return
                new_lines, new_metrics = rerun
                new_metrics = {**new_metrics, "global_budget_repaired": True, "global_budget_direction": target.direction}

                async with write_transaction(db):
                    await ai_job_service.save_checkpoint(
                        db, job_id, target.section_index, "section", "valid",
                        compute_config_hash({"section": worst_spec.model_dump()}, "section"),
                        result_json=_SECTION_LINES_ADAPTER.dump_json(new_lines).decode("utf-8"),
                        metrics_json=json.dumps(new_metrics),
                        commit=False,
                    )
                all_lines = []
                for section_spec in outline.sections:
                    if section_spec.index == target.section_index:
                        all_lines.extend(new_lines)
                        continue
                    checkpoint = section_checkpoints.get(section_spec.index)
                    if checkpoint is not None:
                        all_lines.extend(_SECTION_LINES_ADAPTER.validate_json(checkpoint["result_json"]))
                hard_errors, _warnings = validate_global(
                    all_lines, target_words, known_speaker_ids, num_speakers, project["topic"]
                )
            continue

        if (
            _has_repetition_error(hard_errors)
            and not repetition_repair_used
            and SCRIPT_PIPELINE_MAX_REPETITION_REPAIRS > 0
        ):
            # Task 14.13 (D17), now length-aware (Task 17.1, required behaviour
            # #2): one repair of the single worst section by repeated-gram
            # occurrence count.
            repetition_repair_used = True
            section_checkpoints = await _load_section_checkpoints(db, job_id)
            ordered_sections: list[tuple[int, list[SectionLineOut]]] = []
            for section_spec in outline.sections:
                checkpoint = section_checkpoints.get(section_spec.index)
                if checkpoint is not None:
                    ordered_sections.append(
                        (section_spec.index, _SECTION_LINES_ADAPTER.validate_json(checkpoint["result_json"]))
                    )

            repeated_grams, per_section_counts = find_repeated_8grams_by_section(ordered_sections)
            if per_section_counts:
                worst_index = max(per_section_counts, key=per_section_counts.get)
                worst_checkpoint = section_checkpoints[worst_index]
                worst_lines = _SECTION_LINES_ADAPTER.validate_json(worst_checkpoint["result_json"])
                try:
                    worst_metrics = json.loads(worst_checkpoint["metrics_json"])
                except (TypeError, ValueError):
                    worst_metrics = {}
                if not isinstance(worst_metrics, dict):
                    worst_metrics = {}
                worst_spec = next(spec for spec in outline.sections if spec.index == worst_index)
                effective_target = worst_metrics.get("target_effective", worst_spec.target_words)
                worst_effective_spec = worst_spec.model_copy(update={"target_words": effective_target})
                repeated_phrases = [" ".join(gram) for gram in repeated_grams]
                # Task 17.1, required behaviour #2: an explicit checklist entry,
                # not just the ambient target/delta context repair.txt already
                # renders unconditionally -- Gate B-7 run 1's evidence is that a
                # repetition repair silently inflated length past this same range.
                min_words = round(effective_target * (1 - SCRIPT_SECTION_WORD_TOLERANCE))
                max_words = round(effective_target * (1 + SCRIPT_SECTION_WORD_TOLERANCE))
                length_note = (
                    f"keep this section's length between {min_words} and {max_words} words "
                    f"(target {effective_target}) while removing the repetition -- do not let fixing "
                    "the repetition push the length outside this range"
                )

                try:
                    new_worst_lines, structural_errors, _budget_errors = await _repair_section(
                        router, project, worst_effective_spec, worst_lines,
                        [f'repeated phrase used elsewhere in the script: "{phrase}"' for phrase in repeated_phrases]
                        + [length_note],
                        known_speaker_ids, db, job_id,
                        purpose="script_section_repetition_repair",
                    )
                except ProviderError as exc:
                    await _fail_provider(db, job_id, exc)
                    return
                if structural_errors:
                    await _fail(db, job_id, "section_validation_failed", structural_errors)
                    return

                new_words = section_word_count(new_worst_lines)
                async with write_transaction(db):
                    await ai_job_service.save_checkpoint(
                        db, job_id, worst_index, "section", "valid",
                        compute_config_hash({"section": worst_spec.model_dump()}, "section"),
                        result_json=_SECTION_LINES_ADAPTER.dump_json(new_worst_lines).decode("utf-8"),
                        metrics_json=json.dumps({**worst_metrics, "words": new_words, "repetition_repaired": True}),
                        commit=False,
                    )

                all_lines = []
                for section_index, lines in ordered_sections:
                    all_lines.extend(new_worst_lines if section_index == worst_index else lines)

                hard_errors, _warnings = validate_global(
                    all_lines, target_words, known_speaker_ids, num_speakers, project["topic"]
                )
            continue

        break

    if hard_errors:
        await _fail(db, job_id, "global_validation_failed", hard_errors)
        return

    async with read_transaction():
        final_project = await project_service.get_project(db, project_id)
    if compute_config_hash(final_project, job["operation"]) != job["config_hash"]:
        async with write_transaction(db):
            await ai_job_service.mark_stale(db, job_id, commit=False)
        return
    if await _is_cancelled(db, job_id, project_id):
        await _cancel(db, job_id)
        return

    server_lines = [
        {
            "speaker_id": line.speaker_id,
            "text": line.text,
            "language_notes": line.language_notes.model_dump(),
        }
        for line in all_lines
    ]
    async with write_transaction(db):
        await script_service.save_script(db, project_id, server_lines, known_speaker_ids, commit=False)
        await project_service.mark_script_changed(db, project_id, commit=False)
        await ai_job_service.transition_status(db, job_id, "complete", commit=False)
