"""Task 24.1: storyboard storage, validation against the project, and the image estimate."""

from __future__ import annotations

import json
import re
import uuid
from datetime import datetime, timezone
from typing import Any

import aiosqlite
from pydantic import ValidationError as PydanticValidationError

from backend.core.config import settings
from backend.core.exceptions import ProviderError, SchemaValidationError, ValidationError
from backend.ai.llm.prompt_loader import render_storyboard_prompt
from backend.db.transactions import read_transaction, write_transaction
from backend.schemas.storyboard import EXPRESSIONS, BeatInput, StoryboardInput
from backend.content import project_service
from backend.library import library_service as library
from backend.ai.llm.contracts import GenerationRequest
from backend.ai.llm.router import AIRouter, build_ai_router_from_settings

# Phase 44 (D123): a picture is drawn by Qwen-Image-2.1 (~90 s); a library match costs nothing, so the minutes are an
# upper bound.
GPU_MINUTES_PER_IMAGE = 1.5


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def estimate_images(beats: list[BeatInput] | list[dict], cast_size: int) -> int:
    """Owner E4: pictures follow places and actions, not duration. Phase 44 (D123): with the talking characters there
    are no drawn shots of the cast -- each distinct place needs one scene picture and each insert one illustration
    (both may already exist in the libraries). `cast_size` is kept for the callers' signature."""
    places: set[str] = set()
    inserts = 0
    for beat in beats:
        item = beat if isinstance(beat, dict) else beat.model_dump()
        if item["kind"] == "insert":
            inserts += 1
        else:
            places.add(item.get("scene_id") or f"new:{item.get('new_place')}")
    return len(places) + inserts


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


async def validate_against_project(db: aiosqlite.Connection, project_id: str,
                                  body: StoryboardInput, *, active_only: bool = False) -> list[BeatInput]:
    """The 24.1 project rules, shared by owner edits and AI proposals (one source of truth):
    beats tile every script line once, speakers are cast, scenes exist, images fit the cap."""
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
        cursor = await db.execute(f"SELECT id, archived_at FROM scenes WHERE id IN ({marks})", tuple(scene_ids))
        scenes = {row[0]: row[1] for row in await cursor.fetchall()}
        missing = scene_ids - scenes.keys()
        if missing:
            raise ValidationError(f"Unknown scene(s): {sorted(missing)}")
        archived = {scene_id for scene_id, archived_at in scenes.items() if archived_at is not None}
        if archived and not active_only:
            archived -= await library.project_scene_ids(db, project_id)
        if archived:
            raise ValidationError(f"Archived scene(s) cannot be selected: {sorted(archived)}")
    images = estimate_images(beats, len(cast))
    if images > settings.VISUALS_IMAGE_CAP:
        raise ValidationError(
            f"This storyboard needs {images} images; the cap is {settings.VISUALS_IMAGE_CAP}. "
            "Reuse places, merge actions or drop inserts."
        )
    return beats


async def replace_storyboard(db: aiosqlite.Connection, project_id: str, body: StoryboardInput,
                             source: str) -> dict[str, Any]:
    """Validate the beats against the project, then replace its storyboard (caller holds the write
    transaction)."""
    beats = await validate_against_project(db, project_id, body, active_only=source != "owner")
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


def _most_active(line_speakers: list[int], cast: set[int]) -> list[int]:
    """Task 33.8: the (at most two) cast members who talk most in a beat, ties going to the first to speak; with three or more
    people the two on screen are the ones the beat is about, not the two lowest speaker numbers."""
    counts: dict[int, int] = {}
    for speaker in line_speakers:
        if speaker in cast:
            counts[speaker] = counts.get(speaker, 0) + 1
    order = {speaker: line_speakers.index(speaker) for speaker in counts}
    return sorted(sorted(counts, key=lambda speaker: (-counts[speaker], order[speaker]))[:2])


def rule_beats(line_speakers: list[int], cast: set[int], scene_ids: list[str]) -> list[BeatInput]:
    """Task 24.2 deterministic fallback: the lines split into k near-equal contiguous beats, one per
    active library scene (at most 3, and never more places than the image cap allows), each showing the
    cast members who talk in it. Always passes `validate_against_project`."""
    framing = 1  # Phase 44: one scene picture per place
    places = scene_ids or [None]
    count = max(1, min(len(places), 3, len(line_speakers), settings.VISUALS_IMAGE_CAP // framing))
    total = len(line_speakers)
    beats = []
    for index in range(count):
        start, end = round(index * total / count), round((index + 1) * total / count) - 1
        talking = _most_active(line_speakers[start:end + 1], cast)
        beats.append(BeatInput(line_from=start, line_to=end, scene_id=places[index],
                               new_place=None if places[index] else "a quiet conversation space", speakers=talking))
    return beats


_WORD_CHARS = re.compile(r"[^A-Za-z -]+")


def _plain(value: object, max_words: int, max_chars: int) -> str:
    words = _WORD_CHARS.sub(" ", str(value or "")).split()[:max_words]
    text = " ".join(words)
    while len(text) > max_chars and words:
        words = words[:-1]
        text = " ".join(words)
    return text


def _normalize_proposal(parsed: object) -> object:
    """Real-AI finding (Gemini Flash-Lite, 2026-10-05): sound content in a loose shape -- `kind`
    omitted (inserts arrived as scene beats with only `new_place`), empty strings for absent
    places, punctuation and long phrases in `action`. Fix only the shape; never invent content.
    Owner edits (PUT) stay strict."""
    if not isinstance(parsed, dict) or not isinstance(parsed.get("beats"), list):
        return parsed
    beats = []
    for raw in parsed["beats"]:
        if not isinstance(raw, dict):
            beats.append(raw)
            continue
        beat = dict(raw)
        beat["scene_id"] = beat.get("scene_id") or None
        beat["new_place"] = _plain(beat.get("new_place"), 5, 40) or None
        speakers = [index for index in beat.get("speakers") or [] if isinstance(index, int)]
        beat["speakers"] = list(dict.fromkeys(speakers))[:2]
        if beat.get("kind") not in ("scene", "insert"):
            beat["kind"] = "insert" if not beat["scene_id"] and not beat["speakers"] else "scene"
        if beat["kind"] == "scene" and beat["scene_id"]:
            beat["new_place"] = None  # the library scene wins over a free-text place
        beat["action"] = _plain(beat.get("action"), 8, 40)
        if beat.get("expression") not in EXPRESSIONS:
            beat["expression"] = "calm"
        beats.append(beat)
    return {"beats": beats, "status": "draft"}


def fit_to_cap(beats: list[BeatInput], cast_size: int) -> tuple[list[BeatInput], int]:
    """Task 24.2 real-AI finding: the content was good but the image arithmetic often was not
    (15 for a cap of 12, even after the repair). Trim the AI's own plan instead of discarding it,
    least story value first: fold inserts (the concrete illustrations) into the beat before them,
    then fold whole places into the beat before (Phase 44: actions inside a place cost nothing, so
    they are no longer flattened). Returns (beats, steps taken).
    Line coverage is preserved by every step."""
    beats = [beat.model_copy() for beat in sorted(beats, key=lambda beat: beat.line_from)]
    steps = 0

    def merge_into_previous(index: int) -> None:
        target = index - 1 if index > 0 else index + 1
        low = min(beats[index].line_from, beats[target].line_from)
        high = max(beats[index].line_to, beats[target].line_to)
        beats[target] = beats[target].model_copy(update={"line_from": low, "line_to": high})
        del beats[index]

    def place(beat: BeatInput) -> str:
        return beat.scene_id or f"new:{beat.new_place}"

    while estimate_images(beats, cast_size) > settings.VISUALS_IMAGE_CAP and len(beats) > 1:
        steps += 1
        inserts = [index for index, beat in enumerate(beats) if beat.kind == "insert"]
        if inserts:
            merge_into_previous(inserts[-1])
            continue
        places = list(dict.fromkeys(place(beat) for beat in beats))
        last_place = places[-1]
        merge_into_previous(max(index for index, beat in enumerate(beats) if place(beat) == last_place))
    return beats, steps


def proposal_schema() -> dict:
    """The schema sent to the AI: like `StoryboardInput`, but every beat field is required, so a
    model cannot drop `kind` (the default made it optional in the generated schema)."""
    schema = StoryboardInput.model_json_schema()
    beat = schema["$defs"]["BeatInput"]
    beat["required"] = ["line_from", "line_to", "kind", "scene_id", "new_place", "speakers", "action", "expression"]
    schema.get("properties", {}).pop("status", None)
    return schema


def _parse_proposal(text: str) -> StoryboardInput:
    """Like `ai.validation.parse_and_validate`, but the error names each failing field so the one
    repair call can fix it (messages carry locations and rules, never the raw response text)."""
    try:
        parsed = json.loads(text)
    except json.JSONDecodeError as exc:
        raise SchemaValidationError(f"the answer is not valid JSON ({exc.msg})") from exc
    try:
        return StoryboardInput.model_validate(_normalize_proposal(parsed))
    except PydanticValidationError as exc:
        problems = "; ".join(
            f"{'.'.join(str(part) for part in error['loc'])}: {error['msg']}" for error in exc.errors()[:5]
        )
        raise SchemaValidationError(f"the answer does not match the schema ({problems})") from exc


async def _proposal_context(db: aiosqlite.Connection, project_id: str) -> dict[str, Any]:
    project = await project_service.get_project(db, project_id)
    cursor = await db.execute(
        "SELECT sl.line_index, sp.speaker_index, sl.text FROM script_lines sl JOIN speakers sp ON sp.id = sl.speaker_id "
        "WHERE sl.project_id = ? ORDER BY sl.line_index",
        (project_id,),
    )
    lines = [{"index": position, "speaker_index": row[1], "text": " ".join(row[2].split())}
             for position, row in enumerate(await cursor.fetchall())]
    if not lines:
        raise ValidationError("The project has no script lines to storyboard yet")
    cursor = await db.execute(
        "SELECT pc.speaker_index, c.name FROM project_cast pc JOIN characters c ON c.id = pc.character_id "
        "WHERE pc.project_id = ? ORDER BY pc.speaker_index",
        (project_id,),
    )
    names = {speaker["speaker_index"]: speaker["name"] for speaker in project["speakers"]}
    cast = [{"speaker_index": row[0], "speaker_name": names.get(row[0], f"Speaker {row[0] + 1}"),
             "character_name": row[1]} for row in await cursor.fetchall()]
    cursor = await db.execute(
        "SELECT id, name, place, category FROM scenes WHERE archived_at IS NULL ORDER BY category, name, id"
    )
    scenes = [dict(zip(("id", "name", "place", "category"), row)) for row in await cursor.fetchall()]
    cursor = await db.execute(
        "SELECT a.activity, c.name FROM activity_library a LEFT JOIN characters c ON c.id = a.character_id "
        "WHERE a.review_state = 'approved' ORDER BY a.activity, c.name"
    )
    own: dict[str, list[str]] = {}
    for activity, character in await cursor.fetchall():
        names = own.setdefault(activity, [])
        if character and character not in names:
            names.append(character)
    cast_names = {member["character_name"] for member in cast}
    activities = [{"name": name, "characters": [who for who in names if who in cast_names]} for name, names in own.items()]
    return {"project": project, "lines": lines, "cast": cast, "scenes": scenes, "activities": activities}


async def propose_storyboard(db: aiosqlite.Connection, project_id: str,
                             router: AIRouter | None = None) -> dict[str, Any]:
    """Task 24.2 (owner E3): the AI proposes, the owner reviews. One AI call checked like owner
    input, one repair call quoting the exact error, else the deterministic `rule_beats`. AI I/O runs
    outside any DB transaction; only the final save writes."""
    async with read_transaction():
        context = await _proposal_context(db, project_id)
    project = context["project"]
    cast_indexes = {member["speaker_index"] for member in context["cast"]}
    framing = 1  # Phase 44 (D123): one scene picture per place, no per-cast shot set
    router = router or build_ai_router_from_settings()
    chosen: StoryboardInput | None = None
    path, reason, previous_error = "rule", None, ""
    for attempt in range(2):
        prompt = await render_storyboard_prompt(
            topic=project["topic"], genre=project["genre"], cefr_level=project["cefr_level"],
            cast=context["cast"], lines=context["lines"], scenes=context["scenes"], framing=framing,
            image_cap=settings.VISUALS_IMAGE_CAP, previous_error=previous_error, activities=context["activities"],
        )
        request = GenerationRequest(prompt=prompt, json_schema=proposal_schema(),
                                    deadline_seconds=settings.AI_REQUEST_DEADLINE_SECONDS, purpose="storyboard")
        try:
            result = await router.generate(request)
        except ProviderError as exc:
            reason = f"AI unavailable ({type(exc).__name__})"
            break
        try:
            body = _parse_proposal(result.text)
            fitted, steps = fit_to_cap(body.beats, len(cast_indexes))
            body = body.model_copy(update={"beats": fitted})
            async with read_transaction():
                await validate_against_project(db, project_id, body, active_only=True)
        except (SchemaValidationError, ValidationError) as exc:
            previous_error = reason = str(exc)
            continue
        chosen, path = body, ("ai" if attempt == 0 else "ai_repaired")
        reason = f"trimmed to the image cap in {steps} step(s)" if steps else None
        break
    async with write_transaction(db):
        if chosen is not None:
            try:
                await validate_against_project(db, project_id, chosen, active_only=True)
            except ValidationError as exc:
                chosen, path, reason = None, "rule", str(exc)
        if chosen is None:
            # AI I/O can outlive an archive/restore. Capture fallback choices under the save lock.
            cursor = await db.execute("SELECT id FROM scenes WHERE archived_at IS NULL ORDER BY category, name, id")
            scene_ids = [row[0] for row in await cursor.fetchall()]
            line_speakers = [line["speaker_index"] for line in context["lines"]]
            chosen = StoryboardInput(beats=rule_beats(line_speakers, cast_indexes, scene_ids))
        view = await replace_storyboard(db, project_id, chosen, "rule" if path == "rule" else "ai")
    view["proposal"] = {"path": path, "reason": reason}
    return view


async def approved_beats(db: aiosqlite.Connection, project_id: str) -> list[dict] | None:
    """Task 24.5: the beats to generate from, only once the owner approved the storyboard."""
    cursor = await db.execute("SELECT status FROM project_storyboards WHERE project_id = ?", (project_id,))
    meta = await cursor.fetchone()
    if meta is None or meta[0] != "approved":
        return None
    return (await get_storyboard(db, project_id))["beats"]


async def materialize_new_places(db: aiosqlite.Connection, project_id: str) -> int:
    """Task 24.5a: a scene beat's free-text `new_place` becomes a user library scene, so it gets a
    plate (Task 23.2) and can be reused; its beats then point at that scene (caller holds the
    write transaction). Returns how many scenes were created."""
    cursor = await db.execute(
        "SELECT id, new_place FROM project_beats WHERE project_id = ? AND kind = 'scene' "
        "AND scene_id IS NULL AND new_place IS NOT NULL ORDER BY position",
        (project_id,),
    )
    rows = await cursor.fetchall()
    cursor = await db.execute("SELECT name FROM scenes")
    names = {row[0] for row in await cursor.fetchall()}
    created: dict[str, str] = {}
    now = _now()
    for beat_id, place in rows:
        if place not in created:
            base = place[:1].upper() + place[1:]
            base = base[2:] if base.lower().startswith("a ") else base
            base = (base[:1].upper() + base[1:])[:36]
            name, number = base, 2
            while name in names:
                name, number = f"{base} {number}", number + 1
            names.add(name)
            scene_id = str(uuid.uuid4())
            await db.execute(
                "INSERT INTO scenes (id, name, place, staging, category, time_of_day, seed, created_at, updated_at) "
                "VALUES (?, ?, ?, 'standing', 'other', 'day', ?, ?, ?)",
                (scene_id, name, place, int(uuid.uuid4().int % 2147483646) + 1, now, now),
            )
            created[place] = scene_id
        await db.execute("UPDATE project_beats SET scene_id = ?, new_place = NULL, updated_at = ? WHERE id = ?",
                         (created[place], now, beat_id))
    return len(created)
