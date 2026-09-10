"""Project management routes."""

import time

import aiosqlite
from fastapi import APIRouter, Depends

from app.core.responses import ok
from app.db.database import get_db
from app.models.project import ProjectUpdate, ScriptConfig
from app.services import project_service

router = APIRouter(prefix="/api/projects", tags=["projects"])


@router.get("")
async def list_projects(db: aiosqlite.Connection = Depends(get_db)) -> dict:
    """List all projects for the dashboard grid."""
    started_at = time.perf_counter()
    projects = await project_service.list_projects(db)
    return ok(projects, started_at=started_at)


@router.post("")
async def create_project(
    config: ScriptConfig, db: aiosqlite.Connection = Depends(get_db)
) -> dict:
    """Create a new project from the Step 1 wizard config."""
    started_at = time.perf_counter()
    project = await project_service.create_project(db, config)
    return ok(project, started_at=started_at)


@router.get("/{project_id}")
async def get_project(project_id: str, db: aiosqlite.Connection = Depends(get_db)) -> dict:
    """Fetch full project detail, including speakers."""
    started_at = time.perf_counter()
    project = await project_service.get_project(db, project_id)
    return ok(project, started_at=started_at)


@router.put("/{project_id}")
async def update_project(
    project_id: str, patch: ProjectUpdate, db: aiosqlite.Connection = Depends(get_db)
) -> dict:
    """Apply a partial update to a project — also used as the auto-save endpoint."""
    started_at = time.perf_counter()
    project = await project_service.update_project(db, project_id, patch)
    return ok(project, started_at=started_at)


@router.delete("/{project_id}")
async def delete_project(project_id: str, db: aiosqlite.Connection = Depends(get_db)) -> dict:
    """Delete a project."""
    started_at = time.perf_counter()
    await project_service.delete_project(db, project_id)
    return ok(None, started_at=started_at)
