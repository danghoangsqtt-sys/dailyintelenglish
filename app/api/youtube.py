"""YouTube Package routes (Task 1.9)."""

import time

import aiosqlite
from fastapi import APIRouter, Depends, Response

from app.api.projects import _read_transaction, _write_transaction
from app.core.exceptions import ValidationError
from app.core.responses import ok
from app.db.database import get_db
from app.services import audio_service, project_service, script_service, thumbnail_service, video_service, youtube_service

router = APIRouter(prefix="/api/projects/{project_id}/youtube", tags=["youtube"])


@router.post("/generate")
async def generate_youtube_package(
    project_id: str, db: aiosqlite.Connection = Depends(get_db)
) -> dict:
    """Generate a YouTube package (titles/description/tags/chapters) via Gemini.

    Chapters are measured from real audio when a completed audio mix exists (Task 1.6),
    otherwise estimated from script word count (Sub-task 1.9a's original behavior).
    """
    started_at = time.perf_counter()
    async with _read_transaction():
        project = await project_service.get_project(db, project_id)
        script_lines = await script_service.get_script(db, project_id)
        audio_job = await audio_service.get_audio_job(db, project_id)
    if not script_lines:
        raise ValidationError("Cannot generate a YouTube package: script is empty")
    timestamps = audio_job["timestamps"] if audio_job and audio_job["status"] == "complete" else None
    package = await youtube_service.generate_package(project, script_lines, timestamps)  # no lock — Gemini call
    async with _write_transaction(db):
        saved = await youtube_service.save_package(db, project_id, package, commit=False)
    return ok(saved, started_at=started_at)


@router.get("")
async def get_youtube_package(project_id: str, db: aiosqlite.Connection = Depends(get_db)) -> dict:
    """Fetch the current YouTube package for a project (null if not generated yet)."""
    started_at = time.perf_counter()
    async with _read_transaction():
        await project_service.get_project(db, project_id)
        package = await youtube_service.get_package(db, project_id)
    return ok(package, started_at=started_at)


@router.get("/export")
async def export_youtube_package(project_id: str, db: aiosqlite.Connection = Depends(get_db)) -> Response:
    """Download the full YouTube package as a .zip (video, thumbnail, SRT, metadata.txt).

    Requires a generated YouTube package, a completed video, and a selected favorite
    thumbnail — a ValidationError names exactly which piece is missing.
    """
    async with _read_transaction():
        await project_service.get_project(db, project_id)
        package = await youtube_service.get_package(db, project_id)
        video_job = await video_service.get_video_job(db, project_id)
        thumbnail_rows = await thumbnail_service.get_thumbnail_rows(db, project_id)

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

    zip_bytes = youtube_service.build_export_zip(package, video_job, favorite_thumbnail)
    return Response(
        content=zip_bytes,
        media_type="application/zip",
        headers={"Content-Disposition": f'attachment; filename="{project_id}-youtube-package.zip"'},
    )
