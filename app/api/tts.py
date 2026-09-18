"""TTS engine discovery + per-line preview routes (Task 1.6)."""

import time

import aiosqlite
from fastapi import APIRouter, Depends
from fastapi.responses import FileResponse

from app.api.projects import _read_transaction, _write_transaction
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

    Only lists engines `tts_service.py` can actually dispatch to (matches
    `TTS_ENGINES`). `omnivoice` is unconditionally reported unavailable: its
    synthesis function is a hardcoded, always-failing stub today (see
    `tts_service.py`'s module docstring) — no filesystem check could make that
    claim honestly `true`, model directory or not. "piper"/"google"/"azure" were
    removed entirely 2026-09-18 (found by an independent audit): they were
    accepted as valid `tts_engine` values but had zero synthesis implementation,
    silently falling through to Edge TTS with no error — an advertised capability
    that didn't actually run.
    """
    started_at = time.perf_counter()
    engines = [
        {"id": "omnivoice", "available": False, "kind": "local_gpu"},
        {"id": "edge_tts", "available": True, "kind": "online_free"},
    ]
    return ok(engines, started_at=started_at)


@preview_router.post("/preview")
async def preview_line(
    project_id: str, payload: PreviewLineRequest, db: aiosqlite.Connection = Depends(get_db)
) -> dict:
    """Synthesize one script line to audio (OmniVoice if configured, else Edge TTS) and cache it.

    No lock is held across the synthesis call itself (network round-trip to Edge
    TTS, potentially slow) — same "no lock across slow work" rule already applied
    to Gemini calls and audio/video generation elsewhere in this codebase. A short
    `_read_transaction` snapshots what's needed, then a separate, short
    `_write_transaction` persists the result.
    """
    started_at = time.perf_counter()
    async with _read_transaction():
        project = await project_service.get_project(db, project_id)
        line = await script_service.get_script_line(db, project_id, payload.line_id)
    result = await tts_service.synthesize_line_audio(project, line)  # no lock held — network call
    async with _write_transaction(db):
        await tts_service.save_line_audio_cache(
            db, project_id, payload.line_id, result["audio_path"], commit=False
        )
    return ok(result, started_at=started_at)


@preview_router.get("/cache/{line_id}.mp3")
async def get_cached_audio(project_id: str, line_id: str, db: aiosqlite.Connection = Depends(get_db)) -> FileResponse:
    """Serve a previously synthesized line's cached audio file."""
    async with _read_transaction():
        audio_path = await tts_service.get_cached_audio_path(db, project_id, line_id)
    if not audio_path:
        raise NotFoundError(f"No cached audio for line {line_id}")
    return FileResponse(audio_path, media_type="audio/mpeg")
