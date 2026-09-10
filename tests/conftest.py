"""Shared pytest fixtures — an in-memory database with migrations applied."""

from pathlib import Path

import aiosqlite
import pytest

MIGRATIONS_DIR = Path(__file__).resolve().parent.parent / "app" / "db" / "migrations"


@pytest.fixture
async def db() -> aiosqlite.Connection:
    """Open an in-memory SQLite connection with all migrations applied."""
    connection = await aiosqlite.connect(":memory:")
    connection.row_factory = aiosqlite.Row
    await connection.execute("PRAGMA foreign_keys = ON")
    for migration_file in sorted(MIGRATIONS_DIR.glob("*.sql")):
        await connection.executescript(migration_file.read_text(encoding="utf-8"))
    await connection.commit()
    yield connection
    await connection.close()
