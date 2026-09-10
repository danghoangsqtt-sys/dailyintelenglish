"""Generates and persists Learning Content packs via the Gemini API (Task 1.5).

Mirrors app/services/script_service.py's approach: Gemini is called directly
over its REST endpoint via httpx.AsyncClient (native async, direct HTTP status
control for 429 backoff, trivially mockable in tests), with exponential
backoff on rate limiting and strict Pydantic schema validation of the response.
"""

import asyncio
import hashlib
import json
import logging
import time
import uuid
from datetime import datetime, timezone

import aiosqlite
import httpx
from pydantic import ValidationError as PydanticValidationError

from app.core.config import settings
from app.core.constants import GEMINI_MAX_RETRIES, GEMINI_MODEL, GEMINI_RETRY_BASE_DELAY
from app.core.exceptions import LearningGenerationError, NotFoundError
from app.core.prompt_loader import render_learning_prompt
from app.models.learning import LearningPackOut

logger = logging.getLogger(__name__)

GEMINI_ENDPOINT = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"


def _now() -> str:
    """Current UTC timestamp in ISO8601, used for created_at/updated_at."""
    return datetime.now(timezone.utc).isoformat()


async def _call_gemini(prompt: str) -> tuple[httpx.Response, float]:
    """Make one HTTP call to Gemini generateContent. Returns (response, latency_ms)."""
    url = GEMINI_ENDPOINT.format(model=GEMINI_MODEL)
    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {"responseMimeType": "application/json"},
    }
    started_at = time.perf_counter()
    async with httpx.AsyncClient(timeout=60.0) as client:
        response = await client.post(url, params={"key": settings.GEMINI_API_KEY}, json=payload)
    latency_ms = (time.perf_counter() - started_at) * 1000
    return response, latency_ms


async def _generate_with_retry(prompt: str) -> str:
    """Call Gemini with exponential backoff on HTTP 429, returning the raw response text.

    Retries only on 429 (rate limit) — any other non-200 status fails immediately,
    since retrying won't fix a bad request or an auth error. Never logs the raw
    prompt or API key — only a hash of the prompt, for correlating log lines.
    """
    prompt_hash = hashlib.sha256(prompt.encode("utf-8")).hexdigest()[:16]
    delay = GEMINI_RETRY_BASE_DELAY

    for attempt in range(1, GEMINI_MAX_RETRIES + 1):
        try:
            response, latency_ms = await _call_gemini(prompt)
        except httpx.RequestError as exc:
            raise LearningGenerationError(f"Gemini API request failed: {exc}") from exc

        if response.status_code == 200:
            data = response.json()
            tokens_used = data.get("usageMetadata", {}).get("totalTokenCount")
            logger.info(
                "gemini_learning_call model=%s prompt_hash=%s latency_ms=%.1f tokens_used=%s attempt=%d",
                GEMINI_MODEL,
                prompt_hash,
                latency_ms,
                tokens_used,
                attempt,
            )
            try:
                return data["candidates"][0]["content"]["parts"][0]["text"]
            except (KeyError, IndexError) as exc:
                raise LearningGenerationError(f"Unexpected Gemini response shape: {exc}") from exc

        if response.status_code == 429 and attempt < GEMINI_MAX_RETRIES:
            logger.warning(
                "gemini_learning_rate_limited prompt_hash=%s attempt=%d retry_in_s=%.1f",
                prompt_hash,
                attempt,
                delay,
            )
            await asyncio.sleep(delay)
            delay *= 2
            continue

        raise LearningGenerationError(
            f"Gemini API returned HTTP {response.status_code} after {attempt} attempt(s): "
            f"{response.text[:200]}"
        )


async def generate_learning_pack(
    project_id: str, config: dict, script_lines: list[dict]
) -> LearningPackOut:
    """Generate a full Learning Content pack for a project via Gemini.

    Args:
        project_id: UUID of the project (used for error context/logging only).
        config: Project-shaped dict as returned by project_service.get_project —
            must include topic, cefr_level, and genre.
        script_lines: The project's persisted script lines (as returned by
            script_service.get_script), in order. Must be non-empty — their
            `text` is joined into the transcript Gemini extracts the pack
            from.

    Returns:
        The validated Learning Content pack.

    Raises:
        LearningGenerationError: If the API key is unset, the script is
            empty, Gemini fails after retries, returns malformed JSON, or
            the response fails schema validation.
    """
    if not settings.GEMINI_API_KEY:
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

    raw_text = await _generate_with_retry(prompt)

    try:
        parsed = json.loads(raw_text)
    except json.JSONDecodeError as exc:
        raise LearningGenerationError(f"Gemini did not return valid JSON: {exc}") from exc

    try:
        pack = LearningPackOut.model_validate(parsed)
    except PydanticValidationError as exc:
        raise LearningGenerationError(f"Gemini response failed schema validation: {exc}") from exc

    return pack


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

    merged = {
        "vocabulary": patch.get("vocabulary", existing["vocabulary"]),
        "idioms": patch.get("idioms", existing["idioms"]),
        "grammar": patch.get("grammar", existing["grammar"]),
        "questions": patch.get("questions", existing["questions"]),
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
