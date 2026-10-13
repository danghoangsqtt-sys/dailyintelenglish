"""Task 33.1: register legacy sprite packs as profile assets, and rehearse migration 018 on a copy.

    venv\\Scripts\\python scripts\\migrate_character_profiles_v2.py rehearse [--db data/app.db] [--data data]
    venv\\Scripts\\python scripts\\migrate_character_profiles_v2.py register-sprites   # real DB, after a backup

`rehearse` copies the database and the character/sprite library folders into a fresh temporary folder, applies every
migration there with the app's own runner, registers the sprites, and prints a before/after comparison. It never writes
the source database or the real `data/` folder.

`register-sprites` is the idempotent post-migration step on the real database: every picture listed in a character's
`sprite_set.json` becomes an approved `character_assets` row (`kind='sprite'`, `slot_key='sprite/<name>'`,
`source='legacy_migration'`); the files stay where they are and `sprite_set.json` stays the renderer's manifest.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import shutil
import sqlite3
import sys
import tempfile
import uuid
from contextlib import closing
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

SPRITE_SET = "sprite_set.json"


def register_legacy_sprites(connection: sqlite3.Connection, data_dir: Path) -> int:
    """Insert one approved asset row per sprite picture not yet registered. Returns the number of new rows."""
    added, now = 0, datetime.now(timezone.utc).isoformat()
    characters = connection.execute("SELECT id, identity_version FROM characters").fetchall()
    for character_id, identity_version in characters:
        folder = data_dir / "library" / "sprites" / character_id
        manifest = folder / SPRITE_SET
        if not manifest.is_file():
            continue
        names = sorted(json.loads(manifest.read_text(encoding="utf-8")).get("pictures", {}))
        for name in names:
            slot_key = f"sprite/{name}"
            exists = connection.execute(
                "SELECT 1 FROM character_assets WHERE character_id = ? AND identity_version = ? AND facing = 'native' "
                "AND slot_key = ? AND is_current = 1",
                (character_id, identity_version, slot_key),
            ).fetchone()
            picture = folder / f"{name}.png"
            if exists or not picture.is_file():
                continue
            connection.execute(
                "INSERT INTO character_assets (id, character_id, kind, path, approved, created_at, slot_key, source, "
                "original_filename, review_state, identity_version, is_current, updated_at, facing) "
                "VALUES (?, ?, 'sprite', ?, 1, ?, ?, 'legacy_migration', ?, 'approved', ?, 1, ?, 'native')",
                (str(uuid.uuid4()), character_id, str(picture.relative_to(data_dir.parent)), now, slot_key, picture.name,
                 identity_version, now),
            )
            added += 1
    connection.commit()
    return added


def _snapshot(connection: sqlite3.Connection) -> dict:
    tables = {row[0] for row in connection.execute("SELECT name FROM sqlite_master WHERE type = 'table'")}
    return {
        "characters": [tuple(row) for row in connection.execute("SELECT id, name, gender FROM characters ORDER BY id")],
        "asset_counts": {"character_assets": connection.execute("SELECT COUNT(*) FROM character_assets").fetchone()[0]},
        "approved_paths": sorted(row[0] for row in connection.execute(
            "SELECT path FROM character_assets WHERE approved = 1 AND kind != 'sprite'")),
        "cast": [tuple(row) for row in connection.execute(
            "SELECT project_id, speaker_index, character_id FROM project_cast ORDER BY 1, 2")],
        "speakers": [tuple(row) for row in connection.execute(
            "SELECT * FROM speakers ORDER BY project_id, speaker_index")] if "speakers" in tables else [],
    }


async def _apply_migrations(data_dir: Path) -> None:
    from backend.core.config import settings
    from backend.db import database

    settings.DATA_DIR = data_dir  # the runner opens settings.db_path, which lives under DATA_DIR
    database.Database._instance = None
    await database.init_db()
    await database.Database.instance().close()
    database.Database._instance = None


def rehearse(source_db: Path, source_data: Path) -> dict:
    real_data = (ROOT / "data").resolve()
    with tempfile.TemporaryDirectory(prefix="phase33-rehearsal-") as temp:
        target = Path(temp) / "data"
        if target.resolve().is_relative_to(real_data):
            raise SystemExit("refusing to rehearse inside the real data folder")
        target.mkdir()
        for sub in ("characters", "sprites"):
            if (source_data / "library" / sub).is_dir():
                shutil.copytree(source_data / "library" / sub, target / "library" / sub)
        shutil.copy2(source_db, target / "app.db")
        with closing(sqlite3.connect(target / "app.db")) as connection:
            before = _snapshot(connection)
        asyncio.run(_apply_migrations(target))
        with closing(sqlite3.connect(target / "app.db")) as connection:
            connection.execute("PRAGMA foreign_keys = ON")
            first = register_legacy_sprites(connection, target)
            second = register_legacy_sprites(connection, target)
            after = _snapshot(connection)
            fk_problems = connection.execute("PRAGMA foreign_key_check").fetchall()
            profile = [tuple(row) for row in connection.execute(
                "SELECT name, normalized_name, sprite_facing, is_seed, identity_version FROM characters ORDER BY name")]
            versions = connection.execute("SELECT DISTINCT profile_version FROM project_cast").fetchall()
    unchanged = {key: before[key] == after[key] for key in ("characters", "approved_paths", "cast", "speakers")}
    return {"unchanged": unchanged, "sprites_registered": first, "sprites_registered_again": second,
            "assets_before": before["asset_counts"], "assets_after": after["asset_counts"],
            "foreign_key_problems": fk_problems, "profiles": profile, "cast_profile_versions": versions}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = parser.add_subparsers(dest="command", required=True)
    rehearse_cmd = sub.add_parser("rehearse")
    rehearse_cmd.add_argument("--db", type=Path, default=ROOT / "data" / "app.db")
    rehearse_cmd.add_argument("--data", type=Path, default=ROOT / "data")
    sub.add_parser("register-sprites")
    args = parser.parse_args()
    if args.command == "rehearse":
        print(json.dumps(rehearse(args.db, args.data), indent=2, default=str))
    else:
        with closing(sqlite3.connect(ROOT / "data" / "app.db")) as connection:
            print(json.dumps({"sprites_registered": register_legacy_sprites(connection, ROOT / "data")}))


if __name__ == "__main__":
    main()
