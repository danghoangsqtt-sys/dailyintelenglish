"""Synthesize plain dialogue using Edge TTS and its native word timestamps."""

import asyncio
import json
import logging
import os
import uuid
from asyncio import sleep
from pathlib import Path
from typing import NamedTuple

import aiosqlite
import edge_tts
from pydub import AudioSegment

from backend.ai.tts.vocal_cues import caption_text, has_vocal_cues
from backend.core.config import settings
from backend.core.constants import EDGE_TTS_PITCH_LIMIT_HZ, EDGE_TTS_VOICE_MAP
from backend.core.exceptions import ConflictError, NotFoundError, TTSError, ValidationError

from backend.core.voice import line_fingerprint, resolve_voice_id
from backend.db.transactions import write_transaction

logger = logging.getLogger(__name__)

# pydub's converter and ffprobe lookup must also work when a preview reaches TTS
# before the audio mixer module has been imported.
AudioSegment.converter = settings.FFMPEG_PATH
_ffmpeg_dir = str(Path(settings.FFMPEG_PATH).parent)
if _ffmpeg_dir != "." and _ffmpeg_dir not in os.environ.get("PATH", "").split(os.pathsep):
    os.environ["PATH"] = _ffmpeg_dir + os.pathsep + os.environ.get("PATH", "")

class WordBoundary(NamedTuple):
    """One word's timing within its own line's audio (local time, not mix-aggregated).

    Edge TTS reports `offset`/`duration` as 100-ns ticks (.NET convention) -- converted to
    float seconds once here so ticks never leave this module (Task 19.2, D19.2-a).
    """

    text: str
    offset_sec: float
    duration_sec: float


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
    requested = round(pitch * EDGE_TTS_PITCH_LIMIT_HZ)
    value = max(-EDGE_TTS_PITCH_LIMIT_HZ, min(EDGE_TTS_PITCH_LIMIT_HZ, requested))
    return f"{'+' if value >= 0 else ''}{value}Hz"


EDGE_TTS_MAX_ATTEMPTS = 2
EDGE_TTS_RETRY_DELAY_SECONDS = 0.5

# Edge TTS reports offset/duration in 100-nanosecond ticks (.NET convention) --
# confirmed against a real WordBoundary chunk (Task 19.2, D19.2-a probe).
_TICKS_PER_SECOND = 10_000_000


async def _synthesize_edge_tts(text: str, speaker: dict) -> tuple[bytes, list[WordBoundary]]:
    """Synthesize speech via the Edge TTS online engine, capturing per-word timestamps.

    Edge TTS's free endpoint occasionally returns an empty stream under rapid-fire
    requests (observed live: "No audio was received" on an otherwise-valid call that
    succeeds on immediate retry) — treat an empty/failed result as a failed cue and
    allow one retry before raising, rather than failing the whole line permanently.

    Task 19.2 (D19.2-a): `edge_tts.Communicate` defaults to `boundary="SentenceBoundary"`
    -- confirmed live that no `WordBoundary` chunks appear at all without explicitly
    passing `boundary="WordBoundary"`. Word boundaries are returned alongside the audio
    bytes rather than via a separate call, so there's exactly one Edge TTS request per line.
    """
    text = caption_text(text).strip()
    if not text:
        raise TTSError("Enter spoken dialogue before generating audio.")
    voice = resolve_voice_id(speaker)
    last_error: Exception | None = None
    for attempt in range(1, EDGE_TTS_MAX_ATTEMPTS + 1):
        communicate = edge_tts.Communicate(
            text,
            voice,
            rate=_rate_percent(speaker["speed"]),
            volume=_volume_percent(speaker["volume"]),
            pitch=_pitch_hz(speaker["pitch"]),
            boundary="WordBoundary",
        )
        chunks = bytearray()
        word_boundaries: list[WordBoundary] = []
        try:
            async for chunk in communicate.stream():
                if chunk["type"] == "audio":
                    chunks.extend(chunk["data"])
                elif chunk["type"] == "WordBoundary":
                    word_boundaries.append(
                        WordBoundary(
                            text=chunk["text"],
                            offset_sec=chunk["offset"] / _TICKS_PER_SECOND,
                            duration_sec=chunk["duration"] / _TICKS_PER_SECOND,
                        )
                    )
        except Exception as exc:
            last_error = exc
        else:
            if chunks:
                return bytes(chunks), word_boundaries
            last_error = RuntimeError("Edge TTS returned no audio data")

        if attempt < EDGE_TTS_MAX_ATTEMPTS:
            logger.warning("Edge TTS attempt %d/%d failed (%s), retrying", attempt, EDGE_TTS_MAX_ATTEMPTS, last_error)
            await sleep(EDGE_TTS_RETRY_DELAY_SECONDS)

    raise TTSError(f"Edge TTS synthesis failed after {EDGE_TTS_MAX_ATTEMPTS} attempts: {last_error}") from last_error


def _find_speaker(project: dict, speaker_id: str) -> dict:
    for speaker in project["speakers"]:
        if speaker["id"] == speaker_id:
            return speaker
    raise NotFoundError(f"Speaker {speaker_id} not found on project {project['id']}")


def _write_audio_cache_sync(cache_dir: Path, audio_path: Path, audio_bytes: bytes) -> None:
    """Blocking cache-directory creation + file write — must run in a thread, never on
    the event loop directly."""
    cache_dir.mkdir(parents=True, exist_ok=True)
    audio_path.write_bytes(audio_bytes)


def _word_timestamps_path(audio_path: Path) -> Path:
    """Sidecar path for a line's raw per-word capture (Task 19.2, D19.2-c) -- derived
    deterministically from the cached MP3's own path so `AudioService` can find it at mix
    time without a new `script_lines` column. One MP3 per line (`<line_id>.mp3`), confirmed
    against this module's own cache-path convention above, so this is a safe 1:1 rename."""
    return audio_path.with_suffix(".words.json")


def _write_word_boundaries_sync(path: Path, word_boundaries: list[WordBoundary]) -> None:
    """Blocking sidecar write — must run in a thread, same rule as `_write_audio_cache_sync`."""
    path.write_text(
        json.dumps([wb._asdict() for wb in word_boundaries]),
        encoding="utf-8",
    )


def has_word_timings(audio_cache_path: str) -> bool:
    """Task 32.8c (BUG-030): a cached line is only reusable for a mix when its word-timing sidecar exists.

    Lines cached before Task 19.2 have an MP3 but no sidecar; mixing them silently drops karaoke for those lines.
    Blocking filesystem check -- call it in a thread from async code.
    """
    return _word_timestamps_path(Path(audio_cache_path)).is_file()


async def synthesize_line_audio(project: dict, line: dict) -> dict:
    """Synthesize one script line's audio and cache it to disk. Touches no database.

    This is the slow half (network call to Edge TTS) of what `synthesize_line` used to do as one step. Callers that hold a
    `write_transaction` lock (see `backend/db/transactions.py`'s module docstring on why
    that lock must never wrap slow network/GPU work) must call this function
    *outside* that lock, then a separate, short `save_line_audio_cache` call inside
    it — see `backend/api/tts.py::preview_line` for the intended shape. Found by an
    independent audit: `preview_line` previously ran this entire synthesis inside
    the app's single connection-wide write lock, stalling every other request
    (even an unrelated dashboard GET) for the duration of a live Edge TTS call.

    Returns:
        {"audio_path": str, "engine_used": "edge_tts"}

    Raises:
        NotFoundError: If the line's speaker_id doesn't match any project speaker.
        TTSError: If Edge TTS fails after its retry.

    Task 19.2: the captured per-word timestamps are written to a sidecar file next to the
    cached MP3 (`_word_timestamps_path`) rather than returned here -- `AudioService.mix_project`
    derives the same path independently at mix time (D19.2-c).
    """
    speaker = _find_speaker(project, line["speaker_id"])

    # Problems the user can fix are 422s whose message the UI shows; provider failures stay 502.
    if (speaker.get("tts_engine") or "edge_tts") != "edge_tts":
        raise ValidationError("Only Edge TTS is supported. Reload the updated project settings.")
    if not caption_text(line["text"]).strip():
        raise ValidationError("Enter spoken dialogue before generating audio.")
    audio_bytes, word_boundaries = await _synthesize_edge_tts(line["text"], speaker)

    cache_dir = settings.DATA_DIR / "tts_cache" / project["id"] / uuid.uuid4().hex
    audio_path = cache_dir / f"{line['id']}.mp3"
    await asyncio.to_thread(_write_audio_cache_sync, cache_dir, audio_path, audio_bytes)
    await asyncio.to_thread(_write_word_boundaries_sync, _word_timestamps_path(audio_path), word_boundaries)

    await asyncio.to_thread(
        audio_path.with_suffix(".tts.json").write_text,
        json.dumps(line_fingerprint(project, line), sort_keys=True), encoding="utf-8",
    )
    return {"audio_path": str(audio_path), "engine_used": "edge_tts"}


async def save_line_audio_cache(
    db: aiosqlite.Connection, project_id: str, line_id: str, audio_path: str, *, commit: bool = True,
    expected_fingerprint: dict | None = None,
) -> None:
    """Record a script line's freshly synthesized audio path.

    Always call this only after `synthesize_line_audio` has already produced the
    file — this function does no synthesis itself, just the fast DB write.
    """
    if expected_fingerprint is not None:
        await assert_line_current(db, project_id, line_id, expected_fingerprint)
    await db.execute(
        "UPDATE script_lines SET audio_cache_path = ? WHERE id = ? AND project_id = ?",
        (audio_path, line_id, project_id),
    )
    if commit:
        await db.commit()


async def synthesize_line(
    db: aiosqlite.Connection, project: dict, line: dict, *, commit: bool = True
) -> dict:
    """Synthesize one script line and cache it, in one call.

    Convenience wrapper around `synthesize_line_audio` + `save_line_audio_cache` for
    callers with no lock to release in between (tests, or any future caller outside
    a `write_transaction`). `backend/api/tts.py::preview_line` calls the two phases
    directly instead, so the slow network/GPU work never runs while holding the
    app's connection-wide write lock.
    """
    _find_speaker(project, line["speaker_id"])
    expected = line_fingerprint(project, line)
    result = await synthesize_line_audio(project, line)
    if commit:
        async with write_transaction(db):
            await save_line_audio_cache(
                db, project["id"], line["id"], result["audio_path"], commit=False, expected_fingerprint=expected,
            )
    else:
        await save_line_audio_cache(
            db, project["id"], line["id"], result["audio_path"], commit=False, expected_fingerprint=expected,
        )
    return result


def _resolve_cached_audio_sync(project_id: str, stored_path: str) -> str:
    """Validate a stored audio-cache path is still a real file under this project's own
    cache directory before it's ever handed to FileResponse — same containment check
    already used by
    thumbnail_service._resolve_content_sync, applied here for consistency (a moved/deleted
    cache file would otherwise surface as an unhandled FileNotFoundError/500 instead of a
    clean 404)."""
    candidate = Path(stored_path).resolve()
    project_root = (settings.DATA_DIR / "tts_cache" / project_id).resolve()
    if project_root not in candidate.parents or not candidate.is_file():
        raise NotFoundError(f"Cached audio for line not found under project {project_id}")
    return str(candidate)


async def get_cached_audio_path(db: aiosqlite.Connection, project_id: str, line_id: str) -> str | None:
    """Look up a previously synthesized line's cached, validated audio file path, if any."""
    cursor = await db.execute(
        "SELECT audio_cache_path FROM script_lines WHERE project_id = ? AND id = ?",
        (project_id, line_id),
    )
    row = await cursor.fetchone()
    if row is None:
        raise NotFoundError(f"Script line {line_id} not found for project {project_id}")
    if not row["audio_cache_path"]:
        return None
    return await asyncio.to_thread(_resolve_cached_audio_sync, project_id, row["audio_cache_path"])


def cache_matches(project: dict, line: dict, *, allow_legacy: bool = True) -> bool:
    """Read-only cache validation; legacy timings remain reusable until an explicit input change clears their reference."""
    stored = line.get("audio_cache_path")
    if not stored:
        return False
    path = Path(stored)
    project_root = (settings.DATA_DIR / "tts_cache" / project["id"]).resolve()
    try:
        engine = line_fingerprint(project, line)["engine"]
        needs_word_timings = engine == "edge_tts"
        if (project_root not in path.resolve().parents or not path.is_file()
                or (needs_word_timings and not has_word_timings(str(path)))):
            return False
        metadata = path.with_suffix(".tts.json")
        if not metadata.exists():
            return allow_legacy and not has_vocal_cues(line["text"])
        return json.loads(metadata.read_text(encoding="utf-8")) == line_fingerprint(project, line)
    except (OSError, ValueError, ValidationError):
        return False


async def assert_line_current(
    db: aiosqlite.Connection, project_id: str, line_id: str, expected_fingerprint: dict,
) -> None:
    """Reject a stale TTS completion; caller holds the publication transaction."""
    cursor = await db.execute(
        "SELECT id, speaker_id, text FROM script_lines WHERE project_id = ? AND id = ?", (project_id, line_id),
    )
    line = await cursor.fetchone()
    if line is None:
        raise ConflictError("The script line changed while speech was being generated. Generate it again.")
    cursor = await db.execute(
        "SELECT id, tts_engine, voice_id, voice_description, accent, gender, speed, pitch, volume FROM speakers WHERE project_id=? AND id=?",
        (project_id, line["speaker_id"]),
    )
    speaker = await cursor.fetchone()
    if speaker is None or line_fingerprint({"speakers": [dict(speaker)]}, dict(line)) != expected_fingerprint:
        raise ConflictError("Voice or text changed while speech was being generated. Generate it again.")
