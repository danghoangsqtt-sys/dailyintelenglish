"""Phase 33 migration and copied-data rehearsal guarantees."""

from __future__ import annotations

import json
from pathlib import Path

import aiosqlite
import pytest

from app.db.database import MIGRATIONS_DIR
from scripts.migrate_character_profiles_v2 import apply_pending_migrations, rehearse


async def _migrated_file(path: Path, through: str = "017") -> None:
    async with aiosqlite.connect(path) as db:
        await db.execute("PRAGMA foreign_keys = ON")
        await db.execute(
            "CREATE TABLE IF NOT EXISTS schema_migrations (filename TEXT PRIMARY KEY, applied_at TEXT NOT NULL)"
        )
        for migration in sorted(MIGRATIONS_DIR.glob("*.sql")):
            if migration.name > f"{through}_zzzz.sql":
                break
            await db.executescript(migration.read_text(encoding="utf-8"))
            await db.execute(
                "INSERT OR IGNORE INTO schema_migrations VALUES (?, 'test')", (migration.name,)
            )
        await db.commit()


@pytest.mark.asyncio
async def test_migration_018_applies_to_fresh_database(db):
    columns = {row[1] for row in await (await db.execute("PRAGMA table_info(characters)")).fetchall()}
    assert {"normalized_name", "identity_version", "wizard_step", "archived_at", "is_seed"} <= columns
    asset_columns = {row[1] for row in await (await db.execute("PRAGMA table_info(character_assets)")).fetchall()}
    assert {"slot_key", "source", "review_state", "identity_version", "is_current"} <= asset_columns
    cast_columns = {row[1] for row in await (await db.execute("PRAGMA table_info(project_cast)")).fetchall()}
    assert "profile_version" in cast_columns
    assert await (await db.execute("PRAGMA foreign_key_check")).fetchall() == []


@pytest.mark.asyncio
async def test_pending_migration_is_recorded_once(tmp_path):
    copied_db = tmp_path / "copy.db"
    await _migrated_file(copied_db)
    async with aiosqlite.connect(copied_db) as db:
        first = await apply_pending_migrations(db)
        second = await apply_pending_migrations(db)
        assert "018_character_profiles_v2.sql" in first
        assert second == []
        count = await (await db.execute(
            "SELECT COUNT(*) FROM schema_migrations WHERE filename = '018_character_profiles_v2.sql'"
        )).fetchone()
        assert count[0] == 1


@pytest.mark.asyncio
async def test_rehearsal_preserves_ids_cast_and_voice_and_registers_sprites(tmp_path):
    copied_db = tmp_path / "copy.db"
    data_dir = tmp_path / "copied-data"
    await _migrated_file(copied_db)
    data_dir.mkdir()
    async with aiosqlite.connect(copied_db) as db:
        await db.execute(
            "INSERT INTO projects (id, name, status, created_at, updated_at) VALUES ('p1', 'P', 'draft', 'n', 'n')"
        )
        await db.execute(
            "INSERT INTO speakers (id, project_id, speaker_index, name, accent, tts_engine, voice_id, speed, pitch, volume) "
            "VALUES ('s1', 'p1', 0, 'Lina', 'british', 'edge_tts', 'voice-1', 1.1, 0.2, 0.9)"
        )
        await db.execute(
            "INSERT INTO characters (id, name, gender, age_group, ethnicity, role, hair, eyes, extra, top_color, "
            "top_item, bottom_color, bottom_item, status, base_seed, created_at, updated_at) "
            "VALUES ('lina-id', 'Lina', 'female', 'adult', 'Russian', 'teacher', 'dark hair', 'brown', '', "
            "'white', 'mini dress', 'white', 'mini dress', 'locked', 1, 'n', 'n')"
        )
        await db.execute("INSERT INTO project_cast VALUES ('p1', 0, 'lina-id')")
        await db.commit()
    sprite_dir = data_dir / "library" / "sprites" / "lina-id"
    sprite_dir.mkdir(parents=True)
    (sprite_dir / "calm__closed.png").write_bytes(b"png-placeholder")
    (sprite_dir / "sprite_set.json").write_text(
        json.dumps({"pictures": {"calm__closed": {"head_dx": 0}}}), encoding="utf-8"
    )

    report = await rehearse(copied_db, data_dir)

    assert report["characters_unchanged"] is True
    assert report["cast_unchanged"] is True
    assert report["speakers_unchanged"] is True
    assert report["asset_files_unchanged"] is True
    assert report["foreign_key_errors"] == []
    assert report["registered_sprites"] == 1
    assert report["counts_after"]["character_assets"] == report["counts_before"]["character_assets"] + 1
    assert report["asset_checksums"]["library/sprites/lina-id/calm__closed.png"]["sha256"]
    async with aiosqlite.connect(copied_db) as db:
        row = await (await db.execute(
            "SELECT is_seed, default_accent, default_voice_id FROM characters WHERE id = 'lina-id'"
        )).fetchone()
        assert row == (1, "british", "voice-1")
        asset = await (await db.execute(
            "SELECT slot_key, review_state, identity_version FROM character_assets WHERE character_id = 'lina-id'"
        )).fetchone()
        assert asset == ("calm__closed", "approved", 1)


@pytest.mark.asyncio
async def test_rehearsal_refuses_live_paths(tmp_path, monkeypatch):
    from app.core.config import settings

    live_data = tmp_path / "live"
    live_data.mkdir()
    live_db = live_data / "app.db"
    live_db.touch()
    monkeypatch.setattr(settings, "DATA_DIR", live_data)
    with pytest.raises(ValueError, match="live database"):
        await rehearse(live_db, tmp_path / "copy-data")

