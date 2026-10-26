"""TTS engine discovery + per-line preview routes (Task 1.6)."""

import asyncio
import time
from typing import Literal

import aiosqlite
from fastapi import APIRouter, Depends, Query
from fastapi.responses import FileResponse, Response

from backend.db.transactions import read_transaction, write_transaction
from backend.core.exceptions import NotFoundError
from backend.core.responses import ok
from backend.core.voice import line_fingerprint
from backend.db.database import get_db
from backend.schemas.tts import PreviewLineRequest, VoiceCatalog, VoicePreviewRequest, VoicePreviewResult
from backend.content import project_service, script_service
from backend.ai.tts import tts_service, voice_catalog_service, voice_preview_service

router = APIRouter(prefix="/api/tts", tags=["tts"])
preview_router = APIRouter(prefix="/api/projects/{project_id}/tts", tags=["tts"])


@router.get("/voices")
async def list_voices(
    locale: str = Query(default="", max_length=35),
    gender: Literal["", "male", "female", "neutral"] = "",
    q: str = Query(default="", max_length=100),
    refresh: bool = False,
) -> dict:
    """Discover actual English voices, including explicit cache freshness metadata."""
    started_at = time.perf_counter()
    catalog = await voice_catalog_service.get_catalog(refresh=refresh, locale=locale, gender=gender, q=q)
    return ok(VoiceCatalog.model_validate(catalog).model_dump(), started_at=started_at)


@router.post("/voices/preview")
async def preview_voice(payload: VoicePreviewRequest) -> dict:
    """Audition a selected voice independently of every project and production cache."""
    started_at = time.perf_counter()
    result = await voice_preview_service.preview_voice(payload)
    return ok(VoicePreviewResult.model_validate(result).model_dump(), started_at=started_at)


@router.get("/voices/preview/{preview_id}.mp3")
async def voice_preview_media(preview_id: str) -> Response:
    """Serve a bounded audition already read into memory; no open file can race cleanup."""
    audio = await voice_preview_service.read_preview(preview_id)
    return Response(audio, media_type="audio/mpeg", headers={"Cache-Control": "no-store"})


@router.get("/engines")
async def list_engines() -> dict:
    """Report the supported plain-speech engine."""
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
        cursor = await db.execute("SELECT audio_cache_path FROM script_lines WHERE project_id = ? AND id = ?",
                                  (project_id, payload.line_id))
        line["audio_cache_path"] = (await cursor.fetchone())["audio_cache_path"]
        expected = line_fingerprint(project, line)
    if payload.reuse_cached and await asyncio.to_thread(tts_service.cache_matches, project, line):
        async with read_transaction():
            await tts_service.assert_line_current(db, project_id, payload.line_id, expected)
        return ok({"audio_path": line["audio_cache_path"], "engine_used": expected["engine"], "reused": True},
                  started_at=started_at)
    result = await tts_service.synthesize_line_audio(project, line)
    async with write_transaction(db):
        await tts_service.save_line_audio_cache(
            db, project_id, payload.line_id, result["audio_path"], commit=False, expected_fingerprint=expected,
        )
    return ok(result, started_at=started_at)


@preview_router.get("/cache/{line_id}.mp3")
async def get_cached_audio(project_id: str, line_id: str, db: aiosqlite.Connection = Depends(get_db)) -> FileResponse:
    """Serve a previously synthesized line's cached audio file."""
    async with read_transaction():
        audio_path = await tts_service.get_cached_audio_path(db, project_id, line_id)
    if not audio_path:
        raise NotFoundError(f"No cached audio for line {line_id}")
    return FileResponse(audio_path, media_type="audio/mpeg", headers={"Cache-Control": "no-store"})
