"""Task 22.7: Music Library track details (rows in `music_tracks`) for hand-downloaded free music.

Files in `DATA_DIR/music_library` stay the source of truth for the listing; every listed file gets a
row lazily, with a title guessed from the filename and a duration measured by ffprobe (never typed).
Write functions run inside write_transaction.
"""

from __future__ import annotations

import asyncio
import os
import re
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import quote

import aiosqlite

from app.core.config import settings
from app.db.transactions import read_transaction, write_transaction
from app.models.music import LICENCES, MOODS, PACES, SOURCES
from app.services import music_analysis

FFPROBE_TIMEOUT_SECONDS = 30
AUDIO_EXTENSIONS = {".mp3", ".wav", ".ogg", ".m4a"}
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
    """`changes` holds only the fields the owner sent (None clears a field). Task 22.9: a pace sets
    an owner override; an empty pace returns to the automatic class from the measured onset rate."""
    fields = [field for field in DETAIL_FIELDS if field in changes]
    if fields:
        assignments = ", ".join(f"{field} = ?" for field in fields)
        await db.execute(
            f"UPDATE music_tracks SET {assignments}, updated_at = ? WHERE filename = ?",
            (*[changes[field] for field in fields], _now(), filename),
        )
    if "pace" in changes:
        if changes["pace"]:
            await db.execute("UPDATE music_tracks SET pace = ?, pace_source = 'owner', updated_at = ? WHERE filename = ?",
                             (changes["pace"], _now(), filename))
        else:
            cursor = await db.execute("SELECT onset_rate FROM music_tracks WHERE filename = ?", (filename,))
            row = await cursor.fetchone()
            auto = music_analysis.classify_pace(row[0]) if row and row[0] is not None else None
            await db.execute("UPDATE music_tracks SET pace = ?, pace_source = 'auto', updated_at = ? WHERE filename = ?",
                             (auto, _now(), filename))


async def save_analysis(db: aiosqlite.Connection, filename: str, result: dict[str, Any] | None) -> None:
    """Store an analysis; an owner-set pace is kept. A failed analysis is marked done (no retry loop)."""
    if result is None:
        await db.execute("UPDATE music_tracks SET analysed_at = ? WHERE filename = ?", (_now(), filename))
        return
    await db.execute(
        "UPDATE music_tracks SET bpm = ?, onset_rate = ?, energy_db = ?, brightness_hz = ?, mood_auto = ?, "
        "pace = CASE WHEN pace_source = 'owner' THEN pace ELSE ? END, "
        "pace_source = COALESCE(pace_source, 'auto'), analysed_at = ? WHERE filename = ?",
        (result["bpm"], result["onset_rate"], result["energy_db"], result["brightness_hz"], result["mood_auto"],
         result["pace"], _now(), filename),
    )


async def analyse_missing(db: aiosqlite.Connection) -> int:
    """Task 22.9: classify every library track not analysed yet (librosa, off the event loop)."""
    tracks = await list_tracks(db)
    pending = [track["filename"] for track in tracks if track["needs_analysis"]]
    folder = music_dir()
    for filename in pending:
        result = await asyncio.to_thread(music_analysis.analyse, folder / filename)
        async with write_transaction(db):
            await save_analysis(db, filename, result)
    return len(pending)


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
    effective_mood = details["mood"] or row.get("mood_auto")
    pace = row.get("pace")
    return {
        **track,
        **details,
        "title": details["title"] or guess_title(track["filename"]),
        "duration_s": row.get("duration_s"),
        # Task 22.9: the owner's mood wins; otherwise the analysed suggestion, marked as automatic.
        "effective_mood": effective_mood,
        "mood_is_auto": not details["mood"] and bool(row.get("mood_auto")),
        "mood_label": MOODS.get(effective_mood or ""),
        "pace": pace,
        "pace_label": PACES.get(pace or ""),
        "pace_is_auto": bool(pace) and row.get("pace_source") != "owner",
        "bpm": row.get("bpm"),
        "onset_rate": row.get("onset_rate"),
        "needs_analysis": row.get("analysed_at") is None,
        "source_label": SOURCES.get(details["source"] or ""),
        "licence_label": LICENCES[details["licence"]]["label"] if details["licence"] in LICENCES else None,
        "attribution_required": required,
        "needs_attribution": bool(required) and not details["attribution"],
    }


def music_dir() -> Path:
    return settings.DATA_DIR / "music_library"


def track_payload(path: Path) -> dict[str, Any]:
    """The public metadata payload for one music file."""
    return {
        "filename": path.name,
        "size_bytes": path.stat().st_size,
        "content_url": f"/api/music/{quote(path.name, safe='')}",
    }


def list_music_files() -> list[dict[str, Any]]:
    """Blocking: every audio file in the library, by name."""
    folder = music_dir()
    folder.mkdir(parents=True, exist_ok=True)
    tracks = []
    for path in sorted(folder.iterdir(), key=lambda item: item.name.lower()):
        if not path.is_file() or path.suffix.lower() not in AUDIO_EXTENSIONS:
            continue
        try:
            tracks.append(track_payload(path))
        except FileNotFoundError:
            # A concurrent delete between directory iteration and stat simply removes the row.
            continue
    return tracks


async def with_details(db: aiosqlite.Connection, tracks: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Give every listed file a details row (guessed title, measured duration) and its view."""
    async with read_transaction():
        rows = await rows_by_filename(db)
    missing = [track["filename"] for track in tracks
               if track["filename"] not in rows or rows[track["filename"]]["duration_s"] is None]
    if missing:
        folder = music_dir()
        durations = {name: await asyncio.to_thread(probe_duration, folder / name) for name in missing}
        async with write_transaction(db):
            for name, duration_s in durations.items():
                if name in rows:
                    await set_duration(db, name, duration_s)
                else:
                    await insert_row(db, name, duration_s)
        async with read_transaction():
            rows = await rows_by_filename(db)
    return [track_view(track, rows.get(track["filename"])) for track in tracks]


async def list_tracks(db: aiosqlite.Connection) -> list[dict[str, Any]]:
    """Every library track with its details (the Library page and auto-select share this)."""
    return await with_details(db, await asyncio.to_thread(list_music_files))


CREDIT_PREFIX = "🎵 Music: "


def credit_line(filename: str, row: dict[str, Any] | None) -> str:
    """Task 22.5: the owner's credit text when given, else a line built from the track details."""
    row = row or {}
    if row.get("attribution"):
        return CREDIT_PREFIX + row["attribution"]
    title = row.get("title") or guess_title(filename)
    text = f'"{title}"'
    if row.get("artist"):
        text += f" by {row['artist']}"
    if row.get("source") in SOURCES:
        text += f" — {SOURCES[row['source']]}"
    if row.get("licence") in LICENCES:
        text += f" ({LICENCES[row['licence']]['label']})"
    if row.get("source_url"):
        text += f" {row['source_url']}"
    return CREDIT_PREFIX + text


async def music_credit(db: aiosqlite.Connection, project_id: str) -> str | None:
    """The credit for the music in the project's completed audio mix, or None."""
    cursor = await db.execute(
        "SELECT background_music FROM audio_jobs WHERE project_id = ? AND status = 'complete'", (project_id,),
    )
    job = await cursor.fetchone()
    if job is None or not job[0]:
        return None
    cursor = await db.execute("SELECT * FROM music_tracks WHERE filename = ?", (job[0],))
    row = await cursor.fetchone()
    return credit_line(job[0], dict(row) if row else None)
