"""Phase 72 (ENH-054): the audience -- international, Vietnamese or both -- and how the vocabulary is explained.

One setting decides the on-screen vocabulary (an English dictionary definition, the Vietnamese meaning, or both), the
YouTube description's language and the learners the AI writes for. The voice is always English.

A video's own value wins, then its series' (through its channel episode), then the channel default in `app_settings`
(`both`). NULL means "inherit".
"""

from __future__ import annotations

from datetime import datetime, timezone

import aiosqlite

AUDIENCES = ("international", "vietnamese", "both")
DEFAULT = "both"
SETTING_KEY = "audience"
LINES = {
    "international": "international learners of English",
    "vietnamese": "Vietnamese learners of English",
    "both": "international and Vietnamese learners of English",
}


def line(audience: str | None) -> str:
    """The learners the AI prompts write for."""
    return LINES.get(audience or DEFAULT, LINES[DEFAULT])


def valid(value: str | None) -> str | None:
    return value if value in AUDIENCES else None


async def get_channel(db: aiosqlite.Connection) -> str:
    cursor = await db.execute("SELECT value FROM app_settings WHERE key = ?", (SETTING_KEY,))
    row = await cursor.fetchone()
    return valid(row[0] if row else None) or DEFAULT


async def set_channel(db: aiosqlite.Connection, audience: str) -> None:
    await db.execute(
        "INSERT INTO app_settings (key, value, updated_at) VALUES (?, ?, ?) "
        "ON CONFLICT(key) DO UPDATE SET value = excluded.value, updated_at = excluded.updated_at",
        (SETTING_KEY, audience, datetime.now(timezone.utc).isoformat()))


async def for_project(db: aiosqlite.Connection, project_id: str) -> dict:
    """The video's own value, its series' value, the channel default and the one that applies."""
    cursor = await db.execute(
        "SELECT p.audience, s.audience FROM projects p "
        "LEFT JOIN channel_episodes e ON e.project_id = p.id LEFT JOIN channel_series s ON s.id = e.series_id "
        "WHERE p.id = ? LIMIT 1", (project_id,))
    row = await cursor.fetchone()
    own, series = (valid(row[0]), valid(row[1])) if row else (None, None)
    channel = await get_channel(db)
    return {"audience": own, "series": series, "channel": channel, "effective": own or series or channel}


async def resolve(db: aiosqlite.Connection, project_id: str | None) -> str:
    if not project_id:
        return await get_channel(db)
    return (await for_project(db, project_id))["effective"]


async def set_project(db: aiosqlite.Connection, project_id: str, audience: str | None) -> None:
    now = datetime.now(timezone.utc).isoformat()  # updated_at: the library package syncs the newer value
    await db.execute("UPDATE projects SET audience = ?, updated_at = ? WHERE id = ?", (valid(audience), now, project_id))


async def set_series(db: aiosqlite.Connection, series_id: str, audience: str | None) -> None:
    now = datetime.now(timezone.utc).isoformat()
    await db.execute("UPDATE channel_series SET audience = ?, updated_at = ? WHERE id = ?", (valid(audience), now, series_id))
