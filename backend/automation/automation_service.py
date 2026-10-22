"""Phase 62 (ENH-044): the automation settings, the queue of due episodes and the run report (database side)."""

from __future__ import annotations

import uuid
from datetime import date, datetime, timedelta, timezone
from typing import Any

import aiosqlite

from backend.automation import rules

SETTING_FIELDS = ("enabled", "window_start", "window_end", "days_ahead", "max_per_night", "start_with_windows", "keep_awake")
BOOLEAN_FIELDS = {"enabled", "start_with_windows", "keep_awake"}


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


async def get_settings(db: aiosqlite.Connection) -> dict[str, Any]:
    cursor = await db.execute("SELECT * FROM automation_settings WHERE id = 1")
    row = await cursor.fetchone()
    if row is None:  # the migration inserts it; a hand-cleared table gets it back
        await db.execute("INSERT OR IGNORE INTO automation_settings (id) VALUES (1)")
        cursor = await db.execute("SELECT * FROM automation_settings WHERE id = 1")
        row = await cursor.fetchone()
    item = {field: row[field] for field in SETTING_FIELDS}
    for field in BOOLEAN_FIELDS:
        item[field] = bool(item[field])
    return item


async def update_settings(db: aiosqlite.Connection, patch: dict[str, Any]) -> dict[str, Any]:
    fields = {key: (int(value) if key in BOOLEAN_FIELDS else value) for key, value in patch.items() if key in SETTING_FIELDS}
    if fields:
        assignments = ", ".join(f"{key} = ?" for key in fields)
        await db.execute(f"UPDATE automation_settings SET {assignments}, updated_at = ? WHERE id = 1",
                         (*fields.values(), now_iso()))
    return await get_settings(db)


async def episodes(db: aiosqlite.Connection) -> list[dict[str, Any]]:
    """Every Channel plan episode with its series, its project and whether the project is finished (YouTube package)."""
    cursor = await db.execute(
        "SELECT e.id, e.number, e.title, e.status, e.publish_date, e.project_id, e.series_id, s.name AS series, "
        "s.presentation_mode, s.explainer_style, "
        "EXISTS(SELECT 1 FROM youtube_packages y WHERE y.project_id = e.project_id) AS finished "
        "FROM channel_episodes e JOIN channel_series s ON s.id = e.series_id")
    return [{**dict(row), "finished": bool(row["finished"])} for row in await cursor.fetchall()]


async def due(db: aiosqlite.Connection, today: date, days_ahead: int) -> list[dict[str, Any]]:
    return rules.due_episodes(await episodes(db), today, days_ahead)


async def episode(db: aiosqlite.Connection, episode_id: str) -> dict[str, Any] | None:
    return next((item for item in await episodes(db) if item["id"] == episode_id), None)


# ---------------------------------------------------------------- runs and items

async def create_run(db: aiosqlite.Connection, trigger: str, started_at: str | None = None) -> dict[str, Any]:
    run = {"id": uuid.uuid4().hex, "trigger": trigger, "status": "running", "message": "", "started_at": started_at or now_iso(),
           "finished_at": None}
    await db.execute("INSERT INTO automation_runs (id, trigger, status, message, started_at) VALUES (?, ?, ?, ?, ?)",
                     (run["id"], trigger, "running", "", run["started_at"]))
    return run


async def finish_run(db: aiosqlite.Connection, run_id: str, status: str, message: str = "") -> None:
    await db.execute("UPDATE automation_runs SET status = ?, message = ?, finished_at = ? WHERE id = ?",
                     (status, message, now_iso(), run_id))


async def running_runs(db: aiosqlite.Connection) -> list[dict[str, Any]]:
    cursor = await db.execute("SELECT * FROM automation_runs WHERE status = 'running' ORDER BY started_at")
    return [dict(row) for row in await cursor.fetchall()]


async def start_item(db: aiosqlite.Connection, run_id: str, item: dict[str, Any]) -> str:
    item_id = uuid.uuid4().hex
    await db.execute(
        "INSERT INTO automation_items (id, run_id, episode_id, project_id, title, step, status, message, started_at) "
        "VALUES (?, ?, ?, ?, ?, ?, 'running', '', ?)",
        (item_id, run_id, item["id"], item.get("project_id"), _title(item), "", now_iso()))
    return item_id


def _title(item: dict[str, Any]) -> str:
    return f"{item.get('series') or ''} · Ep. {item.get('number')}: {item.get('title') or ''}".strip(" ·")


async def update_item(db: aiosqlite.Connection, item_id: str, **fields: Any) -> None:
    finished = fields.get("status") in ("waiting_review", "needs_attention", "error")
    if finished:
        fields["finished_at"] = now_iso()
    assignments = ", ".join(f"{key} = ?" for key in fields)
    await db.execute(f"UPDATE automation_items SET {assignments} WHERE id = ?", (*fields.values(), item_id))


async def run_items(db: aiosqlite.Connection, run_id: str) -> list[dict[str, Any]]:
    cursor = await db.execute("SELECT * FROM automation_items WHERE run_id = ? ORDER BY started_at", (run_id,))
    return [dict(row) for row in await cursor.fetchall()]


async def items_since(db: aiosqlite.Connection, started_at: str) -> list[dict[str, Any]]:
    """The items of every run that started at or after `started_at` (one night, even across an app restart)."""
    cursor = await db.execute("SELECT i.* FROM automation_items i JOIN automation_runs r ON r.id = i.run_id "
                              "WHERE r.started_at >= ? ORDER BY i.started_at", (started_at,))
    return [dict(row) for row in await cursor.fetchall()]


async def report(db: aiosqlite.Connection, limit: int = 10) -> list[dict[str, Any]]:
    """The last runs, newest first, each with its items and a link to the step to look at."""
    cursor = await db.execute("SELECT * FROM automation_runs ORDER BY started_at DESC LIMIT ?", (limit,))
    runs = []
    for row in await cursor.fetchall():
        run = dict(row)
        run["items"] = [{**item, "step_label": rules.STEP_LABELS.get(item["step"], item["step"]),
                         "link": _link(item)} for item in await run_items(db, run["id"])]
        runs.append(run)
    return runs


def _link(item: dict[str, Any]) -> str:
    if not item.get("project_id"):
        return "/channel"
    page = "/step7" if item["status"] == "waiting_review" else rules.STEP_PAGES.get(item["step"], "/step2")
    return f"{page}?project_id={item['project_id']}"


# ---------------------------------------------------------------- Phase 67 (ENH-049): the review studio board

KINDS = {"presenter": "Solo", "vox": "VOX", "news": "Short · English news", "blur": "Short · text on blur",
         "mistakes": "Short · Don't say / Say", "wordday": "Short · word of the day", "top5": "Short · top 5",
         "quiz": "Short · quiz", "listen": "Short · listening", "chat": "Short · chat", "wyr": "Short · would you rather"}


def kind_of(presentation_mode: str | None, style: str | None) -> str:
    if presentation_mode == "solo_explainer":
        return KINDS.get(style or "presenter", "Solo")
    # a conversation series keeps the default style "presenter": only chat / would-you-rather mark a conversation Short
    return KINDS[style] if style in ("chat", "wyr") else "Conversation"


def state_of(episode: dict[str, Any], item: dict[str, Any] | None) -> str:
    """One state per episode for the board: published > approved > changes > the latest automation item > made > planned."""
    if episode["status"] == "published":
        return "published"
    if episode.get("review_status") == "approved":
        return "approved"
    if episode.get("review_status") == "changes":
        return "changes"
    if item and item["status"] == "running":
        return "making"
    if episode.get("finished"):
        return "waiting_review"
    if item and item["status"] in ("needs_attention", "error"):
        return "needs_attention"
    return "in_progress" if episode.get("project_id") else "planned"


async def board(db: aiosqlite.Connection, today: date, days: int = 14) -> dict[str, Any]:
    """The schedule strip (the next `days` days, late ones on today) and every made or started video, for the studio."""
    from backend.media import thumbnail_service

    cursor = await db.execute(
        "SELECT e.id, e.number, e.title, e.status, e.publish_date, e.project_id, e.video_url, e.review_status, e.review_note, "
        "s.name AS series, s.presentation_mode, s.explainer_style, "
        "EXISTS(SELECT 1 FROM youtube_packages y WHERE y.project_id = e.project_id) AS finished, "
        "EXISTS(SELECT 1 FROM video_jobs v WHERE v.project_id = e.project_id AND v.status = 'complete') AS has_video, "
        "(SELECT a.duration_seconds FROM audio_jobs a WHERE a.project_id = e.project_id AND a.status = 'complete' "
        " ORDER BY a.completed_at DESC LIMIT 1) AS duration "
        "FROM channel_episodes e JOIN channel_series s ON s.id = e.series_id")
    episodes = [{**dict(row), "finished": bool(row["finished"]), "has_video": bool(row["has_video"])} for row in await cursor.fetchall()]
    cursor = await db.execute("SELECT * FROM automation_items ORDER BY started_at")
    latest = {}
    for row in await cursor.fetchall():
        latest[row["episode_id"]] = dict(row)
    thumbs: dict[str, str] = {}
    for episode in episodes:
        if not episode["project_id"]:
            continue
        rows = [row for row in await thumbnail_service.get_thumbnail_rows(db, episode["project_id"]) if row["is_selected"]]
        if rows:
            record = (await thumbnail_service.public_records(rows[:1]))[0]
            thumbs[episode["project_id"]] = (record["assets"].get("16x9") or {}).get("jpg") or (record["assets"].get("16x9") or {}).get("png") or ""
    cards = []
    for episode in episodes:
        item = latest.get(episode["id"])
        cards.append({
            "episode_id": episode["id"], "project_id": episode["project_id"], "title": episode["title"], "number": episode["number"],
            "series": episode["series"], "publish_date": episode["publish_date"], "kind": kind_of(episode["presentation_mode"], episode["explainer_style"]),
            "vertical": episode["explainer_style"] in ("news", "blur", "mistakes", "wordday", "top5", "quiz", "listen", "chat", "wyr"),
            "state": state_of(episode, item), "step": rules.STEP_LABELS.get(item["step"], "") if item else "",
            "message": item["message"] if item and item["status"] != "waiting_review" else "",
            "has_video": episode["has_video"], "duration": episode["duration"], "thumbnail_url": thumbs.get(episode["project_id"] or "", ""),
            "video_url": episode["video_url"], "review_status": episode["review_status"], "review_note": episode["review_note"],
        })
    strip = []
    for offset in range(days):
        day = today + timedelta(days=offset)
        strip.append({"date": day.isoformat(), "items": [card for card in cards if card["publish_date"] and (
            card["publish_date"] == day.isoformat() or (offset == 0 and card["publish_date"] < day.isoformat() and card["state"] not in ("published",)))]})
    videos = sorted([card for card in cards if card["project_id"]], key=lambda card: card["publish_date"] or "", reverse=True)
    return {"days": strip, "videos": videos}
