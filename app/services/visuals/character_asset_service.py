"""Canonical profile asset slots, versioned storage, review, and prompt export."""

from __future__ import annotations

import asyncio
import io
import json
import uuid
import zipfile
from pathlib import Path

import aiofiles
import aiosqlite

from app.core.config import settings
from app.core.exceptions import ConflictError, NotFoundError, ValidationError
from app.services.visuals import library_service as library
from app.services.visuals import sprite_service
from app.services.visuals.image_upload import PreparedImage

IDENTITY_BASE_SLOTS = {"face", "full_body", "calm__closed"}
CORE_SLOTS = {
    "face": ("Reference portrait", "A clear front-facing head-and-shoulders portrait", (512, 512)),
    "full_body": ("Full body", "The complete character and default outfit, head to feet", (640, 960)),
    "portrait_calm": ("Calm portrait", "A neutral calm portrait matching the identity reference", (512, 512)),
    "portrait_smile": ("Smile portrait", "A natural smile matching the identity reference", (512, 512)),
    "portrait_surprised": ("Surprised portrait", "A surprised expression matching the identity reference", (512, 512)),
}
TIER_1 = {
    "calm__closed", "calm__open", "smile__closed", "smile__open",
    "surprised__closed", "surprised__open", "blink",
}
TIER_2 = {
    "laugh__closed", "laugh__open", "thinking__closed", "thinking__open",
    "worried__closed", "worried__open", "serious__closed", "serious__open",
}


def _sprite_tier(slot_key: str) -> int:
    if slot_key in TIER_1:
        return 1
    if slot_key in TIER_2:
        return 2
    return 3


def slot_contracts() -> dict[str, dict]:
    """Return the single authoritative canonical slot registry."""
    contracts: dict[str, dict] = {}
    for key, (title, prompt, minimum) in CORE_SLOTS.items():
        contracts[key] = {
            "key": key, "title": title, "group": "core", "tier": 0, "required": True,
            "minimum_size": list(minimum), "transparent": False, "prompt": prompt,
        }
    for key in sprite_service.ALL_NAMES:
        readable = key.replace("__", " · mouth ").replace("gesture-", "Gesture · ").replace("_", " ")
        contracts[key] = {
            "key": key, "title": readable.title(), "group": "sprite", "tier": _sprite_tier(key),
            "required": key in TIER_1, "exact_size": list(sprite_service.SIZE), "transparent": True,
            "prompt": "Edit the approved calm base only in the named expression, mouth, or arm region. "
                      "Keep identity, head position, torso, outfit, lighting, and transparent canvas unchanged.",
        }
    return contracts


def get_contract(slot_key: str) -> dict:
    """Return one canonical contract or reject unknown keys."""
    contract = slot_contracts().get(slot_key)
    if contract is None:
        raise ValidationError("Unknown character asset slot")
    return contract


def _asset_kind(contract: dict) -> str:
    return "sprite" if contract["group"] == "sprite" else contract["key"]


def _asset_view(row: dict) -> dict:
    result = dict(row)
    result["content_url"] = f"/api/visuals/assets/{result['id']}/content"
    result["validation"] = json.loads(result.pop("validation_json") or "{}")
    result.pop("path", None)
    return result


async def asset_slots(db: aiosqlite.Connection, character_id: str) -> dict:
    """List slot contracts and current-version persisted state for one profile."""
    character = await library.get_character_row(db, character_id)
    cursor = await db.execute(
        "SELECT * FROM character_assets WHERE character_id = ? AND identity_version = ? AND is_current = 1",
        (character_id, character["identity_version"]),
    )
    current = {row["slot_key"]: _asset_view(dict(row)) for row in await cursor.fetchall() if row["slot_key"]}
    groups: dict[str, list[dict]] = {"core": [], "tier_1": [], "tier_2": [], "tier_3": []}
    for contract in slot_contracts().values():
        group = "core" if contract["group"] == "core" else f"tier_{contract['tier']}"
        groups[group].append({**contract, "asset": current.get(contract["key"]),
                              "state": (current.get(contract["key"]) or {}).get("review_state", "missing")})
    return {"character_id": character_id, "identity_version": character["identity_version"], "groups": groups}


async def store_prepared(
    db: aiosqlite.Connection,
    character_id: str,
    slot_key: str,
    original_filename: str,
    prepared: PreparedImage,
    expected_identity_version: int,
    *,
    replace_identity: bool = False,
    source: str = "external_upload",
) -> dict:
    """Persist one validated image and create a needs-review current asset row."""
    contract = get_contract(slot_key)
    character = await library.get_character_row(db, character_id)
    current_version = character["identity_version"]
    if expected_identity_version != current_version:
        raise ConflictError("Character identity changed; reload the profile before uploading")
    cursor = await db.execute(
        "SELECT * FROM character_assets WHERE character_id = ? AND identity_version = ? "
        "AND slot_key = ? AND is_current = 1",
        (character_id, current_version, slot_key),
    )
    previous = await cursor.fetchone()
    target_version = current_version
    if previous is not None and slot_key in IDENTITY_BASE_SLOTS:
        if not replace_identity:
            raise ConflictError("Replacing this identity base requires explicit confirmation")
        target_version += 1

    asset_id = str(uuid.uuid4())
    folder = settings.DATA_DIR / "library" / "characters" / character_id / f"v{target_version}"
    await asyncio.to_thread(folder.mkdir, parents=True, exist_ok=True)
    safe_slot = slot_key.replace("/", "-")
    temporary = folder / f".{asset_id}.upload"
    target = folder / f"{safe_slot}__{asset_id}.png"
    try:
        async with aiofiles.open(temporary, "wb") as destination:
            await destination.write(prepared.content)
        await asyncio.to_thread(temporary.replace, target)
        now = library._now()
        try:
            if target_version != current_version:
                await db.execute(
                    "UPDATE character_assets SET review_state = 'stale', approved = 0, updated_at = ? "
                    "WHERE character_id = ? AND identity_version = ? AND is_current = 1",
                    (now, character_id, current_version),
                )
                await db.execute(
                    "UPDATE characters SET identity_version = ?, status = 'draft', reference_asset_id = NULL, "
                    "updated_at = ? WHERE id = ?",
                    (target_version, now, character_id),
                )
            else:
                await db.execute(
                    "UPDATE character_assets SET is_current = 0, updated_at = ? WHERE character_id = ? "
                    "AND identity_version = ? AND slot_key = ? AND is_current = 1",
                    (now, character_id, target_version, slot_key),
                )
            await db.execute(
                "INSERT INTO character_assets (id, character_id, kind, path, seed, prompt_tokens, prompt_truncated, "
                "approved, created_at, slot_key, source, original_filename, review_state, validation_json, "
                "identity_version, is_current, updated_at) "
                "VALUES (?, ?, ?, ?, NULL, NULL, 0, 0, ?, ?, ?, ?, 'needs_review', ?, ?, 1, ?)",
                (asset_id, character_id, _asset_kind(contract), str(target), now, slot_key, source,
                 Path(original_filename).name, json.dumps(prepared.validation()), target_version, now),
            )
            if slot_key == "face":
                await db.execute("UPDATE characters SET reference_asset_id = ? WHERE id = ?", (asset_id, character_id))
        except Exception:
            await asyncio.to_thread(target.unlink, missing_ok=True)
            raise
    finally:
        await asyncio.to_thread(temporary.unlink, missing_ok=True)
    return _asset_view(dict(await (await db.execute(
        "SELECT * FROM character_assets WHERE id = ?", (asset_id,)
    )).fetchone()))


async def review_asset(
    db: aiosqlite.Connection, character_id: str, asset_id: str, review_state: str,
) -> dict:
    """Apply an explicit owner review to a current asset."""
    if review_state not in {"needs_review", "approved", "rejected"}:
        raise ValidationError("Unknown asset review state")
    cursor = await db.execute(
        "SELECT * FROM character_assets WHERE id = ? AND character_id = ?", (asset_id, character_id)
    )
    row = await cursor.fetchone()
    if row is None:
        raise NotFoundError("Character asset not found")
    if not row["is_current"]:
        raise ConflictError("Only the current slot asset can be reviewed")
    await db.execute(
        "UPDATE character_assets SET review_state = ?, approved = ?, updated_at = ? WHERE id = ?",
        (review_state, int(review_state == "approved"), library._now(), asset_id),
    )
    updated = await (await db.execute("SELECT * FROM character_assets WHERE id = ?", (asset_id,))).fetchone()
    return _asset_view(dict(updated))


async def remove_asset(db: aiosqlite.Connection, character_id: str, asset_id: str) -> Path | None:
    """Remove a current asset from the profile; retain pinned-version files as history."""
    cursor = await db.execute(
        "SELECT * FROM character_assets WHERE id = ? AND character_id = ?", (asset_id, character_id)
    )
    row = await cursor.fetchone()
    if row is None:
        raise NotFoundError("Character asset not found")
    pinned = await (await db.execute(
        "SELECT 1 FROM project_cast WHERE character_id = ? AND profile_version = ? LIMIT 1",
        (character_id, row["identity_version"]),
    )).fetchone()
    if pinned is not None:
        await db.execute(
            "UPDATE character_assets SET is_current = 0, review_state = 'stale', approved = 0, updated_at = ? WHERE id = ?",
            (library._now(), asset_id),
        )
        return None
    await db.execute("DELETE FROM character_assets WHERE id = ?", (asset_id,))
    return Path(row["path"])


async def prompt_pack(db: aiosqlite.Connection, character_id: str) -> tuple[str, bytes]:
    """Build a provider-neutral ZIP with requirements, prompts, and current references."""
    character = await library.get_character_row(db, character_id)
    slots = slot_contracts()
    memory = io.BytesIO()
    with zipfile.ZipFile(memory, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        archive.writestr(
            "README.md",
            f"# {character['name']} — Character asset prompt pack\n\n"
            f"Identity version: {character['identity_version']}\n\n"
            "Create one image per canonical slot. Upload each result into the matching slot in the app. "
            "Sprite images must be transparent 1280×1536 PNG files and keep the approved base aligned.\n",
        )
        archive.writestr("slots.json", json.dumps(list(slots.values()), indent=2))
        cursor = await db.execute(
            "SELECT slot_key, path FROM character_assets WHERE character_id = ? AND identity_version = ? "
            "AND is_current = 1 AND approved = 1 AND slot_key IN ('face', 'full_body', 'calm__closed')",
            (character_id, character["identity_version"]),
        )
        for row in await cursor.fetchall():
            path = Path(row["path"])
            if path.is_file():
                archive.write(path, f"references/{row['slot_key']}.png")
    return f"{library.normalize_character_name(character['name']).replace(' ', '-')}-prompt-pack.zip", memory.getvalue()
