"""Project cast, ordered scenes, shot records and safe shot content."""

from __future__ import annotations

import json
import random
import uuid
from pathlib import Path

import aiosqlite

from app.core.config import settings
from app.core.exceptions import NotFoundError, ValidationError
from app.services import project_service
from app.services.visuals import library_service as library


async def cast_rows(db: aiosqlite.Connection, project_id: str) -> list[dict]:
    cursor = await db.execute(
        "SELECT pc.speaker_index, pc.character_id, c.name, c.top_color, c.status "
        "FROM project_cast pc JOIN characters c ON c.id = pc.character_id "
        "WHERE pc.project_id = ? ORDER BY pc.speaker_index",
        (project_id,),
    )
    return [dict(row) for row in await cursor.fetchall()]


async def scene_rows(db: aiosqlite.Connection, project_id: str) -> list[dict]:
    cursor = await db.execute(
        "SELECT ps.position, s.* FROM project_scenes ps JOIN scenes s ON s.id = ps.scene_id "
        "WHERE ps.project_id = ? ORDER BY ps.position",
        (project_id,),
    )
    return [dict(row) for row in await cursor.fetchall()]


async def shot_rows(db: aiosqlite.Connection, project_id: str) -> list[dict]:
    cursor = await db.execute(
        "SELECT * FROM project_shots WHERE project_id = ? ORDER BY created_at, rowid", (project_id,)
    )
    return [dict(row) for row in await cursor.fetchall()]


async def get_shot_row(db: aiosqlite.Connection, project_id: str, shot_id: str) -> dict:
    cursor = await db.execute(
        "SELECT * FROM project_shots WHERE id = ? AND project_id = ?", (shot_id, project_id)
    )
    row = await cursor.fetchone()
    if row is None:
        raise NotFoundError("Project shot not found")
    return dict(row)


async def _warnings(db: aiosqlite.Connection, project_id: str) -> list[str]:
    cast = await cast_rows(db, project_id)
    colors = [member["top_color"] for member in cast]
    return ["Characters share a top colour; colours may bleed in duo shots."] if len(colors) != len(set(colors)) else []


async def project_visuals(db: aiosqlite.Connection, project_id: str) -> dict:
    await project_service.get_project(db, project_id)
    cast = await cast_rows(db, project_id)
    for member in cast:
        assets = await library.list_assets(db, member["character_id"])
        face = next((asset for asset in assets if asset["kind"] == "face"), None)
        member["face_url"] = f"/api/visuals/assets/{face['id']}/content" if face else None
    scenes = await scene_rows(db, project_id)
    for scene in scenes:
        scene["preview_url"] = f"/api/visuals/scenes/{scene['id']}/preview" if scene["preview_path"] else None
        scene.pop("preview_path", None)
    shots = await shot_rows(db, project_id)
    for shot in shots:
        shot["speaker_indexes"] = json.loads(shot["speaker_indexes"])
        shot["raw_url"] = (
            f"/api/projects/{project_id}/visuals/shots/{shot['id']}/content?variant=raw"
            if shot["raw_path"] else None
        )
        shot["final_url"] = (
            f"/api/projects/{project_id}/visuals/shots/{shot['id']}/content?variant=final"
            if shot["final_path"] else None
        )
        shot.pop("raw_path", None)
        shot.pop("final_path", None)
    cursor = await db.execute(
        "SELECT * FROM image_jobs WHERE status IN ('pending', 'running') "
        "AND kind IN ('project_shots', 'shot_regenerate') ORDER BY created_at"
    )
    active = next((job for job in await cursor.fetchall()
                   if (job["kind"] == "project_shots" and job["target_id"] == project_id)
                   or (job["kind"] == "shot_regenerate"
                       and json.loads(job["payload_json"]).get("project_id") == project_id)), None)
    return {"cast": cast, "scenes": scenes, "shots": shots,
            "warnings": await _warnings(db, project_id), "active_job": dict(active) if active else None}


async def set_cast(db: aiosqlite.Connection, project_id: str, members: list[dict]) -> dict:
    project = await project_service.get_project(db, project_id)
    valid_indexes = {speaker["speaker_index"] for speaker in project["speakers"]}
    indexes = [member["speaker_index"] for member in members]
    if len(indexes) != len(set(indexes)) or any(index not in valid_indexes for index in indexes):
        raise ValidationError("Cast speaker indexes must be unique and exist in this project")
    for member in members:
        character = await library.get_character_row(db, member["character_id"])
        if character["status"] != "locked":
            raise ValidationError("Only locked characters can join a project cast")
    await db.execute("DELETE FROM project_cast WHERE project_id = ?", (project_id,))
    for member in members:
        await db.execute(
            "INSERT INTO project_cast (project_id, speaker_index, character_id) VALUES (?, ?, ?)",
            (project_id, member["speaker_index"], member["character_id"]),
        )
    return await project_visuals(db, project_id)


async def set_scenes(db: aiosqlite.Connection, project_id: str, scene_ids: list[str]) -> dict:
    await project_service.get_project(db, project_id)
    if not 1 <= len(scene_ids) <= 3 or len(set(scene_ids)) != len(scene_ids):
        raise ValidationError("Select one to three distinct scenes")
    for scene_id in scene_ids:
        await library.get_scene_row(db, scene_id)
    await db.execute("DELETE FROM project_scenes WHERE project_id = ?", (project_id,))
    for position, scene_id in enumerate(scene_ids):
        await db.execute(
            "INSERT INTO project_scenes (project_id, position, scene_id) VALUES (?, ?, ?)",
            (project_id, position, scene_id),
        )
    return await project_visuals(db, project_id)


async def prepare_shots(db: aiosqlite.Connection, project_id: str) -> list[dict]:
    cast = await cast_rows(db, project_id)
    scenes = await scene_rows(db, project_id)
    if not cast or not scenes:
        raise ValidationError("Assign at least one locked character and one scene before generating shots")
    await db.execute("DELETE FROM project_shots WHERE project_id = ?", (project_id,))
    specs = []
    for scene in scenes:
        for member in cast:
            specs.append((scene["id"], "single", [member["speaker_index"]]))
        if len(cast) >= 2:
            pair = [cast[0]["speaker_index"], cast[1]["speaker_index"]]
            specs.extend((scene["id"], kind, pair) for kind in ("duo_close", "duo_wide"))
    now = library._now()
    for scene_id, kind, indexes in specs:
        await db.execute(
            "INSERT INTO project_shots (id, project_id, scene_id, kind, speaker_indexes, seed, status, "
            "created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, 'pending', ?, ?)",
            (str(uuid.uuid4()), project_id, scene_id, kind, json.dumps(indexes),
             random.randint(1, 2**31 - 1), now, now),
        )
    return await shot_rows(db, project_id)


async def prepare_regenerate(db: aiosqlite.Connection, project_id: str, shot_id: str) -> dict:
    shot = await get_shot_row(db, project_id, shot_id)
    seed = random.randint(1, 2**31 - 1)
    while seed == shot["seed"]:
        seed = random.randint(1, 2**31 - 1)
    await db.execute(
        "UPDATE project_shots SET seed = ?, status = 'pending', raw_path = NULL, final_path = NULL, "
        "error = NULL, updated_at = ? WHERE id = ?",
        (seed, library._now(), shot_id),
    )
    return await get_shot_row(db, project_id, shot_id)


def resolve_shot_content(project_id: str, path: str) -> Path:
    root = (settings.DATA_DIR / "visuals" / project_id / "shots").resolve()
    candidate = Path(path).resolve()
    if not candidate.is_relative_to(root) or not candidate.is_file():
        raise NotFoundError("Shot image not found")
    return candidate
