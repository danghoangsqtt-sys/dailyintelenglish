"""Phase 62 (ENH-044): automatic production -- its settings, the queue of due episodes, Run now / Stop and the report."""

import time
from datetime import date

import aiosqlite
from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field, field_validator

from backend.automation import automation_service as service
from backend.automation import rules, startup
from backend.automation.runner import get_runner
from backend.core.exceptions import ValidationError
from backend.core.responses import ok
from backend.db.database import get_db
from backend.db.transactions import read_transaction, write_transaction

router = APIRouter(prefix="/api/automation", tags=["automation"])


class AutomationSettingsPatch(BaseModel):
    enabled: bool | None = None
    window_start: str | None = None
    window_end: str | None = None
    days_ahead: int | None = Field(default=None, ge=0, le=30)
    max_per_night: int | None = Field(default=None, ge=1, le=20)
    start_with_windows: bool | None = None
    keep_awake: bool | None = None

    @field_validator("window_start", "window_end")
    @classmethod
    def clock(cls, value: str | None) -> str | None:
        if value is not None:
            try:
                rules.parse_clock(value)
            except ValueError as exc:
                raise ValueError("Use a time like 23:00") from exc
        return value


async def _view(db: aiosqlite.Connection) -> dict:
    config = await service.get_settings(db)
    queue = await service.due(db, date.today(), int(config["days_ahead"]))
    runner = get_runner()
    return {
        "settings": {**config, "start_with_windows": startup.is_enabled() if startup.available() else config["start_with_windows"]},
        "startup_available": startup.available(),
        "status": runner.status() if runner else {"running": False, "manual": False, "stop_requested": False, "current": None},
        "queue": [{key: item[key] for key in ("id", "number", "title", "series", "publish_date", "project_id", "presentation_mode")}
                  for item in queue],
        "runs": await service.report(db),
    }


@router.get("")
async def get_automation(db: aiosqlite.Connection = Depends(get_db)) -> dict:
    started_at = time.perf_counter()
    async with read_transaction():
        result = await _view(db)
    return ok(result, started_at=started_at)


@router.put("/settings")
async def put_settings(body: AutomationSettingsPatch, db: aiosqlite.Connection = Depends(get_db)) -> dict:
    started_at = time.perf_counter()
    patch = body.model_dump(exclude_none=True)
    if "start_with_windows" in patch:
        startup.apply(patch["start_with_windows"])  # raises a clear ValidationError when not possible
    async with write_transaction(db):
        await service.update_settings(db, patch)
    async with read_transaction():
        result = await _view(db)
    return ok(result, started_at=started_at)


@router.post("/run-now")
async def run_now(db: aiosqlite.Connection = Depends(get_db)) -> dict:
    """Make the due episodes now, outside the night window (up to the per-night limit)."""
    started_at = time.perf_counter()
    runner = get_runner()
    if runner is None:
        raise ValidationError("Automatic production is not running in this app")
    runner.request_run_now()
    async with read_transaction():
        result = await _view(db)
    return ok(result, started_at=started_at)


@router.post("/stop")
async def stop(db: aiosqlite.Connection = Depends(get_db)) -> dict:
    """Stop after the current step; the episode goes on from that step next time."""
    started_at = time.perf_counter()
    runner = get_runner()
    if runner is not None:
        runner.request_stop()
    async with read_transaction():
        result = await _view(db)
    return ok(result, started_at=started_at)
