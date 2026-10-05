"""Task 24.1: storyboard storage, validation against the project, and the image estimate."""

from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from typing import Any

import aiosqlite

from app.core.config import settings
from app.core.exceptions import ValidationError
from app.models.storyboard import BeatInput, StoryboardInput

GPU_MINUTES_PER_IMAGE = 2  # measured 20.11/23.2 smokes: ~120 s per shot with checks and repair


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def estimate_images(beats: list[BeatInput] | list[dict], cast_size: int) -> int:
    """Owner E4: images follow places and actions, not duration. Each distinct place gets its
    framing set (one single per cast member, plus duo close + duo wide with two or more), each
    further distinct action in that place one image, and each insert one image."""
    framing = cast_size + (2 if cast_size >= 2 else 0)
    actions: dict[str, set[str]] = {}
    inserts = 0
    for beat in beats:
        item = beat if isinstance(beat, dict) else beat.model_dump()
        if item["kind"] == "insert":
            inserts += 1
            continue
        place = item.get("scene_id") or f"new:{item.get('new_place')}"
        actions.setdefault(place, set()).add(item.get("action") or "")
    return sum(max(framing, 1) + len(found) - 1 for found in actions.values()) + inserts


async def _line_speakers(db: aiosqlite.Connection, project_id: str) -> list[int]:
    cursor = await db.execute(
        "SELECT sp.speaker_index FROM script_lines sl JOIN speakers sp ON sp.id = sl.speaker_id "
        "WHERE sl.project_id = ? ORDER BY sl.line_index",
        (project_id,),
    )
    return [row[0] for row in await cursor.fetchall()]


async def _cast_indexes(db: aiosqlite.Connection, project_id: str) -> set[int]:
    cursor = await db.execute("SELECT speaker_index FROM project_cast WHERE project_id = ?", (project_id,))
    return {row[0] for row in await cursor.fetchall()}


def _view(meta: dict | None, rows: list[dict], cast_size: int, warnings: list[str]) -> dict[str, Any]:
    beats = [{
        "id": row["id"], "position": row["position"], "line_from": row["line_from"], "line_to": row["line_to"],
        "kind": row["kind"], "scene_id": row["scene_id"], "new_place": row["new_place"],
        "speakers": json.loads(row["speakers_json"]), "action": row["action"], "expression": row["expression"],
    } for row in rows]
    images = estimate_images(beats, cast_size) if beats else 0
    return {
        "status": meta["status"] if meta else None, "source": meta["source"] if meta else None,
        "updated_at": meta["updated_at"] if meta else None, "beats": beats,
        "estimate": {"images": images, "cap": settings.VISUALS_IMAGE_CAP,
                     "gpu_minutes": images * GPU_MINUTES_PER_IMAGE},
        "warnings": warnings,
    }


async def get_storyboard(db: aiosqlite.Connection, project_id: str) -> dict[str, Any]:
    cursor = await db.execute("SELECT * FROM project_storyboards WHERE project_id = ?", (project_id,))
    meta = await cursor.fetchone()
    cursor = await db.execute("SELECT * FROM project_beats WHERE project_id = ? ORDER BY position", (project_id,))
    rows = [dict(row) for row in await cursor.fetchall()]
    cast_size = len(await _cast_indexes(db, project_id))
    return _view(dict(meta) if meta else None, rows, cast_size, _speaker_warnings(rows, await _line_speakers(db, project_id)))


def _speaker_warnings(beats: list[dict], line_speakers: list[int]) -> list[str]:
    warnings = []
    for position, beat in enumerate(beats):
        speakers = beat["speakers"] if "speakers" in beat else json.loads(beat["speakers_json"])
        talking = set(line_speakers[beat["line_from"]:beat["line_to"] + 1])
        silent = [index for index in speakers if index not in talking]
        if beat["kind"] == "scene" and silent:
            warnings.append(f"beat {position + 1}: speaker(s) {silent} are on screen but do not speak in its lines")
    return warnings


async def replace_storyboard(db: aiosqlite.Connection, project_id: str, body: StoryboardInput,
                             source: str) -> dict[str, Any]:
    """Validate the beats against the project, then replace its storyboard (caller holds the write
    transaction)."""
    line_speakers = await _line_speakers(db, project_id)
    if not line_speakers:
        raise ValidationError("The project has no script lines to storyboard yet")
    beats = sorted(body.beats, key=lambda beat: beat.line_from)
    expected = 0
    for beat in beats:
        if beat.line_from != expected:
            problem = "overlap" if beat.line_from < expected else "gap"
            raise ValidationError(f"Beats must cover every script line once: {problem} at line {expected}")
        expected = beat.line_to + 1
    if expected != len(line_speakers):
        raise ValidationError(f"Beats must cover lines 0..{len(line_speakers) - 1}; they end at {expected - 1}")
    cast = await _cast_indexes(db, project_id)
    for position, beat in enumerate(beats):
        unknown = [index for index in beat.speakers if index not in cast]
        if unknown:
            raise ValidationError(f"beat {position + 1}: speaker(s) {unknown} are not in the project cast")
    scene_ids = {beat.scene_id for beat in beats if beat.scene_id}
    if scene_ids:
        marks = ",".join("?" * len(scene_ids))
        cursor = await db.execute(f"SELECT id FROM scenes WHERE id IN ({marks})", tuple(scene_ids))
        missing = scene_ids - {row[0] for row in await cursor.fetchall()}
        if missing:
            raise ValidationError(f"Unknown scene(s): {sorted(missing)}")
    images = estimate_images(beats, len(cast))
    if images > settings.VISUALS_IMAGE_CAP:
        raise ValidationError(
            f"This storyboard needs {images} images; the cap is {settings.VISUALS_IMAGE_CAP}. "
            "Reuse places, merge actions or drop inserts."
        )
    now = _now()
    await db.execute("DELETE FROM project_beats WHERE project_id = ?", (project_id,))
    for position, beat in enumerate(beats):
        await db.execute(
            "INSERT INTO project_beats (id, project_id, position, line_from, line_to, kind, scene_id, new_place, "
            "speakers_json, action, expression, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (str(uuid.uuid4()), project_id, position, beat.line_from, beat.line_to, beat.kind, beat.scene_id,
             beat.new_place, json.dumps(beat.speakers), beat.action, beat.expression, now, now),
        )
    await db.execute(
        "INSERT INTO project_storyboards (project_id, status, source, updated_at) VALUES (?, ?, ?, ?) "
        "ON CONFLICT(project_id) DO UPDATE SET status = excluded.status, source = excluded.source, "
        "updated_at = excluded.updated_at",
        (project_id, body.status, source, now),
    )
    return await get_storyboard(db, project_id)
