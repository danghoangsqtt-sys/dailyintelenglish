"""Reusable character-profile lifecycle and computed readiness."""

from __future__ import annotations

import json
from pathlib import Path

import aiosqlite

from app.core.exceptions import ConflictError, ValidationError
from app.models.visuals import CharacterInput, CharacterPatch
from app.services.visuals import library_service as library
from app.services.visuals import sprite_service

CORE_VISUAL_SLOTS = ("face", "full_body", "portrait_calm", "portrait_smile", "portrait_surprised")
TALKING_STARTER_SLOTS = (
    "calm__closed", "calm__open", "smile__closed", "smile__open",
    "surprised__closed", "surprised__open", "blink",
)
FULL_EXPRESSION_SLOTS = TALKING_STARTER_SLOTS + (
    "laugh__closed", "laugh__open", "thinking__closed", "thinking__open",
    "worried__closed", "worried__open", "serious__closed", "serious__open",
)
FULL_SPRITE_SLOTS = tuple(sprite_service.ALL_NAMES)
PROFILE_COLUMNS = {
    "intro", "speaking_style", "dialogue_behavior", "default_accent", "default_tts_engine",
    "default_voice_id", "default_voice_description", "default_speed", "default_pitch", "default_volume",
    "wizard_step",
}


def _state(required: tuple[str, ...], available: set[str]) -> dict:
    missing = [item for item in required if item not in available]
    if not missing:
        value = "ready"
    elif len(missing) == len(required):
        value = "missing"
    else:
        value = "partial"
    return {"state": value, "missing": missing, "complete": len(required) - len(missing), "total": len(required)}


async def _activity_counts(db: aiosqlite.Connection, character_id: str) -> dict:
    cursor = await db.execute(
        "SELECT review_state, COUNT(*) FROM activity_library WHERE character_id = ? GROUP BY review_state",
        (character_id,),
    )
    counts = {row[0]: row[1] for row in await cursor.fetchall()}
    generic = await (await db.execute(
        "SELECT COUNT(*) FROM activity_library WHERE character_id IS NULL AND review_state = 'approved'"
    )).fetchone()
    return {
        "approved": counts.get("approved", 0), "pending": counts.get("pending", 0),
        "rejected": counts.get("rejected", 0), "generic_approved": generic[0],
    }


async def readiness(db: aiosqlite.Connection, row: dict, assets: list[dict] | None = None) -> dict:
    """Compute independent capability badges from current persisted data."""
    assets = assets if assets is not None else await library.list_assets(db, row["id"])
    stored_personality = row.get("personality", row.get("personality_json") or "[]")
    personality = stored_personality if isinstance(stored_personality, list) else json.loads(stored_personality)
    profile_missing = [
        label for label, present in (
            ("name", bool(row.get("name"))), ("role", bool(row.get("role"))),
            ("personality", bool(personality)), ("speaking_style", bool(row.get("speaking_style"))),
        ) if not present
    ]
    voice_missing = [
        label for label, present in (
            ("tts_engine", bool(row.get("default_tts_engine"))),
            ("voice_id", bool(row.get("default_voice_id"))),
        ) if not present
    ]
    approved = {
        asset.get("slot_key") or asset["kind"] for asset in assets
        if asset.get("is_current", 1) and (asset.get("review_state") == "approved" or asset.get("approved"))
    }
    # Phase 20 locked profiles already passed the four-sheet review. Their face row was
    # an internal crop rather than a separately reviewed asset.
    if row.get("status") == "locked" and any(asset["kind"] == "face" for asset in assets):
        approved.add("face")
    sprite_names = {asset.get("slot_key") for asset in assets if asset.get("kind") == "sprite" and asset.get("approved")}
    legacy_set = sprite_service.load_set(row["id"])
    if legacy_set:
        sprite_names.update(legacy_set["names"])
    activity = await _activity_counts(db, row["id"])
    return {
        "profile": {"state": "ready" if not profile_missing else "missing", "missing": profile_missing},
        "voice": {"state": "ready" if not voice_missing else "missing", "missing": voice_missing},
        "visual": _state(CORE_VISUAL_SLOTS, approved),
        "talking_starter": _state(TALKING_STARTER_SLOTS, sprite_names),
        "full_expressions": _state(FULL_EXPRESSION_SLOTS, sprite_names),
        "full_sprite_pack": _state(FULL_SPRITE_SLOTS, sprite_names),
        "activities": activity,
    }


async def profile_view(db: aiosqlite.Connection, character_id: str) -> dict:
    """Return the legacy character view enriched with profile fields and readiness."""
    view = await library.character_view(db, character_id)
    view["personality"] = json.loads(view.pop("personality_json") or "[]")
    view["lifecycle"] = "archived" if view.get("archived_at") else "active"
    view["readiness"] = await readiness(db, view)
    return view


async def list_profiles(
    db: aiosqlite.Connection, *, query: str = "", state: str = "active", readiness_filter: str = "",
) -> list[dict]:
    """List filtered profiles in stable display-name order."""
    clauses: list[str] = []
    params: list[str] = []
    if state == "active":
        clauses.append("archived_at IS NULL")
    elif state == "archived":
        clauses.append("archived_at IS NOT NULL")
    normalized_query = library.normalize_character_name(query)
    if normalized_query:
        clauses.append("(normalized_name LIKE ? OR lower(role) LIKE ?)")
        params.extend((f"%{normalized_query}%", f"%{normalized_query}%"))
    where = f" WHERE {' AND '.join(clauses)}" if clauses else ""
    cursor = await db.execute(f"SELECT id FROM characters{where} ORDER BY normalized_name, id", params)
    profiles = [await profile_view(db, row[0]) for row in await cursor.fetchall()]
    if not readiness_filter:
        return profiles
    if readiness_filter == "video_ready":
        return [item for item in profiles if item["readiness"]["voice"]["state"] == "ready"
                and item["readiness"]["visual"]["state"] == "ready"]
    if readiness_filter == "talking_ready":
        return [item for item in profiles if item["readiness"]["talking_starter"]["state"] == "ready"]
    if readiness_filter == "needs_setup":
        return [item for item in profiles if item["readiness"]["profile"]["state"] != "ready"
                or item["readiness"]["voice"]["state"] != "ready"
                or item["readiness"]["visual"]["state"] != "ready"]
    raise ValidationError("Unknown readiness filter")


async def _ensure_active_name_available(
    db: aiosqlite.Connection, name: str, *, excluding_id: str | None = None,
) -> str:
    normalized = library.normalize_character_name(name)
    cursor = await db.execute(
        "SELECT id FROM characters WHERE normalized_name = ? AND archived_at IS NULL",
        (normalized,),
    )
    row = await cursor.fetchone()
    if row is not None and row[0] != excluding_id:
        raise ConflictError("An active character profile already uses this name")
    return normalized


async def create_profile(db: aiosqlite.Connection, body: CharacterInput) -> dict:
    """Create a draft reusable profile while preserving legacy full-input support."""
    await _ensure_active_name_available(db, body.name)
    created = await library.create_character(db, body)
    values = body.model_dump()
    await db.execute(
        "UPDATE characters SET intro = ?, personality_json = ?, speaking_style = ?, dialogue_behavior = ?, "
        "default_accent = ?, default_tts_engine = ?, default_voice_id = ?, default_voice_description = ?, "
        "default_speed = ?, default_pitch = ?, default_volume = ?, wizard_step = ? WHERE id = ?",
        (values["intro"], json.dumps(values["personality"]), values["speaking_style"], values["dialogue_behavior"],
         values["default_accent"], values["default_tts_engine"], values["default_voice_id"],
         values["default_voice_description"], values["default_speed"], values["default_pitch"],
         values["default_volume"], values["wizard_step"], created["id"]),
    )
    return await profile_view(db, created["id"])


async def patch_profile(db: aiosqlite.Connection, character_id: str, patch: CharacterPatch) -> dict:
    """Autosave only supplied profile fields and retain legacy appearance validation."""
    await library.get_character_row(db, character_id)
    fields = patch.model_dump(exclude_unset=True)
    if any(value is None for value in fields.values()):
        raise ValidationError("Character profile fields cannot be null")
    if "name" in fields:
        await _ensure_active_name_available(db, fields["name"], excluding_id=character_id)
    appearance = {key: value for key, value in fields.items() if key in library.CHARACTER_FIELDS and key != "name"}
    if appearance:
        await library.edit_character(db, character_id, CharacterPatch(**appearance))
    updates: dict[str, object] = {}
    if "name" in fields:
        name = CharacterInput.validate_name(fields["name"])
        updates.update(name=name, normalized_name=library.normalize_character_name(name))
    for key in PROFILE_COLUMNS:
        if key in fields:
            updates[key] = fields[key]
    if "personality" in fields:
        updates["personality_json"] = json.dumps(fields["personality"])
    if updates:
        updates["updated_at"] = library._now()
        await db.execute(
            "UPDATE characters SET " + ", ".join(f"{key} = ?" for key in updates) + " WHERE id = ?",
            (*updates.values(), character_id),
        )
    return await profile_view(db, character_id)


async def duplicate_profile(db: aiosqlite.Connection, character_id: str) -> dict:
    """Copy profile fields into a new draft with no shared asset rows."""
    source = await library.get_character_row(db, character_id)
    base = f"{source['name']} copy"[:40]
    name = base
    number = 2
    while True:
        try:
            await _ensure_active_name_available(db, name)
            break
        except ConflictError:
            suffix = f" {number}"
            name = f"{base[:40 - len(suffix)]}{suffix}"
            number += 1
    body = CharacterInput(
        name=name, **{key: source[key] for key in library.CHARACTER_FIELDS if key != "name"},
        intro=source["intro"], personality=json.loads(source["personality_json"] or "[]"),
        speaking_style=source["speaking_style"], dialogue_behavior=source["dialogue_behavior"],
        default_accent=source["default_accent"], default_tts_engine=source["default_tts_engine"],
        default_voice_id=source["default_voice_id"], default_voice_description=source["default_voice_description"],
        default_speed=source["default_speed"], default_pitch=source["default_pitch"],
        default_volume=source["default_volume"], wizard_step=min(source["wizard_step"], 4),
    )
    return await create_profile(db, body)


async def archive_profile(db: aiosqlite.Connection, character_id: str) -> dict:
    """Archive a profile without changing any dependent project data."""
    await library.get_character_row(db, character_id)
    await db.execute(
        "UPDATE characters SET archived_at = COALESCE(archived_at, ?), updated_at = ? WHERE id = ?",
        (library._now(), library._now(), character_id),
    )
    return await profile_view(db, character_id)


async def restore_profile(db: aiosqlite.Connection, character_id: str) -> dict:
    """Restore an archived profile after checking its active display name."""
    row = await library.get_character_row(db, character_id)
    await _ensure_active_name_available(db, row["name"], excluding_id=character_id)
    await db.execute("UPDATE characters SET archived_at = NULL, updated_at = ? WHERE id = ?", (library._now(), character_id))
    return await profile_view(db, character_id)


async def dependencies(db: aiosqlite.Connection, character_id: str) -> dict:
    """Return all dependency classes that make permanent deletion unsafe."""
    row = await library.get_character_row(db, character_id)
    projects = await (await db.execute(
        "SELECT COUNT(DISTINCT project_id) FROM project_cast WHERE character_id = ?", (character_id,)
    )).fetchone()
    activities = await (await db.execute(
        "SELECT COUNT(*) FROM activity_library WHERE character_id = ?", (character_id,)
    )).fetchone()
    shot_cursor = await db.execute("SELECT character_ids_json FROM shot_library")
    shots = sum(character_id in json.loads(item[0]) for item in await shot_cursor.fetchall())
    sprite_set = sprite_service.load_set(character_id)
    result = {
        "projects": projects[0], "shots": shots, "activities": activities[0],
        "sprite_assets": len(sprite_set["names"]) if sprite_set else 0,
        "seed_profile": bool(row["is_seed"]),
    }
    result["can_delete"] = not result["seed_profile"] and not any(
        result[key] for key in ("projects", "shots", "activities")
    )
    return result


async def permanent_delete(db: aiosqlite.Connection, character_id: str) -> None:
    """Delete a non-seed profile only when no external dependency remains."""
    report = await dependencies(db, character_id)
    if not report["can_delete"]:
        raise ConflictError("Archive this profile instead; permanent deletion is blocked by seed protection or dependencies")
    await library.delete_character(db, character_id, force=False)


def profile_asset_root(data_dir: Path, character_id: str) -> Path:
    """Return the existing profile asset root for post-commit cleanup."""
    return data_dir / "library" / "characters" / character_id

