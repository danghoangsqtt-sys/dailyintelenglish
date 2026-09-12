"""Generates and persists YouTube Package metadata via the Gemini API (Task 1.9, Sub-task 1.9a).

Mirrors app/services/learning_service.py's approach: Gemini is called directly over
its REST endpoint via httpx.AsyncClient, with 429-only exponential backoff and strict
Pydantic schema validation of the response.

Chapter timestamps are ESTIMATED from a fixed reading speed (no real audio duration
exists yet — Task 1.7/AudioService are blocked on ffmpeg, see TRACKER.md Known Issues),
never measured. This is documented in the API response shape and the UI copy.
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
from app.core.constants import (
    GEMINI_MAX_RETRIES,
    GEMINI_MODEL,
    GEMINI_RETRY_BASE_DELAY,
    YOUTUBE_CHAPTER_MIN_LINES,
    YOUTUBE_CHAPTER_WORDS_PER_MINUTE,
)
from app.core.exceptions import ValidationError, YouTubePackageGenerationError
from app.core.prompt_loader import render_youtube_prompt
from app.models.youtube import YouTubePackageOut

logger = logging.getLogger(__name__)

GEMINI_ENDPOINT = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"


def _now() -> str:
    """Current UTC timestamp in ISO8601, used for created_at/updated_at."""
    return datetime.now(timezone.utc).isoformat()


async def _call_gemini(prompt: str, schema: dict) -> tuple[httpx.Response, float]:
    """Make one HTTP call to Gemini generateContent. Returns (response, latency_ms)."""
    url = GEMINI_ENDPOINT.format(model=GEMINI_MODEL)
    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {
            "responseMimeType": "application/json",
            "responseJsonSchema": schema,
        },
    }
    started_at = time.perf_counter()
    async with httpx.AsyncClient(timeout=60.0) as client:
        response = await client.post(url, params={"key": settings.GEMINI_API_KEY}, json=payload)
    return response, (time.perf_counter() - started_at) * 1000


async def _generate_with_retry(prompt: str, schema: dict) -> str:
    """Call Gemini with exponential backoff on HTTP 429, returning the raw response text.

    Retries only on 429 (rate limit) — any other non-200 status fails immediately.
    Never logs the raw prompt or API key — only a hash of the prompt.
    """
    prompt_hash = hashlib.sha256(prompt.encode("utf-8")).hexdigest()[:16]
    delay = GEMINI_RETRY_BASE_DELAY

    for attempt in range(1, GEMINI_MAX_RETRIES + 1):
        try:
            response, latency_ms = await _call_gemini(prompt, schema)
        except httpx.RequestError as exc:
            raise YouTubePackageGenerationError(f"Gemini API request failed: {exc}") from exc

        if response.status_code == 200:
            data = response.json()
            logger.info(
                "gemini_youtube_call model=%s prompt_hash=%s latency_ms=%.1f "
                "tokens_used=%s attempt=%d",
                GEMINI_MODEL,
                prompt_hash,
                latency_ms,
                data.get("usageMetadata", {}).get("totalTokenCount"),
                attempt,
            )
            try:
                return data["candidates"][0]["content"]["parts"][0]["text"]
            except (KeyError, IndexError) as exc:
                raise YouTubePackageGenerationError(
                    f"Unexpected Gemini response shape: {exc}"
                ) from exc

        if response.status_code == 429 and attempt < GEMINI_MAX_RETRIES:
            logger.warning(
                "gemini_youtube_rate_limited prompt_hash=%s attempt=%d retry_in_s=%.1f",
                prompt_hash,
                attempt,
                delay,
            )
            await asyncio.sleep(delay)
            delay *= 2
            continue

        raise YouTubePackageGenerationError(
            f"Gemini API returned HTTP {response.status_code} after {attempt} attempt(s): "
            f"{response.text[:200]}"
        )
    raise YouTubePackageGenerationError("Gemini API retry loop ended unexpectedly")


def _chapter_label(text: str, max_words: int = 6) -> str:
    """Build a short chapter label from a line's leading words."""
    words = text.split()
    label = " ".join(words[:max_words])
    return f"{label}…" if len(words) > max_words else label


def estimate_chapters(script_lines: list[dict]) -> str:
    """Estimate YouTube chapter markers from script text alone.

    No real audio duration exists yet (Task 1.7/AudioService are blocked on ffmpeg),
    so each chapter's timestamp is estimated from the cumulative word count of every
    preceding line at a fixed reading speed (YOUTUBE_CHAPTER_WORDS_PER_MINUTE) — an
    approximation for a draft aid, not a measurement. A new chapter starts every
    YOUTUBE_CHAPTER_MIN_LINES lines (a simple topic-shift heuristic); the first
    chapter is always "00:00 Introduction".

    Returns:
        Plain-text "MM:SS Label" lines (YouTube's chapter format), one per line,
        or "" if there are no script lines.
    """
    if not script_lines:
        return ""
    chapters: list[str] = []
    cumulative_words = 0
    for index, line in enumerate(script_lines):
        if index == 0:
            chapters.append("00:00 Introduction")
        elif index % YOUTUBE_CHAPTER_MIN_LINES == 0:
            seconds = round(cumulative_words / YOUTUBE_CHAPTER_WORDS_PER_MINUTE * 60)
            minutes, secs = divmod(seconds, 60)
            chapters.append(f"{minutes:02d}:{secs:02d} {_chapter_label(line['text'])}")
        cumulative_words += len(line["text"].split())
    return "\n".join(chapters)


async def generate_package(project: dict, script_lines: list[dict]) -> dict:
    """Generate a full YouTube package (titles/description/tags/estimated chapters) via Gemini.

    Args:
        project: Project-shaped dict as returned by project_service.get_project —
            must include name, topic, cefr_level, and genre.
        script_lines: The project's persisted script lines, in order. Must be
            non-empty — their text is joined into the transcript Gemini uses,
            and is also used to estimate chapter timestamps.

    Returns:
        A dict shaped like a persisted package row's public form: titles,
        description, tags, chapters_text.

    Raises:
        ValidationError: If the script is empty.
        YouTubePackageGenerationError: If the API key is unset, Gemini fails
            after retries, returns malformed JSON, or fails schema validation.
    """
    if not settings.GEMINI_API_KEY:
        raise YouTubePackageGenerationError("DIE_GEMINI_API_KEY is not configured")
    if not script_lines:
        raise ValidationError("Cannot generate a YouTube package: script is empty")

    transcript_text = "\n".join(line["text"] for line in script_lines)
    prompt = await render_youtube_prompt(
        project_name=project["name"],
        topic=project["topic"],
        genre=project["genre"],
        cefr_level=project["cefr_level"],
        transcript_text=transcript_text,
    )
    raw_text = await _generate_with_retry(prompt, schema=YouTubePackageOut.model_json_schema())

    try:
        parsed = json.loads(raw_text)
    except json.JSONDecodeError as exc:
        raise YouTubePackageGenerationError(f"Gemini did not return valid JSON: {exc}") from exc
    try:
        package = YouTubePackageOut.model_validate(parsed)
    except PydanticValidationError as exc:
        raise YouTubePackageGenerationError(
            f"Gemini response failed schema validation: {exc}"
        ) from exc

    return {
        "titles": [title.model_dump() for title in package.titles],
        "description": package.description,
        "tags": package.tags,
        "chapters_text": estimate_chapters(script_lines),
    }


def _row_to_package(row: aiosqlite.Row) -> dict:
    """Convert a youtube_packages row to a dict, decoding its JSON column."""
    package = dict(row)
    package["titles"] = json.loads(package.pop("title_options_json"))
    package["tags"] = [tag.strip() for tag in package["tags"].split(",") if tag.strip()]
    return package


async def get_package(db: aiosqlite.Connection, project_id: str) -> dict | None:
    """Fetch a project's YouTube package, or None if never generated."""
    cursor = await db.execute(
        "SELECT id, project_id, title_options_json, description, chapters_text, tags, "
        "created_at, updated_at FROM youtube_packages WHERE project_id = ?",
        (project_id,),
    )
    row = await cursor.fetchone()
    return None if row is None else _row_to_package(row)


async def save_package(
    db: aiosqlite.Connection, project_id: str, package: dict, commit: bool = True
) -> dict:
    """Create or replace the YouTube package for a project (UPSERT on project_id).

    A repeat call (Regenerate) replaces the previous package rather than erroring
    or duplicating a row.
    """
    now = _now()
    await db.execute(
        "INSERT INTO youtube_packages "
        "(id, project_id, title_options_json, description, chapters_text, tags, "
        "created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?) "
        "ON CONFLICT(project_id) DO UPDATE SET "
        "title_options_json = excluded.title_options_json, "
        "description = excluded.description, "
        "chapters_text = excluded.chapters_text, "
        "tags = excluded.tags, "
        "updated_at = excluded.updated_at",
        (
            str(uuid.uuid4()),
            project_id,
            json.dumps(package["titles"]),
            package["description"],
            package["chapters_text"],
            ", ".join(package["tags"]),
            now,
            now,
        ),
    )
    if commit:
        await db.commit()
    return await get_package(db, project_id)
