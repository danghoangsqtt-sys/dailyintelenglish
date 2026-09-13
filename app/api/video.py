"""Video generation routes (Task 1.7, Sub-task 1.7a).

`GET /status` is a plain polling GET, not real Server-Sent Events — same documented
deviation as `app/api/audio.py`'s `/status` route.
"""

import time

import aiosqlite
from fastapi import APIRouter, Depends
from fastapi.responses import FileResponse

from app.api.projects import _read_transaction, _write_transaction
from app.core.exceptions import NotFoundError, ValidationError
from app.core.responses import ok
from app.db.database import get_db
from app.models.project import ProjectUpdate
from app.models.video import GenerateVideoRequest
from app.services import audio_service, project_service, video_service

router = APIRouter(prefix="/api/projects/{project_id}/video", tags=["video"])
templates_router = APIRouter(prefix="/api/video", tags=["video"])

_DOWNLOAD_FORMATS = {"mp4": "video/mp4", "srt": "application/x-subrip"}


@templates_router.get("/templates")
async def list_templates() -> dict:
    """List the fixed set of pre-rendered background templates."""
    started_at = time.perf_counter()
    return ok(video_service.list_video_templates(), started_at=started_at)


@router.post("/generate")
async def generate_video(
    project_id: str, payload: GenerateVideoRequest, db: aiosqlite.Connection = Depends(get_db)
) -> dict:
    """Render the project's completed audio mix into an MP4 with burned-in subtitles."""
    started_at = time.perf_counter()
    async with _read_transaction():
        project = await project_service.get_project(db, project_id)
        audio_job = await audio_service.get_audio_job(db, project_id)
    if audio_job is None or audio_job["status"] != "complete":
        raise ValidationError("Cannot generate video: generate the audio mix first.")

    # No lock held across the render itself (CPU-bound, runs in a thread — see
    # video_service.generate_video).
    try:
        result = await video_service.generate_video(project_id, audio_job, payload.template_id)
    except Exception as exc:
        async with _write_transaction(db):
            await video_service.save_video_job(
                db, project_id, status="error", error_message=str(exc), commit=False
            )
        raise

    async with _write_transaction(db):
        job = await video_service.save_video_job(
            db,
            project_id,
            status="complete",
            mp4_path=result["mp4_path"],
            srt_path=result["srt_path"],
            background_image=result["background_image"],
            commit=False,
        )
        if project["status"] == "audio_generated":
            await project_service.update_project(
                db, project_id, ProjectUpdate(status="video_generated"), commit=False
            )
    return ok(job, started_at=started_at)


@router.get("/status")
async def get_video_status(project_id: str, db: aiosqlite.Connection = Depends(get_db)) -> dict:
    """Return the current video job for a project (404 if video was never generated)."""
    started_at = time.perf_counter()
    async with _read_transaction():
        await project_service.get_project(db, project_id)
        job = await video_service.get_video_job(db, project_id)
    if job is None:
        raise NotFoundError(f"No video job for project {project_id}")
    return ok(job, started_at=started_at)


@router.get("/download")
async def download_video(
    project_id: str, format: str = "mp4", db: aiosqlite.Connection = Depends(get_db)
) -> FileResponse:
    """Download the generated video as MP4 (default) or the SRT subtitle file."""
    media_type = _DOWNLOAD_FORMATS.get(format)
    if media_type is None:
        raise ValidationError(f"Unsupported format {format!r}: expected 'mp4' or 'srt'")
    async with _read_transaction():
        await project_service.get_project(db, project_id)
        job = await video_service.get_video_job(db, project_id)
    if job is None or job["status"] != "complete":
        raise NotFoundError(f"No completed video for project {project_id}")
    path = job["mp4_path"] if format == "mp4" else job["srt_path"]
    return FileResponse(path, media_type=media_type, filename=f"{project_id}.{format}")
