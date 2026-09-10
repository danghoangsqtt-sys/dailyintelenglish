"""Learning Content routes (Task 1.5 — Sprint 1.5B)."""

import time

import aiosqlite
from fastapi import APIRouter, Depends

from app.api.projects import _read_transaction, _write_transaction
from app.core.exceptions import ValidationError
from app.core.responses import ok
from app.db.database import get_db
from app.models.learning import LearningPackUpdate
from app.services import learning_service, project_service, script_service

router = APIRouter(prefix="/api/projects/{project_id}/learning", tags=["learning"])


@router.post("/generate")
async def generate_learning_content(
    project_id: str, db: aiosqlite.Connection = Depends(get_db)
) -> dict:
    """Generate a Learning Content pack via Gemini from the project's script and persist it."""
    started_at = time.perf_counter()
    async with _read_transaction():
        project = await project_service.get_project(db, project_id)
        script_lines = await script_service.get_script(db, project_id)
    if not script_lines:
        raise ValidationError("Cannot generate learning content: script is empty")
    pack = await learning_service.generate_learning_pack(  # no lock held — Gemini call
        project_id, project, script_lines
    )
    async with _write_transaction(db):
        saved = await learning_service.save_learning_content(
            db, project_id, pack.model_dump(), commit=False
        )
    return ok(saved, started_at=started_at)


@router.get("")
async def get_learning_content(project_id: str, db: aiosqlite.Connection = Depends(get_db)) -> dict:
    """Fetch the current Learning Content pack for a project (null if not generated yet)."""
    started_at = time.perf_counter()
    async with _read_transaction():
        await project_service.get_project(db, project_id)
        pack = await learning_service.get_learning_content(db, project_id)
    return ok(pack, started_at=started_at)


@router.put("")
async def update_learning_content(
    project_id: str, payload: LearningPackUpdate, db: aiosqlite.Connection = Depends(get_db)
) -> dict:
    """Apply a partial user-edit to an existing Learning Content pack."""
    started_at = time.perf_counter()
    async with _read_transaction():
        await project_service.get_project(db, project_id)
    async with _write_transaction(db):
        updated = await learning_service.update_learning_content(
            db, project_id, payload.model_dump(exclude_unset=True), commit=False
        )
    return ok(updated, started_at=started_at)
