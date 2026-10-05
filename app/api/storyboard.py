"""Task 24.1: a project's storyboard (beats that tile the script lines)."""

import aiosqlite
from fastapi import APIRouter, Depends

from app.core.responses import ok
from app.db.database import get_db
from app.db.transactions import read_transaction, write_transaction
from app.models.storyboard import StoryboardInput
from app.services import project_service
from app.services.visuals import storyboard_service as storyboard

router = APIRouter(prefix="/api/projects/{project_id}/storyboard", tags=["storyboard"])


@router.get("")
async def get_storyboard(project_id: str, db: aiosqlite.Connection = Depends(get_db)) -> dict:
    async with read_transaction():
        await project_service.get_project(db, project_id)
        return ok(await storyboard.get_storyboard(db, project_id))


@router.put("")
async def put_storyboard(project_id: str, body: StoryboardInput, db: aiosqlite.Connection = Depends(get_db)) -> dict:
    async with write_transaction(db):
        await project_service.get_project(db, project_id)
        return ok(await storyboard.replace_storyboard(db, project_id, body, "owner"))
