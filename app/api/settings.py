"""App-level settings routes (Task 12.1; Task 18.3 cloud provider settings)."""

import time

import aiosqlite
from fastapi import APIRouter, Depends

from app.core.config import settings
from app.db.transactions import write_transaction
from app.core.responses import ok
from app.db.database import get_db
from app.models.settings import AIModeUpdate, CloudSettingsUpdate, CloudTestConnectionRequest
from app.services import settings_service

router = APIRouter(prefix="/api/settings", tags=["settings"])


@router.get("")
async def get_settings(db: aiosqlite.Connection = Depends(get_db)) -> dict:
    """Report the cloud provider's status and the current AI_MODE.

    Never returns the raw cloud key -- see settings_service.get_cloud_settings_status.
    `allow_cloud` (Task 18.3, PM review C3) and `effective_mode`/`effective_reason`
    let the Settings page show, and explain, when the selected mode differs from
    what actually runs.
    """
    started_at = time.perf_counter()
    cloud_status = await settings_service.get_cloud_settings_status(db)
    ai_mode_status = await settings_service.get_ai_mode_status(db)
    effective_mode, effective_reason = settings_service.compute_effective_mode_and_reason(
        ai_mode_status["ai_mode"]
    )
    return ok(
        {
            **cloud_status,
            **ai_mode_status,
            "allow_cloud": settings.AI_ALLOW_CLOUD,
            "effective_mode": effective_mode,
            "effective_reason": effective_reason,
        },
        started_at=started_at,
    )


@router.put("/ai-mode")
async def update_ai_mode(payload: AIModeUpdate, db: aiosqlite.Connection = Depends(get_db)) -> dict:
    """Save a new AI_MODE (ADR-001 kill switch) -- takes effect immediately, no restart needed."""
    started_at = time.perf_counter()
    async with write_transaction(db):
        status = await settings_service.set_ai_mode(db, payload.ai_mode)
    return ok(status, started_at=started_at)


@router.put("/cloud")
async def update_cloud_settings(
    payload: CloudSettingsUpdate, db: aiosqlite.Connection = Depends(get_db)
) -> dict:
    """Save the cloud provider's base URL/model, and (optionally) its API key --
    takes effect immediately, no restart needed."""
    started_at = time.perf_counter()
    async with write_transaction(db):
        status = await settings_service.set_cloud_settings(
            db, payload.base_url, payload.model, payload.api_key
        )
    return ok(status, started_at=started_at)


@router.delete("/cloud/api-key")
async def clear_cloud_api_key(db: aiosqlite.Connection = Depends(get_db)) -> dict:
    """Remove the stored cloud API key and revert to the original .env/environment value."""
    started_at = time.perf_counter()
    async with write_transaction(db):
        status = await settings_service.clear_cloud_api_key(db)
    return ok(status, started_at=started_at)


@router.post("/cloud/test-connection")
async def test_cloud_connection(payload: CloudTestConnectionRequest) -> dict:
    """One real, tiny probe call to the cloud provider -- never persists anything."""
    started_at = time.perf_counter()
    result = await settings_service.test_cloud_connection(payload.base_url, payload.model, payload.api_key)
    return ok(result, started_at=started_at)
