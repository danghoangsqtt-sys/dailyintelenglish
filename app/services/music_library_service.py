"""Task 22.7: Music Library track details (rows in `music_tracks`) for hand-downloaded free music.

Files in `DATA_DIR/music_library` stay the source of truth for the listing; every listed file gets a
row lazily, with a title guessed from the filename and a duration measured by ffprobe (never typed).
Write functions run inside write_transaction.
"""

from __future__ import annotations

import os
import re
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import aiosqlite

from app.core.config import settings
from app.models.music import LICENCES, MOODS, SOURCES

FFPROBE_TIMEOUT_SECONDS = 30
DETAIL_FIELDS = ("title", "artist", "mood", "tags", "source", "licence", "attribution", "source_url")


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def ffprobe_path() -> str:
    """ffprobe ships next to ffmpeg; `FFMPEG_PATH` may be an absolute path (no system PATH entry)."""
    ffmpeg = Path(settings.FFMPEG_PATH)
    if ffmpeg.parent == Path("."):
        return "ffprobe"
    suffix = ".exe" if os.name == "nt" or ffmpeg.suffix == ".exe" else ""
    return str(ffmpeg.with_name(f"ffprobe{suffix}"))


def probe_duration(path: Path) -> float | None:
    """Blocking: the file's real duration in seconds, or None when ffprobe cannot read it."""
    try:
        result = subprocess.run(
            [ffprobe_path(), "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(path)],
            capture_output=True, text=True, timeout=FFPROBE_TIMEOUT_SECONDS,
        )
        seconds = float(result.stdout.strip())
    except (OSError, ValueError, subprocess.TimeoutExpired):
        return None
    return round(seconds, 2) if seconds > 0 else None


def guess_title(filename: str) -> str:
    """"calm_morning-piano (1).mp3" -> "Calm morning piano"."""
    stem = re.sub(r"\s*\(\d+\)$", "", Path(filename).stem)
    words = " ".join(re.sub(r"[_\-.]+", " ", stem).split())
    return (words[:1].upper() + words[1:]) if words else filename


async def rows_by_filename(db: aiosqlite.Connection) -> dict[str, dict[str, Any]]:
    cursor = await db.execute("SELECT * FROM music_tracks")
    return {row["filename"]: dict(row) for row in await cursor.fetchall()}


async def insert_row(db: aiosqlite.Connection, filename: str, duration_s: float | None) -> None:
    now = _now()
    await db.execute(
        "INSERT OR IGNORE INTO music_tracks (filename, title, duration_s, created_at, updated_at) "
        "VALUES (?, ?, ?, ?, ?)",
        (filename, guess_title(filename), duration_s, now, now),
    )


async def set_duration(db: aiosqlite.Connection, filename: str, duration_s: float | None) -> None:
    await db.execute("UPDATE music_tracks SET duration_s = ?, updated_at = ? WHERE filename = ?",
                     (duration_s, _now(), filename))


async def patch_track(db: aiosqlite.Connection, filename: str, changes: dict[str, Any]) -> None:
    """`changes` holds only the fields the owner sent (None clears a field)."""
    fields = [field for field in DETAIL_FIELDS if field in changes]
    if not fields:
        return
    assignments = ", ".join(f"{field} = ?" for field in fields)
    await db.execute(
        f"UPDATE music_tracks SET {assignments}, updated_at = ? WHERE filename = ?",
        (*[changes[field] for field in fields], _now(), filename),
    )


async def delete_row(db: aiosqlite.Connection, filename: str) -> None:
    await db.execute("DELETE FROM music_tracks WHERE filename = ?", (filename,))


def attribution_required(licence: str | None) -> bool | None:
    if licence is None:
        return None
    return LICENCES[licence]["attribution_required"] if licence in LICENCES else None


def track_view(track: dict[str, Any], row: dict[str, Any] | None) -> dict[str, Any]:
    """The file payload plus its details and the "credit needed" warning."""
    row = row or {}
    details = {field: row.get(field) for field in DETAIL_FIELDS}
    required = attribution_required(details["licence"])
    return {
        **track,
        **details,
        "title": details["title"] or guess_title(track["filename"]),
        "duration_s": row.get("duration_s"),
        "mood_label": MOODS.get(details["mood"] or ""),
        "source_label": SOURCES.get(details["source"] or ""),
        "licence_label": LICENCES[details["licence"]]["label"] if details["licence"] in LICENCES else None,
        "attribution_required": required,
        "needs_attribution": bool(required) and not details["attribution"],
    }
