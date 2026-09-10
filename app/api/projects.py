"""Project management routes. Full config/create/update lands in Task 1.2-1.3."""

import time

import aiosqlite
from fastapi import APIRouter, Depends

from app.core.responses import ok
from app.db.database import get_db
from app.services import project_service

router = APIRouter(prefix="/api/projects", tags=["projects"])


@router.get("")
async def list_projects(db: aiosqlite.Connection = Depends(get_db)) -> dict:
    """List all projects for the dashboard grid."""
    started_at = time.perf_counter()
    projects = await project_service.list_projects(db)
    return ok(projects, started_at=started_at)
