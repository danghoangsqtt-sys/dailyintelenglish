"""Atomic schema publication, historical partial-ALTER recovery and legacy mode defaults."""
import shutil
import sqlite3

import aiosqlite
import pytest

from backend.core.config import settings
from backend.db import database

SOURCE_MIGRATIONS = database.MIGRATIONS_DIR


@pytest.fixture
def isolated_migrations(tmp_path, monkeypatch):
    migrations = tmp_path / "migrations"
    migrations.mkdir()
    for source in SOURCE_MIGRATIONS.glob("*.sql"):
        if source.name < "027":
            shutil.copyfile(source, migrations / source.name)
    monkeypatch.setattr(settings, "DATA_DIR", tmp_path / "db")
    monkeypatch.setattr(database, "MIGRATIONS_DIR", migrations)
    return migrations


async def columns(db, table):
    cursor = await db.execute(f'PRAGMA table_info("{table}")')
    return {row["name"] for row in await cursor.fetchall()}


async def test_middle_migration_failure_rolls_back_schema_and_tracking_then_restarts(isolated_migrations):
    try:
        await database.init_db()
        db = database.Database.instance().connection
        bad = isolated_migrations / "027_solo_explainer.sql"
        bad.write_text("ALTER TABLE projects ADD COLUMN presentation_mode TEXT DEFAULT 'classic';\n"
                       "CREATE TABLE probe (id INTEGER);\nINSERT INTO missing_table VALUES (1);", encoding="utf-8")
        with pytest.raises(sqlite3.OperationalError, match="missing_table"):
            await database.init_db()
        assert "presentation_mode" not in await columns(db, "projects")
        assert not await columns(db, "probe")
        cursor = await db.execute("SELECT 1 FROM schema_migrations WHERE filename = ?", (bad.name,))
        assert await cursor.fetchone() is None
        shutil.copyfile(SOURCE_MIGRATIONS / bad.name, bad)
        await database.init_db()
        assert "presentation_mode" in await columns(db, "projects")
        await database.close_db()
        await database.init_db()
        db = database.Database.instance().connection
        cursor = await db.execute("SELECT COUNT(*) FROM schema_migrations WHERE filename = ?", (bad.name,))
        assert (await cursor.fetchone())[0] == 1
        assert not await (await db.execute("PRAGMA foreign_key_check")).fetchall()
    finally:
        await database.close_db()


async def test_partial_untracked_historical_add_column_resumes_remaining_statements(isolated_migrations):
    # Discover the historical file rather than assuming the suffix from a prior version.
    nineteenth = next(isolated_migrations.glob("019*.sql"))
    later = [(path.name, path.read_bytes()) for path in isolated_migrations.glob("*.sql") if path.name >= "019"]
    for name, _ in later:
        (isolated_migrations / name).unlink()
    try:
        await database.init_db()
        db = database.Database.instance().connection
        await db.execute("ALTER TABLE characters ADD COLUMN appearance TEXT NOT NULL DEFAULT ''")
        await db.commit()
        for name, content in later:
            (isolated_migrations / name).write_bytes(content)
        await database.init_db()
        assert {"appearance", "outfit"} <= await columns(db, "characters")
        assert await (await db.execute("SELECT 1 FROM schema_migrations WHERE filename=?", (nineteenth.name,))).fetchone()
    finally:
        await database.close_db()


async def test_new_migrations_never_swallow_a_duplicate_and_mark_whole_file_done(isolated_migrations):
    try:
        await database.init_db()
        db = database.Database.instance().connection
        await db.execute("ALTER TABLE projects ADD COLUMN presentation_mode TEXT")
        await db.commit()
        migration = isolated_migrations / "027_solo_explainer.sql"
        shutil.copyfile(SOURCE_MIGRATIONS / migration.name, migration)
        with pytest.raises(sqlite3.OperationalError, match="duplicate column"):
            await database.init_db()
        assert "explainer_structure" not in await columns(db, "projects")
        assert not await (await db.execute("SELECT 1 FROM schema_migrations WHERE filename=?", (migration.name,))).fetchone()
    finally:
        await database.close_db()


async def test_split_statements_keeps_trigger_body_and_quoted_semicolons_atomic():
    db = await aiosqlite.connect(":memory:")
    db.row_factory = aiosqlite.Row
    try:
        await db.execute("CREATE TABLE schema_migrations (filename TEXT PRIMARY KEY, applied_at TEXT)")
        await db.commit()
        await database._apply_migration(db, "027_test.sql", """
            BEGIN;
            CREATE TABLE values_table (value TEXT);
            CREATE TABLE audit (value TEXT);
            CREATE TRIGGER copy_value AFTER INSERT ON values_table BEGIN
              INSERT INTO audit VALUES (NEW.value);
              INSERT INTO audit VALUES ('second;entry');
            END;
            INSERT INTO values_table VALUES ('first;entry');
            COMMIT;
        """)
        assert [row[0] for row in await (await db.execute("SELECT value FROM audit")).fetchall()] == ["first;entry", "second;entry"]
    finally:
        await db.close()
