"""Task 21.1 (Phase 21) -- Kokoro TTS spike measurement runner.

Runs in this project's own `venv/` (Python 3.14). Orchestrates:
  1. Fetches 3 real B1 script lines from the pinned demo project (mode=ro, matches every
     prior Phase 19 spike's read-only-DB discipline).
  2. Spawns `scripts/kokoro_worker.py` as a subprocess inside `venv-kokoro/` (Python
     3.11 -- Kokoro has no published version compatible with this project's own Python
     3.14, see task-21.1.md D21.1-a), synthesizes each line with 2 Kokoro voices.
  3. Synthesizes the same 3 lines directly (in-process) via the existing
     `tts_service._synthesize_edge_tts`, with 2 Edge TTS voices per line (Guy/Jenny --
     this project's own real `EDGE_TTS_VOICE_MAP["american"]` entries, not the card's
     "Aria/Guy" phrasing, which doesn't match: Aria is the neutral/fallback voice, not a
     male one -- confirmed real by reading app/core/constants.py directly).
  4. Saves 12 self-describing WAV files + a concatenated spike_comparison.mp3 under
     data/tmp/phase21_spike/.
  5. Prints a JSON measurement block to stdout (same convention as
     scripts/run_remotion_spike.py) -- docs/operations/phase21-spike-kokoro.md is filled
     in by hand from this output.

**Read-only, always.** The real DB (`data/app.db`) is opened via SQLite's `mode=ro` URI --
a genuine OS-level read-only handle, not the app's shared read-write singleton.

Usage:
    venv\\Scripts\\python scripts\\spike_kokoro.py
"""

from __future__ import annotations

import asyncio
import json
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

import aiosqlite
from pydub import AudioSegment

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from app.core.config import settings  # noqa: E402
from app.services import tts_service  # noqa: E402

PINNED_PROJECT_ID = "b330d37f-a212-4cf7-a779-7a109098bd6c"
TEST_LINE_INDICES = [0, 24, 29]  # D21.1-c: real lines, line 24 corrected from the card's
# vague "line 5 or similar" -- it has a real idiom ("wake up on the right side of the bed")

KOKORO_VOICES = {"female": "af_heart", "male": "am_michael"}
EDGE_VOICES = {"female": "en-US-JennyNeural", "male": "en-US-GuyNeural"}

VENV_KOKORO_DIR = PROJECT_ROOT / "venv-kokoro"
KOKORO_WORKER_PYTHON = VENV_KOKORO_DIR / "Scripts" / "python.exe"
KOKORO_WORKER_SCRIPT = PROJECT_ROOT / "scripts" / "kokoro_worker.py"
SPIKE_OUTPUT_DIR = settings.DATA_DIR / "tmp" / "phase21_spike"

WORKER_STARTUP_TIMEOUT_SECONDS = 60.0
WORKER_REQUEST_TIMEOUT_SECONDS = 30.0


class SpikeError(RuntimeError):
    """Raised for any condition that should stop the spike before it measures."""


async def _fetch_test_lines(db: aiosqlite.Connection) -> tuple[dict, list[dict]]:
    """Real project + the 3 test lines with their real originating speaker."""
    project_cursor = await db.execute(
        "SELECT id, name, topic, cefr_level FROM projects WHERE id = ?", (PINNED_PROJECT_ID,)
    )
    project_row = await project_cursor.fetchone()
    if project_row is None:
        raise SpikeError(f"Pinned project {PINNED_PROJECT_ID} not found")
    project = dict(project_row)

    speakers_cursor = await db.execute(
        "SELECT id, name, gender, accent, speed, pitch, volume FROM speakers WHERE project_id = ?",
        (PINNED_PROJECT_ID,),
    )
    speakers_by_id = {row["id"]: dict(row) for row in await speakers_cursor.fetchall()}

    lines_cursor = await db.execute(
        "SELECT line_index, speaker_id, text FROM script_lines WHERE project_id = ? ORDER BY line_index",
        (PINNED_PROJECT_ID,),
    )
    all_lines = {row["line_index"]: dict(row) for row in await lines_cursor.fetchall()}

    lines = []
    for index in TEST_LINE_INDICES:
        if index not in all_lines:
            raise SpikeError(f"Line index {index} not found in pinned project's script")
        line = all_lines[index]
        speaker = speakers_by_id.get(line["speaker_id"])
        if speaker is None:
            raise SpikeError(f"Speaker {line['speaker_id']} not found for line {index}")
        lines.append({"index": index, "text": line["text"], "speaker": speaker})
    return project, lines


def _start_kokoro_worker() -> subprocess.Popen:
    if not KOKORO_WORKER_PYTHON.is_file():
        raise SpikeError(
            f"{KOKORO_WORKER_PYTHON} not found -- set up venv-kokoro first: "
            "py -3.11 -m venv venv-kokoro && venv-kokoro\\Scripts\\pip install -r requirements-kokoro.txt"
        )
    stderr_log = SPIKE_OUTPUT_DIR / "kokoro_worker_stderr.log"
    SPIKE_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    process = subprocess.Popen(
        [str(KOKORO_WORKER_PYTHON), str(KOKORO_WORKER_SCRIPT)],
        cwd=PROJECT_ROOT,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=open(stderr_log, "w", encoding="utf-8"),
        text=True,
        bufsize=1,
    )
    return process


def _kokoro_request(process: subprocess.Popen, text: str, voice: str, output_path: Path) -> dict[str, Any]:
    request = {"text": text, "voice": voice, "output_path": str(output_path)}
    assert process.stdin is not None and process.stdout is not None
    process.stdin.write(json.dumps(request) + "\n")
    process.stdin.flush()
    response_line = process.stdout.readline()
    if not response_line:
        raise SpikeError("kokoro_worker closed stdout unexpectedly (crashed?) -- see kokoro_worker_stderr.log")
    return json.loads(response_line)


async def _edge_tts_request(text: str, voice_id: str, output_path: Path) -> dict[str, Any]:
    """Builds a minimal speaker dict matching `_synthesize_edge_tts`'s real signature
    (accent/gender resolved to the exact `voice_id` via a synthetic accent key, rather
    than reusing a real project speaker's accent -- this spike wants an exact voice pick
    per D21.1-c, not accent-derived resolution)."""
    from app.core.constants import EDGE_TTS_VOICE_MAP

    accent_key = next(
        (accent for accent, genders in EDGE_TTS_VOICE_MAP.items() if voice_id in genders.values()), "american"
    )
    gender = next(
        gender for gender, vid in EDGE_TTS_VOICE_MAP[accent_key].items() if vid == voice_id
    )
    speaker = {"accent": accent_key, "gender": gender, "speed": 1.0, "volume": 1.0, "pitch": 0.0}

    start = time.monotonic()
    audio_bytes, word_boundaries = await tts_service._synthesize_edge_tts(text, speaker)
    wall_time_sec = time.monotonic() - start

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_bytes(audio_bytes)
    audio = AudioSegment.from_file(output_path)
    duration_sec = len(audio) / 1000

    return {
        "status": "ok",
        "duration_sec": round(duration_sec, 4),
        "wall_time_sec": round(wall_time_sec, 4),
        "word_boundaries": [
            {"text": wb.text, "offset_sec": round(wb.offset_sec, 4), "duration_sec": round(wb.duration_sec, 4)}
            for wb in word_boundaries
        ],
    }


def _build_comparison_mp3(clip_paths: list[Path], output_path: Path) -> None:
    """Concatenates all real clips with 1s silence between each, per D21.1-f."""
    silence = AudioSegment.silent(duration=1000)
    combined = AudioSegment.empty()
    for index, path in enumerate(clip_paths):
        if index > 0:
            combined += silence
        combined += AudioSegment.from_file(path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    combined.export(output_path, format="mp3", bitrate="192k")


async def _main() -> dict[str, Any]:
    db_uri = f"file:{settings.db_path.as_posix()}?mode=ro"
    db = await aiosqlite.connect(db_uri, uri=True)
    db.row_factory = aiosqlite.Row
    try:
        project, lines = await _fetch_test_lines(db)
    finally:
        await db.close()

    SPIKE_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    clips: list[dict[str, Any]] = []
    clip_paths_in_order: list[Path] = []

    worker = _start_kokoro_worker()
    worker_start = time.monotonic()
    kokoro_import_load_seconds: float | None = None
    try:
        for line in lines:
            for gender, voice in KOKORO_VOICES.items():
                filename = f"kokoro_{gender}_{voice}_line{line['index']}.wav"
                output_path = SPIKE_OUTPUT_DIR / filename
                result = _kokoro_request(worker, line["text"], voice, output_path)
                if kokoro_import_load_seconds is None:
                    # First real request pays the one-time model-load cost too --
                    # reported separately below via the worker's own stderr log line,
                    # this field just marks when the worker became ready to measure from.
                    kokoro_import_load_seconds = time.monotonic() - worker_start
                clips.append(
                    {"engine": "kokoro", "voice": voice, "gender": gender, "line_index": line["index"],
                     "filename": filename, **result}
                )
                if result["status"] == "ok":
                    clip_paths_in_order.append(output_path)
    finally:
        if worker.stdin:
            worker.stdin.close()
        worker.wait(timeout=WORKER_STARTUP_TIMEOUT_SECONDS)

    for line in lines:
        for gender, voice_id in EDGE_VOICES.items():
            filename = f"edge_{gender}_line{line['index']}.mp3"
            output_path = SPIKE_OUTPUT_DIR / filename
            result = await _edge_tts_request(line["text"], voice_id, output_path)
            clips.append(
                {"engine": "edge_tts", "voice": voice_id, "gender": gender, "line_index": line["index"],
                 "filename": filename, **result}
            )
            if result["status"] == "ok":
                clip_paths_in_order.append(output_path)

    comparison_path = SPIKE_OUTPUT_DIR / "spike_comparison.mp3"
    _build_comparison_mp3(clip_paths_in_order, comparison_path)

    return {
        "project": {"id": project["id"], "name": project["name"], "topic": project["topic"],
                     "cefr_level": project["cefr_level"]},
        "lines": [{"index": line_data["index"], "text": line_data["text"],
                    "speaker": line_data["speaker"]["name"]} for line_data in lines],
        "clips": clips,
        "comparison_mp3": str(comparison_path),
        "worker_stderr_log": str(SPIKE_OUTPUT_DIR / "kokoro_worker_stderr.log"),
    }


if __name__ == "__main__":
    measurements = asyncio.run(_main())
    print(json.dumps(measurements, indent=2))
