"""Global character and scene library lifecycle and safe content paths."""

from __future__ import annotations

import asyncio
import random
import shutil
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import aiosqlite
from PIL import Image
from pydantic import ValidationError as PydanticValidationError

from app.core.config import settings
from app.core.exceptions import ConflictError, NotFoundError, ValidationError
from app.models.visuals import CharacterInput, CharacterPatch, SceneInput, ScenePatch
from app.services.visuals.recipes import SHEET_KINDS

CHARACTER_FIELDS = (
    "name", "gender", "age_group", "ethnicity", "role", "hair", "eyes", "extra",
    "top_color", "top_item", "bottom_color", "bottom_item",
)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


async def _one(db: aiosqlite.Connection, sql: str, params: tuple) -> dict | None:
    cursor = await db.execute(sql, params)
    row = await cursor.fetchone()
    return dict(row) if row is not None else None


async def get_character_row(db: aiosqlite.Connection, character_id: str) -> dict:
    row = await _one(db, "SELECT * FROM characters WHERE id = ?", (character_id,))
    if row is None:
        raise NotFoundError("Character not found")
    return row


async def list_assets(db: aiosqlite.Connection, character_id: str) -> list[dict]:
    cursor = await db.execute(
        "SELECT * FROM character_assets WHERE character_id = ? ORDER BY kind, seed, created_at",
        (character_id,),
    )
    return [dict(row) for row in await cursor.fetchall()]


async def character_view(db: aiosqlite.Connection, character_id: str) -> dict:
    row = await get_character_row(db, character_id)
    assets = await list_assets(db, character_id)
    for asset in assets:
        asset["url"] = f"/api/visuals/assets/{asset['id']}/content"
        asset.pop("path")
    row["assets"] = assets
    row["reference_url"] = next((a["url"] for a in assets if a["id"] == row["reference_asset_id"]), None)
    row["face_url"] = next((a["url"] for a in assets if a["kind"] == "face"), None)
    row["sheet_urls"] = {a["kind"]: a["url"] for a in assets if a["kind"] in SHEET_KINDS}
    return row


async def list_characters(db: aiosqlite.Connection) -> list[dict]:
    cursor = await db.execute("SELECT id FROM characters ORDER BY created_at, id")
    return [await character_view(db, row["id"]) for row in await cursor.fetchall()]


async def create_character(db: aiosqlite.Connection, body: CharacterInput) -> dict:
    character_id, now = str(uuid.uuid4()), _now()
    values = body.model_dump()
    await db.execute(
        "INSERT INTO characters (id, name, gender, age_group, ethnicity, role, hair, eyes, extra, "
        "top_color, top_item, bottom_color, bottom_item, status, base_seed, created_at, updated_at) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'draft', ?, ?, ?)",
        (character_id, *(values[key] for key in CHARACTER_FIELDS), random.randint(1, 2**31 - 5), now, now),
    )
    return await character_view(db, character_id)


async def edit_character(db: aiosqlite.Connection, character_id: str, patch: CharacterPatch) -> dict:
    row = await get_character_row(db, character_id)
    if row["status"] == "locked":
        raise ConflictError("Unlock the character before editing its appearance")
    fields = patch.model_dump(exclude_unset=True)
    if any(value is None for value in fields.values()):
        raise ValidationError("Character fields cannot be null")
    try:
        merged = CharacterInput.model_validate({key: fields.get(key, row[key]) for key in CHARACTER_FIELDS})
    except PydanticValidationError as exc:
        raise ValidationError(str(exc)) from exc
    new = merged.model_dump()
    changed = any(new[key] != row[key] for key in CHARACTER_FIELDS if key != "name")
    if changed:
        await db.execute("DELETE FROM character_assets WHERE character_id = ?", (character_id,))
        await db.execute(
            "UPDATE characters SET reference_asset_id = NULL, status = 'draft' WHERE id = ?", (character_id,)
        )
    await db.execute(
        "UPDATE characters SET " + ", ".join(f"{key} = ?" for key in CHARACTER_FIELDS)
        + ", updated_at = ? WHERE id = ?",
        (*(new[key] for key in CHARACTER_FIELDS), _now(), character_id),
    )
    return await character_view(db, character_id)


async def get_asset_row(db: aiosqlite.Connection, asset_id: str) -> dict:
    row = await _one(db, "SELECT * FROM character_assets WHERE id = ?", (asset_id,))
    if row is None:
        raise NotFoundError("Character asset not found")
    return row


async def add_asset(
    db: aiosqlite.Connection, character_id: str, kind: str, path: Path,
    seed: int | None, response: dict[str, Any] | None = None,
) -> dict:
    asset_id = str(uuid.uuid4())
    await db.execute(
        "INSERT INTO character_assets (id, character_id, kind, path, seed, prompt_tokens, "
        "prompt_truncated, approved, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, 0, ?)",
        (asset_id, character_id, kind, str(path), seed, (response or {}).get("prompt_tokens"),
         int(bool((response or {}).get("prompt_truncated"))), _now()),
    )
    return await get_asset_row(db, asset_id)


def _face_crop_sync(source: Path, destination: Path) -> None:
    with Image.open(source) as image:
        width, height = image.size
        box = (round(0.20 * width), round(0.02 * height), round(0.80 * width), round(0.62 * height))
        face = image.convert("RGB").crop(box).resize((512, 512), Image.Resampling.LANCZOS)
    destination.parent.mkdir(parents=True, exist_ok=True)
    face.save(destination, format="PNG")


async def pick_reference(db: aiosqlite.Connection, character_id: str, asset_id: str) -> dict:
    row = await get_character_row(db, character_id)
    if row["status"] == "locked":
        raise ConflictError("Unlock the character before changing its reference")
    asset = await get_asset_row(db, asset_id)
    if asset["character_id"] != character_id or asset["kind"] != "candidate":
        raise ValidationError("Reference must be this character's candidate")
    destination = settings.DATA_DIR / "library" / "characters" / character_id / "face.png"
    await asyncio.to_thread(_face_crop_sync, Path(asset["path"]), destination)
    await db.execute(
        "DELETE FROM character_assets WHERE character_id = ? AND kind NOT IN ('candidate')", (character_id,)
    )
    await add_asset(db, character_id, "face", destination, asset["seed"])
    await db.execute(
        "UPDATE characters SET reference_asset_id = ?, status = 'candidates', updated_at = ? WHERE id = ?",
        (asset_id, _now(), character_id),
    )
    return await character_view(db, character_id)


async def approve_asset(db: aiosqlite.Connection, character_id: str, asset_id: str, approved: bool) -> dict:
    row = await get_character_row(db, character_id)
    if row["status"] == "locked":
        raise ConflictError("Unlock the character before changing approvals")
    asset = await get_asset_row(db, asset_id)
    if asset["character_id"] != character_id or asset["kind"] not in SHEET_KINDS:
        raise ValidationError("Only this character's sheet assets can be approved")
    await db.execute("UPDATE character_assets SET approved = ? WHERE id = ?", (int(approved), asset_id))
    return await character_view(db, character_id)


async def lock_character(db: aiosqlite.Connection, character_id: str) -> dict:
    row = await get_character_row(db, character_id)
    if not row["reference_asset_id"]:
        raise ConflictError("Pick a candidate before locking")
    assets = await list_assets(db, character_id)
    if not all(any(a["kind"] == kind and a["approved"] for a in assets) for kind in SHEET_KINDS):
        raise ConflictError("Approve all four sheet assets before locking")
    await db.execute("UPDATE characters SET status = 'locked', updated_at = ? WHERE id = ?", (_now(), character_id))
    return await character_view(db, character_id)


async def unlock_character(db: aiosqlite.Connection, character_id: str) -> dict:
    await get_character_row(db, character_id)
    cursor = await db.execute("SELECT 1 FROM project_cast WHERE character_id = ? LIMIT 1", (character_id,))
    if await cursor.fetchone() is not None:
        raise ConflictError("Remove this character from every project cast before unlocking")
    await db.execute("UPDATE characters SET status = 'sheet', updated_at = ? WHERE id = ?", (_now(), character_id))
    return await character_view(db, character_id)


async def delete_character(db: aiosqlite.Connection, character_id: str, force: bool) -> None:
    await get_character_row(db, character_id)
    cursor = await db.execute("SELECT 1 FROM project_cast WHERE character_id = ? LIMIT 1", (character_id,))
    if await cursor.fetchone() is not None and not force:
        raise ConflictError("Character is used by a project cast; use force=true to remove those cast entries")
    if force:
        await db.execute("DELETE FROM project_cast WHERE character_id = ?", (character_id,))
    await db.execute("DELETE FROM characters WHERE id = ?", (character_id,))


async def remove_character_files(character_id: str) -> None:
    path = settings.DATA_DIR / "library" / "characters" / character_id
    await asyncio.to_thread(shutil.rmtree, path, ignore_errors=True)


async def list_scenes(db: aiosqlite.Connection) -> list[dict]:
    cursor = await db.execute("SELECT * FROM scenes ORDER BY is_builtin DESC, name")
    return [_scene_view(dict(row)) for row in await cursor.fetchall()]


def _scene_view(row: dict) -> dict:
    row["preview_url"] = f"/api/visuals/scenes/{row['id']}/preview" if row["preview_path"] else None
    row.pop("preview_path", None)
    return row


async def get_scene_row(db: aiosqlite.Connection, scene_id: str) -> dict:
    row = await _one(db, "SELECT * FROM scenes WHERE id = ?", (scene_id,))
    if row is None:
        raise NotFoundError("Scene not found")
    return row


async def create_scene(db: aiosqlite.Connection, body: SceneInput) -> dict:
    scene_id, now = str(uuid.uuid4()), _now()
    try:
        await db.execute(
            "INSERT INTO scenes (id, name, place, staging, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?)",
            (scene_id, body.name, body.place, body.staging, now, now),
        )
    except aiosqlite.IntegrityError as exc:
        raise ConflictError("Scene name already exists") from exc
    return _scene_view(await get_scene_row(db, scene_id))


async def edit_scene(db: aiosqlite.Connection, scene_id: str, patch: ScenePatch) -> dict:
    row = await get_scene_row(db, scene_id)
    fields = patch.model_dump(exclude_unset=True)
    if any(value is None for value in fields.values()):
        raise ValidationError("Scene fields cannot be null")
    merged = {key: fields.get(key, row[key]) for key in ("name", "place", "staging")}
    try:
        await db.execute(
            "UPDATE scenes SET name = ?, place = ?, staging = ?, updated_at = ? WHERE id = ?",
            (merged["name"], merged["place"], merged["staging"], _now(), scene_id),
        )
    except aiosqlite.IntegrityError as exc:
        raise ConflictError("Scene name already exists") from exc
    return _scene_view(await get_scene_row(db, scene_id))


async def delete_scene(db: aiosqlite.Connection, scene_id: str) -> None:
    row = await get_scene_row(db, scene_id)
    if row["is_builtin"]:
        raise ConflictError("Built-in scenes cannot be deleted")
    await db.execute("DELETE FROM scenes WHERE id = ?", (scene_id,))


def resolve_library_content(path: str, subtree: str = "library") -> Path:
    root = (settings.DATA_DIR / subtree).resolve()
    candidate = Path(path).resolve()
    if not candidate.is_relative_to(root) or not candidate.is_file():
        raise NotFoundError("Image not found")
    return candidate
