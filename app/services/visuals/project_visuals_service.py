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
        "SELECT pc.speaker_index, pc.character_id, pc.profile_version, c.name, c.top_color, c.status "
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
    # Task 24.5a: storyboard shots can use any library scene, and inserts have none.
    cursor = await db.execute("SELECT id, name FROM scenes")
    scene_names = {row[0]: row[1] for row in await cursor.fetchall()}
    for shot in shots:
        shot["speaker_indexes"] = json.loads(shot["speaker_indexes"])
        shot["scene_name"] = "Inserts" if shot["kind"] == "insert" else scene_names.get(shot["scene_id"], "Scene")
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
    character_ids = [member["character_id"] for member in members]
    if len(character_ids) != len(set(character_ids)):
        raise ValidationError("Each project speaker must use a distinct character profile")
    versions: dict[str, int] = {}
    characters: dict[str, dict] = {}
    for member in members:
        character = await library.get_character_row(db, member["character_id"])
        if character["status"] != "locked":
            raise ValidationError("Only locked characters can join a project cast")
        versions[member["character_id"]] = character["identity_version"]
        characters[member["character_id"]] = character
    await db.execute("DELETE FROM project_cast WHERE project_id = ?", (project_id,))
    for member in members:
        await db.execute(
            "INSERT INTO project_cast (project_id, speaker_index, character_id, profile_version) VALUES (?, ?, ?, ?)",
            (project_id, member["speaker_index"], member["character_id"], versions[member["character_id"]]),
        )
        if member.get("copy_profile_defaults"):
            character = characters[member["character_id"]]
            accent = character["default_accent"] or project["speakers"][member["speaker_index"]]["accent"]
            await db.execute(
                "UPDATE speakers SET name = ?, gender = ?, accent = ?, tts_engine = ?, voice_id = ?, "
                "voice_description = ?, speed = ?, pitch = ?, volume = ? "
                "WHERE project_id = ? AND speaker_index = ?",
                (
                    character["name"], character["gender"], accent,
                    character["default_tts_engine"], character["default_voice_id"] or None,
                    character["default_voice_description"], character["default_speed"],
                    character["default_pitch"], character["default_volume"], project_id,
                    member["speaker_index"],
                ),
            )
    if any(member.get("copy_profile_defaults") for member in members):
        await project_service.mark_speaker_voice_changed(db, project_id, commit=False)
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


def storyboard_shot_specs(beats: list[dict], cast: list[dict]) -> list[dict]:
    """Task 24.5a (owner E4): the pictures an approved storyboard needs, in order of first use.
    Per place: its framing set (one single per cast member, plus duo close + duo wide for the
    first reviewed pair) carrying the place's first action and expression; one action shot per
    later distinct action/pair (a duo wide for two people, else that person's single);
    one insert shot per insert. The count equals `storyboard_service.estimate_images`."""
    indexes = [member["speaker_index"] for member in cast]
    specs: list[dict] = []
    seen_moments: dict[str, set[tuple[str, tuple[int, ...]]]] = {}

    def participants(beat: dict) -> list[int]:
        reviewed = list(dict.fromkeys(
            index for index in (beat.get("speakers") or []) if index in indexes
        ))[:2]
        return reviewed or indexes[:2] or indexes[:1]

    for position, beat in enumerate(beats):
        if beat["kind"] == "insert":
            specs.append({"scene_id": "", "kind": "insert", "speakers": list(beat.get("speakers") or []),
                          "action": beat.get("action") or "", "expression": beat.get("expression") or "calm",
                          "subject": beat.get("new_place") or beat.get("action") or "an illustration",
                          "beat_position": position})
            continue
        place = beat["scene_id"]
        action, expression = beat.get("action") or "", beat.get("expression") or "calm"
        on_screen = participants(beat)
        signature = (action, tuple(on_screen))
        if place not in seen_moments:
            seen_moments[place] = {signature}
            for index in indexes:
                specs.append({"scene_id": place, "kind": "single", "speakers": [index], "action": action,
                              "expression": expression, "subject": None, "beat_position": None})
            if len(on_screen) == 2:
                for kind in ("duo_close", "duo_wide"):
                    specs.append({"scene_id": place, "kind": kind, "speakers": on_screen, "action": action,
                                  "expression": expression, "subject": None, "beat_position": None})
            continue
        if signature in seen_moments[place]:
            continue
        seen_moments[place].add(signature)
        if len(on_screen) == 2:
            kind, speakers = "duo_wide", on_screen
        else:
            kind, speakers = "single", on_screen[:1]
        specs.append({"scene_id": place, "kind": kind, "speakers": speakers, "action": action,
                      "expression": expression, "subject": None, "beat_position": position})
    return specs


async def prepare_storyboard_shots(db: aiosqlite.Connection, project_id: str) -> list[dict] | None:
    """Replace the project's shots with the approved storyboard's (caller holds the write
    transaction). None when there is no approved storyboard -- the caller uses `prepare_shots`."""
    from app.services.visuals import storyboard_service

    if await storyboard_service.approved_beats(db, project_id) is None:
        return None
    cast = await cast_rows(db, project_id)
    if not cast:
        raise ValidationError("Assign at least one locked character before generating storyboard shots")
    await storyboard_service.materialize_new_places(db, project_id)
    beats = await storyboard_service.approved_beats(db, project_id)
    specs = storyboard_shot_specs(beats, cast)
    expected = storyboard_service.estimate_images(beats, len(cast))
    if len(specs) != expected:  # one definition of "the pictures this storyboard needs"
        raise ValidationError(f"Storyboard shot plan has {len(specs)} images; the estimate is {expected}")
    await db.execute("DELETE FROM project_shots WHERE project_id = ?", (project_id,))
    now = library._now()
    for spec in specs:
        await db.execute(
            "INSERT INTO project_shots (id, project_id, scene_id, kind, speaker_indexes, seed, status, action, "
            "expression, subject, beat_position, created_at, updated_at) "
            "VALUES (?, ?, ?, ?, ?, ?, 'pending', ?, ?, ?, ?, ?, ?)",
            (str(uuid.uuid4()), project_id, spec["scene_id"], spec["kind"], json.dumps(spec["speakers"]),
             random.randint(1, 2**31 - 1), spec["action"], spec["expression"], spec["subject"],
             spec["beat_position"], now, now),
        )
    return await shot_rows(db, project_id)


async def prepare_regenerate(db: aiosqlite.Connection, project_id: str, shot_id: str) -> dict:
    shot = await get_shot_row(db, project_id, shot_id)
    seed = random.randint(1, 2**31 - 1)
    while seed == shot["seed"]:
        seed = random.randint(1, 2**31 - 1)
    await db.execute(
        "UPDATE project_shots SET seed = ?, status = 'pending', raw_path = NULL, final_path = NULL, "
        "error = NULL, review_note = NULL, source = 'generated', library_shot_id = NULL, updated_at = ? WHERE id = ?",
        (seed, library._now(), shot_id),
    )
    return await get_shot_row(db, project_id, shot_id)


def resolve_shot_content(project_id: str, path: str) -> Path:
    root = (settings.DATA_DIR / "visuals" / project_id / "shots").resolve()
    candidate = Path(path).resolve()
    if not candidate.is_relative_to(root) or not candidate.is_file():
        raise NotFoundError("Shot image not found")
    return candidate


def assign_line_shots(lines: list[dict], chapters: list[dict], scenes: list[dict], shots: list[dict]) -> list[str | None]:
    """Assign a complete scene shot to each audio line using chapter and speaker order."""
    if not scenes:
        return [None] * len(lines)
    complete = [shot for shot in shots if shot.get("status") == "complete" and shot.get("final_path")]
    positions: dict[int, int] = {}
    assigned: list[str | None] = []
    for line in lines:
        chapter = max((index for index, item in enumerate(chapters)
                       if item["startSec"] <= line["startSec"]), default=0)
        position = positions.get(chapter, 0)
        positions[chapter] = position + 1
        scene_id = scenes[chapter % len(scenes)]["id"]
        available = [shot for shot in complete if shot["scene_id"] == scene_id]

        def first(kind: str, speaker: int | None = None) -> dict | None:
            return next((shot for shot in available if shot["kind"] == kind and
                         (speaker is None or speaker in (
                             json.loads(shot["speaker_indexes"])
                             if isinstance(shot["speaker_indexes"], str) else shot["speaker_indexes"]
                         ))), None)

        wanted = (first("duo_wide") if position == 0 else
                  first("duo_close") if position % 4 == 3 else
                  first("single", line.get("speaker_index")))
        chosen = wanted or first("single") or first("duo_close") or first("duo_wide")
        assigned.append((chosen or (available[0] if available else None) or {}).get("id"))
    return assigned


def assign_beat_shots(lines: list[dict], beats: list[dict], shots: list[dict]) -> list[str | None]:
    """Task 24.5b: the shot shown during each audio line, from the approved storyboard. An insert
    beat shows its illustration. A scene beat with its own action shot opens on it and alternates
    it with the speaker's single; otherwise it opens on the place's duo wide, shows the duo close on
    every 4th line and the speaker's single in between. Fallbacks: single -> duo close -> duo wide
    -> any shot of the place -> None (the midnight background)."""
    complete = [shot for shot in shots if shot.get("status") == "complete" and shot.get("final_path")]

    def speakers_of(shot: dict) -> list[int]:
        value = shot["speaker_indexes"]
        return json.loads(value) if isinstance(value, str) else value

    assigned: list[str | None] = []
    for index, line in enumerate(lines):
        position = next((number for number, beat in enumerate(beats)
                         if beat["line_from"] <= index <= beat["line_to"]), None)
        if position is None:
            assigned.append(None)
            continue
        beat = beats[position]
        if beat["kind"] == "insert":
            insert = next((shot for shot in complete
                           if shot["kind"] == "insert" and shot.get("beat_position") == position), None)
            assigned.append(insert["id"] if insert else None)
            continue
        place = [shot for shot in complete if shot["scene_id"] == beat["scene_id"] and shot["kind"] != "insert"]
        framing = [shot for shot in place if shot.get("beat_position") is None]
        action_shot = next((shot for shot in place if shot.get("beat_position") == position), None)

        def first(kind: str, speaker: int | None = None, speakers: list[int] | None = None) -> dict | None:
            return next((shot for shot in framing if shot["kind"] == kind
                         and (speaker is None or speaker in speakers_of(shot))
                         and (speakers is None or speakers_of(shot) == speakers)), None)

        offset = index - beat["line_from"]
        reviewed = list(dict.fromkeys(beat.get("speakers") or []))[:2]
        if not reviewed:
            reviewed = list(dict.fromkeys(
                item.get("speaker_index") for item in lines[beat["line_from"]:beat["line_to"] + 1]
                if item.get("speaker_index") is not None
            ))[:2]
        if action_shot is not None:
            wanted = action_shot if offset % 2 == 0 else first("single", line.get("speaker_index"))
        elif offset == 0:
            wanted = (first("duo_wide", speakers=reviewed) if len(reviewed) == 2
                      else first("single", reviewed[0] if reviewed else line.get("speaker_index")))
        elif offset % 4 == 3:
            wanted = (first("duo_close", speakers=reviewed) if len(reviewed) == 2
                      else first("single", reviewed[0] if reviewed else line.get("speaker_index")))
        else:
            wanted = first("single", line.get("speaker_index"))
        chosen = (wanted or first("single", line.get("speaker_index"))
                  or (first("duo_close", speakers=reviewed) if len(reviewed) == 2 else None)
                  or (first("duo_wide", speakers=reviewed) if len(reviewed) == 2 else None)
                  or first("single") or (place[0] if place else None))
        assigned.append(chosen["id"] if chosen else None)
    return assigned


def storyboard_timeline_ready(beats: list[dict] | None, shots: list[dict]) -> bool:
    """The beat timeline applies only when every place of the approved storyboard has a complete
    shot (i.e. shots were generated from it); otherwise the per-scene rule keeps working."""
    if not beats:
        return False
    complete_places = {shot["scene_id"] for shot in shots if shot.get("status") == "complete" and shot.get("final_path")}
    return all(beat["scene_id"] in complete_places for beat in beats if beat["kind"] == "scene")
