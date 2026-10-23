"""Global character and scene library lifecycle and safe content paths."""

from __future__ import annotations

import asyncio
import random
import shutil
import uuid
import warnings
from contextlib import suppress
from datetime import datetime, timezone
from io import BytesIO
from pathlib import Path
from typing import Any
from urllib.parse import quote

import aiosqlite
from fastapi import UploadFile
from PIL import Image, ImageOps, UnidentifiedImageError
from pydantic import ValidationError as PydanticValidationError

from backend.core.config import settings
from backend.core.exceptions import AppError, ConflictError, NotFoundError, ValidationError
from backend.schemas.visuals import CharacterInput, CharacterPatch, SceneInput, ScenePatch
from backend.ai.image import recipes
from backend.ai.image.recipes import SHEET_KINDS
from backend.db.transactions import read_transaction, write_transaction

CHARACTER_FIELDS = (
    "name", "gender", "age_group", "ethnicity", "role", "hair", "eyes", "extra",
    "top_color", "top_item", "bottom_color", "bottom_item",
)

_SCENE_UPLOAD_CHUNK_BYTES = 1024 * 1024
_SCENE_MAX_UPLOAD_BYTES = 20 * 1024 * 1024
_SCENE_MAX_PIXELS = 24_000_000
_SCENE_BACKGROUND_SIZE = (1280, 720)
_SCENE_IMAGE_SUFFIXES = {".png", ".jpg", ".jpeg", ".webp"}


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
    row["body_url"] = row["sheet_urls"].get("full_body")  # the library tile shows the whole person (Task 27.3b)
    return row


async def list_characters(db: aiosqlite.Connection) -> list[dict]:
    cursor = await db.execute("SELECT id FROM characters ORDER BY created_at, id")
    return [await character_view(db, row["id"]) for row in await cursor.fetchall()]


def normalized_name(name: str) -> str:
    """Task 33.1: the active-name uniqueness key (trim + case-fold), same rule as migration 018's backfill."""
    return name.strip().lower()


def default_sprite_facing(gender: str) -> str:
    """Amendment A (D82): a male pack looks to the right of the picture, a female pack to the left."""
    return "right" if gender == "male" else "left"


async def _ensure_name_free(db: aiosqlite.Connection, name: str, own_id: str | None = None) -> None:
    row = await _one(
        db, "SELECT id FROM characters WHERE normalized_name = ? AND archived_at IS NULL AND id IS NOT ?",
        (normalized_name(name), own_id),
    )
    if row is not None:
        raise ConflictError(f"A character named {name.strip()!r} already exists")


async def create_character(db: aiosqlite.Connection, body: CharacterInput) -> dict:
    character_id, now = str(uuid.uuid4()), _now()
    values = body.model_dump()
    await _ensure_name_free(db, values["name"])
    await db.execute(
        "INSERT INTO characters (id, name, gender, age_group, ethnicity, role, hair, eyes, extra, "
        "top_color, top_item, bottom_color, bottom_item, status, base_seed, created_at, updated_at, "
        "normalized_name, sprite_facing) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'draft', ?, ?, ?, ?, ?)",
        (character_id, *(values[key] for key in CHARACTER_FIELDS), random.randint(1, 2**31 - 5), now, now,
         normalized_name(values["name"]), default_sprite_facing(values["gender"])),
    )
    return await character_view(db, character_id)


async def edit_character(db: aiosqlite.Connection, character_id: str, patch: CharacterPatch) -> dict:
    row = await get_character_row(db, character_id)
    if row["status"] == "locked":
        raise ConflictError("Unlock the character before editing its appearance")
    fields = patch.model_dump(exclude_unset=True)
    if any(value is None for value in fields.values()):
        raise ValidationError("Character fields cannot be null")
    if any(value != row[key] for key, value in fields.items() if key != "name"):
        # Phase 35 (D89): this old route wipes every picture on an appearance change; a profile's slot pictures (and the
        # seeds) are never wiped from here -- the Profiles tab edits them.
        cursor = await db.execute("SELECT 1 FROM character_assets WHERE character_id = ? AND slot_key IS NOT NULL LIMIT 1",
                                  (character_id,))
        if row["is_seed"] or await cursor.fetchone() is not None:
            raise ConflictError("This character's pictures are made in its profile; change its appearance in the Profiles tab")
    try:
        merged = CharacterInput.model_validate({key: fields.get(key, row[key]) for key in CHARACTER_FIELDS})
    except PydanticValidationError as exc:
        raise ValidationError(str(exc)) from exc
    new = merged.model_dump()
    await _ensure_name_free(db, new["name"], own_id=character_id)
    changed = any(new[key] != row[key] for key in CHARACTER_FIELDS if key != "name")
    if changed:
        await db.execute("DELETE FROM character_assets WHERE character_id = ?", (character_id,))
        await db.execute(
            "UPDATE characters SET reference_asset_id = NULL, status = 'draft' WHERE id = ?", (character_id,)
        )
    await db.execute(
        "UPDATE characters SET " + ", ".join(f"{key} = ?" for key in CHARACTER_FIELDS)
        + ", normalized_name = ?, sprite_facing = ?, updated_at = ? WHERE id = ?",
        (*(new[key] for key in CHARACTER_FIELDS), normalized_name(new["name"]), default_sprite_facing(new["gender"]),
         _now(), character_id),
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
    row = await get_character_row(db, character_id)
    if row["status"] != "locked":
        raise ConflictError("Character is not locked")
    cursor = await db.execute("SELECT 1 FROM project_cast WHERE character_id = ? LIMIT 1", (character_id,))
    if await cursor.fetchone() is not None:
        raise ConflictError("Remove this character from every project cast before unlocking")
    await db.execute("UPDATE characters SET status = 'sheet', updated_at = ? WHERE id = ?", (_now(), character_id))
    return await character_view(db, character_id)


async def delete_character(db: aiosqlite.Connection, character_id: str, force: bool) -> None:
    row = await get_character_row(db, character_id)
    if row["is_seed"]:  # Phase 35 (D89): the old route ignored this; the profile route already refused it
        raise ConflictError("Lina and Alex are protected profiles; archive them instead")
    cursor = await db.execute("SELECT 1 FROM project_cast WHERE character_id = ? LIMIT 1", (character_id,))
    if await cursor.fetchone() is not None and not force:
        raise ConflictError("Character is used by a project cast; use force=true to remove those cast entries")
    if force:
        await db.execute("DELETE FROM project_cast WHERE character_id = ?", (character_id,))

    await db.execute("DELETE FROM characters WHERE id = ?", (character_id,))


async def remove_character_files(character_id: str) -> None:
    path = settings.DATA_DIR / "library" / "characters" / character_id
    await asyncio.to_thread(shutil.rmtree, path, ignore_errors=True)
    # Phase 32: the character's talking-sprite set goes with it
    await asyncio.to_thread(shutil.rmtree, settings.DATA_DIR / "library" / "sprites" / character_id, ignore_errors=True)


# Keep usage and historical visibility on the same definition of a project reference.
# Plan versions and approved snapshots remain usable after the current plan is edited.
_SCENE_REFERENCES_CTE = """
WITH explainer_documents AS (
    SELECT project_id, plan_json FROM project_explainer_plans
    UNION ALL
    SELECT project_id, plan_json FROM project_explainer_plan_versions
    UNION ALL
    SELECT project_id, json_extract(approved_snapshot_json, '$.plan')
    FROM project_explainer_plans WHERE approved_snapshot_json IS NOT NULL
), scene_references AS (
    SELECT project_id, scene_id FROM project_scenes
    UNION
    SELECT project_id, scene_id FROM project_beats WHERE scene_id IS NOT NULL
    UNION
    SELECT d.project_id, json_extract(segment.value, '$.scene.scene_id')
    FROM explainer_documents d, json_each(d.plan_json, '$.segments') segment
    WHERE json_type(segment.value, '$.scene.scene_id') = 'text'
    UNION
    SELECT p.project_id, json_extract(scene.value, '$.id')
    FROM project_explainer_plans p, json_each(p.approved_snapshot_json, '$.stage.scenes') scene
    WHERE json_type(scene.value, '$.id') = 'text'
)
"""


async def project_scene_ids(db: aiosqlite.Connection, project_id: str) -> set[str]:
    """Scene IDs already referenced by this project, including its saved history."""
    cursor = await db.execute(
        _SCENE_REFERENCES_CTE + "SELECT scene_id FROM scene_references WHERE project_id = ?", (project_id,),
    )
    return {row[0] for row in await cursor.fetchall()}


async def list_scenes(
    db: aiosqlite.Connection, include_archived: bool = False, project_id: str | None = None,
) -> list[dict]:
    """Active choices, optionally including all archives or only this project's historical ones."""
    cursor = await db.execute(
        _SCENE_REFERENCES_CTE
        + "SELECT s.*, COUNT(DISTINCT refs.project_id) AS used_count FROM scenes s "
        "LEFT JOIN scene_references refs ON refs.scene_id = s.id "
        "WHERE s.archived_at IS NULL OR ? OR EXISTS ("
        "SELECT 1 FROM scene_references own WHERE own.scene_id = s.id AND own.project_id = ?) "
        "GROUP BY s.id ORDER BY s.is_builtin DESC, s.name",
        (include_archived, project_id),
    )
    return [_scene_view(dict(row)) for row in await cursor.fetchall()]


async def duplicate_scene(db: aiosqlite.Connection, scene_id: str) -> dict:
    """Task 23.4: a user copy with the same place/staging/category/time, a new seed, no plate."""
    row = await get_scene_row(db, scene_id)
    cursor = await db.execute("SELECT name FROM scenes")
    names = {existing[0] for existing in await cursor.fetchall()}
    base = f"{row['name'][:35]} copy"
    name, number = base, 2
    while name in names:
        name, number = f"{base} {number}", number + 1
    new_id, now = str(uuid.uuid4()), _now()
    await db.execute(
        "INSERT INTO scenes (id, name, place, staging, category, time_of_day, seed, created_at, updated_at, "
        "source_request, image_prompt) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (new_id, name, row["place"], row["staging"], row["category"], row["time_of_day"],
         random.randint(1, 2**31 - 2), now, now, row["source_request"], row["image_prompt"]),
    )
    return _scene_view(await get_scene_row(db, new_id))


def _scene_view(row: dict) -> dict:
    # Task 23.4: the version query makes a regenerated plate bypass the browser cache.
    version = quote(str(row.get("updated_at", "")), safe="")
    row["preview_url"] = f"/api/visuals/scenes/{row['id']}/preview?v={version}" if row["preview_path"] else None
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
            "INSERT INTO scenes (id, name, place, staging, category, time_of_day, seed, created_at, updated_at, "
            "source_request, image_prompt) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (scene_id, body.name, body.place, body.staging, body.category, body.time_of_day,
             random.randint(1, 2**31 - 2), now, now, body.source_request, body.image_prompt),
        )
    except aiosqlite.IntegrityError as exc:
        raise ConflictError("Scene name already exists") from exc
    return _scene_view(await get_scene_row(db, scene_id))


async def edit_scene(db: aiosqlite.Connection, scene_id: str, patch: ScenePatch) -> dict:
    row = await get_scene_row(db, scene_id)
    _require_active_scene(row)
    fields = patch.model_dump(exclude_unset=True)
    if any(value is None for value in fields.values()):
        raise ValidationError("Scene fields cannot be null")
    keys = ("name", "place", "staging", "category", "time_of_day", "source_request", "image_prompt")
    merged = {key: fields.get(key, row[key]) for key in keys}
    # Task 23.2: the plate shows the place at a time of day; changing either makes it stale.
    stale = (merged["place"] != row["place"] or merged["time_of_day"] != row["time_of_day"]
             or recipes.qwen_scene_prompt(merged) != recipes.qwen_scene_prompt(row))
    try:
        await db.execute(
            "UPDATE scenes SET name = ?, place = ?, staging = ?, category = ?, time_of_day = ?, "
            "source_request = ?, image_prompt = ?, "
            "preview_path = CASE WHEN ? THEN NULL ELSE preview_path END, updated_at = ? WHERE id = ?",
            (*(merged[key] for key in keys), int(stale), _now(), scene_id),
        )
    except aiosqlite.IntegrityError as exc:
        raise ConflictError("Scene name already exists") from exc
    return _scene_view(await get_scene_row(db, scene_id))


def _require_active_scene(row: dict) -> None:
    if row["archived_at"] is not None:
        raise ConflictError("Restore the archived scene before editing it or uploading a background")


async def read_scene_upload(file: UploadFile) -> bytes:
    """Read a bounded scene image upload and always close its temporary file handle."""
    content = bytearray()
    try:
        if Path(file.filename or "").suffix.lower() not in _SCENE_IMAGE_SUFFIXES:
            raise ValidationError("Scene backgrounds support PNG, JPEG and WebP")
        while chunk := await file.read(_SCENE_UPLOAD_CHUNK_BYTES):
            content.extend(chunk)
            if len(content) > _SCENE_MAX_UPLOAD_BYTES:
                raise ValidationError("Scene backgrounds must be 20 MB or smaller")
        if not content:
            raise ValidationError("Uploaded scene background is empty")
        return bytes(content)
    finally:
        await file.close()


def _encode_scene_background(content: bytes) -> bytes:
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("error", Image.DecompressionBombWarning)
            with Image.open(BytesIO(content), formats=("PNG", "JPEG", "WEBP")) as source:
                if source.width * source.height > _SCENE_MAX_PIXELS:
                    raise ValidationError("Scene background exceeds the 24 million pixel limit")
                source.verify()
            with Image.open(BytesIO(content), formats=("PNG", "JPEG", "WEBP")) as source:
                image = ImageOps.exif_transpose(source).convert("RGBA")
                background = Image.new("RGBA", image.size, "white")
                background.alpha_composite(image)
                fitted = ImageOps.fit(background.convert("RGB"), _SCENE_BACKGROUND_SIZE,
                                      method=Image.Resampling.LANCZOS, centering=(0.5, 0.15))
                encoded = BytesIO()
                fitted.save(encoded, format="PNG")
                return encoded.getvalue()
    except (Image.DecompressionBombError, Image.DecompressionBombWarning) as exc:
        raise ValidationError("Scene background exceeds the pixel limit") from exc
    except (OSError, ValueError, SyntaxError, UnidentifiedImageError) as exc:
        raise ValidationError("Scene background must be a readable PNG, JPEG or WebP image") from exc


def _write_scene_background(target: Path, content: bytes) -> None:
    target.parent.mkdir(parents=True, exist_ok=True)
    with target.open("xb") as output:
        output.write(content)


async def upload_scene_background(db: aiosqlite.Connection, scene_id: str, file: UploadFile) -> dict:
    """Import a scene plate outside DB locks, then atomically publish its new version.

    Owns its read/write transactions. Historical files remain intact, including on decode,
    storage or commit failure; concurrent edits or archives require the owner to retry.
    """
    try:
        async with read_transaction():
            original = await get_scene_row(db, scene_id)
            _require_active_scene(original)
    except BaseException:
        await file.close()
        raise
    content = await read_scene_upload(file)
    encoded = await asyncio.to_thread(_encode_scene_background, content)
    root = (settings.DATA_DIR / "library" / "scenes").resolve()
    folder = (root / scene_id).resolve()
    if folder.parent != root:
        raise ValidationError("Invalid scene storage path")
    target = folder / f"background-{uuid.uuid4().hex}.png"
    try:
        await asyncio.to_thread(_write_scene_background, target, encoded)
        async with write_transaction(db):
            current = await get_scene_row(db, scene_id)
            _require_active_scene(current)
            if current["updated_at"] != original["updated_at"]:
                raise ConflictError("Scene changed during upload; reload and try again")
            await db.execute("UPDATE scenes SET preview_path = ?, updated_at = ? WHERE id = ?",
                             (str(target), _now(), scene_id))
            result = _scene_view(await get_scene_row(db, scene_id))
        return result
    except BaseException as exc:
        with suppress(OSError):
            await asyncio.to_thread(target.unlink, missing_ok=True)
        if isinstance(exc, (OSError, aiosqlite.Error)):
            raise AppError("Could not save scene background; the previous background was kept") from exc
        raise


async def delete_scene(db: aiosqlite.Connection, scene_id: str) -> None:
    row = await get_scene_row(db, scene_id)
    if row["is_builtin"]:
        raise ConflictError("Built-in scenes cannot be deleted")
    await archive_scene(db, scene_id)


async def archive_scene(db: aiosqlite.Connection, scene_id: str) -> dict:
    """Archive a custom scene while retaining its plate and all project references."""
    row = await get_scene_row(db, scene_id)
    if row["is_builtin"]:
        raise ConflictError("Built-in scenes cannot be archived")
    # Lifecycle changes do not change the plate's version or invalidate approved render snapshots.
    await db.execute("UPDATE scenes SET archived_at = COALESCE(archived_at, ?) WHERE id = ?", (_now(), scene_id))
    return _scene_view(await get_scene_row(db, scene_id))


async def restore_scene(db: aiosqlite.Connection, scene_id: str) -> dict:
    """Make an archived scene available for new selections without changing its plate version."""
    await get_scene_row(db, scene_id)
    await db.execute("UPDATE scenes SET archived_at = NULL WHERE id = ?", (scene_id,))
    return _scene_view(await get_scene_row(db, scene_id))


def data_path(path: str) -> Path:
    r"""A stored file path: older rows hold `data\library\...` relative to the app folder; read them under the current data
    folder, so a packaged app or a copied data folder still finds its pictures (absolute paths are kept as they are)."""
    candidate = Path(path)
    if not candidate.is_absolute() and candidate.parts and candidate.parts[0] == "data":
        return settings.DATA_DIR.joinpath(*candidate.parts[1:])
    return candidate


def resolve_library_content(path: str, subtree: str = "library") -> Path:
    root = (settings.DATA_DIR / subtree).resolve()
    candidate = data_path(path)
    candidate = candidate.resolve()
    if not candidate.is_relative_to(root) or not candidate.is_file():
        raise NotFoundError("Image not found")
    return candidate
