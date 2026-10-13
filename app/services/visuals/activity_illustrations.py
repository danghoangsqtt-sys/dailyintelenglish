"""Task 33.10 (Gate B-23, D102): which storyboard inserts have an Activity Library picture, and the pictures still missing.

The talking-sprites video shows an insert's illustration behind the speakers only when an approved library picture matches it
(`activity_matcher`). For an insert without one, Step 5 names the closest library activities, the pending picture drawn or
uploaded for it, and the prompt for an outside AI; the `activity_illustrations` image job draws the missing ones on the local GPU.
"""

from __future__ import annotations

from typing import Any

import aiosqlite

from app.core.exceptions import NotFoundError
from app.services.visuals import activity_library_service as activity_library
from app.services.visuals import activity_matcher, recipes, storyboard_service
from app.services.visuals import project_visuals_service as project_visuals


def activity_name(beat: dict[str, Any]) -> str:
    """The library activity a picture drawn for this insert is filed under: its action, else what it shows."""
    return activity_library._token(beat.get("action") or beat.get("new_place") or "")


async def _usable(db: aiosqlite.Connection, review_state: str) -> list[dict[str, Any]]:
    usable = []
    for row in await activity_library.list_activities(db, review_state=review_state):
        try:
            await activity_library.content_path(db, row["id"])
        except NotFoundError:
            continue
        usable.append(row)
    return usable


async def coverage(db: aiosqlite.Connection, project_id: str) -> dict[str, Any]:
    """Per insert of the approved storyboard: matched (character/generic) or missing, with what helps fill it."""
    beats = await storyboard_service.approved_beats(db, project_id) or []
    cursor = await db.execute(
        "SELECT sl.line_index, sl.text, sp.speaker_index FROM script_lines sl JOIN speakers sp ON sp.id = sl.speaker_id "
        "WHERE sl.project_id = ? ORDER BY sl.line_index", (project_id,),
    )
    lines = [dict(row) for row in await cursor.fetchall()]
    cast = {row["speaker_index"]: row["character_id"] for row in await project_visuals.cast_rows(db, project_id)}
    candidates = await activity_library.approved_candidates(db)
    pending = await _usable(db, "pending")
    size = max((line["line_index"] for line in lines), default=-1) + 1
    line_speakers: list[int | None] = [None] * size
    line_texts = [""] * size
    for line in lines:
        line_speakers[line["line_index"]], line_texts[line["line_index"]] = line["speaker_index"], line["text"]
    items = []
    for beat in beats:
        if beat["kind"] != "insert":
            continue
        speaker = activity_matcher.beat_speaker_index(beat, line_speakers, line_texts) if size else None
        character_id = cast.get(speaker) if speaker is not None else None
        dialogue = " ".join(line["text"] for line in lines if beat["line_from"] <= line["line_index"] <= beat["line_to"])
        found = activity_matcher.match_activity(candidates, character_id, beat.get("action") or "", dialogue)
        item: dict[str, Any] = {
            "beat_id": beat["id"], "position": beat["position"], "action": beat.get("action") or "",
            "place": beat.get("new_place") or "", "status": found["match_type"] if found else "missing",
            "fallback": None if found else "sprites",
            "match": {key: value for key, value in found.items() if key != "asset"} if found else None,
        }
        if not found:
            name = activity_name(beat)
            waiting = next((row for row in pending if row["activity"] == name and not row.get("character_id")), None)
            item.update({
                "activity": name,
                "suggestions": activity_matcher.suggest(candidates, f"{item['action']} {item['place']} {dialogue}"),
                "pending": {"id": waiting["id"], "url": f"/api/visuals/library/activities/{waiting['id']}/content"}
                if waiting else None,
                "prompt": recipes.activity_outside_prompt(item["action"] or item["place"] or "doing everyday things",
                                                          item["place"] if item["action"] else ""),
            })
        items.append(item)
    character = sum(item["status"] == "character" for item in items)
    generic = sum(item["status"] == "generic" for item in items)
    missing = sum(item["status"] == "missing" for item in items)
    return {"items": items, "matched": character + generic, "character": character, "generic": generic,
            "missing": missing, "sprite_fallback": missing,
            "to_draw": sum(item["status"] == "missing" and item["pending"] is None for item in items)}
