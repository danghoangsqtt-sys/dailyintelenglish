"""Music Library provenance rows (Task 22.2). Write functions run inside write_transaction."""

from __future__ import annotations

import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import aiosqlite

from app.core.config import settings

PROVENANCE_FIELDS = ("style", "brief", "caption", "seed", "duration_s", "model", "licence", "strategy",
                     "created_at")


def music_dir() -> Path:
    return settings.DATA_DIR / "music_library"


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def place_without_overwrite(temporary_path: Path, requested_name: str) -> Path:
    """Atomically place a file in its folder, adding a numeric suffix instead of overwriting."""
    folder = temporary_path.parent
    requested_path = Path(requested_name)
    collision_index = 0
    while True:
        if collision_index == 0:
            candidate_name = requested_name
        else:
            candidate_name = f"{requested_path.stem} ({collision_index}){requested_path.suffix}"
        candidate_path = folder / candidate_name
        try:
            os.link(temporary_path, candidate_path)
        except FileExistsError:
            collision_index += 1
            continue
        temporary_path.unlink()
        return candidate_path


async def record_upload(db: aiosqlite.Connection, filename: str) -> None:
    await db.execute(
        "INSERT OR REPLACE INTO music_tracks (filename, source, created_at) VALUES (?, 'upload', ?)",
        (filename, _now()),
    )


async def record_ai(db: aiosqlite.Connection, filename: str, provenance: dict[str, Any]) -> None:
    await db.execute(
        "INSERT OR REPLACE INTO music_tracks (filename, source, style, brief, caption, seed, duration_s, model, "
        "licence, strategy, job_id, created_at) VALUES (?, 'ai', ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (filename, provenance["style"], provenance["brief"], provenance["caption"], provenance["seed"],
         provenance["duration_s"], provenance["model"], provenance["licence"], provenance["strategy"],
         provenance.get("job_id"), _now()),
    )


async def delete_row(db: aiosqlite.Connection, filename: str) -> None:
    await db.execute("DELETE FROM music_tracks WHERE filename = ?", (filename,))


async def rows_by_filename(db: aiosqlite.Connection) -> dict[str, dict[str, Any]]:
    cursor = await db.execute("SELECT * FROM music_tracks")
    return {row["filename"]: dict(row) for row in await cursor.fetchall()}


def with_provenance(track: dict[str, Any], row: dict[str, Any] | None) -> dict[str, Any]:
    """A file with no row is an upload made before Task 22.2."""
    source = row["source"] if row else "upload"
    provenance = {field: row[field] for field in PROVENANCE_FIELDS} if source == "ai" else None
    return {**track, "source": source, "provenance": provenance}
