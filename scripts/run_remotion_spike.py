"""Task 19.1 (Phase 19, ENH-013) -- Remotion spike measurement runner.

Renders ONE real, already-completed project through the `video-renderer/` Remotion
composition and measures wall time, output correctness, and disk footprint, per
`.viepilot/phases/19-remotion/tasks/task-19.1.md` (design decisions D19.1-a..f).

This is a measurement script, not app code: it is never imported by `app/`, and it never
touches `app/services/video_service.py` or the ffmpeg fallback path.

**Read-only, always.** The real DB (`data/app.db`) is opened via SQLite's `mode=ro` URI --
a real OS-level read-only handle, not the app's shared read-write singleton
(`app/db/database.py`) -- so a bug here cannot write to it even by accident (D19.1-e).

Usage:
    venv\\Scripts\\python scripts\\run_remotion_spike.py

Prints a JSON measurement block to stdout. `docs/operations/phase19-spike-remotion.md` is
filled in by hand from this output plus the handful of measurements that need a human
(peak RAM via Task Manager, the packaging-size estimate, the PASS/SCOPE-CUT/STOP proposal).
"""

from __future__ import annotations

import asyncio
import json
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from typing import Any

import aiosqlite

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from app.core.config import settings  # noqa: E402
from app.services import audio_service, project_service  # noqa: E402

VIDEO_RENDERER_DIR = PROJECT_ROOT / "video-renderer"
SPIKE_AUDIO_DIR = VIDEO_RENDERER_DIR / "public" / "spike-audio"
SPIKE_OUTPUT_DIR = settings.DATA_DIR / "tmp" / "phase19_spike"

TARGET_CEFR_LEVEL = "B1"
TARGET_DURATION_SECONDS = 8 * 60
RENDER_FPS = 30
RENDER_WIDTH = 1280
RENDER_HEIGHT = 720
RENDER_TIMEOUT_FLOOR_SECONDS = 600.0
RENDER_TIMEOUT_PER_AUDIO_SECOND = 8.0


class SpikeError(RuntimeError):
    """Raised for any condition that should stop the spike before it renders."""


async def _select_project(db: aiosqlite.Connection) -> tuple[dict, dict]:
    """Pick the B1 project with a completed audio mix whose duration is closest to 8
    minutes (D19.1-e). Real-DB check (2026-09-28): no project has `status = 'complete'`
    yet (that status is never reached by any project currently in the DB, and the only
    project with a completed `audio_jobs` row is `status = 'video_generated'`) -- so
    selection is driven by `audio_jobs.status = 'complete'` directly rather than
    `projects.status`, which turned out not to be a reliable "has audio" signal."""
    cursor = await db.execute(
        "SELECT id, created_at FROM projects WHERE cefr_level = ? ORDER BY created_at DESC",
        (TARGET_CEFR_LEVEL,),
    )
    candidate_ids = [row[0] for row in await cursor.fetchall()]
    if not candidate_ids:
        raise SpikeError(f"No project with cefr_level='{TARGET_CEFR_LEVEL}' found.")

    best_project: dict | None = None
    best_audio_job: dict | None = None
    best_gap = float("inf")
    for project_id in candidate_ids:
        audio_job = await audio_service.get_audio_job(db, project_id)
        if audio_job is None or audio_job.get("status") != "complete":
            continue
        gap = abs(audio_job["duration_seconds"] - TARGET_DURATION_SECONDS)
        if gap < best_gap:
            project = await project_service.get_project(db, project_id)
            best_project, best_audio_job, best_gap = project, audio_job, gap

    if best_project is None or best_audio_job is None:
        raise SpikeError("No candidate project has a completed audio mix.")
    return best_project, best_audio_job


def _build_input_props(project: dict, audio_job: dict) -> dict[str, Any]:
    """D19.1-b: strict passthrough of AudioService's already-measured per-line timestamps.
    No new DB read paths, no per-word timing."""
    lines = [
        {
            "startSec": entry["start_sec"],
            "endSec": entry["end_sec"],
            "speaker": entry["label"],
            "text": entry["text"],
        }
        for entry in audio_job["timestamps"]
    ]
    return {
        "episodeId": project["id"],
        "lines": lines,
        "audioPath": f"spike-audio/{project['id']}.mp3",
        "fps": RENDER_FPS,
        "width": RENDER_WIDTH,
        "height": RENDER_HEIGHT,
    }


def _copy_audio_into_public(project_id: str, mp3_path: str) -> Path:
    """D19.1-d addendum: Remotion can't read an absolute filesystem path as an asset src --
    every asset must live under video-renderer/public/ and be loaded via staticFile()."""
    SPIKE_AUDIO_DIR.mkdir(parents=True, exist_ok=True)
    destination = SPIKE_AUDIO_DIR / f"{project_id}.mp3"
    shutil.copyfile(mp3_path, destination)
    return destination


def _render_timeout_seconds(audio_duration_seconds: float) -> float:
    return max(RENDER_TIMEOUT_FLOOR_SECONDS, RENDER_TIMEOUT_PER_AUDIO_SECOND * audio_duration_seconds)


def _run_render(input_props: dict[str, Any], output_path: Path, timeout_seconds: float) -> dict[str, Any]:
    """D19.1-d: props via a temp JSON file (never inline on argv), wall time measured with
    `time.monotonic()` around the subprocess boundary."""
    output_path.parent.mkdir(parents=True, exist_ok=True)

    props_file = tempfile.NamedTemporaryFile(
        mode="w", suffix=".json", delete=False, encoding="utf-8"
    )
    try:
        json.dump(input_props, props_file)
        props_file.close()

        npx = shutil.which("npx.cmd") or shutil.which("npx") or "npx"
        command = [
            npx,
            "remotion",
            "render",
            "src/index.ts",
            "Episode",
            str(output_path),
            f"--props={props_file.name}",
        ]

        start = time.monotonic()
        result = subprocess.run(
            command,
            cwd=VIDEO_RENDERER_DIR,
            capture_output=True,
            text=True,
            timeout=timeout_seconds,
        )
        wall_time_seconds = time.monotonic() - start
    finally:
        Path(props_file.name).unlink(missing_ok=True)

    return {
        "wall_time_seconds": round(wall_time_seconds, 3),
        "exit_code": result.returncode,
        "stdout": result.stdout,
        "stderr": result.stderr,
    }


def _ffprobe_json(path: Path) -> dict[str, Any]:
    ffprobe = shutil.which("ffprobe") or "ffprobe"
    result = subprocess.run(
        [
            ffprobe,
            "-v", "error",
            "-print_format", "json",
            "-show_format",
            "-show_streams",
            str(path),
        ],
        capture_output=True,
        text=True,
        timeout=60,
    )
    if result.returncode != 0:
        raise SpikeError(f"ffprobe failed on {path}: {result.stderr}")
    return json.loads(result.stdout)


def _dir_size_bytes(path: Path) -> int:
    if not path.is_dir():
        return 0
    return sum(f.stat().st_size for f in path.rglob("*") if f.is_file())


async def _main() -> dict[str, Any]:
    db_uri = f"file:{settings.db_path.as_posix()}?mode=ro"
    db = await aiosqlite.connect(db_uri, uri=True)
    db.row_factory = aiosqlite.Row
    try:
        project, audio_job = await _select_project(db)
    finally:
        await db.close()

    project_id = project["id"]
    input_props = _build_input_props(project, audio_job)
    _copy_audio_into_public(project_id, audio_job["mp3_path"])

    # Resolved to absolute: the render subprocess runs with cwd=video-renderer/, and a
    # relative path here would land under video-renderer/ instead of the intended
    # data/tmp/phase19_spike/ (found by running the spike for real -- exit 0 but the file
    # silently landed in the wrong directory relative to the subprocess's own cwd).
    output_path = (SPIKE_OUTPUT_DIR / f"{project_id}.mp4").resolve()
    timeout_seconds = _render_timeout_seconds(audio_job["duration_seconds"])
    render_result = _run_render(input_props, output_path, timeout_seconds)

    measurements: dict[str, Any] = {
        "project_id": project_id,
        "script_line_count": len(input_props["lines"]),
        "audio_duration_seconds": audio_job["duration_seconds"],
        "audio_file_size_bytes": Path(audio_job["mp3_path"]).stat().st_size,
        "render": render_result,
        "node_modules_size_bytes": _dir_size_bytes(VIDEO_RENDERER_DIR / "node_modules"),
    }

    if render_result["exit_code"] == 0 and output_path.is_file():
        measurements["output_file_size_bytes"] = output_path.stat().st_size
        measurements["output_ffprobe"] = _ffprobe_json(output_path)

    return measurements


if __name__ == "__main__":
    measurements = asyncio.run(_main())
    print(json.dumps(measurements, indent=2))
