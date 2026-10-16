"""Consistent SQLite backup and idle-work guard for the local Desktop installer."""

from __future__ import annotations

import argparse
import json
import sqlite3
from contextlib import closing
from pathlib import Path

JOB_TABLES = ("ai_generation_jobs", "image_jobs", "audio_jobs", "video_jobs")
TERMINAL_STATUSES = {"complete", "error", "cancelled", "stale", "failed"}


def inspect_database(connection: sqlite3.Connection) -> dict:
    """Fail closed on unfinished jobs or corrupt references; return counts only."""
    if connection.execute("PRAGMA integrity_check").fetchall() != [("ok",)]:
        raise RuntimeError("Database integrity check failed; Desktop was not replaced")
    if connection.execute("PRAGMA foreign_key_check").fetchone() is not None:
        raise RuntimeError("Database foreign key check failed; Desktop was not replaced")
    tables = {row[0] for row in connection.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    active = {}
    for table in JOB_TABLES:
        if table in tables:
            count = sum(count for status, count in connection.execute(f'SELECT status, count(*) FROM "{table}" GROUP BY status')
                        if status not in TERMINAL_STATUSES)
            if count:
                active[table] = count
    if active:
        raise RuntimeError(f"Unfinished Studio jobs: {active}. Finish or cancel them before upgrading; no process was stopped.")
    return {table: connection.execute(f'SELECT count(*) FROM "{table}"').fetchone()[0]
            for table in ("projects", "characters", "character_assets", *JOB_TABLES) if table in tables}


def backup_database(database: Path, destination: Path | None = None) -> dict:
    """Read an idle SQLite store and snapshot committed WAL data using SQLite backup."""
    database = database.resolve(strict=True)
    with closing(sqlite3.connect(database.as_uri() + "?mode=ro", uri=True, timeout=5)) as source:
        counts = inspect_database(source)
        if destination is None:
            return counts
        destination = destination.resolve()
        if destination == database or destination.exists():
            raise ValueError("Backup must be a new file separate from the live database")
        destination.parent.mkdir(parents=True, exist_ok=True)
        with closing(sqlite3.connect(destination)) as target:
            source.backup(target)
            # Inspect the actual snapshot too: work may have started during backup.
            counts = inspect_database(target)
        return counts


def main() -> None:
    """Run the installer preflight without importing application settings/workers."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--database", type=Path, required=True)
    parser.add_argument("--backup", type=Path)
    args = parser.parse_args()
    print(json.dumps(backup_database(args.database, args.backup), sort_keys=True))


if __name__ == "__main__":
    main()
