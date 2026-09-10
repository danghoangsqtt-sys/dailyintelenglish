"""Shared pytest fixtures — an in-memory database with migrations applied."""

from asyncio import Lock
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


@pytest.fixture(autouse=True)
def _reset_write_lock():
    """Give every test a fresh app.api.projects._write_lock.

    asyncio.Lock binds to whichever event loop first calls acquire() on it,
    and pytest-asyncio hands each test function its own loop (function-scoped
    by default). Without this, the second test to exercise a write endpoint
    would fail with "Lock ... is bound to a different event loop" — an
    artifact of the test runner, never reachable in production where the app
    has exactly one event loop for its entire lifetime.
    """
    from app.api import projects as projects_api

    projects_api._write_lock = Lock()
    yield
