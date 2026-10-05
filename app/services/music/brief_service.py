"""Task 22.3 (D45): a project's music brief -- the AI proposes, the owner edits, 3 previews, a pick,
and the full-length track attached to the project. Write functions run inside write_transaction."""

from __future__ import annotations

import json
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import aiosqlite
from pydantic import ValidationError as PydanticValidationError

from app.core.config import settings
from app.core.exceptions import NotFoundError, ProviderError, SchemaValidationError
from app.core.prompt_loader import render_music_brief_prompt
from app.db.transactions import read_transaction, write_transaction
from app.models.music import (
    BRIEF_SCRIPT_LINES, EPISODE_MARGIN_S, GENRE_BRIEF, GENRE_STYLE, MAX_DURATION_S, MIN_DURATION_S,
    MUSIC_STYLES, MusicBriefInput,
)
from app.services import project_service
from app.services.ai.contracts import GenerationRequest
from app.services.ai.router import AIRouter, build_ai_router_from_settings
from app.services.visuals import jobs

PREVIEWS_CATEGORY = "music_previews"


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def previews_dir(project_id: str) -> Path:
    return settings.DATA_DIR / PREVIEWS_CATEGORY / project_id


def preview_path(project_id: str, seed: int) -> Path:
    return previews_dir(project_id) / f"{int(seed)}.mp3"


async def episode_seconds(db: aiosqlite.Connection, project: dict[str, Any]) -> int:
    """The bed should cover the whole episode: the real mixed length when audio exists, else the
    planned length, plus a margin (the mixer loops a short bed with a hard cut)."""
    cursor = await db.execute(
        "SELECT duration_seconds FROM audio_jobs WHERE project_id = ? AND status = 'complete'", (project["id"],),
    )
    row = await cursor.fetchone()
    seconds = row[0] if row and row[0] else float(project["duration_minutes"]) * 60
    return int(max(MIN_DURATION_S, min(MAX_DURATION_S, round(seconds) + EPISODE_MARGIN_S)))


def rule_brief(genre: str) -> dict[str, str]:
    style = GENRE_STYLE.get(genre, "lofi")
    return {"style": style, "brief": GENRE_BRIEF[style]}


def brief_schema() -> dict:
    return {
        "type": "object",
        "properties": {"style": {"type": "string", "enum": list(MUSIC_STYLES)},
                       "brief": {"type": "string"}},
        "required": ["style", "brief"],
    }


def parse_brief(text: str, duration_s: int) -> MusicBriefInput:
    """Errors name the failing field so the one repair call can fix it, never quoting the answer."""
    try:
        parsed = json.loads(text)
    except json.JSONDecodeError as exc:
        raise SchemaValidationError(f"the answer is not valid JSON ({exc.msg})") from exc
    if not isinstance(parsed, dict):
        raise SchemaValidationError("the answer must be a JSON object with style and brief")
    try:
        return MusicBriefInput.model_validate({
            "style": str(parsed.get("style", "")).strip().lower(), "brief": parsed.get("brief", ""),
            "duration_s": duration_s,
        })
    except PydanticValidationError as exc:
        problems = "; ".join(
            f"{'.'.join(str(part) for part in error['loc'])}: {error['msg']}" for error in exc.errors()[:3]
        )
        raise SchemaValidationError(f"the answer does not match the schema ({problems})") from exc


async def _script_opening(db: aiosqlite.Connection, project_id: str) -> list[str]:
    cursor = await db.execute(
        "SELECT sp.name, sl.text FROM script_lines sl JOIN speakers sp ON sp.id = sl.speaker_id "
        "WHERE sl.project_id = ? ORDER BY sl.line_index LIMIT ?",
        (project_id, BRIEF_SCRIPT_LINES),
    )
    return [f"{name}: {text}" for name, text in await cursor.fetchall()]


async def get_row(db: aiosqlite.Connection, project_id: str) -> dict[str, Any] | None:
    cursor = await db.execute("SELECT * FROM project_music WHERE project_id = ?", (project_id,))
    row = await cursor.fetchone()
    if row is None:
        return None
    result = dict(row)
    result["previews"] = json.loads(result.pop("previews_json"))
    return result


async def require_row(db: aiosqlite.Connection, project_id: str) -> dict[str, Any]:
    row = await get_row(db, project_id)
    if row is None:
        raise NotFoundError("This project has no music brief yet")
    return row


async def save_brief(db: aiosqlite.Connection, project_id: str, body: MusicBriefInput, source: str) -> None:
    """A new style or mood makes the previews and the pick stale; a new length alone does not."""
    await project_service.get_project(db, project_id)
    current = await get_row(db, project_id)
    same_music = current is not None and (current["style"], current["brief"]) == (body.style, body.brief)
    if current is None:
        await db.execute(
            "INSERT INTO project_music (project_id, style, brief, duration_s, source, updated_at) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (project_id, body.style, body.brief, body.duration_s, source, _now()),
        )
    elif same_music:
        await db.execute("UPDATE project_music SET duration_s = ?, updated_at = ? WHERE project_id = ?",
                         (body.duration_s, _now(), project_id))
    else:
        await db.execute(
            "UPDATE project_music SET style = ?, brief = ?, duration_s = ?, source = ?, previews_json = '[]', "
            "picked_seed = NULL, updated_at = ? WHERE project_id = ?",
            (body.style, body.brief, body.duration_s, source, _now(), project_id),
        )


async def set_previews(db: aiosqlite.Connection, project_id: str, seeds: list[int]) -> None:
    await db.execute(
        "UPDATE project_music SET previews_json = ?, picked_seed = NULL, updated_at = ? WHERE project_id = ?",
        (json.dumps([{"seed": seed} for seed in seeds]), _now(), project_id),
    )


async def set_job(db: aiosqlite.Connection, project_id: str, column: str, job_id: str) -> None:
    assert column in ("preview_job_id", "full_job_id")
    await db.execute(f"UPDATE project_music SET {column} = ?, updated_at = ? WHERE project_id = ?",
                     (job_id, _now(), project_id))


async def pick(db: aiosqlite.Connection, project_id: str, seed: int) -> None:
    await db.execute("UPDATE project_music SET picked_seed = ?, updated_at = ? WHERE project_id = ?",
                     (seed, _now(), project_id))


async def attach_track(db: aiosqlite.Connection, project_id: str, filename: str) -> None:
    await db.execute("UPDATE project_music SET track_filename = ?, updated_at = ? WHERE project_id = ?",
                     (filename, _now(), project_id))


async def _active_job(db: aiosqlite.Connection, job_id: str | None) -> dict[str, Any] | None:
    if not job_id:
        return None
    try:
        job = await jobs.get_job(db, job_id)
    except NotFoundError:
        return None
    return job if job["status"] in ("pending", "running") else None


async def get_view(db: aiosqlite.Connection, project_id: str) -> dict[str, Any]:
    project = await project_service.get_project(db, project_id)
    row = await get_row(db, project_id)
    view: dict[str, Any] = {
        "project_id": project_id, "saved": row is not None,
        "default_duration_s": await episode_seconds(db, project),
        "style": None, "brief": "", "duration_s": None, "source": None, "previews": [],
        "picked_seed": None, "track_filename": None, "track_exists": False,
        "preview_job": None, "full_job": None,
    }
    if row is None:
        return view
    library = settings.DATA_DIR / "music_library"
    previews = [
        {"seed": item["seed"], "url": f"/api/projects/{project_id}/music/previews/{item['seed']}"}
        for item in row["previews"] if preview_path(project_id, item["seed"]).is_file()
    ]
    view.update({
        "style": row["style"], "brief": row["brief"], "duration_s": row["duration_s"], "source": row["source"],
        "previews": previews, "picked_seed": row["picked_seed"], "track_filename": row["track_filename"],
        "track_exists": bool(row["track_filename"]) and (library / row["track_filename"]).is_file(),
        "preview_job": await _active_job(db, row["preview_job_id"]),
        "full_job": await _active_job(db, row["full_job_id"]),
    })
    return view


async def propose_brief(db: aiosqlite.Connection, project_id: str, router: AIRouter | None = None) -> dict[str, Any]:
    """One AI call checked like owner input, one repair call quoting the exact error, else the genre
    rule. AI I/O runs outside any DB transaction; only the final save writes."""
    async with read_transaction():
        project = await project_service.get_project(db, project_id)
        lines = await _script_opening(db, project_id)
        current = await get_row(db, project_id)
        duration_s = current["duration_s"] if current else await episode_seconds(db, project)
    router = router or build_ai_router_from_settings()
    chosen: MusicBriefInput | None = None
    path, reason, previous_error = "rule", None, ""
    for attempt in range(2):
        prompt = await render_music_brief_prompt(topic=project["topic"], genre=project["genre"],
                                                 cefr_level=project["cefr_level"], lines=lines,
                                                 previous_error=previous_error)
        request = GenerationRequest(prompt=prompt, json_schema=brief_schema(),
                                    deadline_seconds=settings.AI_REQUEST_DEADLINE_SECONDS, purpose="music_brief")
        try:
            result = await router.generate(request)
        except ProviderError as exc:
            reason = f"AI unavailable ({type(exc).__name__})"
            break
        try:
            chosen = parse_brief(result.text, duration_s)
        except SchemaValidationError as exc:
            previous_error = reason = str(exc)
            continue
        path, reason = ("ai" if attempt == 0 else "ai_repaired"), None
        break
    if chosen is None:
        chosen = MusicBriefInput(**rule_brief(project["genre"]), duration_s=duration_s)
    async with write_transaction(db):
        await save_brief(db, project_id, chosen, "rule" if path == "rule" else "ai")
    async with read_transaction():
        view = await get_view(db, project_id)
    view["proposal"] = {"path": path, "reason": reason}
    return view


def remove_previews_sync(project_id: str, keep: set[int] | None = None) -> None:
    folder = previews_dir(project_id)
    if not folder.is_dir():
        return
    if keep is None:
        shutil.rmtree(folder, ignore_errors=True)
        return
    for path in folder.glob("*.mp3"):
        if path.stem.isdigit() and int(path.stem) in keep:
            continue
        path.unlink(missing_ok=True)
