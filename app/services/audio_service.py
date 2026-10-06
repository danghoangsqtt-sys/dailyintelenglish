"""Mixes per-line TTS audio into one podcast track (Task 1.6, Sub-task 1.6b).

Responsibility split from TTSService (ARCHITECTURE.md "Module Dependencies"): this module
only processes already-synthesized audio files — it never calls a TTS engine itself. The
caller (app/api/audio.py) is responsible for making sure every line has a cached audio file
before calling `mix_project`.

Background music (Task 22.4, D51) goes through `music_bed`: loudness-normalised, fitted to the
length with crossfade loops, ducked under each spoken line and faded in/out. The mix also writes a
voice-only stem (`voice.wav`), so the video render can build a full-length soundtrack that covers
the Enhanced intro/outro (`build_soundtrack`). The old flat-ceiling helpers (`_duck_music`,
`_loop_to_length`) are kept for reference tests only.
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
    SILENCE_DIFFERENT_SPEAKER_MS,
    SILENCE_SAME_SPEAKER_MS,
    TARGET_LOUDNESS_LUFS,
    WAV_BIT_DEPTH,
    WAV_SAMPLE_RATE_HZ,
)
from app.core.exceptions import AudioMixError
from app.services import music_bed


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


def _aggregate_word_boundaries(audio_cache_path: str, start_ms: int) -> list[dict]:
    """Task 19.2 (D19.2-c): read a line's raw per-word sidecar (written by
    `tts_service.synthesize_line_audio`, one MP3 per line so the derived path is safe) and
    aggregate onto the mixed timeline using `start_ms` -- the exact same offset already used
    for this line's `timestamps_json` entry above, not a second computation.

    Returns an empty list, never `None`, when there's no sidecar (omnivoice lines, or any
    line synthesized before this task existed) -- both cases mean "no words available for
    this line" and are indistinguishable at aggregation time, which is fine (see design doc).
    """
    sidecar_path = Path(audio_cache_path).with_suffix(".words.json")
    if not sidecar_path.is_file():
        return []
    raw_words = json.loads(sidecar_path.read_text(encoding="utf-8"))
    start_sec = start_ms / 1000
    return [
        {
            "text": word["text"],
            "start_sec": round(start_sec + word["offset_sec"], 3),
            "end_sec": round(start_sec + word["offset_sec"] + word["duration_sec"], 3),
        }
        for word in raw_words
    ]


def _mix_project_sync(
    speaker_names_by_id: dict[str, str],
    lines: list[dict],
    background_music_path: Path | None,
    output_dir: Path,
) -> dict:
    """Pure, blocking pydub/pyloudnorm work — must run off the event loop (asyncio.to_thread)."""
    segments: list[AudioSegment] = []
    timestamps: list[dict] = []
    word_timestamps: list[dict] = []
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
                "text": line.get("text", ""),
            }
        )
        word_timestamps.append(
            {"line_id": line["id"], "words": _aggregate_word_boundaries(line["audio_cache_path"], start_ms)}
        )
        previous_speaker_id = line["speaker_id"]

    mixed = segments[0]
    for segment in segments[1:]:
        mixed += segment

    # The voice-only stem, normalised exactly as a music-free mix is; with no music it IS the mix.
    voice, final_loudness = _normalize_to_target(mixed, TARGET_LOUDNESS_LUFS)
    output_dir.mkdir(parents=True, exist_ok=True)
    voice.export(output_dir / VOICE_STEM_NAME, format="wav")
    mixed = voice

    if background_music_path is not None:
        # Task 22.4: the bed over the speech span (the video adds the intro/outro itself). The
        # FINAL mix is normalised as a whole (Task 2.1c: measuring only the voice stem left the
        # delivered file up to 1.12 dB off target).
        voice_audio = music_bed.from_segment(voice)
        spans = [(entry["start_sec"], entry["end_sec"]) for entry in timestamps]
        bed = music_bed.build_bed(music_bed.decode(background_music_path), voice_audio.shape[1], spans)
        mixed = music_bed.to_segment(music_bed.mix(voice_audio, bed))
        final_loudness = _measure_lufs(mixed)

    mp3_path = output_dir / "mix.mp3"
    wav_path = output_dir / "mix.wav"
    mixed.export(mp3_path, format="mp3", bitrate=MP3_BITRATE)
    mixed_wav = mixed.set_frame_rate(WAV_SAMPLE_RATE_HZ).set_sample_width(WAV_BIT_DEPTH // 8)
    mixed_wav.export(wav_path, format="wav")

    return {
        "mp3_path": str(mp3_path),
        "wav_path": str(wav_path),
        "timestamps": timestamps,
        "word_timestamps": word_timestamps,
        "duration_seconds": round(len(mixed) / 1000, 3),
        "loudness_lufs": None if math.isinf(final_loudness) else round(float(final_loudness), 2),
    }


VOICE_STEM_NAME = "voice.wav"
SOUNDTRACK_NAME = "soundtrack.mp3"


def voice_stem_path(project_id: str) -> Path:
    return settings.DATA_DIR / "audio" / project_id / VOICE_STEM_NAME


def _place(track: np.ndarray, audio: np.ndarray, start_s: float) -> float:
    """Add `audio` into `track` at `start_s` (clipped to the track); returns where it ends."""
    offset = int(round(start_s * music_bed.SAMPLE_RATE))
    length = max(0, min(audio.shape[1], track.shape[1] - offset))
    track[:, offset:offset + length] += audio[:, :length]
    return (offset + length) / music_bed.SAMPLE_RATE


def _build_soundtrack_sync(voice_path: Path, music_path: Path, timestamps: list[dict], lead_in_s: float,
                           total_s: float, output_path: Path,
                           extra_voices: list[tuple[str, float]] | None = None) -> dict:
    """Blocking: lead-in + voice + tail as one soundtrack exactly `total_s` long, with the music
    bed over all of it -- open in the lead-in and tail, ducked under every line, faded out to
    silence on the last sample. Phase 25: `extra_voices` (the branded greeting and farewell) are
    placed at their start times, at the voice's loudness, and the music ducks under them too."""
    voice = music_bed.from_segment(AudioSegment.from_file(voice_path))
    total = int(round(total_s * music_bed.SAMPLE_RATE))
    placed = np.zeros((music_bed.CHANNELS, total), dtype=np.float32)
    _place(placed, voice, lead_in_s)
    spans = [(entry["start_sec"] + lead_in_s, entry["end_sec"] + lead_in_s) for entry in timestamps]
    for path, start_s in extra_voices or []:
        extra = music_bed.normalise(music_bed.decode(Path(path)), TARGET_LOUDNESS_LUFS)
        spans.append((start_s, _place(placed, extra, start_s)))
    bed = music_bed.build_bed(music_bed.decode(music_path), total, spans)
    soundtrack = music_bed.to_segment(music_bed.mix(placed, bed))
    output_path.parent.mkdir(parents=True, exist_ok=True)
    soundtrack.export(output_path, format="mp3", bitrate=MP3_BITRATE)
    return {"path": str(output_path), "duration_seconds": round(total / music_bed.SAMPLE_RATE, 3),
            "lead_in_seconds": lead_in_s}


async def build_soundtrack(audio_job: dict, lead_in_s: float, total_s: float, output_path: Path,
                           extra_voices: list[tuple[str, float]] | None = None) -> dict | None:
    """Task 22.4 (D51): the full-video soundtrack, or None when the episode has no music or was
    mixed before voice stems existed (the caller then uses the plain mix, unchanged)."""
    filename = audio_job.get("background_music")
    if not filename:
        return None
    music_path = settings.DATA_DIR / "music_library" / _validate_music_filename(filename)
    voice_path = voice_stem_path(audio_job["project_id"])
    if not await asyncio.to_thread(music_path.is_file) or not await asyncio.to_thread(voice_path.is_file):
        return None
    try:
        return await asyncio.to_thread(_build_soundtrack_sync, voice_path, music_path, audio_job["timestamps"],
                                       lead_in_s, total_s, output_path, extra_voices)
    except Exception as exc:
        raise AudioMixError(f"Building the music soundtrack failed: {exc}") from exc


def _validate_music_filename(filename: str) -> str:
    """Reject a background-music filename that could escape `data/music_library/`.

    Same character-level check as `app/api/music.py::_validate_filename` — this is a
    separate call site (mix_project accepts a bare filename from the audio-generate
    request body, not the music-library upload/list/delete routes) so it needs its own
    guard rather than assuming a filename reaching here was already validated there.
    Without this, an absolute path (e.g. "C:/Windows/win.ini") silently discards the
    `music_library` base entirely (pathlib join semantics), and "../"-style relative
    paths escape it just as easily.
    """
    cleaned = filename.strip()
    if (
        not cleaned
        or cleaned != filename
        or cleaned in {".", ".."}
        or "/" in cleaned
        or "\\" in cleaned
        or Path(cleaned).name != cleaned
        or Path(cleaned).is_absolute()
    ):
        raise AudioMixError(f"Invalid background music filename: {filename!r}")
    return cleaned


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
        safe_name = _validate_music_filename(background_music_filename)
        candidate = settings.DATA_DIR / "music_library" / safe_name
        if not await asyncio.to_thread(candidate.is_file):
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
        "SELECT id, line_index, speaker_id, text, audio_cache_path, duration_seconds "
        "FROM script_lines WHERE project_id = ? ORDER BY line_index",
        (project_id,),
    )
    rows = await cursor.fetchall()
    return [dict(row) for row in rows]


def _row_to_job(row: aiosqlite.Row) -> dict:
    job = dict(row)
    job["timestamps"] = json.loads(job["timestamps_json"]) if job["timestamps_json"] else []
    del job["timestamps_json"]
    # Task 19.2: additive column, NULL for every row created before this task -- reads back
    # as an empty list, same fallback pattern as timestamps_json above, never a crash.
    job["word_timestamps"] = json.loads(job["word_timestamps_json"]) if job["word_timestamps_json"] else []
    del job["word_timestamps_json"]
    return job


async def get_audio_job(db: aiosqlite.Connection, project_id: str) -> dict | None:
    """Fetch a project's audio job row, or None if audio has never been generated."""
    cursor = await db.execute(
        "SELECT id, project_id, status, mp3_path, wav_path, timestamps_json, "
        "word_timestamps_json, background_music, duration_seconds, loudness_lufs, "
        "error_message, started_at, completed_at FROM audio_jobs WHERE project_id = ?",
        (project_id,),
    )
    row = await cursor.fetchone()
    return None if row is None else _row_to_job(row)


async def mark_audio_job_failed(
    db: aiosqlite.Connection,
    project_id: str,
    error_message: str,
    commit: bool = True,
) -> dict:
    """Record a failed generation attempt without discarding a prior successful mix.

    Existing rows retain every artifact and metadata column. A project whose first
    attempt fails receives the same minimal error row that the former error-path
    ``save_audio_job`` call created.
    """
    now = _now()
    cursor = await db.execute(
        "UPDATE audio_jobs SET status = 'error', error_message = ?, completed_at = ? "
        "WHERE project_id = ?",
        (error_message, now, project_id),
    )
    if cursor.rowcount == 0:
        await db.execute(
            "INSERT INTO audio_jobs "
            "(id, project_id, status, error_message, started_at, completed_at) "
            "VALUES (?, ?, 'error', ?, ?, ?)",
            (str(uuid.uuid4()), project_id, error_message, now, now),
        )
    if commit:
        await db.commit()
    return await get_audio_job(db, project_id)


async def save_audio_job(
    db: aiosqlite.Connection,
    project_id: str,
    *,
    status: str,
    mp3_path: str | None = None,
    wav_path: str | None = None,
    timestamps: list[dict] | None = None,
    word_timestamps: list[dict] | None = None,
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
        "(id, project_id, status, mp3_path, wav_path, timestamps_json, word_timestamps_json, "
        "background_music, duration_seconds, loudness_lufs, error_message, started_at, completed_at) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?) "
        "ON CONFLICT(project_id) DO UPDATE SET "
        "status = excluded.status, mp3_path = excluded.mp3_path, wav_path = excluded.wav_path, "
        "timestamps_json = excluded.timestamps_json, word_timestamps_json = excluded.word_timestamps_json, "
        "background_music = excluded.background_music, "
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
            json.dumps(word_timestamps) if word_timestamps is not None else None,
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
