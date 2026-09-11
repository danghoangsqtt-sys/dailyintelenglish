"""TTS engine discovery + per-line preview routes (Task 1.6)."""

import shutil
import time

import aiosqlite
from fastapi import APIRouter, Depends
from fastapi.responses import FileResponse

from app.api.projects import _read_transaction, _write_transaction
from app.core.config import settings
from app.core.exceptions import NotFoundError
from app.core.responses import ok
from app.db.database import get_db
from app.models.tts import PreviewLineRequest
from app.services import project_service, script_service, tts_service

router = APIRouter(prefix="/api/tts", tags=["tts"])
preview_router = APIRouter(prefix="/api/projects/{project_id}/tts", tags=["tts"])


@router.get("/engines")
async def list_engines() -> dict:
    """Report which TTS engines are currently usable on this machine.

    OmniVoice availability is based on the model directory existing —
    actual model loading and GPU checks happen at startup / in
    scripts/check_dependencies.py, not on every request here.
    """
    started_at = time.perf_counter()
    engines = [
        {
            "id": "omnivoice",
            "available": settings.OMNIVOICE_MODEL_PATH.exists(),
            "kind": "local_gpu",
        },
        {"id": "edge_tts", "available": True, "kind": "online_free"},
        {
            "id": "piper",
            "available": shutil.which("piper") is not None,
            "kind": "local_offline",
        },
    ]
    return ok(engines, started_at=started_at)


@preview_router.post("/preview")
async def preview_line(
    project_id: str, payload: PreviewLineRequest, db: aiosqlite.Connection = Depends(get_db)
) -> dict:
    """Synthesize one script line to audio (OmniVoice if configured, else Edge TTS) and cache it."""
    started_at = time.perf_counter()
    async with _read_transaction():
        project = await project_service.get_project(db, project_id)
        line = await script_service.get_script_line(db, project_id, payload.line_id)
    async with _write_transaction(db):
        result = await tts_service.synthesize_line(db, project, line, commit=False)
    return ok(result, started_at=started_at)


@preview_router.get("/cache/{line_id}.mp3")
async def get_cached_audio(project_id: str, line_id: str, db: aiosqlite.Connection = Depends(get_db)) -> FileResponse:
    """Serve a previously synthesized line's cached audio file."""
    async with _read_transaction():
        audio_path = await tts_service.get_cached_audio_path(db, project_id, line_id)
    if not audio_path:
        raise NotFoundError(f"No cached audio for line {line_id}")
    return FileResponse(audio_path, media_type="audio/mpeg")
