"""YouTube Package routes (Task 1.9)."""

import asyncio
import time

import aiosqlite
from fastapi import APIRouter, Depends, Response

from backend.db.transactions import read_transaction, write_transaction
from backend.core.exceptions import ValidationError
from backend.core.responses import ok
from backend.db.database import get_db
from backend.media import audio_service, music_library_service, thumbnail_service, video_service
from backend.channel import channel_service
from backend.content import learning_service, project_service, script_service, youtube_service
from backend.content import export_service

router = APIRouter(prefix="/api/projects/{project_id}/youtube", tags=["youtube"])


async def _composed(db: aiosqlite.Connection, project_id: str, package: dict | None) -> dict | None:
    """Task 36.2: the package with its composed description, hashtags line and pinned comment(s) (caller holds a read
    transaction)."""
    if package is None:
        return None
    project = await project_service.get_project(db, project_id)
    script_lines = await script_service.get_script(db, project_id)
    learning = await learning_service.get_learning_content(db, project_id)
    credit = await music_library_service.music_credit(db, project_id)
    episode = await channel_service.episode_context(db, project_id)  # Task 36.5: the series block
    return youtube_service.compose(package, project, script_lines, learning, credit, episode)


@router.post("/generate")
async def generate_youtube_package(
    project_id: str, db: aiosqlite.Connection = Depends(get_db)
) -> dict:
    """Generate a YouTube package (titles/description/tags/chapters) via Gemini.

    Chapters are measured from real audio when a completed audio mix exists (Task 1.6),
    otherwise estimated from script word count (Sub-task 1.9a's original behavior).
    """
    started_at = time.perf_counter()
    async with read_transaction():
        project = await project_service.get_project(db, project_id)
        script_lines = await script_service.get_script(db, project_id)
        audio_job = await audio_service.get_audio_job(db, project_id)
    if not script_lines:
        raise ValidationError("Cannot generate a YouTube package: script is empty")
    timestamps = audio_job["timestamps"] if audio_job and audio_job["status"] == "complete" else None
    package = await youtube_service.generate_package(project, script_lines, timestamps)  # no lock — Gemini call
    async with write_transaction(db):
        saved = await youtube_service.save_package(db, project_id, package, commit=False)
    async with read_transaction():
        composed = await _composed(db, project_id, saved)
    await export_service.sync_quietly(db, project_id)  # Phase 41 (D120): the project folder follows
    return ok(composed, started_at=started_at)


@router.get("")
async def get_youtube_package(project_id: str, db: aiosqlite.Connection = Depends(get_db)) -> dict:
    """Fetch the current YouTube package for a project (null if not generated yet)."""
    started_at = time.perf_counter()
    async with read_transaction():
        await project_service.get_project(db, project_id)
        package = await _composed(db, project_id, await youtube_service.get_package(db, project_id))
    return ok(package, started_at=started_at)


@router.get("/transcript.txt")
async def download_transcript(project_id: str, db: aiosqlite.Connection = Depends(get_db)) -> Response:
    """Task 36.2 (D93): the full transcript as a text file, to attach or share with the episode."""
    async with read_transaction():
        project = await project_service.get_project(db, project_id)
        script_lines = await script_service.get_script(db, project_id)
    if not script_lines:
        raise ValidationError("The project has no script yet")
    return Response(
        content=youtube_service.transcript_text(project, script_lines).encode("utf-8"),
        media_type="text/plain; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{project_id}-transcript.txt"'},
    )


@router.get("/export")
async def export_youtube_package(project_id: str, db: aiosqlite.Connection = Depends(get_db)) -> Response:
    """Download the full YouTube package as a .zip, including transcript/Learning Content.

    Requires a generated YouTube package, a completed video, and a selected favorite
    thumbnail — a ValidationError names exactly which piece is missing.
    """
    async with read_transaction():
        project = await project_service.get_project(db, project_id)
        package = await youtube_service.get_package(db, project_id)
        video_job = await video_service.get_video_job(db, project_id)
        thumbnail_rows = await thumbnail_service.get_thumbnail_rows(db, project_id)
        script_lines = await script_service.get_script(db, project_id)
        learning_content = await learning_service.get_learning_content(db, project_id)
        package = await _composed(db, project_id, package)

    missing = []
    if package is None:
        missing.append("YouTube package (generate it on this page first)")
    if video_job is None or video_job["status"] != "complete":
        missing.append("video (finish Step 5 — Video Studio first)")
    favorite_thumbnail = next((row for row in thumbnail_rows if row["is_selected"]), None)
    if favorite_thumbnail is None:
        missing.append("a selected favorite thumbnail (finish Step 6 — Thumbnail Generator first)")
    if missing:
        raise ValidationError(f"Cannot export the full package yet: missing {', '.join(missing)}.")

    # build_export_zip is synchronous (real disk reads + zipfile DEFLATE compression of a
    # multi-MB video) -- must not block the event loop, same class of bug fixed for 4 other
    # call sites in Task 2.2 (this route was added separately and missed that pass).
    zip_bytes = await asyncio.to_thread(
        youtube_service.build_export_zip,
        package,
        video_job,
        favorite_thumbnail,
        project,
        script_lines,
        learning_content,
    )
    return Response(
        content=zip_bytes,
        media_type="application/zip",
        headers={"Content-Disposition": f'attachment; filename="{project_id}-youtube-package.zip"'},
    )
