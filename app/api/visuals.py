"""Character, scene, and project visuals API."""

import time

import aiosqlite
from fastapi import APIRouter, Depends

from app.core.config import settings
from app.core.responses import ok
from app.db.database import get_db
from app.db.transactions import read_transaction
from app.services.visuals import jobs
from app.services.visuals.engine import IMAGE_PYTHON

router = APIRouter(prefix="/api/visuals", tags=["visuals"])


@router.get("/health")
async def visuals_health(db: aiosqlite.Connection = Depends(get_db)) -> dict:
    started_at = time.perf_counter()
    async with read_transaction():
        queue = await jobs.queue_counts(db)
    return ok({"enabled": settings.AI_VISUALS_ENABLED, "engine": settings.IMAGE_ENGINE,
               "venv_image_present": IMAGE_PYTHON.is_file(), "queue": queue}, started_at=started_at)
