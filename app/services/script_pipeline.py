"""Checkpointed script generation pipeline (Phase 13, Task 13.4).

Replaces one long synchronous Gemini call with outline -> validated 1-2 minute
sections -> global merge, checkpointing each valid section so an interrupted job
resumes instead of restarting. Runs as an `ai_worker` "script" operation handler;
`app/main.py` wiring is deferred to Task 13.6 (not in this task's allowed files —
see task-13.4.md).
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import re
from collections import Counter
from datetime import datetime, timezone
from typing import TYPE_CHECKING

from jinja2 import Environment, FileSystemLoader, StrictUndefined, TemplateNotFound
from pydantic import BaseModel, Field, TypeAdapter

from app.core.config import settings
from app.core.constants import (
    CEFR_WORDS_PER_MINUTE,
    SCRIPT_GLOBAL_WORD_TOLERANCE,
    SCRIPT_MAX_CONSECUTIVE_LINES_PER_SPEAKER,
    SCRIPT_MAX_REPEATED_8GRAM_RATIO,
    SCRIPT_SECTION_TARGET_MINUTES,
    SCRIPT_SECTION_WORD_TOLERANCE,
    SCRIPT_SPEAKER_BALANCE_MAX_SHARE,
    SCRIPT_SPEAKER_BALANCE_MIN_SHARE,
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

_env = Environment(
    loader=FileSystemLoader(str(SCRIPT_PROMPTS_DIR)),
    undefined=StrictUndefined,
    trim_blocks=True,
    lstrip_blocks=True,
)
_WORD_RE = re.compile(r"\S+")


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


_OUTLINE_ADAPTER = TypeAdapter(ScriptOutline)
_SECTION_LINES_ADAPTER = TypeAdapter(list[SectionLineOut])


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


def repeated_8gram_ratio(words: list[str]) -> float:
    """Fraction of 8-word sliding windows that repeat elsewhere in `words`."""
    if len(words) < 8:
        return 0.0
    grams = [tuple(words[i : i + 8]) for i in range(len(words) - 7)]
    counts = Counter(grams)
    repeated = sum(count for count in counts.values() if count > 1)
    return repeated / len(grams)


def validate_section(
    lines: list[SectionLineOut], target_words: int, known_speaker_ids: set[str]
) -> list[str]:
    """Hard checks for one generated section. Empty list means valid."""
    errors: list[str] = []
    if not lines:
        return ["section has no lines"]

    total_words = sum(len(_WORD_RE.findall(line.text)) for line in lines)
    tolerance = target_words * SCRIPT_SECTION_WORD_TOLERANCE
    if not (target_words - tolerance <= total_words <= target_words + tolerance):
        errors.append(
            f"section word count {total_words} is outside "
            f"±{int(SCRIPT_SECTION_WORD_TOLERANCE * 100)}% of target {target_words}"
        )

    unknown = {line.speaker_id for line in lines} - known_speaker_ids
    if unknown:
        errors.append(f"unknown speaker_id(s): {sorted(unknown)}")

    if len(known_speaker_ids) > 1:
        consecutive = 1
        for previous, current in zip(lines, lines[1:], strict=False):
            if previous.speaker_id == current.speaker_id:
                consecutive += 1
                if consecutive > SCRIPT_MAX_CONSECUTIVE_LINES_PER_SPEAKER:
                    errors.append(
                        f"more than {SCRIPT_MAX_CONSECUTIVE_LINES_PER_SPEAKER} "
                        "consecutive lines from one speaker"
                    )
                    break
            else:
                consecutive = 1

    return errors


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
            f"total word count {total_words} is outside "
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
        section_index=None, is_repair=False,
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
) -> tuple[list[SectionLineOut], list[str]]:
    cefr_constraints = await load_cefr_block(project["cefr_level"])
    prompt = await _render(
        "section.txt",
        topic=project["topic"],
        genre=project["genre"],
        cefr_level=project["cefr_level"],
        outline_title=outline.title,
        section_index=section_spec.index,
        section_count=len(outline.sections),
        objective=section_spec.objective,
        target_words=section_spec.target_words,
        prior_summary=prior_summary,
        is_last_section=is_last_section,
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
            json_schema=_SECTION_LINES_ADAPTER.json_schema(),
            deadline_seconds=settings.AI_REQUEST_DEADLINE_SECONDS,
            purpose="script_section",
        ),
        section_index=section_spec.index, is_repair=False,
    )
    try:
        lines = parse_and_validate(result.text, _SECTION_LINES_ADAPTER)
    except SchemaValidationError as exc:
        return [], [str(exc)]
    return lines, validate_section(lines, section_spec.target_words, known_speaker_ids)


async def _repair_section(
    router: "AIRouter",
    project: dict,
    section_spec: OutlineSectionSpec,
    previous_lines: list[SectionLineOut],
    errors: list[str],
    known_speaker_ids: set[str],
    db,
    job_id: str,
) -> tuple[list[SectionLineOut], list[str]]:
    previous_output = (
        _SECTION_LINES_ADAPTER.dump_json(previous_lines).decode("utf-8") if previous_lines else "[]"
    )
    prompt = await _render(
        "repair.txt",
        objective=section_spec.objective,
        target_words=section_spec.target_words,
        speakers=project["speakers"],
        errors=errors,
        previous_output=previous_output,
    )
    result = await _call_router(
        db, job_id, router,
        GenerationRequest(
            prompt=prompt,
            json_schema=_SECTION_LINES_ADAPTER.json_schema(),
            deadline_seconds=settings.AI_REQUEST_DEADLINE_SECONDS,
            purpose="script_section_repair",
        ),
        section_index=section_spec.index, is_repair=True,
    )
    try:
        lines = parse_and_validate(result.text, _SECTION_LINES_ADAPTER)
    except SchemaValidationError as exc:
        return [], [str(exc)]
    return lines, validate_section(lines, section_spec.target_words, known_speaker_ids)


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
            "circuit_open": result.circuit_open,
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
        "circuit_open": False,
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
) -> GenerationResult:
    """Call `router.generate`, then record Task 14.2 telemetry for it inside a
    short `write_transaction` of its own -- the transaction never spans the
    actual inference call itself (task-14.2.md: "Holding any transaction across a
    router call" is explicitly forbidden). On a `ProviderError`, the call is
    still recorded (`outcome="error"`) before re-raising, so the orchestrator's
    `except ProviderError` handler can fail the job with a specific error_code."""
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

    for position, section_spec in enumerate(outline.sections, start=1):
        idx = section_spec.index
        if idx != 0 and idx in checkpoints_by_index:
            section_lines = _SECTION_LINES_ADAPTER.validate_json(checkpoints_by_index[idx]["result_json"])
            all_lines.extend(section_lines)
            prior_summary = summarize_section(section_lines)
            continue

        if await _is_cancelled(db, job_id, project_id):
            await _cancel(db, job_id)
            return

        try:
            section_lines, errors = await _generate_section(
                router, project, outline, section_spec, prior_summary, known_speaker_ids,
                position == total_sections, db, job_id,
            )
        except ProviderError as exc:
            await _fail_provider(db, job_id, exc)
            return

        repaired = False
        words_before_repair: int | None = None
        errors_before_repair = 0
        if errors:
            errors_before_repair = len(errors)
            words_before_repair = section_word_count(section_lines)
            try:
                section_lines, errors = await _repair_section(
                    router, project, section_spec, section_lines, errors, known_speaker_ids, db, job_id,
                )
            except ProviderError as exc:
                await _fail_provider(db, job_id, exc)
                return
            repaired = True
        if errors:
            await _fail(db, job_id, "section_validation_failed", errors)
            return

        words = section_word_count(section_lines)
        target_nominal = section_spec.target_words
        checkpoint_metrics = {
            "target_nominal": target_nominal,
            "target_effective": target_nominal,  # unchanged until Task 14.3
            "words": words,
            "deviation_pct": round((words - target_nominal) / target_nominal, 4),
            "repaired": repaired,
            "words_before_repair": words_before_repair,
            "errors_before_repair": errors_before_repair,
        }
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
        await _update_progress(db, job_id, f"section_{idx}", 10 + round(80 * position / total_sections))
        await worker.heartbeat(job_id)

    async with write_transaction(db):
        await ai_job_service.transition_status(db, job_id, "validating", commit=False)

    hard_errors, _warnings = validate_global(
        all_lines, target_words, known_speaker_ids, num_speakers, project["topic"]
    )
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
