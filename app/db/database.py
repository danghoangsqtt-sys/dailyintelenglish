"""Async SQLite connection management (aiosqlite)."""

import sqlite3
from datetime import datetime, timezone
from pathlib import Path

import aiosqlite

from app.core.config import settings

MIGRATIONS_DIR = Path(__file__).parent / "migrations"


class Database:
    """Singleton holder for the shared aiosqlite connection."""

    _instance: "Database | None" = None

    def __init__(self) -> None:
        self._connection: aiosqlite.Connection | None = None

    @classmethod
    def instance(cls) -> "Database":
        """Return the process-wide Database singleton."""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    async def connect(self) -> aiosqlite.Connection:
        """Open the shared connection if not already open, with foreign keys enforced."""
        if self._connection is None:
            settings.DATA_DIR.mkdir(parents=True, exist_ok=True)
            self._connection = await aiosqlite.connect(settings.db_path)
            self._connection.row_factory = aiosqlite.Row
            await self._connection.execute("PRAGMA foreign_keys = ON")
        return self._connection

    async def close(self) -> None:
        """Close the shared connection if open."""
        if self._connection is not None:
            await self._connection.close()
            self._connection = None

    @property
    def connection(self) -> aiosqlite.Connection:
        """Return the open connection, raising if `connect()` has not run yet."""
        if self._connection is None:
            raise RuntimeError("Database not connected — call init_db() during startup first")
        return self._connection


async def init_db() -> None:
    """Open the database connection and apply each migration file exactly once, in
    filename order, tracked in `schema_migrations`.

    Previously this replayed every migration file on every startup — harmless for
    migrations that only use `CREATE TABLE/INDEX IF NOT EXISTS`, but a real,
    reproducible `sqlite3.OperationalError: duplicate column name` crash on any second
    real app restart once a migration uses `ALTER TABLE ADD COLUMN` (SQLite has no
    `ADD COLUMN IF NOT EXISTS`) — found for real 2026-09-14 while adding migration 005.
    """
    db = Database.instance()
    connection = await db.connect()
    await connection.execute(
        "CREATE TABLE IF NOT EXISTS schema_migrations (filename TEXT PRIMARY KEY, applied_at TEXT NOT NULL)"
    )
    cursor = await connection.execute("SELECT filename FROM schema_migrations")
    applied = {row[0] for row in await cursor.fetchall()}
    for migration_file in sorted(MIGRATIONS_DIR.glob("*.sql")):
        if migration_file.name in applied:
            continue
        script = migration_file.read_text(encoding="utf-8")
        try:
            await connection.executescript(script)
        except sqlite3.OperationalError as exc:
            # A database that predates schema_migrations tracking may already have this
            # migration's effect applied (e.g. an ALTER TABLE ADD COLUMN from before this
            # fix existed) -- record it as applied and continue rather than crashing
            # startup. Any other OperationalError is a real failure and must still raise.
            message = str(exc)
            if "duplicate column name" not in message and "already exists" not in message:
                raise
        await connection.execute(
            "INSERT INTO schema_migrations (filename, applied_at) VALUES (?, ?)",
            (migration_file.name, datetime.now(timezone.utc).isoformat()),
        )
    await connection.commit()


async def close_db() -> None:
    """Close the shared database connection during shutdown."""
    await Database.instance().close()


async def get_db() -> aiosqlite.Connection:
    """FastAPI dependency yielding the shared aiosqlite connection."""
    return Database.instance().connection
