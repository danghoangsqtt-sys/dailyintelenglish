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
from app.services import audio_service, project_service, tts_service  # noqa: E402

VIDEO_RENDERER_DIR = PROJECT_ROOT / "video-renderer"
SPIKE_AUDIO_DIR = VIDEO_RENDERER_DIR / "public" / "spike-audio"
SPIKE_AVATARS_DIR = VIDEO_RENDERER_DIR / "public" / "avatars"
SPIKE_OUTPUT_DIR = settings.DATA_DIR / "tmp" / "phase19_spike"

TARGET_CEFR_LEVEL = "B1"
TARGET_DURATION_SECONDS = 8 * 60
# Task 19.5: pinned to the same episode every prior Phase 19 task (19.1-19.4) rendered and
# measured against, for wall-time comparability -- a new real project
# (c08ce057-792a-44db-be5d-2585e6600f4b, "Demo Episode", 5:00) appeared in the real DB during
# the T6 report-prep window (closer to the 8-min target than this one's 2:56), and the
# "closest to target" selection logic below would otherwise silently switch to it, making
# every wall-time comparison against 19.3/19.4's baseline meaningless (a longer episode
# renders slower for reasons that have nothing to do with this task's own composition cost).
# Falls back to the general "closest to 8 minutes" logic if this specific project is ever
# gone (e.g. a fresh checkout with no prior state).
PINNED_PROJECT_ID = "b330d37f-a212-4cf7-a779-7a109098bd6c"
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
    `projects.status`, which turned out not to be a reliable "has audio" signal.

    Task 19.5: checks `PINNED_PROJECT_ID` first (see its own comment) before falling back to
    the general "closest to target" search below.
    """
    pinned_audio_job = await audio_service.get_audio_job(db, PINNED_PROJECT_ID)
    if pinned_audio_job is not None and pinned_audio_job.get("status") == "complete":
        return await project_service.get_project(db, PINNED_PROJECT_ID), pinned_audio_job

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


def _find_speaker(project: dict, speaker_id: str) -> dict:
    for speaker in project["speakers"]:
        if speaker["id"] == speaker_id:
            return speaker
    raise SpikeError(f"Speaker {speaker_id} not found on project {project['id']}")


def _words_to_props(words: list[dict]) -> list[dict]:
    """`audio_jobs.word_timestamps_json`'s per-word shape (`start_sec`/`end_sec`) to the
    video-renderer props shape (`startSec`/`endSec`, D19.2-d vs. types.ts's `episodeWordSchema`)."""
    return [{"text": word["text"], "startSec": word["start_sec"], "endSec": word["end_sec"]} for word in words]


async def _resynthesize_word_timestamps(project: dict, audio_job: dict) -> list[list[dict]]:
    """Task 19.3 (D19.3-d): the real DB currently has no captured word data for any
    completed-audio episode -- `word_timestamps_json` is NULL and no `.words.json` sidecar
    exists for this project (it predates Task 19.2's capture code and hasn't been re-mixed,
    which would need a forbidden real-DB write). Re-synthesizes each line fresh via a real
    Edge TTS call, **in memory only**: the freshly synthesized audio bytes are discarded (the
    existing cached mix is what actually plays), only the real per-word timing is kept,
    aggregated onto the line's *existing* mix-timeline offset using the exact same formula as
    `audio_service._aggregate_word_boundaries`. Nothing is written to `data/app.db` or to
    `data/tts_cache/` -- the real project's cached files are never touched.

    Returns a list (one entry per `audio_job["timestamps"]` line, same order) of
    already-props-shaped word lists (`{text, startSec, endSec}`).
    """
    per_line_words: list[list[dict]] = []
    for entry in audio_job["timestamps"]:
        speaker = _find_speaker(project, entry["speaker_id"])
        _audio_bytes, word_boundaries = await tts_service._synthesize_edge_tts(entry["text"], speaker)
        start_sec = entry["start_sec"]
        per_line_words.append(
            [
                {
                    "text": wb.text,
                    "startSec": round(start_sec + wb.offset_sec, 3),
                    "endSec": round(start_sec + wb.offset_sec + wb.duration_sec, 3),
                }
                for wb in word_boundaries
            ]
        )
    return per_line_words


def _copy_avatar_into_public(speaker_id: str, avatar_image_path: str) -> str:
    """Task 19.4 (D19.4-b): one-way copy from the real, read-only-accessed
    `speakers.avatar_image_path` into `video-renderer/public/avatars/` -- never a symlink,
    never an absolute path passed to Remotion (staticFile() requires a public/-relative
    asset, same pattern as `_copy_audio_into_public`). The real `data/avatars/` directory is
    never written to; this only reads from it and writes to the video-renderer scratch dir."""
    SPIKE_AVATARS_DIR.mkdir(parents=True, exist_ok=True)
    suffix = Path(avatar_image_path).suffix or ".png"
    destination = SPIKE_AVATARS_DIR / f"{speaker_id}{suffix}"
    shutil.copyfile(avatar_image_path, destination)
    return f"avatars/{destination.name}"


def _build_speakers_props(project: dict) -> list[dict[str, Any]]:
    """Task 19.4: project-level speaker list for the persistent chip overlay. Copies any
    non-null `avatar_image_path` into public/avatars/ (D19.4-b); skips the copy silently for
    NULL avatars (the demo project's real speakers, Alex and Maya, both have none -- the
    name-only chip path is what this task's real render actually exercises)."""
    speakers_props = []
    for speaker in project["speakers"]:
        speaker_props: dict[str, Any] = {
            "id": speaker["id"],
            "name": speaker["name"],
            "gender": speaker["gender"],
        }
        if speaker.get("avatar_image_path"):
            speaker_props["avatarUrl"] = _copy_avatar_into_public(speaker["id"], speaker["avatar_image_path"])
        speakers_props.append(speaker_props)
    return speakers_props


async def _fetch_learning_props(db: aiosqlite.Connection, project_id: str) -> dict[str, Any] | None:
    """Task 19.5: `learning_contents` is optional (a project may have none yet) -- returns
    `None` when the row is absent, which the composition treats as "no learning content at
    all" (D19.5, same opportunistic pattern as 19.2's word timings and 19.4's avatars).
    DB field names are snake_case; converted to the same camelCase convention already used
    for `avatarUrl` (D19.4-b) and this task's own vocab/idiom item schemas."""
    cursor = await db.execute(
        "SELECT vocabulary_json, idioms_json FROM learning_contents WHERE project_id = ?",
        (project_id,),
    )
    row = await cursor.fetchone()
    if row is None:
        return None

    vocab = [
        {
            "word": item["word"],
            "partOfSpeech": item["part_of_speech"],
            "ipa": item["ipa"],
            "definitionEn": item["definition_en"],
            "definitionVi": item["definition_vi"],
            "exampleSentence": item["example_sentence"],
        }
        for item in json.loads(row["vocabulary_json"])
    ]
    idioms = [
        {
            "phrase": item["phrase"],
            "meaningEn": item["meaning_en"],
            "meaningVi": item["meaning_vi"],
            "exampleSentence": item["example_sentence"],
        }
        for item in json.loads(row["idioms_json"])
    ]
    return {"vocab": vocab, "idioms": idioms}


def _build_input_props(
    project: dict, audio_job: dict, word_timestamps: list[list[dict]], learning: dict[str, Any] | None
) -> dict[str, Any]:
    """D19.1-b + D19.3 + D19.4 + D19.5: per-line timestamps from AudioService's measured mix,
    each line's word list (Task 19.3, positionally aligned with `audio_job["timestamps"]`),
    each line's real `speaker_id` and the project-level `speakers` array (Task 19.4), and the
    project's optional learning content (Task 19.5)."""
    lines = [
        {
            "startSec": entry["start_sec"],
            "endSec": entry["end_sec"],
            "speaker": entry["label"],
            "speakerId": entry["speaker_id"],
            "text": entry["text"],
            "words": words,
        }
        for entry, words in zip(audio_job["timestamps"], word_timestamps, strict=True)
    ]
    props: dict[str, Any] = {
        "episodeId": project["id"],
        "lines": lines,
        "speakers": _build_speakers_props(project),
        "audioPath": f"spike-audio/{project['id']}.mp3",
        "fps": RENDER_FPS,
        "width": RENDER_WIDTH,
        "height": RENDER_HEIGHT,
    }
    if learning is not None:
        props["learning"] = learning
    return props


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
        learning = await _fetch_learning_props(db, project["id"])
    finally:
        await db.close()

    project_id = project["id"]

    if audio_job["word_timestamps"]:
        # A future episode actually re-mixed since Task 19.2 landed -- use its real captured
        # data directly, no re-synthesis needed.
        word_timestamps = [_words_to_props(entry["words"]) for entry in audio_job["word_timestamps"]]
        resynthesized_word_count = 0
    else:
        word_timestamps = await _resynthesize_word_timestamps(project, audio_job)
        resynthesized_word_count = len(audio_job["timestamps"])

    input_props = _build_input_props(project, audio_job, word_timestamps, learning)
    _copy_audio_into_public(project_id, audio_job["mp3_path"])

    # Resolved to absolute: the render subprocess runs with cwd=video-renderer/, and a
    # relative path here would land under video-renderer/ instead of the intended
    # data/tmp/phase19_spike/ (found by running the spike for real -- exit 0 but the file
    # silently landed in the wrong directory relative to the subprocess's own cwd).
    output_path = (SPIKE_OUTPUT_DIR / f"{project_id}.mp4").resolve()
    # Task 19.3 (D19.3-d PM caveat): Edge TTS word timings drift slightly run-to-run, so a
    # frame-level spot check must compare against the props actually used for *this* render,
    # not a fixed prior baseline -- dumped alongside the output for exactly that purpose.
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.with_suffix(".props.json").write_text(json.dumps(input_props, indent=2), encoding="utf-8")
    timeout_seconds = _render_timeout_seconds(audio_job["duration_seconds"])
    render_result = _run_render(input_props, output_path, timeout_seconds)

    empty_words_line_count = sum(1 for line in input_props["lines"] if not line["words"])
    measurements: dict[str, Any] = {
        "project_id": project_id,
        "script_line_count": len(input_props["lines"]),
        "audio_duration_seconds": audio_job["duration_seconds"],
        "audio_file_size_bytes": Path(audio_job["mp3_path"]).stat().st_size,
        "resynthesized_line_count": resynthesized_word_count,
        "empty_words_line_count": empty_words_line_count,
        "learning_vocab_count": len(learning["vocab"]) if learning else 0,
        "learning_idiom_count": len(learning["idioms"]) if learning else 0,
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
