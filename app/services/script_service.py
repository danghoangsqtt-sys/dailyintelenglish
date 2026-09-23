"""Generates podcast scripts via the AI provider gateway, with schema validation."""

import json
import logging
import uuid

import aiosqlite
from pydantic import BaseModel, Field, TypeAdapter, field_validator

from app.core.config import settings
from app.core.exceptions import (
    NotFoundError,
    ProviderError,
    SchemaValidationError,
    ScriptGenerationError,
    ValidationError,
)
from app.core.prompt_loader import render_regenerate_line_prompt, render_script_prompt
from app.services.ai.contracts import GenerationRequest
from app.services.ai.router import AIRouter, build_ai_router_from_settings
from app.services.ai.validation import parse_and_validate

logger = logging.getLogger(__name__)


class LanguageNotesOut(BaseModel):
    """Structured language notes attached to one generated script line."""

    collocations: list[str] = Field(default_factory=list)
    idioms: list[str] = Field(default_factory=list)
    grammar_point: str = ""


class ScriptLineOut(BaseModel):
    """One validated line of Gemini-generated dialogue."""

    id: str = Field(min_length=1)
    speaker_id: str
    text: str = Field(min_length=1)
    language_notes: LanguageNotesOut = Field(default_factory=LanguageNotesOut)

    @field_validator("speaker_id")
    @classmethod
    def validate_speaker_id_is_uuid(cls, value: str) -> str:
        """speaker_id must be a UUID (see prompts/script/script_base.txt) — never a display name."""
        try:
            uuid.UUID(value)
        except (ValueError, AttributeError, TypeError) as exc:
            raise ValueError(f"speaker_id must be a UUID string, got {value!r}") from exc
        return value


_SCRIPT_LINES_ADAPTER = TypeAdapter(list[ScriptLineOut])
_SINGLE_LINE_ADAPTER = TypeAdapter(ScriptLineOut)


async def generate_script(
    project_id: str, config: dict, router: AIRouter | None = None
) -> list[ScriptLineOut]:
    """Generate a full podcast script for a project via the AI provider gateway.

    Migrated from this module's own duplicated Gemini retry/fallback-model
    transport to `AIRouter` (Phase 13, Task 13.7) -- the prompt, schema, and every
    validation rule below are unchanged; only the transport underneath changed, per
    the same reasoning already applied to `regenerate_line` in Task 13.4. The old
    multi-model `GEMINI_MODEL_FALLBACKS` cascade is deliberately not preserved --
    ADR-001 explicitly rejects "Multiple automatic fallback models" as unpredictable
    in favor of the router's single-model, one-retry, one-fallback policy.

    Args:
        project_id: UUID of the project (used for error context/logging only).
        config: Project-shaped dict as returned by project_service.get_project —
            must include topic, cefr_level, genre, accent, duration_minutes,
            num_speakers, language_features, and speakers (each with a real
            UUID `id`, as persisted in the speakers table).
        router: Injected `AIRouter` (tests pass a `FakeProvider`-backed one with
            zero network calls); defaults to `build_ai_router_from_settings()`.

    Returns:
        Validated list of script lines. Every `speaker_id` is guaranteed to be
        a UUID that belongs to one of `config["speakers"]`.

    Raises:
        ScriptGenerationError: If every provider attempt this mode allows fails,
            the response is malformed/fails schema validation, or a line
            references a speaker_id that isn't one of the project's actual
            speakers. (Phase 18: an unconfigured cloud key/model no longer
            raises here -- `build_ai_router_from_settings()`'s
            `compute_effective_mode` already degrades to local automatically,
            per invariant 32.)
    """
    known_speaker_ids = {speaker["id"] for speaker in config["speakers"]}

    prompt = await render_script_prompt(
        genre=config["genre"],
        cefr_level=config["cefr_level"],
        topic=config["topic"],
        duration_minutes=config["duration_minutes"],
        num_speakers=config["num_speakers"],
        accent=config["accent"],
        speakers=config["speakers"],
        language_features=config["language_features"],
    )

    router = router or build_ai_router_from_settings()
    request = GenerationRequest(
        prompt=prompt,
        json_schema=_SCRIPT_LINES_ADAPTER.json_schema(),
        deadline_seconds=settings.AI_REQUEST_DEADLINE_SECONDS,
        purpose="script_generate_full",
    )
    try:
        result = await router.generate(request)
    except ProviderError as exc:
        raise ScriptGenerationError(f"Script generation failed: {exc}") from exc

    try:
        lines = parse_and_validate(result.text, _SCRIPT_LINES_ADAPTER)
    except SchemaValidationError as exc:
        raise ScriptGenerationError(str(exc)) from exc

    if not lines:
        raise ScriptGenerationError(f"Gemini returned an empty script for project {project_id}")

    unknown_speakers = {line.speaker_id for line in lines} - known_speaker_ids
    if unknown_speakers:
        raise ScriptGenerationError(
            f"Gemini used speaker_id(s) not in project {project_id}: {unknown_speakers}"
        )

    return lines


async def regenerate_line(
    project_id: str,
    config: dict,
    line_id: str,
    current_text: str,
    speaker_id: str,
    router: AIRouter | None = None,
) -> ScriptLineOut:
    """Regenerate a single script line through the Task 13.2 provider gateway.

    Migrated from this module's own `_generate_with_retry`/`_call_gemini` to
    `AIRouter` (Phase 13, Task 13.4) so single-line regeneration participates in
    local/hybrid routing like every other new AI call in this app — the prompt,
    schema, and every validation rule below are unchanged from before the
    migration; only the HTTP transport underneath changed.

    Args:
        project_id: UUID of the project (used for error context/logging only).
        config: Project-shaped dict — see generate_script.
        line_id: The line's existing id (echoed back, not reassigned).
        current_text: The line's current text, given as context to rewrite.
        speaker_id: The UUID of the speaker who must still deliver this line.
        router: Injected `AIRouter` (tests pass a `FakeProvider`-backed one with
            zero network calls); defaults to `build_ai_router_from_settings()`.

    Returns:
        The validated, re-generated line.

    Raises:
        ScriptGenerationError: If the provider gateway fails, returns malformed
            JSON, the response fails schema validation, or changes the speaker
            away from `speaker_id`.
    """
    speaker = next((s for s in config["speakers"] if s["id"] == speaker_id), None)
    if speaker is None:
        raise ScriptGenerationError(f"speaker_id {speaker_id!r} not found in project {project_id}")

    prompt = await render_regenerate_line_prompt(
        genre=config["genre"],
        cefr_level=config["cefr_level"],
        topic=config["topic"],
        speaker=speaker,
        current_text=current_text,
        line_id=line_id,
        speaker_id=speaker_id,
    )

    router = router or build_ai_router_from_settings()
    request = GenerationRequest(
        prompt=prompt,
        json_schema=ScriptLineOut.model_json_schema(),
        deadline_seconds=settings.AI_REQUEST_DEADLINE_SECONDS,
        purpose="script_regenerate_line",
    )
    try:
        result = await router.generate(request)
    except ProviderError as exc:
        raise ScriptGenerationError(f"Line regeneration failed: {exc}") from exc

    try:
        line = parse_and_validate(result.text, _SINGLE_LINE_ADAPTER)
    except SchemaValidationError as exc:
        raise ScriptGenerationError(str(exc)) from exc

    if line.speaker_id != speaker_id:
        raise ScriptGenerationError(
            f"Model changed speaker_id from {speaker_id} to {line.speaker_id}"
        )

    return line


def _row_to_line(row: aiosqlite.Row) -> dict:
    """Convert a script_lines row to a dict, decoding the language_notes JSON blob."""
    line = dict(row)
    line["language_notes"] = json.loads(line["language_notes"]) if line["language_notes"] else None
    return line


async def get_script(db: aiosqlite.Connection, project_id: str) -> list[dict]:
    """List a project's script lines in order.

    Args:
        db: Open aiosqlite connection.
        project_id: UUID of the project.

    Returns:
        Script lines ordered by `line_index` (empty list if none generated yet).
    """
    cursor = await db.execute(
        "SELECT id, line_index, speaker_id, text, language_notes, duration_seconds "
        "FROM script_lines WHERE project_id = ? ORDER BY line_index",
        (project_id,),
    )
    rows = await cursor.fetchall()
    return [_row_to_line(row) for row in rows]


async def get_script_line(db: aiosqlite.Connection, project_id: str, line_id: str) -> dict:
    """Fetch a single script line.

    Raises:
        NotFoundError: If no such line exists for this project.
    """
    cursor = await db.execute(
        "SELECT id, line_index, speaker_id, text, language_notes, duration_seconds "
        "FROM script_lines WHERE project_id = ? AND id = ?",
        (project_id, line_id),
    )
    row = await cursor.fetchone()
    if row is None:
        raise NotFoundError(f"Script line {line_id} not found in project {project_id}")
    return _row_to_line(row)


async def save_script(
    db: aiosqlite.Connection,
    project_id: str,
    lines: list[dict],
    known_speaker_ids: set[str] | None = None,
    commit: bool = True,
) -> list[dict]:
    """Replace all script lines for a project (delete + insert) in the given order.

    Args:
        db: Open aiosqlite connection.
        project_id: UUID of the project.
        lines: Each item must have `speaker_id`, `text`, and optionally `language_notes`.
        known_speaker_ids: If given, every line's speaker_id must be a member —
            used by the PUT /script route to reject edits referencing a
            speaker that doesn't belong to this project.
        commit: If False, skip the commit — the caller is responsible for
            committing (or rolling back) as part of a larger transaction
            (see `app.api.projects`, which also advances project status).

    Returns:
        The saved lines, as get_script would return them.

    Raises:
        ValidationError: If any line's speaker_id isn't in known_speaker_ids.
    """
    if known_speaker_ids is not None:
        unknown = {line["speaker_id"] for line in lines} - known_speaker_ids
        if unknown:
            raise ValidationError(f"Unknown speaker_id(s) for project {project_id}: {unknown}")

    await db.execute("DELETE FROM script_lines WHERE project_id = ?", (project_id,))
    for index, line in enumerate(lines):
        await db.execute(
            "INSERT INTO script_lines (id, project_id, line_index, speaker_id, text, language_notes) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (
                str(uuid.uuid4()),
                project_id,
                index,
                line["speaker_id"],
                line["text"],
                json.dumps(line.get("language_notes") or {}),
            ),
        )
    if commit:
        await db.commit()
    return await get_script(db, project_id)


async def update_script_line(
    db: aiosqlite.Connection,
    project_id: str,
    line_id: str,
    text: str,
    language_notes: dict,
    commit: bool = True,
) -> dict:
    """Update one script line's text/language_notes in place, preserving its position.

    Clears any cached TTS audio for this line, since it was synthesized from the
    text being replaced here and no longer matches.

    Args:
        commit: If False, skip the commit — the caller is responsible for
            committing (or rolling back) as part of a larger transaction.

    Raises:
        NotFoundError: If no such line exists for this project.
    """
    cursor = await db.execute(
        "UPDATE script_lines SET text = ?, language_notes = ?, "
        "audio_cache_path = NULL, duration_seconds = NULL "
        "WHERE id = ? AND project_id = ?",
        (text, json.dumps(language_notes), line_id, project_id),
    )
    if commit:
        await db.commit()
    if cursor.rowcount == 0:
        raise NotFoundError(f"Script line {line_id} not found in project {project_id}")
    return await get_script_line(db, project_id, line_id)
