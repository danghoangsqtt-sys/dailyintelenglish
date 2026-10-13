"""Phase 33 (Task 33.2): reusable character profiles -- Quick create, autosave, readiness, duplicate, archive and safe delete.

A profile is a `characters` row (migration 018/019 columns) plus its asset rows. Readiness is computed from the saved
fields and the approved current assets every time; nothing stores an aggregate "ready" status. The legacy character routes
(`library_service`) keep working on the same rows.
"""

from __future__ import annotations

import json
import random
import uuid
from datetime import datetime, timezone
from typing import Any

import aiosqlite

from backend.core.constants import EDGE_TTS_VOICE_MAP
from backend.core.exceptions import ConflictError, NotFoundError
from backend.schemas.visuals import SHEET_KINDS, ProfilePatch, ProfileQuickCreate
from backend.library import library_service as library
from backend.library import sprite_service

TIER1_SPRITES = ("calm__closed", "calm__open", "smile__closed", "smile__open", "surprised__closed", "surprised__open",
                 "blink")
TIER2_SPRITES = TIER1_SPRITES + tuple(f"{face}__{mouth}" for face in ("laugh", "thinking", "worried", "serious")
                                      for mouth in ("closed", "open"))
TIER3_SPRITES = sprite_service.ALL_NAMES
PROFILE_FIELDS = ("name", "gender", "accent", "appearance", "outfit")
# Columns a patch may write directly (API name -> column).
_PATCH_COLUMNS = {
    "name": "name", "gender": "gender", "accent": "default_accent", "nationality": "ethnicity", "appearance": "appearance",
    "outfit": "outfit", "intro": "intro", "speaking_style": "speaking_style", "dialogue_behavior": "dialogue_behavior",
    "default_voice_id": "default_voice_id", "default_speed": "default_speed", "default_pitch": "default_pitch",
    "default_volume": "default_volume", "wizard_step": "wizard_step",
}


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def default_voice(accent: str, gender: str) -> str:
    """D79: the Edge TTS voice a new profile starts with."""
    return EDGE_TTS_VOICE_MAP[accent][gender]


async def _row(db: aiosqlite.Connection, character_id: str) -> dict:
    cursor = await db.execute("SELECT * FROM characters WHERE id = ?", (character_id,))
    row = await cursor.fetchone()
    if row is None:
        raise NotFoundError("Character profile not found")
    return dict(row)


async def _approved_slots(db: aiosqlite.Connection, row: dict) -> set[str]:
    cursor = await db.execute(
        "SELECT slot_key FROM character_assets WHERE character_id = ? AND identity_version = ? AND facing = 'native' "
        "AND is_current = 1 AND review_state = 'approved' AND slot_key IS NOT NULL",
        (row["id"], row["identity_version"]),
    )
    return {item["slot_key"] for item in await cursor.fetchall()}


def _sprite_names(row: dict, slots: set[str]) -> set[str]:
    names = {slot.split("/", 1)[1] for slot in slots if slot.startswith("sprite/")}
    if names:
        return names
    legacy = sprite_service.load_set(row["id"])  # Lina/Alex before `register-sprites` ran on this database
    return set((legacy or {}).get("pictures", {}))


def _part(required: tuple[str, ...], present: set[str], label: str) -> dict[str, Any]:
    missing = [f"{label} {name}" for name in required if name not in present]
    return {"ready": not missing, "have": len(required) - len(missing), "need": len(required), "missing": missing}


async def readiness(db: aiosqlite.Connection, row: dict) -> dict[str, Any]:
    slots = await _approved_slots(db, row)
    sprites = _sprite_names(row, slots)
    filled = {"name": row["name"], "gender": row["gender"], "accent": row["default_accent"],
              "appearance": row["appearance"], "outfit": row["outfit"]}
    profile_missing = [f"profile {field}" for field in PROFILE_FIELDS if not (filled[field] or "").strip()]
    voice_missing = [label for label, value in (("voice", row["default_voice_id"]), ("voice accent", row["default_accent"]))
                     if not value]
    cursor = await db.execute("SELECT COUNT(*) AS n FROM activity_library WHERE character_id = ? AND review_state = 'approved'",
                              (row["id"],))
    activities = (await cursor.fetchone())["n"]
    result = {
        "profile": {"ready": not profile_missing, "missing": profile_missing},
        "voice": {"ready": not voice_missing, "missing": voice_missing},
        "core_visuals": _part(SHEET_KINDS, slots, "picture"),
        "talking_starter": _part(TIER1_SPRITES, sprites, "sprite"),
        "full_expressions": _part(TIER2_SPRITES, sprites, "sprite"),
        "full_sprite_pack": _part(TIER3_SPRITES, sprites, "sprite"),
        "activities": {"count": activities},
    }
    result["video_ready"] = all(result[key]["ready"] for key in ("profile", "voice", "core_visuals"))
    result["talking_ready"] = result["video_ready"] and result["talking_starter"]["ready"]
    return result


def _public(row: dict) -> dict[str, Any]:
    return {
        "id": row["id"], "name": row["name"], "gender": row["gender"], "accent": row["default_accent"],
        "nationality": row["ethnicity"], "appearance": row["appearance"], "outfit": row["outfit"], "intro": row["intro"],
        "personality": json.loads(row["personality_json"] or "[]"), "speaking_style": row["speaking_style"],
        "dialogue_behavior": row["dialogue_behavior"],
        "voice": {"engine": row["default_tts_engine"], "voice_id": row["default_voice_id"], "speed": row["default_speed"],
                  "pitch": row["default_pitch"], "volume": row["default_volume"]},
        "sprite_facing": row["sprite_facing"], "identity_version": row["identity_version"],
        "wizard_step": row["wizard_step"], "is_seed": bool(row["is_seed"]), "archived": row["archived_at"] is not None,
        "archived_at": row["archived_at"], "legacy_status": row["status"], "created_at": row["created_at"],
        "updated_at": row["updated_at"],
    }


async def _pictures(db: aiosqlite.Connection, row: dict) -> dict[str, str | None]:
    """URLs for the library card: the calm portrait when approved, else the current base sprite (any review state)."""
    cursor = await db.execute(
        "SELECT id, slot_key, review_state FROM character_assets WHERE character_id = ? AND identity_version = ? "
        "AND is_current = 1 AND facing = 'native' AND slot_key IN ('portrait_calm', 'sprite/calm__closed')",
        (row["id"], row["identity_version"]),
    )
    found = {item["slot_key"]: item for item in await cursor.fetchall()}

    def url(slot_key: str, approved_only: bool) -> str | None:
        asset = found.get(slot_key)
        if asset is None or (approved_only and asset["review_state"] != "approved"):
            return None
        return f"/api/visuals/profiles/{row['id']}/assets/{asset['id']}/content"

    return {"portrait": url("portrait_calm", True), "base": url("sprite/calm__closed", False)}


async def get_profile(db: aiosqlite.Connection, character_id: str) -> dict[str, Any]:
    row = await _row(db, character_id)
    return {**_public(row), "pictures": await _pictures(db, row), "readiness": await readiness(db, row)}


async def list_profiles(db: aiosqlite.Connection, q: str = "", state: str = "active") -> list[dict[str, Any]]:
    clauses, params = [], []
    if state == "active":
        clauses.append("archived_at IS NULL")
    elif state == "archived":
        clauses.append("archived_at IS NOT NULL")
    if q.strip():
        clauses.append("normalized_name LIKE ?")
        params.append(f"%{library.normalized_name(q)}%")
    where = f" WHERE {' AND '.join(clauses)}" if clauses else ""
    cursor = await db.execute(f"SELECT id FROM characters{where} ORDER BY is_seed DESC, created_at, id", params)
    return [await get_profile(db, item["id"]) for item in await cursor.fetchall()]


async def create_quick(db: aiosqlite.Connection, body: ProfileQuickCreate) -> dict[str, Any]:
    """D79: one screen -- name, gender, accent, nationality, appearance, outfit. Voice and facing are derived."""
    await _ensure_name_free(db, body.name)
    character_id, now = str(uuid.uuid4()), _now()
    await db.execute(
        "INSERT INTO characters (id, name, gender, age_group, ethnicity, role, hair, eyes, extra, top_color, top_item, "
        "bottom_color, bottom_item, status, base_seed, created_at, updated_at, normalized_name, default_accent, "
        "default_voice_id, sprite_facing, appearance, outfit, wizard_step) "
        "VALUES (?, ?, ?, 'adult', ?, '', '', '', '', '', '', '', '', 'draft', ?, ?, ?, ?, ?, ?, ?, ?, ?, 1)",
        (character_id, body.name, body.gender, body.nationality, random.randint(1, 2**31 - 5), now, now,
         library.normalized_name(body.name), body.accent, default_voice(body.accent, body.gender),
         library.default_sprite_facing(body.gender), body.appearance, body.outfit),
    )
    return await get_profile(db, character_id)


async def _ensure_name_free(db: aiosqlite.Connection, name: str, own_id: str | None = None) -> None:
    cursor = await db.execute(
        "SELECT 1 FROM characters WHERE normalized_name = ? AND archived_at IS NULL AND id IS NOT ?",
        (library.normalized_name(name), own_id),
    )
    if await cursor.fetchone() is not None:
        raise ConflictError(f"A character named {name.strip()!r} already exists")


async def patch_profile(db: aiosqlite.Connection, character_id: str, patch: ProfilePatch) -> dict[str, Any]:
    row = await _row(db, character_id)
    fields = patch.model_dump(exclude_unset=True)
    if not fields:
        return await get_profile(db, character_id)
    sets: dict[str, Any] = {}
    for key, value in fields.items():
        if key == "personality":
            sets["personality_json"] = json.dumps(value or [])
        elif value is not None or key == "nationality":
            sets[_PATCH_COLUMNS[key]] = value if value is not None else ""
    if "name" in fields and fields["name"]:
        await _ensure_name_free(db, fields["name"], own_id=character_id)
        sets["normalized_name"] = library.normalized_name(fields["name"])
    if fields.get("gender") and fields["gender"] != row["gender"]:
        sets["sprite_facing"] = library.default_sprite_facing(fields["gender"])
    accent = fields.get("accent") or row["default_accent"]
    gender = fields.get("gender") or row["gender"]
    if ("accent" in fields or "gender" in fields) and "default_voice_id" not in fields and accent:
        sets["default_voice_id"] = default_voice(accent, gender)  # keep the voice matching the new accent/gender
    sets["updated_at"] = _now()
    await db.execute(
        f"UPDATE characters SET {', '.join(f'{column} = ?' for column in sets)} WHERE id = ?",
        (*sets.values(), character_id),
    )
    return await get_profile(db, character_id)


async def duplicate(db: aiosqlite.Connection, character_id: str) -> dict[str, Any]:
    """A new profile with the same profile fields and a free name; pictures are not copied (a new identity)."""
    row = await _row(db, character_id)
    base = f"{row['name']} copy"
    name, counter = base, 1
    while True:
        cursor = await db.execute("SELECT 1 FROM characters WHERE normalized_name = ? AND archived_at IS NULL",
                                  (library.normalized_name(name),))
        if await cursor.fetchone() is None:
            break
        counter += 1
        name = f"{base} {counter}"
    new_id, now = str(uuid.uuid4()), _now()
    copied = {key: value for key, value in row.items() if key not in (
        "id", "name", "normalized_name", "status", "reference_asset_id", "created_at", "updated_at", "archived_at",
        "is_seed", "identity_version", "base_seed")}
    columns = ["id", "name", "normalized_name", "status", "base_seed", "created_at", "updated_at", *copied]
    values = [new_id, name, library.normalized_name(name), "draft", random.randint(1, 2**31 - 5), now, now,
              *copied.values()]
    await db.execute(f"INSERT INTO characters ({', '.join(columns)}) VALUES ({', '.join('?' * len(columns))})", values)
    return await get_profile(db, new_id)


async def archive(db: aiosqlite.Connection, character_id: str) -> dict[str, Any]:
    await _row(db, character_id)
    await db.execute("UPDATE characters SET archived_at = COALESCE(archived_at, ?), updated_at = ? WHERE id = ?",
                     (_now(), _now(), character_id))
    return await get_profile(db, character_id)


async def restore(db: aiosqlite.Connection, character_id: str) -> dict[str, Any]:
    row = await _row(db, character_id)
    await _ensure_name_free(db, row["name"], own_id=character_id)
    await db.execute("UPDATE characters SET archived_at = NULL, updated_at = ? WHERE id = ?", (_now(), character_id))
    return await get_profile(db, character_id)


async def dependencies(db: aiosqlite.Connection, character_id: str) -> dict[str, Any]:
    await _row(db, character_id)

    async def ids(sql: str, param: str = character_id) -> list[str]:
        cursor = await db.execute(sql, (param,))
        return [item[0] for item in await cursor.fetchall()]

    report = {
        "projects": await ids("SELECT DISTINCT project_id FROM project_cast WHERE character_id = ?"),
        # character_ids_json is a JSON list of IDs: look for the quoted ID
        "shot_library": len(await ids("SELECT id FROM shot_library WHERE instr(character_ids_json, ?) > 0",
                                      json.dumps(character_id))),
        "activities": len(await ids("SELECT id FROM activity_library WHERE character_id = ?")),
        "sprites": len(await ids("SELECT id FROM character_assets WHERE character_id = ? AND kind = 'sprite'")),
    }
    report["blocking"] = bool(report["projects"] or report["shot_library"] or report["activities"])
    return report


async def delete(db: aiosqlite.Connection, character_id: str) -> None:
    """Permanent deletion: never for a seed profile, never while a project, shot or activity picture depends on it."""
    row = await _row(db, character_id)
    if row["is_seed"]:
        raise ConflictError("Lina and Alex are protected profiles; archive them instead")
    report = await dependencies(db, character_id)
    if report["blocking"]:
        raise ConflictError("This character is still used; archive it instead (see its dependencies)")
    await library.delete_character(db, character_id, force=False)
