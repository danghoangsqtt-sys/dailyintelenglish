"""App-level settings routes (Task 12.1) -- currently just the Gemini API key."""

import time

import aiosqlite
from fastapi import APIRouter, Depends

from app.api.projects import _write_transaction
from app.core.responses import ok
from app.db.database import get_db
from app.models.settings import GeminiApiKeyUpdate
from app.services import settings_service

router = APIRouter(prefix="/api/settings", tags=["settings"])


@router.get("")
async def get_settings(db: aiosqlite.Connection = Depends(get_db)) -> dict:
    """Report the Gemini API key's current source and a masked preview.

    Never returns the raw key -- see settings_service.get_gemini_api_key_status.
    """
    started_at = time.perf_counter()
    status = await settings_service.get_gemini_api_key_status(db)
    return ok(status, started_at=started_at)


@router.put("")
async def update_gemini_api_key(
    payload: GeminiApiKeyUpdate, db: aiosqlite.Connection = Depends(get_db)
) -> dict:
    """Save a new Gemini API key -- takes effect immediately, no restart needed."""
    started_at = time.perf_counter()
    async with _write_transaction(db):
        status = await settings_service.set_gemini_api_key(db, payload.gemini_api_key)
    return ok(status, started_at=started_at)


@router.delete("/gemini-api-key")
async def clear_gemini_api_key(db: aiosqlite.Connection = Depends(get_db)) -> dict:
    """Remove the stored key and revert to the original .env/environment value."""
    started_at = time.perf_counter()
    async with _write_transaction(db):
        status = await settings_service.clear_gemini_api_key(db)
    return ok(status, started_at=started_at)
