"""Generates podcast scripts via the Gemini API, with retry and schema validation."""

import asyncio
import hashlib
import json
import logging
import time
import uuid

import httpx
from pydantic import BaseModel, Field, TypeAdapter, field_validator
from pydantic import ValidationError as PydanticValidationError

from app.core.config import settings
from app.core.constants import GEMINI_MAX_RETRIES, GEMINI_MODEL, GEMINI_RETRY_BASE_DELAY
from app.core.exceptions import ScriptGenerationError
from app.core.prompt_loader import render_script_prompt

logger = logging.getLogger(__name__)

GEMINI_ENDPOINT = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"


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
    since retrying won't fix a bad request or an auth error.
    """
    prompt_hash = hashlib.sha256(prompt.encode("utf-8")).hexdigest()[:16]
    delay = GEMINI_RETRY_BASE_DELAY

    for attempt in range(1, GEMINI_MAX_RETRIES + 1):
        try:
            response, latency_ms = await _call_gemini(prompt)
        except httpx.RequestError as exc:
            raise ScriptGenerationError(f"Gemini API request failed: {exc}") from exc

        if response.status_code == 200:
            data = response.json()
            tokens_used = data.get("usageMetadata", {}).get("totalTokenCount")
            logger.info(
                "gemini_call model=%s prompt_hash=%s latency_ms=%.1f tokens_used=%s attempt=%d",
                GEMINI_MODEL,
                prompt_hash,
                latency_ms,
                tokens_used,
                attempt,
            )
            try:
                return data["candidates"][0]["content"]["parts"][0]["text"]
            except (KeyError, IndexError) as exc:
                raise ScriptGenerationError(f"Unexpected Gemini response shape: {exc}") from exc

        if response.status_code == 429 and attempt < GEMINI_MAX_RETRIES:
            logger.warning(
                "gemini_rate_limited prompt_hash=%s attempt=%d retry_in_s=%.1f",
                prompt_hash,
                attempt,
                delay,
            )
            await asyncio.sleep(delay)
            delay *= 2
            continue

        raise ScriptGenerationError(
            f"Gemini API returned HTTP {response.status_code} after {attempt} attempt(s): "
            f"{response.text[:200]}"
        )


async def generate_script(project_id: str, config: dict) -> list[ScriptLineOut]:
    """Generate a full podcast script for a project via Gemini.

    Args:
        project_id: UUID of the project (used for error context/logging only).
        config: Project-shaped dict as returned by project_service.get_project —
            must include topic, cefr_level, genre, accent, duration_minutes,
            num_speakers, language_features, and speakers (each with a real
            UUID `id`, as persisted in the speakers table).

    Returns:
        Validated list of script lines. Every `speaker_id` is guaranteed to be
        a UUID that belongs to one of `config["speakers"]`.

    Raises:
        ScriptGenerationError: If the API key is unset, Gemini fails after
            retries, returns malformed JSON, the response fails schema
            validation, or a line references a speaker_id that isn't one of
            the project's actual speakers.
    """
    if not settings.GEMINI_API_KEY:
        raise ScriptGenerationError("DIE_GEMINI_API_KEY is not configured")

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

    raw_text = await _generate_with_retry(prompt)

    try:
        parsed = json.loads(raw_text)
    except json.JSONDecodeError as exc:
        raise ScriptGenerationError(f"Gemini did not return valid JSON: {exc}") from exc

    try:
        lines = _SCRIPT_LINES_ADAPTER.validate_python(parsed)
    except PydanticValidationError as exc:
        raise ScriptGenerationError(f"Gemini response failed schema validation: {exc}") from exc

    if not lines:
        raise ScriptGenerationError(f"Gemini returned an empty script for project {project_id}")

    unknown_speakers = {line.speaker_id for line in lines} - known_speaker_ids
    if unknown_speakers:
        raise ScriptGenerationError(
            f"Gemini used speaker_id(s) not in project {project_id}: {unknown_speakers}"
        )

    return lines
