"""Phase 33 (Task 33.2): character profile API.

A separate prefix (`/api/visuals/profiles`) keeps the legacy `/api/visuals/characters` routes and the current Character
Library page working unchanged during the phase; the new library, Quick create and the selector use these routes.
"""

import time
from typing import Literal

import aiosqlite
from fastapi import APIRouter, Depends

from app.core.responses import ok
from app.db.database import get_db
from app.db.transactions import read_transaction, write_transaction
from app.models.visuals import PROFILE_ACCENTS, ProfilePatch, ProfileQuickCreate
from app.services.visuals import character_profile_service as profiles
from app.services.visuals import library_service as library

router = APIRouter(prefix="/api/visuals/profiles", tags=["character profiles"])


@router.get("")
async def list_profiles(
    q: str = "", state: Literal["active", "archived", "all"] = "active", db: aiosqlite.Connection = Depends(get_db),
) -> dict:
    started_at = time.perf_counter()
    async with read_transaction():
        rows = await profiles.list_profiles(db, q, state)
    return ok(rows, started_at=started_at)


@router.get("/options")
async def profile_options() -> dict:
    return ok({"genders": ["male", "female"], "accents": list(PROFILE_ACCENTS)})


@router.post("")
async def create_profile(body: ProfileQuickCreate, db: aiosqlite.Connection = Depends(get_db)) -> dict:
    async with write_transaction(db):
        row = await profiles.create_quick(db, body)
    return ok(row)


@router.get("/{character_id}")
async def get_profile(character_id: str, db: aiosqlite.Connection = Depends(get_db)) -> dict:
    async with read_transaction():
        row = await profiles.get_profile(db, character_id)
    return ok(row)


@router.patch("/{character_id}")
async def patch_profile(character_id: str, body: ProfilePatch, db: aiosqlite.Connection = Depends(get_db)) -> dict:
    async with write_transaction(db):
        row = await profiles.patch_profile(db, character_id, body)
    return ok(row)


@router.post("/{character_id}/duplicate")
async def duplicate_profile(character_id: str, db: aiosqlite.Connection = Depends(get_db)) -> dict:
    async with write_transaction(db):
        row = await profiles.duplicate(db, character_id)
    return ok(row)


@router.post("/{character_id}/archive")
async def archive_profile(character_id: str, db: aiosqlite.Connection = Depends(get_db)) -> dict:
    async with write_transaction(db):
        row = await profiles.archive(db, character_id)
    return ok(row)


@router.post("/{character_id}/restore")
async def restore_profile(character_id: str, db: aiosqlite.Connection = Depends(get_db)) -> dict:
    async with write_transaction(db):
        row = await profiles.restore(db, character_id)
    return ok(row)


@router.get("/{character_id}/dependencies")
async def profile_dependencies(character_id: str, db: aiosqlite.Connection = Depends(get_db)) -> dict:
    async with read_transaction():
        report = await profiles.dependencies(db, character_id)
    return ok(report)


@router.delete("/{character_id}")
async def delete_profile(character_id: str, db: aiosqlite.Connection = Depends(get_db)) -> dict:
    async with write_transaction(db):
        await profiles.delete(db, character_id)
    await library.remove_character_files(character_id)
    return ok({"deleted": character_id})
