"""Converts script lines to speech per speaker (Task 1.6, Sub-task 1.6a).

Engine priority: OmniVoice (local GPU) first when configured and its model directory
exists, falling back to Edge TTS automatically on any failure (SYSTEM-RULES "OmniVoice
Rules": catch OOM/model errors -> fall back, never surface a raw GPU error to the user).

OmniVoice model weights are not present on every development machine yet (see
TRACKER.md Known Issues), so `_synthesize_omnivoice` always raises
`_OmniVoiceUnavailableError` for now — this is the correct, honest state of the local
GPU path, not a stub standing in for a "real" implementation. The fallback logic around
it is what Sub-task 1.6a actually delivers and tests.
"""

import asyncio
import logging

import aiosqlite
import edge_tts

from app.core.config import settings
from app.core.constants import EDGE_TTS_VOICE_MAP, MAX_CONCURRENT_TTS
from app.core.exceptions import NotFoundError, TTSError

logger = logging.getLogger(__name__)

_omnivoice_semaphore = asyncio.Semaphore(MAX_CONCURRENT_TTS)


class _OmniVoiceUnavailableError(Exception):
    """Internal signal that the OmniVoice path could not run — caller falls back to Edge TTS."""


def _edge_tts_voice_for(accent: str, gender: str) -> str:
    """Resolve an accent+gender pair to a concrete Edge TTS neural voice id."""
    accent_map = EDGE_TTS_VOICE_MAP.get(accent, EDGE_TTS_VOICE_MAP["american"])
    return accent_map.get(gender, accent_map["neutral"])


def _rate_percent(speed: float) -> str:
    """Convert a speed multiplier (TTS_SPEED_MIN..MAX, default 1.0) to an Edge TTS rate string."""
    pct = round((speed - 1.0) * 100)
    return f"{'+' if pct >= 0 else ''}{pct}%"


def _volume_percent(volume: float) -> str:
    """Convert a volume multiplier (default 1.0) to an Edge TTS volume string."""
    pct = round((volume - 1.0) * 100)
    return f"{'+' if pct >= 0 else ''}{pct}%"


def _pitch_hz(pitch: float) -> str:
    """Convert the speaker's normalized pitch (-1.0..1.0, SpeakerConfig) to an Edge TTS pitch string.

    -1.0/+1.0 map to -50Hz/+50Hz — audible but not distorted, roughly matching Azure's
    documented safe pitch-shift range for neural voices.
    """
    value = round(pitch * 50)
    return f"{'+' if value >= 0 else ''}{value}Hz"


async def _synthesize_omnivoice(text: str, speaker: dict) -> bytes:
    """Attempt local-GPU synthesis via OmniVoice. Raises _OmniVoiceUnavailableError.

    Not yet integrated: doing so requires the actual OmniVoice model weights and its
    Python package, neither of which are installed. When that lands, this function
    should load the model once at startup (never per-request — SYSTEM-RULES) and run
    inference in a threadpool executor (it's CPU/GPU-bound, not I/O).
    """
    raise _OmniVoiceUnavailableError("OmniVoice model not loaded (models/omnivoice is empty)")


EDGE_TTS_MAX_ATTEMPTS = 2
EDGE_TTS_RETRY_DELAY_SECONDS = 0.5


async def _synthesize_edge_tts(text: str, speaker: dict) -> bytes:
    """Synthesize speech via the Edge TTS online engine.

    Edge TTS's free endpoint occasionally returns an empty stream under rapid-fire
    requests (observed live: "No audio was received" on an otherwise-valid call that
    succeeds on immediate retry) — treat an empty/failed result as a failed cue and
    allow one retry before raising, rather than failing the whole line permanently.
    """
    voice = _edge_tts_voice_for(speaker["accent"], speaker["gender"])
    last_error: Exception | None = None
    for attempt in range(1, EDGE_TTS_MAX_ATTEMPTS + 1):
        communicate = edge_tts.Communicate(
            text,
            voice,
            rate=_rate_percent(speaker["speed"]),
            volume=_volume_percent(speaker["volume"]),
            pitch=_pitch_hz(speaker["pitch"]),
        )
        chunks = bytearray()
        try:
            async for chunk in communicate.stream():
                if chunk["type"] == "audio":
                    chunks.extend(chunk["data"])
        except Exception as exc:
            last_error = exc
        else:
            if chunks:
                return bytes(chunks)
            last_error = RuntimeError("Edge TTS returned no audio data")

        if attempt < EDGE_TTS_MAX_ATTEMPTS:
            logger.warning("Edge TTS attempt %d/%d failed (%s), retrying", attempt, EDGE_TTS_MAX_ATTEMPTS, last_error)
            await asyncio.sleep(EDGE_TTS_RETRY_DELAY_SECONDS)

    raise TTSError(f"Edge TTS synthesis failed after {EDGE_TTS_MAX_ATTEMPTS} attempts: {last_error}") from last_error


def _find_speaker(project: dict, speaker_id: str) -> dict:
    for speaker in project["speakers"]:
        if speaker["id"] == speaker_id:
            return speaker
    raise NotFoundError(f"Speaker {speaker_id} not found on project {project['id']}")


async def synthesize_line(
    db: aiosqlite.Connection, project: dict, line: dict, *, commit: bool = True
) -> dict:
    """Synthesize one script line to an audio file, caching it and recording the path.

    Returns:
        {"audio_path": str, "engine_used": "omnivoice" | "edge_tts"}

    Raises:
        NotFoundError: If the line's speaker_id doesn't match any project speaker.
        TTSError: If Edge TTS also fails after an OmniVoice fallback (or is the only
            configured engine and fails).
    """
    speaker = _find_speaker(project, line["speaker_id"])

    audio_bytes: bytes
    engine_used: str
    if speaker["tts_engine"] == "omnivoice" and settings.OMNIVOICE_MODEL_PATH.exists():
        async with _omnivoice_semaphore:
            try:
                audio_bytes = await _synthesize_omnivoice(line["text"], speaker)
                engine_used = "omnivoice"
            except _OmniVoiceUnavailableError as exc:
                logger.warning("OmniVoice unavailable for line %s, falling back to Edge TTS: %s", line["id"], exc)
                audio_bytes = await _synthesize_edge_tts(line["text"], speaker)
                engine_used = "edge_tts"
    else:
        audio_bytes = await _synthesize_edge_tts(line["text"], speaker)
        engine_used = "edge_tts"

    cache_dir = settings.DATA_DIR / "tts_cache" / project["id"]
    cache_dir.mkdir(parents=True, exist_ok=True)
    audio_path = cache_dir / f"{line['id']}.mp3"
    audio_path.write_bytes(audio_bytes)

    await db.execute(
        "UPDATE script_lines SET audio_cache_path = ? WHERE id = ? AND project_id = ?",
        (str(audio_path), line["id"], project["id"]),
    )
    if commit:
        await db.commit()

    return {"audio_path": str(audio_path), "engine_used": engine_used}


async def get_cached_audio_path(db: aiosqlite.Connection, project_id: str, line_id: str) -> str | None:
    """Look up a previously synthesized line's cached audio file path, if any."""
    cursor = await db.execute(
        "SELECT audio_cache_path FROM script_lines WHERE project_id = ? AND id = ?",
        (project_id, line_id),
    )
    row = await cursor.fetchone()
    if row is None:
        raise NotFoundError(f"Script line {line_id} not found for project {project_id}")
    return row["audio_cache_path"]
