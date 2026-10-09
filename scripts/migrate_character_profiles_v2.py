"""Rehearse Phase 33 migration and register legacy sprite files on copied data only."""

from __future__ import annotations

import argparse
import asyncio
import json
import shutil
import sqlite3
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path

import aiosqlite

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.core.config import settings  # noqa: E402
from app.db.database import MIGRATIONS_DIR  # noqa: E402


def _resolved(path: Path) -> Path:
    return path.expanduser().resolve()


def backup_database(source: Path, destination: Path) -> None:
    """Create a consistent SQLite backup even when the live app has the DB open."""
    if not source.is_file():
        raise ValueError(f"Source database does not exist: {source}")
    destination.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(source) as source_db, sqlite3.connect(destination) as destination_db:
        source_db.backup(destination_db)


def ensure_copy_targets(db_path: Path, data_dir: Path) -> None:
    """Refuse the configured live database and data root."""
    if _resolved(db_path) == _resolved(settings.db_path):
        raise ValueError("Refusing to migrate the configured live database; pass a copied --db path")
    if _resolved(data_dir) == _resolved(settings.DATA_DIR):
        raise ValueError("Refusing to scan the configured live data directory; pass a copied --data-dir path")
    if not db_path.is_file():
        raise ValueError(f"Copied database does not exist: {db_path}")
    if not data_dir.is_dir():
        raise ValueError(f"Copied data directory does not exist: {data_dir}")


async def apply_pending_migrations(db: aiosqlite.Connection) -> list[str]:
    """Apply migrations missing from the copied database and return their filenames."""
    await db.execute(
        "CREATE TABLE IF NOT EXISTS schema_migrations (filename TEXT PRIMARY KEY, applied_at TEXT NOT NULL)"
    )
    cursor = await db.execute("SELECT filename FROM schema_migrations")
    applied = {row[0] for row in await cursor.fetchall()}
    added: list[str] = []
    for migration in sorted(MIGRATIONS_DIR.glob("*.sql")):
        if migration.name in applied:
            continue
        await db.executescript(migration.read_text(encoding="utf-8"))
        await db.execute(
            "INSERT INTO schema_migrations (filename, applied_at) VALUES (?, ?)",
            (migration.name, datetime.now(timezone.utc).isoformat()),
        )
        added.append(migration.name)
    await db.commit()
    return added


async def register_legacy_sprites(db: aiosqlite.Connection, data_dir: Path) -> int:
    """Register current legacy sprite PNGs as approved versioned asset rows."""
    cursor = await db.execute("SELECT id, identity_version FROM characters ORDER BY id")
    characters = await cursor.fetchall()
    registered = 0
    for character_id, version in characters:
        folder = data_dir / "library" / "sprites" / character_id
        manifest = folder / "sprite_set.json"
        if not manifest.is_file():
            continue
        try:
            names = json.loads(manifest.read_text(encoding="utf-8")).get("pictures", {}).keys()
        except (OSError, json.JSONDecodeError):
            names = (path.stem for path in folder.glob("*.png"))
        for name in sorted(set(names)):
            picture = folder / f"{name}.png"
            if not picture.is_file():
                continue
            cursor = await db.execute(
                "SELECT 1 FROM character_assets WHERE character_id = ? AND identity_version = ? "
                "AND slot_key = ? AND is_current = 1",
                (character_id, version, name),
            )
            if await cursor.fetchone() is not None:
                continue
            asset_id = str(uuid.uuid5(uuid.NAMESPACE_URL, f"daily-beyond:{character_id}:v{version}:{name}"))
            now = datetime.now(timezone.utc).isoformat()
            await db.execute(
                "INSERT INTO character_assets "
                "(id, character_id, kind, path, seed, prompt_tokens, prompt_truncated, approved, created_at, "
                "slot_key, source, original_filename, review_state, validation_json, identity_version, is_current, updated_at) "
                "VALUES (?, ?, 'sprite', ?, NULL, NULL, 0, 1, ?, ?, 'legacy_migration', ?, 'approved', '{}', ?, 1, ?)",
                (asset_id, character_id, str(picture), now, name, picture.name, version, now),
            )
            registered += 1
    await db.commit()
    return registered


async def rehearse(db_path: Path, data_dir: Path) -> dict:
    """Apply migration and sprite registration to copies, returning verification evidence."""
    ensure_copy_targets(db_path, data_dir)
    async with aiosqlite.connect(db_path) as db:
        db.row_factory = aiosqlite.Row
        await db.execute("PRAGMA foreign_keys = ON")
        before_characters = [tuple(row) for row in await (await db.execute(
            "SELECT id, name FROM characters ORDER BY id"
        )).fetchall()]
        before_cast = [tuple(row) for row in await (await db.execute(
            "SELECT project_id, speaker_index, character_id FROM project_cast ORDER BY project_id, speaker_index"
        )).fetchall()]
        before_speakers = [tuple(row) for row in await (await db.execute(
            "SELECT id, name, accent, tts_engine, voice_id, speed, pitch, volume FROM speakers ORDER BY id"
        )).fetchall()]
        applied = await apply_pending_migrations(db)
        registered = await register_legacy_sprites(db, data_dir)
        after_characters = [tuple(row) for row in await (await db.execute(
            "SELECT id, name FROM characters ORDER BY id"
        )).fetchall()]
        after_cast = [tuple(row) for row in await (await db.execute(
            "SELECT project_id, speaker_index, character_id FROM project_cast ORDER BY project_id, speaker_index"
        )).fetchall()]
        after_speakers = [tuple(row) for row in await (await db.execute(
            "SELECT id, name, accent, tts_engine, voice_id, speed, pitch, volume FROM speakers ORDER BY id"
        )).fetchall()]
        foreign_keys = [dict(row) for row in await (await db.execute("PRAGMA foreign_key_check")).fetchall()]
    return {
        "database": str(db_path),
        "data_dir": str(data_dir),
        "applied": applied,
        "registered_sprites": registered,
        "characters_unchanged": before_characters == after_characters,
        "cast_unchanged": before_cast == after_cast,
        "speakers_unchanged": before_speakers == after_speakers,
        "foreign_key_errors": foreign_keys,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db", type=Path, required=True, help="Path to a copied app.db")
    parser.add_argument("--data-dir", type=Path, required=True, help="Path to a copied data directory")
    parser.add_argument("--copy-from-live", action="store_true", help="Copy live DB/data into the given empty targets first")
    args = parser.parse_args()
    if args.copy_from_live:
        if args.db.exists() or args.data_dir.exists():
            raise SystemExit("--copy-from-live requires non-existing --db and --data-dir targets")
        args.data_dir.mkdir(parents=True)
        backup_database(settings.db_path, args.db)
        for relative in (Path("library/characters"), Path("library/sprites")):
            source = settings.DATA_DIR / relative
            if source.is_dir():
                shutil.copytree(source, args.data_dir / relative)
    try:
        report = asyncio.run(rehearse(args.db, args.data_dir))
    except (ValueError, sqlite3.Error) as exc:
        print(json.dumps({"ok": False, "error": str(exc)}, indent=2))
        return 1
    print(json.dumps({"ok": not report["foreign_key_errors"] and all(
        report[key] for key in ("characters_unchanged", "cast_unchanged", "speakers_unchanged")
    ), **report}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

