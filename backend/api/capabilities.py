"""Phase 71 (ENH-053): what this computer shows -- the edition and the local AI picture features."""

import time
from typing import Literal

import aiosqlite
from fastapi import APIRouter, Depends
from pydantic import BaseModel

from backend.core import edition
from backend.core.responses import ok
from backend.db.database import get_db
from backend.db.transactions import read_transaction, write_transaction

router = APIRouter(prefix="/api/system/capabilities", tags=["system"])


class CapabilitiesPatch(BaseModel):
    local_image_ai: Literal["auto", "on", "off"]


@router.get("")
async def get_capabilities(db: aiosqlite.Connection = Depends(get_db)) -> dict:
    started_at = time.perf_counter()
    async with read_transaction():
        choice = await edition.get_choice(db)
    name, found = edition.edition(), await edition.detect()
    shown, reason = edition.decide(name, choice, found)
    return ok({"edition": name, "local_image_ai": shown, "choice": choice, "reason": reason, **found}, started_at=started_at)


@router.put("")
async def put_capabilities(patch: CapabilitiesPatch, db: aiosqlite.Connection = Depends(get_db)) -> dict:
    async with write_transaction(db):
        await edition.set_choice(db, patch.local_image_ai)
    return await get_capabilities(db)
