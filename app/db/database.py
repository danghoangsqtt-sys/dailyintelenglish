"""Async SQLite connection management (aiosqlite)."""

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
    """Open the database connection and apply migrations in filename order."""
    db = Database.instance()
    connection = await db.connect()
    for migration_file in sorted(MIGRATIONS_DIR.glob("*.sql")):
        script = migration_file.read_text(encoding="utf-8")
        await connection.executescript(script)
    await connection.commit()


async def close_db() -> None:
    """Close the shared database connection during shutdown."""
    await Database.instance().close()


async def get_db() -> aiosqlite.Connection:
    """FastAPI dependency yielding the shared aiosqlite connection."""
    return Database.instance().connection
