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
from app.services import audio_service, learning_service, project_service, video_service
from app.services.visuals import activity_library_service as activity_library

router = APIRouter(prefix="/api/projects/{project_id}/video", tags=["video"])
templates_router = APIRouter(prefix="/api/video", tags=["video"])

_DOWNLOAD_FORMATS = {"mp4": "video/mp4", "mp4_vertical": "video/mp4", "srt": "application/x-subrip"}


@templates_router.get("/health")
async def video_health() -> dict:
    """Whether the video renderer (Remotion, the only one since Task 35.5) can run, and if not, why."""
    started_at = time.perf_counter()
    problem = video_service.renderer_problem()
    payload = {"remotion_configured": problem is None, "renderer_problem": problem}
    return ok(payload, started_at=started_at)


@router.post("/generate")
async def generate_video(
    project_id: str, payload: GenerateVideoRequest, db: aiosqlite.Connection = Depends(get_db)
) -> dict:
    """Render the project's completed audio mix into the episode MP4 with Remotion (Task 35.5: the only renderer; a
    failure fails the job with its reason)."""
    started_at = time.perf_counter()
    async with read_transaction():
        project = await project_service.get_project(db, project_id)
        audio_job = await audio_service.get_audio_job(db, project_id)
        learning = await learning_service.get_learning_content(db, project_id)
    if audio_job is None or audio_job["status"] != "complete":
        raise ValidationError("Cannot generate video: generate the audio mix first.")

    # No lock held across the render itself (CPU-bound, runs in a thread — see
    # video_service.generate_video).
    try:
        result = await video_service.generate_video(
            project_id,
            audio_job,
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
        previous = await video_service.get_video_job(db, project_id)
        job = await video_service.save_video_job(
            db,
            project_id,
            status="complete",
            mode=result.get("mode", "remotion"),
            mp4_path=result["mp4_path"],
            mp4_path_vertical=(previous or {}).get("mp4_path_vertical"),  # Phase 37: the vertical cut is kept
            srt_path=result["srt_path"],
            background_image=None,
            commit=False,
        )
        for usage in result.get("activity_uses", []):
            await activity_library.record_usage(
                db, usage["activity_id"], project_id, usage.get("beat_id"), job["id"],
            )
        if project["status"] == "audio_generated":
            await project_service.update_project(
                db, project_id, ProjectUpdate(status="video_generated"), commit=False
            )
    return ok(job, started_at=started_at)


@router.post("/vertical")
async def generate_vertical(
    project_id: str, payload: GenerateVideoRequest, db: aiosqlite.Connection = Depends(get_db)
) -> dict:
    """Phase 37 (D98/D100): the whole episode in 1080x1920 for TikTok. Needs the horizontal video first (same audio,
    storyboard and cast)."""
    started_at = time.perf_counter()
    async with read_transaction():
        project = await project_service.get_project(db, project_id)
        audio_job = await audio_service.get_audio_job(db, project_id)
        learning = await learning_service.get_learning_content(db, project_id)
        job = await video_service.get_video_job(db, project_id)
    if job is None or job["status"] != "complete":
        raise ValidationError("Generate the horizontal video first; the vertical one reuses it.")
    result = await video_service.render_vertical(
        project_id, audio_job, db=db, project=project, learning=learning, caption_style=payload.caption_style,
        visual_mode=payload.visual_mode, still_scene_id=payload.still_scene_id)
    async with write_transaction(db):
        await video_service.set_vertical_path(db, project_id, result["mp4_path"])
        job = await video_service.get_video_job(db, project_id)
    return ok(job, started_at=started_at)


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
        raise ValidationError(f"Unsupported format {format!r}: expected 'mp4', 'mp4_vertical' or 'srt'")
    async with read_transaction():
        await project_service.get_project(db, project_id)
        job = await video_service.get_video_job(db, project_id)
    if job is None or job["status"] not in ("complete", "error"):
        raise NotFoundError(f"No completed video for project {project_id}")
    path_by_format = {"mp4": job["mp4_path"], "mp4_vertical": job["mp4_path_vertical"], "srt": job["srt_path"]}
    path = path_by_format[format]
    if path is None:
        raise NotFoundError(f"No {format!r} output was generated for project {project_id}")
    extension = "mp4" if format == "mp4_vertical" else format
    return FileResponse(path, media_type=media_type, filename=f"{project_id}.{extension}")
