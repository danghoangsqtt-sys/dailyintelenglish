"""Audio mixing routes (Task 1.6, Sub-task 1.6b).

`GET /status` is a plain polling GET, not real Server-Sent Events despite
ARCHITECTURE.md's "(SSE)" label on that route — a deliberate, documented deviation (see
task-1.6.md Implementation Notes): mixing a short podcast takes a few seconds of local CPU
work, and every other `*/generate` route in this codebase (script/learning/thumbnail/
youtube) is a synchronous await-then-return call with no SSE anywhere in the actual
implementation.
"""

import time

import aiosqlite
from fastapi import APIRouter, Depends
from fastapi.responses import FileResponse

from app.api.projects import _read_transaction, _write_transaction
from app.core.exceptions import NotFoundError, ValidationError
from app.core.responses import ok
from app.db.database import get_db
from app.models.audio import GenerateAudioRequest
from app.models.project import ProjectUpdate
from app.services import audio_service, project_service

router = APIRouter(prefix="/api/projects/{project_id}/audio", tags=["audio"])

_DOWNLOAD_FORMATS = {"mp3": "audio/mpeg", "wav": "audio/wav"}


@router.post("/generate")
async def generate_audio(
    project_id: str, payload: GenerateAudioRequest, db: aiosqlite.Connection = Depends(get_db)
) -> dict:
    """Mix all of a project's synthesized lines into one podcast track."""
    started_at = time.perf_counter()
    async with _read_transaction():
        project = await project_service.get_project(db, project_id)
        lines = await audio_service.get_lines_for_mixing(db, project_id)
    if not lines:
        raise ValidationError("Cannot generate audio: script is empty")

    # No lock held across the mixing work itself (CPU-bound, runs in a thread — see
    # audio_service.mix_project — same "no lock across slow work" rule already applied to
    # Gemini calls elsewhere in this codebase).
    try:
        result = await audio_service.mix_project(project, lines, payload.background_music)
    except Exception as exc:
        async with _write_transaction(db):
            await audio_service.save_audio_job(
                db, project_id, status="error", error_message=str(exc), commit=False
            )
        raise

    async with _write_transaction(db):
        job = await audio_service.save_audio_job(
            db,
            project_id,
            status="complete",
            mp3_path=result["mp3_path"],
            wav_path=result["wav_path"],
            timestamps=result["timestamps"],
            background_music=payload.background_music,
            duration_seconds=result["duration_seconds"],
            loudness_lufs=result["loudness_lufs"],
            commit=False,
        )
        if project["status"] == "script_generated":
            await project_service.update_project(
                db, project_id, ProjectUpdate(status="audio_generated"), commit=False
            )
    return ok(job, started_at=started_at)


@router.get("/status")
async def get_audio_status(project_id: str, db: aiosqlite.Connection = Depends(get_db)) -> dict:
    """Return the current audio job for a project (404 if audio was never generated)."""
    started_at = time.perf_counter()
    async with _read_transaction():
        await project_service.get_project(db, project_id)
        job = await audio_service.get_audio_job(db, project_id)
    if job is None:
        raise NotFoundError(f"No audio job for project {project_id}")
    return ok(job, started_at=started_at)


@router.get("/download")
async def download_audio(
    project_id: str, format: str = "mp3", db: aiosqlite.Connection = Depends(get_db)
) -> FileResponse:
    """Download the mixed audio as MP3 (default) or WAV."""
    media_type = _DOWNLOAD_FORMATS.get(format)
    if media_type is None:
        raise ValidationError(f"Unsupported format {format!r}: expected 'mp3' or 'wav'")
    async with _read_transaction():
        await project_service.get_project(db, project_id)
        job = await audio_service.get_audio_job(db, project_id)
    if job is None or job["status"] != "complete":
        raise NotFoundError(f"No completed audio mix for project {project_id}")
    path = job["mp3_path"] if format == "mp3" else job["wav_path"]
    return FileResponse(path, media_type=media_type, filename=f"{project_id}.{format}")
