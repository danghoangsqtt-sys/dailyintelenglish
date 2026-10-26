"""Phase 78 (Task 78.1): what the talking-characters video shows during each storyboard beat, for Step 5's beat thumbnails.

Read-only and render-free: it answers with picture URLs, never image bytes, and it asks the renderer's own rules (the place of each
line, who stands on screen, left/right and mirroring, the insert's library illustration) so a thumbnail cannot drift from the video.
Draft beats are accepted while the owner edits: a beat whose lines are out of range comes back with an `error` instead of failing
the whole list.
"""

from __future__ import annotations

import asyncio
import json
from typing import Any

import aiosqlite

from backend.core.exceptions import NotFoundError
from backend.library import activity_illustrations, activity_matcher, library_service, sprite_service
from backend.library import activity_library_service as activity_library
from backend.library import project_visuals_service as project_visuals
from backend.media import video_renderer_remotion as renderer

CUTAWAY_MAX_SECONDS = 6.0  # an insert's illustration shows at most this long (video_renderer_remotion._build_sprite_props)


def _sprite_url(character_id: str, name: str) -> str:
    return f"/api/visuals/library/sprites/{character_id}/{name}/content"


async def _plate_ok(scene: dict) -> bool:
    if not scene.get("preview_path"):
        return False
    try:
        await asyncio.to_thread(library_service.resolve_library_content, scene["preview_path"], "library/scenes")
    except Exception:  # a missing or foreign file: the render skips that plate too
        return False
    return True


async def _fallback_scene(db: aiosqlite.Connection, project_id: str) -> dict | None:
    """The plate the render uses when no storyboard place has one (same order as `_resolve_still_plate`)."""
    candidates = list(await project_visuals.scene_rows(db, project_id))
    cursor = await db.execute("SELECT * FROM scenes WHERE archived_at IS NULL ORDER BY is_builtin DESC, name")
    candidates += [dict(row) for row in await cursor.fetchall()]
    for scene in candidates:
        if await _plate_ok(scene):
            return scene
    return None


def _scene_view(scene: dict) -> dict[str, Any]:
    view = library_service._scene_view(dict(scene))
    return {"id": view["id"], "name": view["name"], "preview_url": view["preview_url"]}


async def preview(db: aiosqlite.Connection, project_id: str, beats: list[dict]) -> dict[str, Any]:
    cursor = await db.execute(
        "SELECT sl.line_index, sl.text, sp.speaker_index FROM script_lines sl JOIN speakers sp ON sp.id = sl.speaker_id "
        "WHERE sl.project_id = ? ORDER BY sl.line_index", (project_id,),
    )
    lines = [dict(row) for row in await cursor.fetchall()]
    line_speakers: list[int | None] = [line["speaker_index"] for line in lines]
    line_texts = [line["text"] for line in lines]
    count = len(lines)
    cast = {row["speaker_index"]: row for row in await project_visuals.cast_rows(db, project_id)}

    in_range = [0 <= beat["line_from"] <= beat["line_to"] < count for beat in beats]
    valid = [beat for beat, ok in zip(beats, in_range) if ok]
    scene_ids = {beat["scene_id"] for beat in valid if beat.get("kind") == "scene" and beat.get("scene_id")}
    scenes: dict[str, dict] = {}
    for scene_id in scene_ids:
        try:
            scene = await library_service.get_scene_row(db, scene_id)
        except NotFoundError:
            continue
        scenes[scene_id] = {**_scene_view(scene), "has_plate": await _plate_ok(scene)}

    # the place of each line, as the render decides it; only places with a plate are drawn
    places = renderer._beat_scene_per_line(
        [{**beat, "scene_id": beat.get("scene_id") if beat.get("scene_id") in scenes else None} for beat in valid], count)
    fallback = None
    if not any(scenes.get(place or "", {}).get("has_plate") for place in places):
        found = await _fallback_scene(db, project_id)
        fallback = {**_scene_view(found), "has_plate": True} if found else None

    segments = renderer.sprite_segments(line_speakers)
    pair_of_line: list[frozenset] = [frozenset()] * count
    for segment in segments:
        for index in range(segment["first"], segment["last"] + 1):
            pair_of_line[index] = segment["pair"]

    sets: dict[str, dict | None] = {}
    tops: dict[str, float] = {}

    async def character(speaker_index: int, slot: int, expression: str) -> dict[str, Any]:
        member = cast.get(speaker_index)
        if member is None:
            return {"speaker_index": speaker_index, "slot": slot, "missing": "cast"}
        character_id = member["character_id"]
        if character_id not in sets:
            sets[character_id] = await asyncio.to_thread(sprite_service.load_set, character_id)
        sprite_set = sets[character_id]
        base = {"speaker_index": speaker_index, "slot": slot, "name": member["name"], "character_id": character_id}
        if not sprite_service.usable(sprite_set):
            return {**base, "missing": "sprites"}
        if character_id not in tops:
            tops[character_id] = await asyncio.to_thread(
                renderer._figure_top, sprite_service.sprite_dir(character_id) / f"{sprite_service.BASE}.png")
        picture = f"{expression}__closed" if f"{expression}__closed" in sprite_set["names"] else sprite_service.BASE
        return {**base, "picture_url": _sprite_url(character_id, picture), "top_fraction": round(tops[character_id], 4),
                "mirror": renderer.sprite_mirrored(slot, member.get("sprite_facing") or "", member.get("gender") or "")}

    candidates = await activity_library.approved_candidates(db)
    pending = None
    results: list[dict[str, Any]] = []
    for position, beat in enumerate(beats):
        if not in_range[position]:
            results.append({"position": position, "error": "Its lines are outside the script."})
            continue
        first = beat["line_from"]
        place = places[first]
        if place and scenes.get(place, {}).get("has_plate"):
            background = scenes[place]
        elif place and place in scenes:
            background = {**scenes[place], "preview_url": None}
        else:
            background = fallback
        pair = sorted(pair_of_line[first])
        placement = renderer.sprite_placement([(index, (cast.get(index) or {}).get("gender") or "") for index in pair])
        expression = beat.get("expression") or "calm"
        characters = [await character(index, slot, expression) for index, slot in sorted(placement.items(), key=lambda item: item[1])]
        item: dict[str, Any] = {
            "position": position, "line_from": first, "line_to": beat["line_to"], "kind": beat.get("kind") or "scene",
            "scene": background, "scene_is_fallback": background is fallback and fallback is not None,
            "speaking": line_speakers[first], "characters": characters,
        }
        if item["kind"] == "insert":
            speaker = activity_matcher.beat_speaker_index(beat, line_speakers, line_texts)
            character_id = (cast.get(speaker) or {}).get("character_id") if speaker is not None else None
            dialogue = " ".join(line_texts[first:beat["line_to"] + 1])
            found = activity_matcher.match_activity(candidates, character_id, beat.get("action") or "", dialogue)
            if found:
                item["illustration"] = {"status": found["match_type"], "activity_id": found["activity_id"],
                                        "url": f"/api/visuals/library/activities/{found['activity_id']}/content",
                                        "max_seconds": CUTAWAY_MAX_SECONDS}
            else:
                if pending is None:
                    pending = await activity_illustrations._usable(db, "pending")
                name = activity_illustrations.activity_name(beat)
                waiting = next((row for row in pending if row["activity"] == name and not row.get("character_id")), None)
                item["illustration"] = {"status": "pending", "activity_id": waiting["id"],
                                        "url": f"/api/visuals/library/activities/{waiting['id']}/content"} \
                    if waiting else {"status": "missing"}
        results.append(item)
    return {"beats": results, "lines": count}


async def saved_beats(db: aiosqlite.Connection, project_id: str) -> list[dict]:
    cursor = await db.execute("SELECT * FROM project_beats WHERE project_id = ? ORDER BY position", (project_id,))
    return [{**dict(row), "speakers": json.loads(row["speakers_json"])} for row in await cursor.fetchall()]
