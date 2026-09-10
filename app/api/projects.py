"""Project management routes."""

import time

import aiosqlite
from fastapi import APIRouter, Depends

from app.core.responses import ok
from app.db.database import get_db
from app.models.project import ProjectUpdate, ScriptConfig
from app.models.script import RegenerateLineRequest, ScriptUpdate
from app.services import project_service, script_service

router = APIRouter(prefix="/api/projects", tags=["projects"])


async def _advance_to_script_generated(
    db: aiosqlite.Connection, project_id: str, project: dict
) -> None:
    """Move a draft project to script_generated once it has a persisted script."""
    if project["status"] == "draft":
        await project_service.update_project(db, project_id, ProjectUpdate(status="script_generated"))


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


@router.get("/{project_id}/script")
async def get_script(project_id: str, db: aiosqlite.Connection = Depends(get_db)) -> dict:
    """Fetch the current script for a project (empty list if not generated yet)."""
    started_at = time.perf_counter()
    await project_service.get_project(db, project_id)
    lines = await script_service.get_script(db, project_id)
    return ok(lines, started_at=started_at)


@router.post("/{project_id}/script/generate")
async def generate_script(project_id: str, db: aiosqlite.Connection = Depends(get_db)) -> dict:
    """Generate a full script for a project via Gemini and persist it."""
    started_at = time.perf_counter()
    project = await project_service.get_project(db, project_id)
    lines = await script_service.generate_script(project_id, project)
    saved = await script_service.save_script(db, project_id, [line.model_dump() for line in lines])
    await _advance_to_script_generated(db, project_id, project)
    return ok(saved, started_at=started_at)


@router.post("/{project_id}/script/regenerate")
async def regenerate_script_line(
    project_id: str, payload: RegenerateLineRequest, db: aiosqlite.Connection = Depends(get_db)
) -> dict:
    """Regenerate a single script line via Gemini, keeping its speaker and position."""
    started_at = time.perf_counter()
    project = await project_service.get_project(db, project_id)
    current_line = await script_service.get_script_line(db, project_id, payload.line_id)
    new_line = await script_service.regenerate_line(
        project_id, project, payload.line_id, current_line["text"], current_line["speaker_id"]
    )
    updated = await script_service.update_script_line(
        db, project_id, payload.line_id, new_line.text, new_line.language_notes.model_dump()
    )
    return ok(updated, started_at=started_at)


@router.put("/{project_id}/script")
async def save_script(
    project_id: str, payload: ScriptUpdate, db: aiosqlite.Connection = Depends(get_db)
) -> dict:
    """Save a user-edited script, replacing the project's current lines."""
    started_at = time.perf_counter()
    project = await project_service.get_project(db, project_id)
    known_speaker_ids = {speaker["id"] for speaker in project["speakers"]}
    saved = await script_service.save_script(
        db,
        project_id,
        [line.model_dump() for line in payload.lines],
        known_speaker_ids,
    )
    await _advance_to_script_generated(db, project_id, project)
    return ok(saved, started_at=started_at)
