"""Task 22.3 (D45): a project's background music -- AI brief, owner edit, 3 previews, pick, full length."""

import asyncio

import aiosqlite
from fastapi import APIRouter, Depends
from fastapi.responses import FileResponse

from app.core.exceptions import ConflictError, NotFoundError
from app.core.responses import ok
from app.db.database import get_db
from app.db.transactions import read_transaction, write_transaction
from app.models.music import MusicBriefInput, MusicFullInput
from app.services.music import brief_service
from app.services.music.engine import require_generation
from app.services.music.pipelines import enqueue_full, enqueue_previews

router = APIRouter(prefix="/api/projects/{project_id}/music", tags=["music"])


def _wake_runner() -> None:
    from app.main import image_job_runner  # lifespan singleton; avoid router import cycle

    image_job_runner.wake()


async def _view(db: aiosqlite.Connection, project_id: str) -> dict:
    async with read_transaction():
        return await brief_service.get_view(db, project_id)


@router.get("")
async def get_project_music(project_id: str, db: aiosqlite.Connection = Depends(get_db)) -> dict:
    return ok(await _view(db, project_id))


@router.post("/brief")
async def propose_project_music(project_id: str, db: aiosqlite.Connection = Depends(get_db)) -> dict:
    """The AI proposes a style + mood (one repair, else the genre rule); the owner edits it next."""
    return ok(await brief_service.propose_brief(db, project_id))


@router.put("")
async def save_project_music(project_id: str, body: MusicBriefInput,
                             db: aiosqlite.Connection = Depends(get_db)) -> dict:
    async with write_transaction(db):
        await brief_service.save_brief(db, project_id, body, "owner")
    return ok(await _view(db, project_id))


@router.post("/previews")
async def make_previews(project_id: str, db: aiosqlite.Connection = Depends(get_db)) -> dict:
    require_generation()
    async with write_transaction(db):
        if await brief_service.get_row(db, project_id) is None:
            raise ConflictError("Save or suggest a music brief first")
        job = await enqueue_previews(db, project_id)
    _wake_runner()
    return ok(job)


@router.get("/previews/{seed}")
async def preview_content(project_id: str, seed: int, db: aiosqlite.Connection = Depends(get_db)) -> FileResponse:
    async with read_transaction():
        row = await brief_service.require_row(db, project_id)
    if seed not in {item["seed"] for item in row["previews"]}:
        raise NotFoundError("Preview not found")
    path = brief_service.preview_path(project_id, seed)
    if not await asyncio.to_thread(path.is_file):
        raise NotFoundError("Preview not found")
    return FileResponse(path, media_type="audio/mpeg")


@router.post("/full")
async def make_full(project_id: str, body: MusicFullInput, db: aiosqlite.Connection = Depends(get_db)) -> dict:
    require_generation()
    async with write_transaction(db):
        job = await enqueue_full(db, project_id, body.seed)
    _wake_runner()
    return ok(job)
