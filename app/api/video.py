"""Video generation routes (Task 1.7, Sub-task 1.7a).

`GET /status` is a plain polling GET, not real Server-Sent Events — same documented
deviation as `app/api/audio.py`'s `/status` route.
"""

import time

import aiosqlite
from fastapi import APIRouter, Depends
from fastapi.responses import FileResponse

from app.db.transactions import read_transaction, write_transaction
from app.core.exceptions import NotFoundError, ValidationError
from app.core.responses import ok
from app.db.database import get_db
from app.models.project import ProjectUpdate
from app.models.video import GenerateVideoRequest
from app.services import audio_service, learning_service, project_service, video_service, video_renderer_remotion

router = APIRouter(prefix="/api/projects/{project_id}/video", tags=["video"])
templates_router = APIRouter(prefix="/api/video", tags=["video"])

_DOWNLOAD_FORMATS = {"mp4": "video/mp4", "mp4_vertical": "video/mp4", "srt": "application/x-subrip"}


@templates_router.get("/templates")
async def list_templates() -> dict:
    """List the fixed set of pre-rendered background templates."""
    started_at = time.perf_counter()
    return ok(video_service.list_video_templates(), started_at=started_at)


@templates_router.get("/health")
async def video_health() -> dict:
    """Task 19.7 (D19.7-d): Remotion availability + the in-memory fallback-rate counters
    (process-lifetime only, reset on restart -- same precedent as app/main.py's
    `_ai_circuits`, Phase 18)."""
    started_at = time.perf_counter()
    payload = {
        "remotion_configured": video_renderer_remotion.is_remotion_configured(),
        **video_renderer_remotion.get_remotion_stats(),
    }
    return ok(payload, started_at=started_at)


@router.post("/generate")
async def generate_video(
    project_id: str, payload: GenerateVideoRequest, db: aiosqlite.Connection = Depends(get_db)
) -> dict:
    """Render the project's completed audio mix into an MP4.

    Task 19.7: `payload.renderer` ("ffmpeg" default) is only ever actually honored as
    "remotion" when `video_service._resolve_renderer`'s kill-switch check agrees (D19.7-b)
    -- passing "remotion" here is always safe, it just silently resolves to ffmpeg when the
    deployment hasn't opted in via `DIE_VIDEO_RENDERER=remotion`.
    """
    started_at = time.perf_counter()
    async with read_transaction():
        project = await project_service.get_project(db, project_id)
        audio_job = await audio_service.get_audio_job(db, project_id)
        # Fetched unconditionally (cheap, single row) -- only actually used by the
        # Remotion path; the ffmpeg path never reads it (D19.7-a).
        learning = await learning_service.get_learning_content(db, project_id)
    if audio_job is None or audio_job["status"] != "complete":
        raise ValidationError("Cannot generate video: generate the audio mix first.")

    # No lock held across the render itself (CPU-bound, runs in a thread — see
    # video_service.generate_video).
    try:
        result = await video_service.generate_video(
            project_id,
            audio_job,
            payload.template_id,
            payload.aspect_ratio,
            renderer=payload.renderer,
            caption_style=payload.caption_style,
            visual_mode=payload.visual_mode,
            still_scene_id=payload.still_scene_id,
            db=db,
            project=project,
            learning=learning,
        )
    except Exception as exc:
        async with write_transaction(db):
            await video_service.mark_video_job_failed(db, project_id, str(exc), commit=False)
        raise

    async with write_transaction(db):
        job = await video_service.save_video_job(
            db,
            project_id,
            status="complete",
            mode=result.get("mode", "background"),
            mp4_path=result["mp4_path"],
            mp4_path_vertical=result.get("mp4_path_vertical"),
            srt_path=result["srt_path"],
            background_image=result["background_image"],
            commit=False,
        )
        if project["status"] == "audio_generated":
            await project_service.update_project(
                db, project_id, ProjectUpdate(status="video_generated"), commit=False
            )
    # fallback_used/wall_time_seconds are per-call context, not persisted columns (no
    # migration in this task's scope) -- surfaced only in this response.
    response = {**job, "fallback_used": result.get("fallback_used", False)}
    return ok(response, started_at=started_at)


@router.get("/status")
async def get_video_status(project_id: str, db: aiosqlite.Connection = Depends(get_db)) -> dict:
    """Return the current video job for a project (404 if video was never generated)."""
    started_at = time.perf_counter()
    async with read_transaction():
        await project_service.get_project(db, project_id)
        job = await video_service.get_video_job(db, project_id)
    if job is None:
        raise NotFoundError(f"No video job for project {project_id}")
    return ok(job, started_at=started_at)


@router.get("/download")
async def download_video(
    project_id: str, format: str = "mp4", db: aiosqlite.Connection = Depends(get_db)
) -> FileResponse:
    """Download the generated video as MP4 (default), the 9:16 vertical MP4, or the SRT
    subtitle file."""
    media_type = _DOWNLOAD_FORMATS.get(format)
    if media_type is None:
        raise ValidationError(f"Unsupported format {format!r}: expected 'mp4', 'mp4_vertical', or 'srt'")
    async with read_transaction():
        await project_service.get_project(db, project_id)
        job = await video_service.get_video_job(db, project_id)
    if job is None or job["status"] not in ("complete", "error"):
        raise NotFoundError(f"No completed video for project {project_id}")
    path_by_format = {"mp4": job["mp4_path"], "mp4_vertical": job["mp4_path_vertical"], "srt": job["srt_path"]}
    path = path_by_format[format]
    if path is None:
        raise NotFoundError(f"No {format!r} output was generated for project {project_id}")
    extension = "mp4" if format in ("mp4", "mp4_vertical") else format
    return FileResponse(path, media_type=media_type, filename=f"{project_id}.{extension}")
