"""Generates and persists Learning Content packs via the AI provider gateway (Task 1.5).

Migrated from a duplicated direct-Gemini transport onto the shared `AIRouter`
gateway in Phase 13, Task 13.7 -- see `app/services/script_service.py::generate_script`
for the identical reasoning (ADR-001 rejects the old multi-model fallback cascade).
"""

import hashlib
import json
import logging
import uuid
from datetime import datetime, timezone

import aiosqlite
from pydantic import TypeAdapter

from app.core.config import settings
from app.core.exceptions import LearningGenerationError, NotFoundError, ProviderError, SchemaValidationError
from app.core.prompt_loader import render_learning_prompt
from app.models.learning import LearningPackOut
from app.services.ai.contracts import AIMode, GenerationRequest
from app.services.ai.router import AIRouter, build_ai_router_from_settings
from app.services.ai.validation import parse_and_validate

logger = logging.getLogger(__name__)

_PACK_ADAPTER = TypeAdapter(LearningPackOut)


def _now() -> str:
    """Current UTC timestamp in ISO8601, used for created_at/updated_at."""
    return datetime.now(timezone.utc).isoformat()


def compute_script_hash(script_lines: list[dict]) -> str:
    """Stable hash over a script's speaker/text content only (Phase 13, Task 13.5).

    Used by `learning_pipeline.py` to detect a script edit landing while a
    learning-generation job is mid-flight -- deliberately ignores line ids and
    timestamps, since only the actual spoken content affects what a learning
    pack should be grounded in.
    """
    canonical = json.dumps(
        [{"speaker_id": line["speaker_id"], "text": line["text"]} for line in script_lines],
        sort_keys=True,
    )
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


async def generate_learning_pack(
    project_id: str, config: dict, script_lines: list[dict], router: AIRouter | None = None
) -> LearningPackOut:
    """Generate a full Learning Content pack for a project via the AI provider gateway.

    Migrated from a duplicated direct-Gemini retry/fallback-model transport to
    `AIRouter` (Phase 13, Task 13.7) -- see `script_service.generate_script` for the
    identical reasoning.

    Args:
        project_id: UUID of the project (used for error context/logging only).
        config: Project-shaped dict as returned by project_service.get_project —
            must include topic, cefr_level, and genre.
        script_lines: The project's persisted script lines (as returned by
            script_service.get_script), in order. Must be non-empty — their
            `text` is joined into the transcript Gemini extracts the pack
            from.
        router: Injected `AIRouter` (tests pass a `FakeProvider`-backed one with
            zero network calls); defaults to `build_ai_router_from_settings()`.

    Returns:
        The validated Learning Content pack.

    Raises:
        LearningGenerationError: If `AI_MODE=gemini` and no API key is configured,
            the script is empty, every provider attempt this mode allows fails, or
            the response is malformed/fails schema validation.
    """
    if AIMode(settings.AI_MODE) is AIMode.GEMINI and not settings.GEMINI_API_KEY:
        raise LearningGenerationError("DIE_GEMINI_API_KEY is not configured")

    if not script_lines:
        raise LearningGenerationError(
            f"Cannot generate learning content for project {project_id}: script is empty"
        )

    transcript_text = "\n".join(line["text"] for line in script_lines)

    prompt = await render_learning_prompt(
        topic=config["topic"],
        cefr_level=config["cefr_level"],
        genre=config["genre"],
        transcript_text=transcript_text,
    )

    router = router or build_ai_router_from_settings()
    request = GenerationRequest(
        prompt=prompt,
        json_schema=LearningPackOut.model_json_schema(),
        deadline_seconds=settings.AI_REQUEST_DEADLINE_SECONDS,
        purpose="learning_generate_full",
    )
    try:
        result = await router.generate(request)
    except ProviderError as exc:
        raise LearningGenerationError(f"Learning content generation failed: {exc}") from exc

    try:
        return parse_and_validate(result.text, _PACK_ADAPTER)
    except SchemaValidationError as exc:
        raise LearningGenerationError(str(exc)) from exc


def _row_to_pack(row: aiosqlite.Row) -> dict:
    """Convert a learning_contents row to a dict, decoding its JSON columns."""
    pack = dict(row)
    pack["vocabulary"] = json.loads(pack.pop("vocabulary_json"))
    pack["idioms"] = json.loads(pack.pop("idioms_json"))
    pack["grammar"] = json.loads(pack.pop("grammar_json"))
    pack["questions"] = json.loads(pack.pop("questions_json"))
    return pack


async def get_learning_content(db: aiosqlite.Connection, project_id: str) -> dict | None:
    """Fetch a project's Learning Content pack.

    Args:
        db: Open aiosqlite connection.
        project_id: UUID of the project.

    Returns:
        The pack as a dict (id, project_id, vocabulary, idioms, grammar,
        questions, created_at, updated_at), or None if nothing has been
        generated for this project yet — not an error, mirrors
        script_service.get_script's "empty means not generated yet".
    """
    cursor = await db.execute(
        "SELECT id, project_id, vocabulary_json, idioms_json, grammar_json, questions_json, "
        "created_at, updated_at FROM learning_contents WHERE project_id = ?",
        (project_id,),
    )
    row = await cursor.fetchone()
    if row is None:
        return None
    return _row_to_pack(row)


async def save_learning_content(
    db: aiosqlite.Connection, project_id: str, pack: dict, commit: bool = True
) -> dict:
    """Create or replace the Learning Content pack for a project (UPSERT).

    A repeat call for the same project replaces its previous pack (matching
    "Regenerate" semantics) rather than erroring or duplicating a row —
    `project_id` is UNIQUE, so this upserts on that constraint.

    Args:
        db: Open aiosqlite connection.
        project_id: UUID of the project.
        pack: Dict shaped like LearningPackOut.model_dump() — vocabulary/
            idioms/grammar/questions lists.
        commit: If False, skip the commit — the caller is responsible for
            committing (or rolling back) as part of a larger transaction.

    Returns:
        The saved Learning Content, as get_learning_content would return it.
    """
    now = _now()
    await db.execute(
        "INSERT INTO learning_contents "
        "(id, project_id, vocabulary_json, idioms_json, grammar_json, questions_json, "
        "created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?) "
        "ON CONFLICT(project_id) DO UPDATE SET "
        "vocabulary_json = excluded.vocabulary_json, "
        "idioms_json = excluded.idioms_json, "
        "grammar_json = excluded.grammar_json, "
        "questions_json = excluded.questions_json, "
        "updated_at = excluded.updated_at",
        (
            str(uuid.uuid4()),
            project_id,
            json.dumps(pack.get("vocabulary", [])),
            json.dumps(pack.get("idioms", [])),
            json.dumps(pack.get("grammar", [])),
            json.dumps(pack.get("questions", [])),
            now,
            now,
        ),
    )
    if commit:
        await db.commit()
    return await get_learning_content(db, project_id)


async def update_learning_content(
    db: aiosqlite.Connection, project_id: str, patch: dict, commit: bool = True
) -> dict:
    """Apply a partial update to an existing Learning Content pack.

    Args:
        db: Open aiosqlite connection.
        project_id: UUID of the project.
        patch: Dict with any subset of vocabulary/idioms/grammar/questions —
            omitted keys are left unchanged.
        commit: If False, skip the commit — the caller is responsible for
            committing (or rolling back) as part of a larger transaction.

    Returns:
        The updated Learning Content pack.

    Raises:
        NotFoundError: If no Learning Content pack exists yet for this project.
    """
    existing = await get_learning_content(db, project_id)
    if existing is None:
        raise NotFoundError(f"No learning content found for project {project_id}")

    for section in ("vocabulary", "idioms", "grammar", "questions"):
        if section in patch and patch[section] is None:
            raise ValueError(
                f"explicit null not allowed for: {section} — omit the field instead to leave it unchanged"
            )

    merged = {
        "vocabulary": patch["vocabulary"] if "vocabulary" in patch else existing["vocabulary"],
        "idioms": patch["idioms"] if "idioms" in patch else existing["idioms"],
        "grammar": patch["grammar"] if "grammar" in patch else existing["grammar"],
        "questions": patch["questions"] if "questions" in patch else existing["questions"],
    }

    await db.execute(
        "UPDATE learning_contents SET vocabulary_json = ?, idioms_json = ?, grammar_json = ?, "
        "questions_json = ?, updated_at = ? WHERE project_id = ?",
        (
            json.dumps(merged["vocabulary"]),
            json.dumps(merged["idioms"]),
            json.dumps(merged["grammar"]),
            json.dumps(merged["questions"]),
            _now(),
            project_id,
        ),
    )
    if commit:
        await db.commit()
    return await get_learning_content(db, project_id)
