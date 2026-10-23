"""Phase 55 (ENH-037): the Solo stage — Scene Library plates and Activity Library pictures behind the presenter.

Choices and references are read from the database only (callers hold the shared lock); file hashing for approval and
render pinning runs outside it.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

import aiosqlite

from backend.core.exceptions import ConflictError, ValidationError
from backend.library.library_service import data_path


async def choices(db: aiosqlite.Connection, character_id: str) -> dict:
    """Scenes that have a plate, and approved activity pictures that are generic or the presenter's own."""
    scenes = [dict(row) for row in await (await db.execute(
        "SELECT id, name, place, category FROM scenes WHERE archived_at IS NULL "
        "AND preview_path IS NOT NULL AND preview_path <> '' ORDER BY category, name"
    )).fetchall()]
    activities = []
    for row in await (await db.execute(
        "SELECT id, activity, context_tags_json, character_id FROM activity_library WHERE review_state = 'approved' "
        "AND (character_id IS NULL OR character_id = ?) ORDER BY activity, character_id IS NULL, id", (character_id,)
    )).fetchall():
        try:
            tags = [str(tag) for tag in json.loads(row["context_tags_json"] or "[]")][:6]
        except (TypeError, ValueError):
            tags = []
        activities.append({"id": row["id"], "activity": row["activity"], "tags": tags,
                           "presenter_own": row["character_id"] is not None})
    return {"scenes": scenes, "activities": activities}


async def references(db: aiosqlite.Connection, segments: list, character_id: str) -> tuple[list[dict], list[dict]]:
    """The identity of every scene/activity the plan uses; an unusable one is marked so review can report it."""
    scenes, activities = {}, {}
    for segment in segments:
        if segment.scene and segment.scene.scene_id not in scenes:
            row = await (await db.execute("SELECT id, preview_path, updated_at FROM scenes WHERE id = ?",
                                          (segment.scene.scene_id,))).fetchone()
            scenes[segment.scene.scene_id] = ({"id": row["id"], "plate": row["preview_path"], "updated_at": row["updated_at"]}
                                              if row and row["preview_path"] else {"id": segment.scene.scene_id, "missing": True})
        if segment.visual.kind == "activity" and segment.visual.activity_id not in activities:
            row = await (await db.execute("SELECT id, path, content_sha, review_state, character_id FROM activity_library WHERE id = ?",
                                          (segment.visual.activity_id,))).fetchone()
            usable = row and row["review_state"] == "approved" and row["character_id"] in (None, character_id)
            activities[segment.visual.activity_id] = ({"id": row["id"], "path": row["path"], "content_sha": row["content_sha"]}
                                                      if usable else {"id": segment.visual.activity_id, "missing": True})
    return (sorted(scenes.values(), key=lambda item: item["id"]), sorted(activities.values(), key=lambda item: item["id"]))


def issues(source: dict, segments: list) -> list[str]:
    """Actionable review messages for unusable stage pictures."""
    missing_scenes = {item["id"] for item in source.get("scenes", []) if item.get("missing")}
    missing_activities = {item["id"] for item in source.get("activities", []) if item.get("missing")}
    result = []
    for segment in segments:
        if segment.scene and segment.scene.scene_id in missing_scenes:
            result.append(f"Segment {segment.id}: its scene has no plate; choose another scene or make the plate")
        if segment.visual.kind == "activity" and segment.visual.activity_id in missing_activities:
            result.append(f"Segment {segment.id}: its activity picture is not an approved picture of this presenter or a generic one")
    return result


def check_proposal(segments: list, captured: dict) -> None:
    """A proposal may use only the scenes and activities it was offered (older jobs offered none)."""
    offered_scenes = captured.get("available_scenes")
    offered_activities = captured.get("available_activities")
    for segment in segments:
        if segment.scene and offered_scenes is not None and segment.scene.scene_id not in {item["id"] for item in offered_scenes}:
            raise ValidationError(f"Segment {segment.id}: use only a scene_id from AVAILABLE SCENES")
        if segment.visual.kind == "activity" and (offered_activities is None
                                                  or segment.visual.activity_id not in {item["id"] for item in offered_activities}):
            raise ValidationError(f"Segment {segment.id}: use only an activity_id from AVAILABLE ACTIVITY PICTURES")


def _sha(path: Path) -> str:
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def pinned_files(source: dict) -> dict:
    """Blocking: hash every stage picture so approval pins exact bytes (run in a thread, outside the DB lock)."""
    scenes, activities = [], []
    for item in source.get("scenes", []):
        if item.get("missing"):
            raise ValidationError("A segment's scene has no plate; choose another scene")
        path = data_path(item["plate"]).resolve()
        if not path.is_file():
            raise ValidationError("A scene plate file is missing; make the plate again or choose another scene")
        scenes.append({"id": item["id"], "path": str(path), "content_hash": _sha(path)})
    for item in source.get("activities", []):
        if item.get("missing"):
            raise ValidationError("A segment's activity picture is not usable; choose another one")
        path = data_path(item["path"]).resolve()
        if not path.is_file():
            raise ValidationError("An activity picture file is missing; choose another one")
        activities.append({"id": item["id"], "path": str(path), "content_hash": _sha(path)})
    return {"scenes": scenes, "activities": activities}


def verify_unchanged(pinned: dict, current: dict) -> None:
    """Render refuses a plate/activity whose bytes changed after approval."""
    if pinned.get("stage", {"scenes": [], "activities": []}) != current:
        raise ConflictError("A scene plate or activity picture changed after approval; review and approve again")
