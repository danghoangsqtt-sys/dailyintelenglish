"""Music jobs on the shared ImageJobRunner, so music and image generation never compete for the GPU.

- `music_track` (Task 22.2): ACE-Step 1.5 -> MP3 in the Music Library + provenance; with a
  `project_id` (Task 22.3) the track is also attached to that project.
- `music_previews` (Task 22.3): 3 short pieces for a project's brief, in one worker session.
"""

from __future__ import annotations

import asyncio
import json
import random
import re
import subprocess
import unicodedata
import uuid
from pathlib import Path
from typing import Any

from app.core.config import settings
from app.core.exceptions import ValidationError
from app.db.transactions import write_transaction
from app.models.music import MAX_SEED, MUSIC_STYLES, PREVIEW_COUNT, PREVIEW_SECONDS
from app.services.music import brief_service, tracks
from app.services.music.engine import FAKE_MODEL, MODEL_LICENCE, get_music_engine
from app.services.visuals import jobs
from app.services.visuals.runner import ImageJobRunner

JOB_KIND = "music_track"
PREVIEWS_JOB_KIND = "music_previews"
JOB_KINDS = (JOB_KIND, PREVIEWS_JOB_KIND)
MP3_BITRATE = "192k"
FFMPEG_TIMEOUT_SECONDS = 300
SLUG_MAX_CHARS = 40


def caption_for(style: str, brief: str) -> str:
    base = MUSIC_STYLES[style]["caption"]
    return f"{brief}, {base}" if brief else base


def slug(text: str) -> str:
    ascii_text = unicodedata.normalize("NFKD", text.replace("đ", "d").replace("Đ", "D"))
    ascii_text = ascii_text.encode("ascii", "ignore").decode("ascii").lower()
    return re.sub(r"[^a-z0-9]+", "-", ascii_text).strip("-")[:SLUG_MAX_CHARS].strip("-")


def track_filename(style: str, brief: str, seed: int) -> str:
    words = slug(brief)
    return f"{style}-{words}-{seed}.mp3" if words else f"{style}-{seed}.mp3"


def _to_mp3(source: Path, target: Path) -> None:
    target.parent.mkdir(parents=True, exist_ok=True)
    result = subprocess.run(
        [settings.FFMPEG_PATH, "-y", "-loglevel", "error", "-i", str(source), "-codec:a", "libmp3lame",
         "-b:a", MP3_BITRATE, "-f", "mp3", str(target)],
        capture_output=True, text=True, timeout=FFMPEG_TIMEOUT_SECONDS,
    )
    if result.returncode != 0 or not target.is_file():
        raise RuntimeError(f"MP3 encode failed: {result.stderr.strip()[:300]}")


def _remove(*paths: Path) -> None:
    for path in paths:
        path.unlink(missing_ok=True)


def _work_wav() -> Path:
    return tracks.music_dir() / ".work" / f"{uuid.uuid4().hex}.wav"


async def _render_mp3(session: Any, caption: str, duration_s: int, seed: int, strategy: str,
                      target: Path) -> dict[str, Any]:
    """One generate request -> an MP3 at `target`; the work WAV never outlives the call."""
    work_wav = _work_wav()
    try:
        response = await session.request({
            "command": "generate", "caption": caption, "duration_s": duration_s, "seed": seed,
            "strategy": strategy, "output_path": str(work_wav),
        })
        await asyncio.to_thread(_to_mp3, work_wav, target)
    finally:
        await asyncio.to_thread(_remove, work_wav)
    return response


async def music_track(job: dict, runner: ImageJobRunner) -> dict:
    payload = json.loads(job["payload_json"])
    style, brief = payload["style"], payload["brief"]
    seed, duration_s = int(payload["seed"]), int(payload["duration_s"])
    project_id = payload.get("project_id")
    caption = caption_for(style, brief)
    temporary_mp3 = tracks.music_dir() / f".{uuid.uuid4().hex}.mp3.tmp"
    await runner.boundary(job["id"], "generating music", 5)
    try:
        async with get_music_engine().session(consumer="music") as session:
            response = await _render_mp3(session, caption, duration_s, seed, settings.MUSIC_LENGTH_STRATEGY,
                                         temporary_mp3)
        await runner.boundary(job["id"], "saving to the library", 95)
        stored = await asyncio.to_thread(tracks.place_without_overwrite, temporary_mp3,
                                         track_filename(style, brief, seed))
    finally:
        await asyncio.to_thread(_remove, temporary_mp3)
    model = response["model"] if response["model"] == FAKE_MODEL else f"{response['model']} (lm {response['lm']})"
    provenance = {
        "style": style, "brief": brief, "caption": caption, "seed": seed, "duration_s": response["duration_s"],
        "model": model, "licence": MODEL_LICENCE, "strategy": response["strategy"], "job_id": job["id"],
    }
    db = runner.get_db()
    async with write_transaction(db):
        await tracks.record_ai(db, stored.name, provenance)
        if project_id:  # Task 22.3: the owner asked for this track for the project; attach it
            await brief_service.attach_track(db, project_id, stored.name)
    return {"filename": stored.name, "project_id": project_id, "wall_time_sec": response["wall_time_sec"],
            "vram_peak_mb": response["vram_peak_mb"], **provenance}


async def music_previews(job: dict, runner: ImageJobRunner) -> dict:
    """3 short previews of the project's brief with different seeds, one model load. Previews of a
    brief the owner changed meanwhile are discarded, never shown under the new brief."""
    project_id = job["target_id"]
    payload = json.loads(job["payload_json"])
    style, brief = payload["style"], payload["brief"]
    caption = caption_for(style, brief)
    seeds = random.sample(range(1, MAX_SEED + 1), PREVIEW_COUNT)
    made: list[int] = []
    timings: list[float] = []
    try:
        async with get_music_engine().session(consumer="music_previews") as session:
            for index, seed in enumerate(seeds):
                await runner.boundary(job["id"], f"preview {index + 1} of {PREVIEW_COUNT}",
                                      5 + index * 90 // PREVIEW_COUNT)
                response = await _render_mp3(session, caption, PREVIEW_SECONDS, seed, "full",
                                             brief_service.preview_path(project_id, seed))
                made.append(seed)
                timings.append(response["wall_time_sec"])
        db = runner.get_db()
        async with write_transaction(db):
            current = await brief_service.get_row(db, project_id)
            fresh = current is not None and (current["style"], current["brief"]) == (style, brief)
            if fresh:
                await brief_service.set_previews(db, project_id, made)
    except BaseException:
        await asyncio.to_thread(_remove, *(brief_service.preview_path(project_id, seed) for seed in made))
        raise
    if not fresh:
        await asyncio.to_thread(_remove, *(brief_service.preview_path(project_id, seed) for seed in made))
        return {"project_id": project_id, "seeds": [], "stale": True}
    # Older previews of this project are no longer listed; drop their files.
    await asyncio.to_thread(brief_service.remove_previews_sync, project_id, set(made))
    return {"project_id": project_id, "seeds": made, "stale": False, "wall_time_sec": timings}


async def enqueue_previews(db, project_id: str) -> dict:
    """Caller holds the write transaction."""
    row = await brief_service.require_row(db, project_id)
    job = await jobs.create_job(db, PREVIEWS_JOB_KIND, project_id, {"style": row["style"], "brief": row["brief"]})
    await brief_service.set_job(db, project_id, "preview_job_id", job["id"])
    return job


async def enqueue_full(db, project_id: str, seed: int) -> dict:
    """Caller holds the write transaction; the seed must be one of the current previews."""
    row = await brief_service.require_row(db, project_id)
    if seed not in {item["seed"] for item in row["previews"]}:
        raise ValidationError("Pick one of this project's current previews")
    payload = {"style": row["style"], "brief": row["brief"], "duration_s": row["duration_s"], "seed": seed,
               "project_id": project_id}
    job = await jobs.create_job(db, JOB_KIND, f"project:{project_id}", payload)
    await brief_service.pick(db, project_id, seed)
    await brief_service.set_job(db, project_id, "full_job_id", job["id"])
    return job

