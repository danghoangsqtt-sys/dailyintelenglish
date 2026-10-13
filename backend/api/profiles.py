"""Phase 33 (Task 33.2): character profile API.

A separate prefix (`/api/visuals/profiles`) keeps the legacy `/api/visuals/characters` routes and the current Character
Library page working unchanged during the phase; the new library, Quick create and the selector use these routes.
"""

import time
from pathlib import Path
from typing import Literal

import aiosqlite
from fastapi import APIRouter, Depends, File, UploadFile
from fastapi.responses import FileResponse, PlainTextResponse, Response
from pydantic import BaseModel, Field

from backend.core.exceptions import NotFoundError, ValidationError
from backend.core.responses import ok
from backend.db.database import get_db
from backend.db.transactions import read_transaction, write_transaction
from backend.schemas.visuals import PROFILE_ACCENTS, ProfilePatch, ProfileQuickCreate
from backend.library import character_asset_service as assets
from backend.library import character_profile_service as profiles
from backend.library import library_service as library

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


# ---------------------------------------------------------------- Task 33.3 (D84/D86): picture slots, prompts, upload, review

MAX_UPLOAD_BYTES = 20 * 1024 * 1024


class ReviewInput(BaseModel):
    decision: Literal["approve", "reject"]


class ApproveManyInput(BaseModel):
    asset_ids: list[str] = Field(min_length=1, max_length=40)


def _slot_from_filename(filename: str) -> str | None:
    """Optional bulk shortcut (D83): `gesture-wave__open.png` or `kai__gesture-wave__open.png` -> `gesture-wave__open`."""
    stem = Path(filename or "").name
    if not stem.lower().endswith(".png"):
        return None
    stem = stem[:-4]
    if stem in assets.SLOTS_BY_KEY:
        return stem
    _, separator, rest = stem.partition("__")
    return rest if separator and rest in assets.SLOTS_BY_KEY else None


async def _read_limited(file: UploadFile) -> bytes:
    content = await file.read(MAX_UPLOAD_BYTES + 1)
    if len(content) > MAX_UPLOAD_BYTES:
        raise ValidationError("the file is larger than 20 MB")
    return content


@router.get("/{character_id}/slots")
async def list_slots(character_id: str, db: aiosqlite.Connection = Depends(get_db)) -> dict:
    async with read_transaction():
        result = await assets.list_slots(db, character_id)
    return ok(result)


@router.post("/{character_id}/slots/{slot_key}/upload")
async def upload_slot(
    character_id: str, slot_key: str, file: UploadFile = File(...), db: aiosqlite.Connection = Depends(get_db),
) -> dict:
    """The slot comes from the card the picture was dropped on, never from the file name (D84)."""
    content = await _read_limited(file)
    async with write_transaction(db):
        result = await assets.upload(db, character_id, slot_key, content, file.filename)
    return ok(result)


@router.post("/{character_id}/slots/upload-batch")
async def upload_batch(
    character_id: str, files: list[UploadFile] = File(...), db: aiosqlite.Connection = Depends(get_db),
) -> dict:
    """Bulk shortcut: files named after a slot go into it (the base first); every other file is listed, not guessed."""
    if len(files) > 40:
        raise ValidationError("drop at most 40 pictures at once")
    named = [(file, _slot_from_filename(file.filename or "")) for file in files]
    named.sort(key=lambda item: item[1] != assets.BASE)
    stored, unmatched, failed = [], [], []
    for file, slot_key in named:
        if slot_key is None:
            unmatched.append({"file": file.filename, "reason": "drop this picture on its slot card"})
            continue
        try:
            content = await _read_limited(file)
            async with write_transaction(db):
                stored.append(await assets.upload(db, character_id, slot_key, content, file.filename))
        except (ValidationError, NotFoundError) as exc:
            failed.append({"file": file.filename, "slot": slot_key, "reason": exc.message})
    return ok({"stored": stored, "unmatched": unmatched, "failed": failed})


@router.get("/{character_id}/slots/{slot_key}/input.png")
async def slot_input(character_id: str, slot_key: str, db: aiosqlite.Connection = Depends(get_db)) -> Response:
    async with read_transaction():
        content = await assets.parent_input(db, character_id, slot_key)
    return Response(content, media_type="image/png",
                    headers={"Content-Disposition": f'attachment; filename="INPUT_{slot_key}.png"'})


@router.put("/{character_id}/assets/{asset_id}/review")
async def review_asset(
    character_id: str, asset_id: str, body: ReviewInput, db: aiosqlite.Connection = Depends(get_db),
) -> dict:
    async with write_transaction(db):
        result = await assets.review(db, character_id, asset_id, body.decision)
    return ok(result)


@router.post("/{character_id}/assets/approve")
async def approve_assets(
    character_id: str, body: ApproveManyInput, db: aiosqlite.Connection = Depends(get_db),
) -> dict:
    async with write_transaction(db):
        result = await assets.approve_many(db, character_id, body.asset_ids)
    return ok(result)


@router.get("/{character_id}/assets/{asset_id}/content")
async def asset_content(character_id: str, asset_id: str, db: aiosqlite.Connection = Depends(get_db)) -> FileResponse:
    async with read_transaction():
        path = await assets.asset_content(db, character_id, asset_id)
    return FileResponse(path, media_type="image/png")


@router.get("/{character_id}/prompt-pack.txt")
async def prompt_pack(character_id: str, db: aiosqlite.Connection = Depends(get_db)) -> PlainTextResponse:
    async with read_transaction():
        text = await assets.prompt_pack_text(db, character_id)
    return PlainTextResponse(text, headers={"Content-Disposition": 'attachment; filename="prompt-pack.txt"'})
