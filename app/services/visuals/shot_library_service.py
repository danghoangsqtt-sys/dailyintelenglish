"""Task 29.4 / 29.5 (ENH-020): the shot library of ready-made pictures of the cast, and the matcher that reuses them.

A library shot is described by tags (scene, framing, the ordered characters, action, expression) so a match is a lookup,
not a guess. Only `approved`, non-stale shots are reused; a shot is tied to each character's face reference through a
signature, so a regenerated character makes its shots stale instead of silently reused.
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import shutil
import uuid
from pathlib import Path
from typing import Any

import aiosqlite

from app.core.config import settings
from app.core.exceptions import ConflictError, NotFoundError, ValidationError
from app.services.visuals import library_service as library

REVIEW_STATES = ("pending", "approved", "rejected")
LIBRARY_KINDS = ("single", "duo_close", "duo_wide")
# An expression is reused for the same expression, and calm and smile stand in for each other (both are a relaxed talk).
_RELAXED = {"calm", "smile"}


def shots_dir() -> Path:
    return settings.DATA_DIR / "library" / "shots"


def _expression_fits(wanted: str, have: str) -> bool:
    return wanted == have or (wanted in _RELAXED and have in _RELAXED)


def _gaze_fits(have: str) -> bool:
    """A shot drawn with the gaze fix is never offered to a setup that turned the fix off, and the other way round."""
    return (have == "off") if settings.VISUALS_GAZE == "off" else (have != "off")


async def face_signature(db: aiosqlite.Connection, character_ids: list[str]) -> str:
    """One string for the face references of these characters, in order: asset id and size of each `face`."""
    parts = []
    for character_id in character_ids:
        assets = await library.list_assets(db, character_id)
        face = next((asset for asset in assets if asset["kind"] == "face"), None)
        if face is None:
            parts.append("none")
            continue
        try:
            size = Path(face["path"]).stat().st_size
        except OSError:
            size = 0
        parts.append(f"{face['id']}:{size}")
    return "|".join(parts)


async def cast_character_ids(db: aiosqlite.Connection, project_id: str, speaker_indexes: list[int]) -> list[str] | None:
    """The characters of these speakers in order, or None when a speaker is not cast."""
    cursor = await db.execute("SELECT speaker_index, character_id FROM project_cast WHERE project_id = ?", (project_id,))
    cast = {row[0]: row[1] for row in await cursor.fetchall()}
    if not speaker_indexes or any(index not in cast for index in speaker_indexes):
        return None
    return [cast[index] for index in speaker_indexes]


def _view(row: dict) -> dict:
    view = dict(row)
    view["character_ids"] = json.loads(view.pop("character_ids_json"))
    view["stale"] = bool(view["stale"])
    view["content_url"] = f"/api/visuals/library/shots/{view['id']}/content"
    view.pop("path", None)
    view.pop("face_signature", None)
    return view


async def _get_row(db: aiosqlite.Connection, shot_id: str) -> dict:
    cursor = await db.execute("SELECT * FROM shot_library WHERE id = ?", (shot_id,))
    row = await cursor.fetchone()
    if row is None:
        raise NotFoundError("Library shot not found")
    return dict(row)


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


async def add_from_project_shot(db: aiosqlite.Connection, project_id: str, shot_id: str) -> dict:
    """Copy a finished project shot into the library as `pending` (the owner approves it once). The same picture is
    never added twice. Caller holds the write transaction."""
    from app.services.visuals import project_visuals_service as project_visuals

    shot = await project_visuals.get_shot_row(db, project_id, shot_id)
    if shot["kind"] not in LIBRARY_KINDS:
        raise ValidationError("Only a single or a duo shot of the cast can go to the library")
    if shot["status"] != "complete" or not shot["final_path"]:
        raise ConflictError("The shot has no finished picture yet")
    character_ids = await cast_character_ids(db, project_id, json.loads(shot["speaker_indexes"]))
    if character_ids is None:
        raise ValidationError("The shot's speakers are not cast characters")
    source = await asyncio.to_thread(project_visuals.resolve_shot_content, project_id, shot["final_path"])
    digest = await asyncio.to_thread(_sha, source)
    cursor = await db.execute("SELECT * FROM shot_library WHERE content_sha = ?", (digest,))
    existing = await cursor.fetchone()
    if existing is not None:
        return _view(dict(existing))
    library_id = str(uuid.uuid4())
    target = shots_dir() / f"{library_id}.png"
    await asyncio.to_thread(target.parent.mkdir, parents=True, exist_ok=True)
    await asyncio.to_thread(shutil.copyfile, source, target)
    now = library._now()
    await db.execute(
        "INSERT INTO shot_library (id, kind, scene_id, character_ids_json, action, expression, gaze, face_signature, "
        "path, content_sha, review_state, source_project_id, created_at, updated_at) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'pending', ?, ?, ?)",
        (library_id, shot["kind"], shot["scene_id"], json.dumps(character_ids), shot.get("action") or "",
         shot.get("expression") or "calm", settings.VISUALS_GAZE, await face_signature(db, character_ids),
         str(target), digest, project_id, now, now),
    )
    return _view(await _get_row(db, library_id))


async def refresh_stale(db: aiosqlite.Connection) -> int:
    """Mark a shot stale when the face reference of any of its characters changed since it was drawn."""
    cursor = await db.execute("SELECT id, character_ids_json, face_signature FROM shot_library WHERE stale = 0")
    rows = await cursor.fetchall()
    marked, cache = 0, {}
    for row in rows:
        ids = json.loads(row["character_ids_json"])
        key = tuple(ids)
        if key not in cache:
            try:
                cache[key] = await face_signature(db, ids)
            except NotFoundError:
                cache[key] = "gone"
        if cache[key] != row["face_signature"]:
            await db.execute("UPDATE shot_library SET stale = 1, updated_at = ? WHERE id = ?", (library._now(), row["id"]))
            marked += 1
    return marked


async def list_shots(db: aiosqlite.Connection, scene_id: str | None = None, kind: str | None = None,
                     review_state: str | None = None, character_id: str | None = None) -> list[dict]:
    clauses, params = [], []
    for column, value in (("scene_id", scene_id), ("kind", kind), ("review_state", review_state)):
        if value:
            clauses.append(f"{column} = ?")
            params.append(value)
    where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
    cursor = await db.execute(f"SELECT * FROM shot_library {where} ORDER BY created_at DESC, rowid DESC", tuple(params))
    views = [_view(dict(row)) for row in await cursor.fetchall()]
    if character_id:
        views = [view for view in views if character_id in view["character_ids"]]
    return views


async def set_review(db: aiosqlite.Connection, shot_id: str, review_state: str) -> dict:
    if review_state not in REVIEW_STATES:
        raise ValidationError(f"review_state must be one of {', '.join(REVIEW_STATES)}")
    await _get_row(db, shot_id)
    await db.execute("UPDATE shot_library SET review_state = ?, updated_at = ? WHERE id = ?",
                     (review_state, library._now(), shot_id))
    return _view(await _get_row(db, shot_id))


async def delete_shot(db: aiosqlite.Connection, shot_id: str) -> None:
    row = await _get_row(db, shot_id)
    await db.execute("DELETE FROM shot_library WHERE id = ?", (shot_id,))
    await asyncio.to_thread(Path(row["path"]).unlink, True)


async def content_path(db: aiosqlite.Connection, shot_id: str) -> Path:
    row = await _get_row(db, shot_id)
    root = shots_dir().resolve()
    candidate = Path(row["path"]).resolve()
    if not candidate.is_relative_to(root) or not candidate.is_file():
        raise NotFoundError("Library shot image not found")
    return candidate


async def find_match(db: aiosqlite.Connection, *, scene_id: str, kind: str, character_ids: list[str], action: str,
                     expression: str, exclude: set[str] | None = None) -> dict | None:
    """The best approved, non-stale library shot for a shot spec, or None. The scene, framing, ordered characters and
    action must be the same (an empty action only matches an empty one); the expression is the same (calm and smile
    stand in for each other). Ranked by: not used lately, fewest uses. A shot in `exclude` (already used in this
    episode) is skipped, so a picture is not repeated inside one video."""
    if kind not in LIBRARY_KINDS or not scene_id or not character_ids:
        return None
    cursor = await db.execute(
        "SELECT * FROM shot_library WHERE scene_id = ? AND kind = ? AND character_ids_json = ? "
        "AND review_state = 'approved' AND stale = 0",
        (scene_id, kind, json.dumps(character_ids)),
    )
    candidates = [dict(row) for row in await cursor.fetchall()]
    if not candidates:
        return None
    signature = await face_signature(db, character_ids)
    usable = []
    for row in candidates:
        if row["face_signature"] != signature:
            await db.execute("UPDATE shot_library SET stale = 1, updated_at = ? WHERE id = ?", (library._now(), row["id"]))
            continue
        if (row["id"] in (exclude or set()) or row["action"].strip().lower() != (action or "").strip().lower()
                or not _expression_fits(expression or "calm", row["expression"]) or not _gaze_fits(row["gaze"])
                or not Path(row["path"]).is_file()):
            continue
        usable.append(row)
    if not usable:
        return None
    usable.sort(key=lambda row: (row["use_count"], row["last_used_at"] or ""))
    return usable[0]


async def mark_used(db: aiosqlite.Connection, shot_id: str) -> None:
    await db.execute("UPDATE shot_library SET use_count = use_count + 1, last_used_at = ? WHERE id = ?",
                     (library._now(), shot_id))


async def coverage(db: aiosqlite.Connection, project_id: str) -> dict[str, Any]:
    """What the library already covers for this project's shots (the approved storyboard's specs, else the shots that
    exist): per shot whether an approved picture would be reused, and the totals."""
    from app.services.visuals import project_visuals_service as project_visuals
    from app.services.visuals import storyboard_service

    cast = await project_visuals.cast_rows(db, project_id)
    beats = await storyboard_service.approved_beats(db, project_id)
    if beats is not None and cast:
        specs = project_visuals.storyboard_shot_specs(beats, cast)
    else:
        specs = [{**row, "speakers": json.loads(row["speaker_indexes"])} for row in await project_visuals.shot_rows(db, project_id)]
    used: set[str] = set()
    items = []
    for spec in specs:
        if spec["kind"] == "insert":
            items.append({"kind": "insert", "covered": False, "reusable": False})
            continue
        ids = await cast_character_ids(db, project_id, list(spec["speakers"]))
        match = (await find_match(db, scene_id=spec["scene_id"], kind=spec["kind"], character_ids=ids or [],
                                  action=spec.get("action") or "", expression=spec.get("expression") or "calm",
                                  exclude=used) if ids else None)
        if match:
            used.add(match["id"])
        items.append({"kind": spec["kind"], "scene_id": spec["scene_id"], "action": spec.get("action") or "",
                      "expression": spec.get("expression") or "calm", "covered": match is not None, "reusable": True,
                      "library_shot_id": match["id"] if match else None})
    reusable = [item for item in items if item["reusable"]]
    return {"items": items, "total": len(reusable), "covered": sum(1 for item in reusable if item["covered"]),
            "missing": sum(1 for item in reusable if not item["covered"])}


async def reuse_for_rows(db: aiosqlite.Connection, project_id: str, rows: list[dict]) -> tuple[list[dict], list[str]]:
    """Task 29.5: copy an approved library shot into each pending non-insert row that has a match (no GPU) and return
    (the rows still to generate, the ids of the rows served from the library). Caller holds the write transaction."""
    if not settings.VISUALS_USE_LIBRARY:
        return rows, []
    remaining, served, used = [], [], set()
    for row in rows:
        if row["kind"] not in LIBRARY_KINDS:
            remaining.append(row)
            continue
        ids = await cast_character_ids(db, project_id, json.loads(row["speaker_indexes"]))
        match = (await find_match(db, scene_id=row["scene_id"], kind=row["kind"], character_ids=ids,
                                  action=row.get("action") or "", expression=row.get("expression") or "calm",
                                  exclude=used) if ids else None)
        if match is None:
            remaining.append(row)
            continue
        folder = settings.DATA_DIR / "visuals" / project_id / "shots" / row["id"]
        final_path = folder / "final.png"
        await asyncio.to_thread(folder.mkdir, parents=True, exist_ok=True)
        await asyncio.to_thread(shutil.copyfile, match["path"], final_path)
        await db.execute(
            "UPDATE project_shots SET final_path = ?, status = 'complete', review_note = NULL, source = 'library', "
            "library_shot_id = ?, error = NULL, updated_at = ? WHERE id = ?",
            (str(final_path), match["id"], library._now(), row["id"]),
        )
        await mark_used(db, match["id"])
        used.add(match["id"])
        served.append(row["id"])
    return remaining, served
