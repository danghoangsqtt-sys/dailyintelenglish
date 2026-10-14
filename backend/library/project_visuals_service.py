"""Project cast and ordered scenes. Phase 44 (D123): the two-person project shots are gone."""

from __future__ import annotations


import aiosqlite

from backend.core.exceptions import ValidationError
from backend.content import project_service
from backend.library import library_service as library


async def cast_rows(db: aiosqlite.Connection, project_id: str) -> list[dict]:
    cursor = await db.execute(
        "SELECT pc.speaker_index, pc.character_id, c.name, c.top_color, c.status, c.gender, c.sprite_facing "
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
    return {"cast": cast, "scenes": scenes}


async def set_cast(db: aiosqlite.Connection, project_id: str, members: list[dict]) -> dict:
    project = await project_service.get_project(db, project_id)
    valid_indexes = {speaker["speaker_index"] for speaker in project["speakers"]}
    indexes = [member["speaker_index"] for member in members]
    if len(indexes) != len(set(indexes)) or any(index not in valid_indexes for index in indexes):
        raise ValidationError("Cast speaker indexes must be unique and exist in this project")
    character_ids = [member["character_id"] for member in members]
    if len(character_ids) != len(set(character_ids)):  # Task 33.1: one profile per project (UNIQUE in migration 018)
        raise ValidationError("A character can play only one speaker in a project")
    versions = {}
    from backend.library import character_profile_service  # lazy: that module imports the library too

    for member in members:
        character = await library.get_character_row(db, member["character_id"])
        if character["status"] != "locked":  # Phase 33: a profile made from outside-AI pictures is never "locked"
            readiness = await character_profile_service.readiness(db, character)
            if not readiness["video_ready"]:
                missing = [item for key in ("profile", "voice", "core_visuals") for item in readiness[key]["missing"]]
                raise ValidationError(f"{character['name']} is not ready for videos yet: {', '.join(missing[:4])}")
        versions[member["character_id"]] = character["identity_version"]
    await db.execute("DELETE FROM project_cast WHERE project_id = ?", (project_id,))
    for member in members:
        await db.execute(
            "INSERT INTO project_cast (project_id, speaker_index, character_id, profile_version) VALUES (?, ?, ?, ?)",
            (project_id, member["speaker_index"], member["character_id"], versions[member["character_id"]]),
        )
    # Phase 40 (D119): the speaker takes the chosen character's name, in the script lines too
    speakers = {speaker["speaker_index"]: speaker for speaker in project["speakers"]}
    renamed = []
    voice_changed = False
    for member in members:
        character = await library.get_character_row(db, member["character_id"])
        speaker = speakers[member["speaker_index"]]
        if character["name"] and speaker["name"] != character["name"]:
            change = await project_service.rename_speaker(db, project_id, speaker["id"], character["name"], commit=False)
            if change["changed"]:
                renamed.append({"speaker_index": member["speaker_index"], **change})
        # the speaker also takes the character's voice (Edge TTS picks the voice from accent + gender)
        if await project_service.apply_character_voice(db, project_id, speaker, character):
            voice_changed = True
    if voice_changed and not renamed and await project_service.has_script(db, project_id):
        await project_service.mark_script_changed(db, project_id, commit=False)
    return {**await project_visuals(db, project_id), "renamed": renamed}


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
