"""The `music_track` job (Task 22.2): ACE-Step 1.5 -> MP3 in the Music Library + provenance.

It runs on the shared ImageJobRunner, so music and image generation never compete for the GPU.
"""

from __future__ import annotations

import asyncio
import json
import re
import subprocess
import unicodedata
import uuid
from pathlib import Path

from app.core.config import settings
from app.db.transactions import write_transaction
from app.models.music import MUSIC_STYLES
from app.services.music import tracks
from app.services.music.engine import FAKE_MODEL, MODEL_LICENCE, get_music_engine
from app.services.visuals.runner import ImageJobRunner

JOB_KIND = "music_track"
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


async def music_track(job: dict, runner: ImageJobRunner) -> dict:
    payload = json.loads(job["payload_json"])
    style, brief = payload["style"], payload["brief"]
    seed, duration_s = int(payload["seed"]), int(payload["duration_s"])
    caption = caption_for(style, brief)
    library = tracks.music_dir()
    work_wav = library / ".work" / f"{uuid.uuid4().hex}.wav"
    temporary_mp3 = library / f".{uuid.uuid4().hex}.mp3.tmp"
    await runner.boundary(job["id"], "generating music", 5)
    try:
        engine = get_music_engine()
        async with engine.session(consumer="music") as session:
            response = await session.request({
                "command": "generate", "caption": caption, "duration_s": duration_s, "seed": seed,
                "strategy": settings.MUSIC_LENGTH_STRATEGY, "output_path": str(work_wav),
            })
        await runner.boundary(job["id"], "encoding MP3", 90)
        await asyncio.to_thread(_to_mp3, work_wav, temporary_mp3)
        stored = await asyncio.to_thread(tracks.place_without_overwrite, temporary_mp3,
                                         track_filename(style, brief, seed))
    finally:
        await asyncio.to_thread(_remove, work_wav, temporary_mp3)
    model = response["model"] if response["model"] == FAKE_MODEL else f"{response['model']} (lm {response['lm']})"
    provenance = {
        "style": style, "brief": brief, "caption": caption, "seed": seed, "duration_s": response["duration_s"],
        "model": model, "licence": MODEL_LICENCE, "strategy": response["strategy"], "job_id": job["id"],
    }
    db = runner.get_db()
    async with write_transaction(db):
        await tracks.record_ai(db, stored.name, provenance)
    return {"filename": stored.name, "wall_time_sec": response["wall_time_sec"],
            "vram_peak_mb": response["vram_peak_mb"], **provenance}
