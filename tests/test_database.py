"""Regression coverage for `init_db()`'s migration-idempotency fix (Task 2.5, found while
adding migration 005): previously every migration file was replayed on every call, which
crashed with `sqlite3.OperationalError: duplicate column name` on a second real app
restart once any migration used `ALTER TABLE ADD COLUMN` (SQLite has no `ADD COLUMN IF
NOT EXISTS`). Uses a real on-disk file (not `:memory:`) since the bug is specifically
about re-running migrations against an already-migrated persisted database, the same way
two real app restarts would.
"""

from app.db.database import MIGRATIONS_DIR, init_db


async def test_init_db_is_idempotent_across_repeated_calls(tmp_path, monkeypatch):
    from app.core.config import settings
    from app.db.database import Database

    monkeypatch.setattr(settings, "DATA_DIR", tmp_path)

    await init_db()
    # A second call against the same on-disk file simulates a real app restart -- must
    # not raise "duplicate column name" for any ALTER TABLE ADD COLUMN migration.
    await init_db()

    connection = Database.instance().connection
    cursor = await connection.execute("SELECT COUNT(*) AS n FROM schema_migrations")
    row = await cursor.fetchone()
    migration_file_count = len(list(MIGRATIONS_DIR.glob("*.sql")))
    assert row["n"] == migration_file_count

    await Database.instance().close()


async def test_init_db_records_every_migration_file_exactly_once(tmp_path, monkeypatch):
    from app.core.config import settings
    from app.db.database import Database

    monkeypatch.setattr(settings, "DATA_DIR", tmp_path)

    await init_db()
    await init_db()
    await init_db()

    connection = Database.instance().connection
    cursor = await connection.execute("SELECT filename FROM schema_migrations")
    rows = await cursor.fetchall()
    recorded = [row["filename"] for row in rows]
    assert len(recorded) == len(set(recorded)), "each migration file must be recorded exactly once"
    assert recorded == sorted(recorded)

    await Database.instance().close()
