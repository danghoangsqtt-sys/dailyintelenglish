"""Phase 41 (D120): the project's output folder and the components exported there."""

import asyncio
import os
import time
from pathlib import Path

import aiosqlite
from fastapi import APIRouter, Depends
from pydantic import BaseModel

from backend.content import export_service, project_service
from backend.core.exceptions import NotFoundError, ValidationError
from backend.core.responses import ok
from backend.db.database import get_db
from backend.db.transactions import read_transaction, write_transaction

router = APIRouter(tags=["export"])


class FolderRequest(BaseModel):
    initial: str | None = None


@router.get("/api/projects/{project_id}/export")
async def get_export(project_id: str, db: aiosqlite.Connection = Depends(get_db)) -> dict:
    async with read_transaction():
        await project_service.get_project(db, project_id)
        return ok(await export_service.public(db, project_id))


@router.put("/api/projects/{project_id}/export")
async def save_export(project_id: str, body: export_service.ExportSettings,
                      db: aiosqlite.Connection = Depends(get_db)) -> dict:
    """Set the folder and the ticked components, then copy what already exists."""
    started_at = time.perf_counter()
    async with write_transaction(db):
        await export_service.save_settings(db, project_id, body)
        result = await export_service.sync(db, project_id)
        view = await export_service.public(db, project_id)
    return ok({**view, "sync": result}, started_at=started_at)


@router.delete("/api/projects/{project_id}/export")
async def clear_export(project_id: str, db: aiosqlite.Connection = Depends(get_db)) -> dict:
    """Stop exporting (the folder and its files stay as they are)."""
    async with write_transaction(db):
        await project_service.get_project(db, project_id)
        await export_service.clear_settings(db, project_id)
        return ok(await export_service.public(db, project_id))


@router.post("/api/projects/{project_id}/export/sync")
async def sync_export(project_id: str, db: aiosqlite.Connection = Depends(get_db)) -> dict:
    started_at = time.perf_counter()
    async with write_transaction(db):
        await project_service.get_project(db, project_id)
        result = await export_service.sync(db, project_id)
    if result["folder"] is None:
        raise ValidationError("Choose a folder for this project first")
    return ok(result, started_at=started_at)


@router.post("/api/projects/{project_id}/export/open")
async def open_export_folder(project_id: str, db: aiosqlite.Connection = Depends(get_db)) -> dict:
    """Open the folder in Windows Explorer (the app runs on the owner's computer)."""
    async with read_transaction():
        saved = await export_service.get_settings(db, project_id)
    if not saved:
        raise NotFoundError("No folder chosen for this project")
    folder = Path(saved["output_dir"])
    if not folder.is_dir():
        raise NotFoundError("The folder does not exist yet")
    if hasattr(os, "startfile"):
        await asyncio.to_thread(os.startfile, str(folder))  # noqa: S606 -- the owner's own chosen folder
    return ok({"opened": str(folder)})


@router.post("/api/system/choose-folder")
async def choose_folder(body: FolderRequest) -> dict:
    """The native folder picker on the owner's screen; `path` is null when cancelled or unavailable."""
    path = await asyncio.to_thread(export_service.choose_folder_dialog, body.initial)
    return ok({"path": path})
