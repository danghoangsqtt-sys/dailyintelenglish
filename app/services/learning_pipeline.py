"""Grounded learning-content pipeline (Phase 13, Task 13.5).

Generates the full Learning Content pack in one call (unlike the script
pipeline's per-section checkpointing -- a learning pack has no natural
sub-section boundary), validates it against the persisted script, repairs once
on failure, and publishes atomically. Runs as an `ai_worker` "learning"
operation handler; `app/main.py` wiring is deferred to Task 13.6, same as the
script pipeline (see task-13.4.md/task-13.5.md).
"""

from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from typing import TYPE_CHECKING

from jinja2 import Environment, FileSystemLoader, StrictUndefined, TemplateNotFound
from pydantic import TypeAdapter

from app.core.config import settings
from app.core.constants import (
    LEARNING_GENERATION_TEMPERATURE,
    LEARNING_MAX_GRAMMAR_POINTS,
    LEARNING_MAX_QUESTIONS,
    LEARNING_MIN_GRAMMAR_POINTS,
    LEARNING_MIN_IDIOMS,
    LEARNING_MIN_QUESTIONS,
    LEARNING_MIN_VOCABULARY,
)
from app.core.exceptions import ProviderError, SchemaValidationError
from app.core.prompt_loader import LEARNING_PROMPTS_DIR, render_learning_prompt
from app.db.transactions import read_transaction, write_transaction
from app.models.learning import LearningPackOut
from app.services import ai_job_service, learning_service, project_service, script_service
from app.services.ai.contracts import GenerationRequest, GenerationResult
from app.services.ai.validation import parse_and_validate
from app.services.script_pipeline import compute_config_hash, normalize_text

if TYPE_CHECKING:
    from app.services.ai.router import AIRouter
    from app.services.ai_worker import AIWorker, JobHandler

_env = Environment(
    loader=FileSystemLoader(str(LEARNING_PROMPTS_DIR)),
    undefined=StrictUndefined,
    trim_blocks=True,
    lstrip_blocks=True,
)
_PACK_ADAPTER = TypeAdapter(LearningPackOut)


# --- pure validators (no I/O -- unit-testable directly) ------------------------------


def validate_counts(pack: LearningPackOut) -> list[str]:
    """Requested-count hard checks. Ranges copied from the prompt's own text."""
    errors: list[str] = []
    if len(pack.vocabulary) < LEARNING_MIN_VOCABULARY:
        errors.append(f"vocabulary has {len(pack.vocabulary)} item(s), need at least {LEARNING_MIN_VOCABULARY}")
    if len(pack.idioms) < LEARNING_MIN_IDIOMS:
        errors.append(f"idioms has {len(pack.idioms)} item(s), need at least {LEARNING_MIN_IDIOMS}")
    if not (LEARNING_MIN_GRAMMAR_POINTS <= len(pack.grammar) <= LEARNING_MAX_GRAMMAR_POINTS):
        errors.append(
            f"grammar has {len(pack.grammar)} point(s), need "
            f"{LEARNING_MIN_GRAMMAR_POINTS}-{LEARNING_MAX_GRAMMAR_POINTS}"
        )
    if not (LEARNING_MIN_QUESTIONS <= len(pack.questions) <= LEARNING_MAX_QUESTIONS):
        errors.append(
            f"questions has {len(pack.questions)} item(s), need "
            f"{LEARNING_MIN_QUESTIONS}-{LEARNING_MAX_QUESTIONS}"
        )
    return errors


def validate_grounding(pack: LearningPackOut, transcript: str) -> list[str]:
    """Every quoted example, and every idiom phrase, must genuinely appear in
    the transcript -- normalized substring match, not fuzzy similarity.

    Vocabulary's bare `word` is deliberately not grounding-checked on its own:
    English inflection (plural/tense) makes a strict substring check too
    fragile there. Its actual usage is covered by its `example_sentence` check.
    """
    errors: list[str] = []
    normalized_transcript = normalize_text(transcript)

    for item in pack.vocabulary:
        if normalize_text(item.example_sentence) not in normalized_transcript:
            errors.append(f"vocabulary '{item.word}': example_sentence not found in transcript")

    for item in pack.idioms:
        if normalize_text(item.phrase) not in normalized_transcript:
            errors.append(f"idiom '{item.phrase}': phrase not found in transcript")
        if normalize_text(item.example_sentence) not in normalized_transcript:
            errors.append(f"idiom '{item.phrase}': example_sentence not found in transcript")

    return errors


def validate_duplicates(pack: LearningPackOut) -> list[str]:
    """No duplicate (normalized) vocabulary word, idiom phrase, or question."""
    errors: list[str] = []
    words = [normalize_text(item.word) for item in pack.vocabulary]
    if len(words) != len(set(words)):
        errors.append("duplicate vocabulary word(s) found")
    phrases = [normalize_text(item.phrase) for item in pack.idioms]
    if len(phrases) != len(set(phrases)):
        errors.append("duplicate idiom phrase(s) found")
    questions = [normalize_text(item.question) for item in pack.questions]
    if len(questions) != len(set(questions)):
        errors.append("duplicate question(s) found")
    return errors


def validate_answers(pack: LearningPackOut) -> list[str]:
    """MCQ correct_answer must be one of its own options; open-ended is exempt."""
    errors: list[str] = []
    for item in pack.questions:
        if not item.options:
            continue  # open-ended -- no options/correct_answer contract to check
        normalized_options = {normalize_text(option) for option in item.options}
        if normalize_text(item.correct_answer) not in normalized_options:
            errors.append(f"question '{item.question[:40]}...': correct_answer not among its options")
    return errors


def validate_pack(pack: LearningPackOut, transcript: str) -> list[str]:
    """All hard checks combined. Empty list means the pack is valid."""
    return (
        validate_counts(pack)
        + validate_grounding(pack, transcript)
        + validate_duplicates(pack)
        + validate_answers(pack)
    )


def find_removable_failures(pack: LearningPackOut, transcript: str) -> list[dict]:
    """Task 14.11 (D15): a structured view over the same grounding/answer checks
    `validate_grounding`/`validate_answers` already do, but naming exactly which
    item fails instead of a prose message -- so the post-repair removal step can
    drop precisely that item. `validate_counts`/`validate_duplicates` failures have
    no single item to blame and are never represented here (per D15, only
    grounding/answer-consistency failures are removable)."""
    removable: list[dict] = []
    normalized_transcript = normalize_text(transcript)

    for item in pack.vocabulary:
        if normalize_text(item.example_sentence) not in normalized_transcript:
            removable.append(
                {"kind": "vocabulary", "key": item.word, "reason": "example_sentence not found in transcript"}
            )

    for item in pack.idioms:
        if (
            normalize_text(item.phrase) not in normalized_transcript
            or normalize_text(item.example_sentence) not in normalized_transcript
        ):
            removable.append(
                {"kind": "idiom", "key": item.phrase, "reason": "phrase or example_sentence not found in transcript"}
            )

    for item in pack.questions:
        if item.options and normalize_text(item.correct_answer) not in {
            normalize_text(option) for option in item.options
        }:
            removable.append(
                {"kind": "question", "key": item.question, "reason": "correct_answer not among its options"}
            )

    return removable


def drop_items(pack: LearningPackOut, removable: list[dict]) -> LearningPackOut:
    """Task 14.11 (D15): a new pack with every item named in `removable` removed.
    Grammar is never touched -- no per-item grammar check exists in
    `find_removable_failures`, so nothing ever names a grammar point here."""
    dropped_vocab = {item["key"] for item in removable if item["kind"] == "vocabulary"}
    dropped_idioms = {item["key"] for item in removable if item["kind"] == "idiom"}
    dropped_questions = {item["key"] for item in removable if item["kind"] == "question"}
    return pack.model_copy(
        update={
            "vocabulary": [item for item in pack.vocabulary if item.word not in dropped_vocab],
            "idioms": [item for item in pack.idioms if item.phrase not in dropped_idioms],
            "questions": [item for item in pack.questions if item.question not in dropped_questions],
        }
    )


# --- prompt rendering (this module's own Jinja env for the new repair template) -------


def _render_repair_prompt_sync(**context: object) -> str:
    try:
        template = _env.get_template("learning_repair.txt")
    except TemplateNotFound as exc:
        raise SchemaValidationError(f"Prompt template not found: {exc}") from exc
    return template.render(**context)


async def _render_repair_prompt(**context: object) -> str:
    return await asyncio.to_thread(_render_repair_prompt_sync, **context)


# --- provider calls --------------------------------------------------------------------


async def _generate_pack(router: "AIRouter", project: dict, transcript: str, db, job_id: str) -> LearningPackOut:
    prompt = await render_learning_prompt(
        topic=project["topic"], cefr_level=project["cefr_level"], genre=project["genre"], transcript_text=transcript
    )
    result = await _call_router(
        db, job_id, router,
        GenerationRequest(
            prompt=prompt,
            json_schema=LearningPackOut.model_json_schema(),
            temperature=LEARNING_GENERATION_TEMPERATURE,
            deadline_seconds=settings.AI_REQUEST_DEADLINE_SECONDS,
            purpose="learning_pack",
        ),
        is_repair=False,
    )
    return parse_and_validate(result.text, _PACK_ADAPTER)


async def _repair_pack(
    router: "AIRouter", transcript: str, previous_pack: LearningPackOut, errors: list[str], db, job_id: str
) -> LearningPackOut:
    prompt = await _render_repair_prompt(
        transcript_text=transcript,
        errors=errors,
        previous_output=previous_pack.model_dump_json(),
    )
    result = await _call_router(
        db, job_id, router,
        GenerationRequest(
            prompt=prompt,
            json_schema=LearningPackOut.model_json_schema(),
            temperature=LEARNING_GENERATION_TEMPERATURE,
            deadline_seconds=settings.AI_REQUEST_DEADLINE_SECONDS,
            purpose="learning_pack_repair",
        ),
        is_repair=True,
    )
    return parse_and_validate(result.text, _PACK_ADAPTER)


# --- orchestration -----------------------------------------------------------------------


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _call_record(
    request: GenerationRequest,
    *,
    is_repair: bool,
    result: GenerationResult | None = None,
    exc: ProviderError | None = None,
) -> dict:
    """Build one Task 14.2 telemetry call record -- safe fields only, never
    prompt/response text or a key (plan §4.2's call record shape). The learning
    pipeline has no section concept, so `section_index` is always `None`."""
    if result is not None:
        return {
            "purpose": request.purpose,
            "section_index": None,
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
        "section_index": None,
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
    db, job_id: str, router: "AIRouter", request: GenerationRequest, *, is_repair: bool,
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
                db, job_id, _call_record(request, is_repair=is_repair, exc=exc), commit=False
            )
        raise
    async with write_transaction(db):
        await ai_job_service.record_generation_call(
            db, job_id, _call_record(request, is_repair=is_repair, result=result), commit=False
        )
    return result


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
    """Build the `ai_worker.register_handler("learning", ...)` handler for `router`."""

    async def _handler(job: dict, worker: "AIWorker") -> None:
        await _run_learning_job(job, worker, router)

    return _handler


async def _run_learning_job(job: dict, worker: "AIWorker", router: "AIRouter") -> None:
    """Implements the controlling plan's grounded learning pipeline (section 6)."""
    db = worker.get_db()
    job_id = job["id"]
    project_id = job["project_id"]

    async with read_transaction():
        project = await project_service.get_project(db, project_id)
        script_lines = await script_service.get_script(db, project_id)

    if compute_config_hash(project, job["operation"]) != job["config_hash"]:
        async with write_transaction(db):
            await ai_job_service.mark_stale(db, job_id, commit=False)
        return
    if await _is_cancelled(db, job_id, project_id):
        await _cancel(db, job_id)
        return

    if not script_lines:
        await _fail(db, job_id, "script_empty", ["cannot generate learning content: script is empty"])
        return

    # This run's own start-of-processing baseline -- see task-13.5.md's "real gap"
    # note: ai_generation_jobs.script_hash_at_start is never populated by the job
    # creation route (out of this task's allowed files), so this pipeline tracks
    # its own before/after hash instead of trusting that DB column.
    script_hash_at_start = learning_service.compute_script_hash(script_lines)
    transcript = "\n".join(line["text"] for line in script_lines)

    try:
        pack = await _generate_pack(router, project, transcript, db, job_id)
    except SchemaValidationError as exc:
        await _fail(db, job_id, "pack_invalid_schema", [str(exc)])
        return
    except ProviderError as exc:
        await _fail_provider(db, job_id, exc)
        return

    dropped_items: list[dict] = []
    errors = validate_pack(pack, transcript)
    if errors:
        try:
            repaired_pack = await _repair_pack(router, transcript, pack, errors, db, job_id)
        except SchemaValidationError as exc:
            await _fail(db, job_id, "pack_invalid_schema", [str(exc)])
            return
        except ProviderError as exc:
            await _fail_provider(db, job_id, exc)
            return
        repaired_errors = validate_pack(repaired_pack, transcript)
        if repaired_errors:
            # Task 14.11 (D15): drop items that still fail grounding/answer checks
            # rather than failing the whole pack outright -- but only when dropping
            # can actually help. A duplicate or a count-only failure has no single
            # item to blame (find_removable_failures never names one for those), so
            # it still hard-fails exactly as before.
            removable = find_removable_failures(repaired_pack, transcript)
            if not removable:
                await _fail(db, job_id, "pack_validation_failed", repaired_errors)
                return
            reduced_pack = drop_items(repaired_pack, removable)
            final_errors = validate_pack(reduced_pack, transcript)
            if final_errors:
                dropped_summary = [
                    f"dropped {item['kind']} {item['key']!r}: {item['reason']}" for item in removable
                ]
                await _fail(db, job_id, "pack_validation_failed", [*final_errors, *dropped_summary])
                return
            repaired_pack = reduced_pack
            dropped_items = removable
        pack = repaired_pack

    async with write_transaction(db):
        await ai_job_service.transition_status(db, job_id, "validating", commit=False)
        if dropped_items:
            await ai_job_service.set_job_metric(db, job_id, "dropped_items", dropped_items, commit=False)

    async with read_transaction():
        current_script_lines = await script_service.get_script(db, project_id)
        current_project = await project_service.get_project(db, project_id)

    if compute_config_hash(current_project, job["operation"]) != job["config_hash"]:
        async with write_transaction(db):
            await ai_job_service.mark_stale(db, job_id, commit=False)
        return
    if learning_service.compute_script_hash(current_script_lines) != script_hash_at_start:
        async with write_transaction(db):
            await ai_job_service.mark_stale(db, job_id, commit=False)
        return
    if await _is_cancelled(db, job_id, project_id):
        await _cancel(db, job_id)
        return

    async with write_transaction(db):
        await learning_service.save_learning_content(db, project_id, pack.model_dump(), commit=False)
        await ai_job_service.transition_status(db, job_id, "complete", commit=False)
