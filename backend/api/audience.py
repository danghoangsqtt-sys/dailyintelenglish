"""Phase 72 (ENH-054): the channel's audience, and a video's own audience (or "inherit")."""

import time
from typing import Literal

import aiosqlite
from fastapi import APIRouter, Depends
from pydantic import BaseModel

from backend.content import audience, project_service
from backend.core.responses import ok
from backend.db.database import get_db
from backend.db.transactions import read_transaction, write_transaction

router = APIRouter(tags=["audience"])

Audience = Literal["international", "vietnamese", "both"]


class ChannelAudience(BaseModel):
    audience: Audience


class OwnAudience(BaseModel):
    audience: Audience | None = None  # None: as its series, or the channel


@router.get("/api/audience")
async def get_channel_audience(db: aiosqlite.Connection = Depends(get_db)) -> dict:
    started_at = time.perf_counter()
    async with read_transaction():
        value = await audience.get_channel(db)
    return ok({"audience": value, "choices": list(audience.AUDIENCES)}, started_at=started_at)


@router.put("/api/audience")
async def put_channel_audience(body: ChannelAudience, db: aiosqlite.Connection = Depends(get_db)) -> dict:
    async with write_transaction(db):
        await audience.set_channel(db, body.audience)
    return await get_channel_audience(db)


@router.get("/api/projects/{project_id}/audience")
async def get_project_audience(project_id: str, db: aiosqlite.Connection = Depends(get_db)) -> dict:
    started_at = time.perf_counter()
    async with read_transaction():
        await project_service.get_project(db, project_id)
        result = await audience.for_project(db, project_id)
    return ok(result, started_at=started_at)


@router.put("/api/projects/{project_id}/audience")
async def put_project_audience(project_id: str, body: OwnAudience, db: aiosqlite.Connection = Depends(get_db)) -> dict:
    async with write_transaction(db):
        await project_service.get_project(db, project_id)
        await audience.set_project(db, project_id, body.audience)
    return await get_project_audience(project_id, db)
