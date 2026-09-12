"""YouTube Package routes (Task 1.9, Sub-task 1.9a)."""

import time

import aiosqlite
from fastapi import APIRouter, Depends

from app.api.projects import _read_transaction, _write_transaction
from app.core.exceptions import ValidationError
from app.core.responses import ok
from app.db.database import get_db
from app.services import project_service, script_service, youtube_service

router = APIRouter(prefix="/api/projects/{project_id}/youtube", tags=["youtube"])


@router.post("/generate")
async def generate_youtube_package(
    project_id: str, db: aiosqlite.Connection = Depends(get_db)
) -> dict:
    """Generate a YouTube package (titles/description/tags/estimated chapters) via Gemini."""
    started_at = time.perf_counter()
    async with _read_transaction():
        project = await project_service.get_project(db, project_id)
        script_lines = await script_service.get_script(db, project_id)
    if not script_lines:
        raise ValidationError("Cannot generate a YouTube package: script is empty")
    package = await youtube_service.generate_package(project, script_lines)  # no lock — Gemini call
    async with _write_transaction(db):
        saved = await youtube_service.save_package(db, project_id, package, commit=False)
    return ok(saved, started_at=started_at)


@router.get("")
async def get_youtube_package(project_id: str, db: aiosqlite.Connection = Depends(get_db)) -> dict:
    """Fetch the current YouTube package for a project (null if not generated yet)."""
    started_at = time.perf_counter()
    async with _read_transaction():
        await project_service.get_project(db, project_id)
        package = await youtube_service.get_package(db, project_id)
    return ok(package, started_at=started_at)
