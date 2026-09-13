"""Mixes per-line TTS audio into one podcast track (Task 1.6, Sub-task 1.6b).

Responsibility split from TTSService (ARCHITECTURE.md "Module Dependencies"): this module
only processes already-synthesized audio files — it never calls a TTS engine itself. The
caller (app/api/audio.py) is responsible for making sure every line has a cached audio file
before calling `mix_project`.

Background music ducking here is a **static-level duck**: the track is capped at a flat
ceiling (`MUSIC_DUCKING_MAX_DBFS`) for its entire length, not lowered dynamically only during
speech. True speech-reactive ducking needs per-segment envelope analysis, which is out of
scope for this sub-task (see task-1.6.md Implementation Notes).
"""

import asyncio
import json
import math
import os
import uuid
from datetime import datetime, timezone
from pathlib import Path

import aiosqlite
import numpy as np
import pyloudnorm as pyln
from pydub import AudioSegment

from app.core.config import settings
from app.core.constants import (
    MP3_BITRATE,
    MUSIC_DUCKING_MAX_DBFS,
    SILENCE_DIFFERENT_SPEAKER_MS,
    SILENCE_SAME_SPEAKER_MS,
    TARGET_LOUDNESS_LUFS,
    WAV_BIT_DEPTH,
    WAV_SAMPLE_RATE_HZ,
)
from app.core.exceptions import AudioMixError


def _ensure_ffmpeg_dir_on_path(ffmpeg_path: str) -> None:
    """Make ffmpeg AND ffprobe resolvable to this pydub version.

    `AudioSegment.converter` (set below) covers pydub's actual encode/decode calls, but
    its media-probing step (`pydub.utils.get_prober_name`) does its own `which("ffprobe")`
    PATH lookup and ignores any class-attribute override entirely — confirmed by reading
    pydub/utils.py in the installed version. `DIE_FFMPEG_PATH` is an absolute path on
    machines (like this one) where ffmpeg was never added to the system PATH (see
    TRACKER.md Known Issues), so prepend its directory to this process's PATH — affects
    only this process, not the system, and a standard ffmpeg distribution always ships
    ffprobe right next to ffmpeg.
    """
    ffmpeg_dir = str(Path(ffmpeg_path).parent)
    if ffmpeg_dir and ffmpeg_dir != "." and ffmpeg_dir not in os.environ.get("PATH", ""):
        os.environ["PATH"] = ffmpeg_dir + os.pathsep + os.environ.get("PATH", "")


_ensure_ffmpeg_dir_on_path(settings.FFMPEG_PATH)
AudioSegment.converter = settings.FFMPEG_PATH

# pyloudnorm.Meter needs at least ~0.4s of audio (its gating block size); anything shorter
# is tiled (repeated) up to this floor purely for measurement — repetition of the same
# signal doesn't change its average loudness, so this doesn't distort the reading.
_MIN_MEASURABLE_SECONDS = 0.5

# Loudness gain is clamped to this range so a near-silent or corrupt track can't be
# "normalized" into an ear-splitting boost (measured loudness of -inf/near-inf would
# otherwise imply an unbounded gain).
_MAX_GAIN_DB = 24.0


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _segment_to_float_array(segment: AudioSegment) -> np.ndarray:
    """Convert a pydub segment to a float64 array in [-1.0, 1.0], shaped for pyloudnorm."""
    samples = np.array(segment.get_array_of_samples()).astype(np.float64)
    max_amplitude = float(2 ** (8 * segment.sample_width - 1))
    samples = samples / max_amplitude
    if segment.channels > 1:
        samples = samples.reshape((-1, segment.channels))
    return samples


def _measure_lufs(segment: AudioSegment) -> float:
    """Measure integrated loudness (LUFS, ITU-R BS.1770) of a segment."""
    data = _segment_to_float_array(segment)
    min_samples = int(math.ceil(_MIN_MEASURABLE_SECONDS * segment.frame_rate))
    if len(data) < min_samples:
        reps = int(math.ceil(min_samples / len(data)))
        data = np.tile(data, (reps, 1) if data.ndim > 1 else reps)
    meter = pyln.Meter(segment.frame_rate)
    return meter.integrated_loudness(data)


def _normalize_to_target(segment: AudioSegment, target_lufs: float) -> tuple[AudioSegment, float]:
    """Apply gain so `segment` matches `target_lufs`, returning (segment, measured_lufs_after)."""
    measured = _measure_lufs(segment)
    if math.isinf(measured) or math.isnan(measured):
        # Digital silence or a degenerate signal: nothing meaningful to normalize.
        return segment, measured
    gain_db = max(-_MAX_GAIN_DB, min(_MAX_GAIN_DB, target_lufs - measured))
    normalized = segment.apply_gain(gain_db)
    return normalized, _measure_lufs(normalized)


def _loop_to_length(segment: AudioSegment, target_ms: int) -> AudioSegment:
    """Loop (or trim) `segment` to exactly `target_ms` milliseconds."""
    if len(segment) == 0:
        return AudioSegment.silent(duration=target_ms, frame_rate=segment.frame_rate)
    repeats = math.ceil(target_ms / len(segment))
    return (segment * repeats)[:target_ms]


def _duck_music(music: AudioSegment, ceiling_dbfs: float) -> AudioSegment:
    """Cap `music`'s level at `ceiling_dbfs`, never boosting an already-quiet track."""
    if music.dBFS == float("-inf"):
        return music
    if music.dBFS > ceiling_dbfs:
        return music.apply_gain(ceiling_dbfs - music.dBFS)
    return music


def _mix_project_sync(
    speaker_names_by_id: dict[str, str],
    lines: list[dict],
    background_music_path: Path | None,
    output_dir: Path,
) -> dict:
    """Pure, blocking pydub/pyloudnorm work — must run off the event loop (asyncio.to_thread)."""
    segments: list[AudioSegment] = []
    timestamps: list[dict] = []
    cursor_ms = 0
    previous_speaker_id: str | None = None

    for line in lines:
        line_audio = AudioSegment.from_file(line["audio_cache_path"])
        if previous_speaker_id is not None:
            gap_ms = (
                SILENCE_SAME_SPEAKER_MS
                if line["speaker_id"] == previous_speaker_id
                else SILENCE_DIFFERENT_SPEAKER_MS
            )
            segments.append(AudioSegment.silent(duration=gap_ms, frame_rate=line_audio.frame_rate))
            cursor_ms += gap_ms

        start_ms = cursor_ms
        segments.append(line_audio)
        cursor_ms += len(line_audio)
        timestamps.append(
            {
                "start_sec": round(start_ms / 1000, 3),
                "end_sec": round(cursor_ms / 1000, 3),
                "label": speaker_names_by_id.get(line["speaker_id"], line["speaker_id"]),
                "speaker_id": line["speaker_id"],
            }
        )
        previous_speaker_id = line["speaker_id"]

    mixed = segments[0]
    for segment in segments[1:]:
        mixed += segment

    mixed, _ = _normalize_to_target(mixed, TARGET_LOUDNESS_LUFS)

    if background_music_path is not None:
        music = AudioSegment.from_file(background_music_path)
        music = _loop_to_length(music, len(mixed))
        music = _duck_music(music, MUSIC_DUCKING_MAX_DBFS)
        mixed = mixed.overlay(music)

    final_loudness = _measure_lufs(mixed)

    output_dir.mkdir(parents=True, exist_ok=True)
    mp3_path = output_dir / "mix.mp3"
    wav_path = output_dir / "mix.wav"
    mixed.export(mp3_path, format="mp3", bitrate=MP3_BITRATE)
    mixed_wav = mixed.set_frame_rate(WAV_SAMPLE_RATE_HZ).set_sample_width(WAV_BIT_DEPTH // 8)
    mixed_wav.export(wav_path, format="wav")

    return {
        "mp3_path": str(mp3_path),
        "wav_path": str(wav_path),
        "timestamps": timestamps,
        "duration_seconds": round(len(mixed) / 1000, 3),
        "loudness_lufs": None if math.isinf(final_loudness) else round(float(final_loudness), 2),
    }


async def mix_project(
    project: dict,
    lines: list[dict],
    background_music_filename: str | None = None,
) -> dict:
    """Mix a project's synthesized lines into one podcast track.

    Args:
        project: Project dict (must include "id" and "speakers").
        lines: Script lines ordered by line_index, each with "speaker_id" and
            "audio_cache_path" (already synthesized — see module docstring).
        background_music_filename: Optional filename under `data/music_library/`.

    Raises:
        AudioMixError: If any line has no cached audio, or the named music file
            doesn't exist, or pydub/ffmpeg fails.
    """
    if not lines:
        raise AudioMixError("Cannot mix audio: project has no script lines.")
    missing = [line["id"] for line in lines if not line.get("audio_cache_path")]
    if missing:
        raise AudioMixError(f"Line(s) not yet synthesized: {', '.join(missing)}")

    background_music_path: Path | None = None
    if background_music_filename:
        candidate = settings.DATA_DIR / "music_library" / background_music_filename
        if not candidate.is_file():
            raise AudioMixError(f"Background music file not found: {background_music_filename}")
        background_music_path = candidate

    speaker_names_by_id = {speaker["id"]: speaker["name"] for speaker in project["speakers"]}
    output_dir = settings.DATA_DIR / "audio" / project["id"]

    try:
        return await asyncio.to_thread(
            _mix_project_sync, speaker_names_by_id, lines, background_music_path, output_dir
        )
    except AudioMixError:
        raise
    except Exception as exc:
        raise AudioMixError(f"Audio mixing failed: {exc}") from exc


async def get_lines_for_mixing(db: aiosqlite.Connection, project_id: str) -> list[dict]:
    """Script lines with the fields AudioService needs, ordered by line_index."""
    cursor = await db.execute(
        "SELECT id, line_index, speaker_id, audio_cache_path, duration_seconds "
        "FROM script_lines WHERE project_id = ? ORDER BY line_index",
        (project_id,),
    )
    rows = await cursor.fetchall()
    return [dict(row) for row in rows]


def _row_to_job(row: aiosqlite.Row) -> dict:
    job = dict(row)
    job["timestamps"] = json.loads(job["timestamps_json"]) if job["timestamps_json"] else []
    del job["timestamps_json"]
    return job


async def get_audio_job(db: aiosqlite.Connection, project_id: str) -> dict | None:
    """Fetch a project's audio job row, or None if audio has never been generated."""
    cursor = await db.execute(
        "SELECT id, project_id, status, mp3_path, wav_path, timestamps_json, "
        "background_music, duration_seconds, loudness_lufs, error_message, "
        "started_at, completed_at FROM audio_jobs WHERE project_id = ?",
        (project_id,),
    )
    row = await cursor.fetchone()
    return None if row is None else _row_to_job(row)


async def save_audio_job(
    db: aiosqlite.Connection,
    project_id: str,
    *,
    status: str,
    mp3_path: str | None = None,
    wav_path: str | None = None,
    timestamps: list[dict] | None = None,
    background_music: str | None = None,
    duration_seconds: float | None = None,
    loudness_lufs: float | None = None,
    error_message: str | None = None,
    commit: bool = True,
) -> dict:
    """Create or replace the audio job row for a project (UPSERT on project_id)."""
    now = _now()
    completed_at = now if status in ("complete", "error") else None
    await db.execute(
        "INSERT INTO audio_jobs "
        "(id, project_id, status, mp3_path, wav_path, timestamps_json, background_music, "
        "duration_seconds, loudness_lufs, error_message, started_at, completed_at) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?) "
        "ON CONFLICT(project_id) DO UPDATE SET "
        "status = excluded.status, mp3_path = excluded.mp3_path, wav_path = excluded.wav_path, "
        "timestamps_json = excluded.timestamps_json, background_music = excluded.background_music, "
        "duration_seconds = excluded.duration_seconds, loudness_lufs = excluded.loudness_lufs, "
        "error_message = excluded.error_message, started_at = excluded.started_at, "
        "completed_at = excluded.completed_at",
        (
            str(uuid.uuid4()),
            project_id,
            status,
            mp3_path,
            wav_path,
            json.dumps(timestamps) if timestamps is not None else None,
            background_music,
            duration_seconds,
            loudness_lufs,
            error_message,
            now,
            completed_at,
        ),
    )
    if commit:
        await db.commit()
    return await get_audio_job(db, project_id)
