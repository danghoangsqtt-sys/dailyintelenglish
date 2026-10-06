"""TTS engine discovery + per-line preview routes (Task 1.6)."""

import time

import aiosqlite
from fastapi import APIRouter, Depends
from fastapi.responses import FileResponse

from app.db.transactions import read_transaction, write_transaction
from app.core.exceptions import NotFoundError
from app.core.responses import ok
from app.db.database import get_db
from app.models.tts import PreviewLineRequest
from app.services import project_service, script_service, tts_service

router = APIRouter(prefix="/api/tts", tags=["tts"])
preview_router = APIRouter(prefix="/api/projects/{project_id}/tts", tags=["tts"])


@router.get("/engines")
async def list_engines() -> dict:
    """Report the TTS engines this app can use: Edge TTS only (D56, owner 2026-10-06).
    OmniVoice (never integrated), Kokoro and StyleTTS 2 were removed."""
    started_at = time.perf_counter()
    engines = [
        {"id": "edge_tts", "available": True, "kind": "online_free"},
    ]
    return ok(engines, started_at=started_at)


@preview_router.post("/preview")
async def preview_line(
    project_id: str, payload: PreviewLineRequest, db: aiosqlite.Connection = Depends(get_db)
) -> dict:
    """Synthesize one script line to audio with Edge TTS and cache it.

    No lock is held across the synthesis call itself (network round-trip to Edge
    TTS, potentially slow) — same "no lock across slow work" rule already applied
    to Gemini calls and audio/video generation elsewhere in this codebase. A short
    `read_transaction` snapshots what's needed, then a separate, short
    `write_transaction` persists the result.
    """
    started_at = time.perf_counter()
    async with read_transaction():
        project = await project_service.get_project(db, project_id)
        line = await script_service.get_script_line(db, project_id, payload.line_id)
    result = await tts_service.synthesize_line_audio(project, line)  # no lock held — network call
    async with write_transaction(db):
        await tts_service.save_line_audio_cache(
            db, project_id, payload.line_id, result["audio_path"], commit=False
        )
    return ok(result, started_at=started_at)


@preview_router.get("/cache/{line_id}.mp3")
async def get_cached_audio(project_id: str, line_id: str, db: aiosqlite.Connection = Depends(get_db)) -> FileResponse:
    """Serve a previously synthesized line's cached audio file."""
    async with read_transaction():
        audio_path = await tts_service.get_cached_audio_path(db, project_id, line_id)
    if not audio_path:
        raise NotFoundError(f"No cached audio for line {line_id}")
    return FileResponse(audio_path, media_type="audio/mpeg")
