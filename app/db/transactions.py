"""Shared write-lock/transaction helpers over the single app-wide aiosqlite connection.

Moved out of `app/api/projects.py` (Task 13.3): the whole app shares one `aiosqlite`
connection (`app.db.database.Database`), which has exactly one implicit transaction
active at a time -- SQLite doesn't support nested transactions on a single connection.
Without a lock, two concurrent requests can interleave their statements inside that one
shared transaction: a rollback triggered by one write wipes out *both* requests'
uncommitted work, and a plain read running alongside an uncommitted write sees that
write's data early (a dirty read) and -- if the write then rolls back -- data that never
really existed (a phantom read). So every route that touches `db`, reads included,
serializes on this single connection-wide lock -- never a per-project lock, which only
protects same-project races and leaves this cross-request corruption open.

The lock is never held across a slow provider call (Gemini/Ollama, network + retries):
holding a connection-wide lock across one would stall every other request -- even an
unrelated dashboard GET -- for its duration. The established pattern (already used by
`script_service.py`/`tts_service.py`/Task 13.3's own `ai_worker.py`) is: take a short
`read_transaction()` to snapshot what's needed, make the slow call with no lock held,
then take a separate `write_transaction()` to persist the result.
"""

from asyncio import Lock
from contextlib import asynccontextmanager

import aiosqlite

write_lock = Lock()


@asynccontextmanager
async def read_transaction():
    """Serialize one read-only section against the shared connection.

    Guarantees a read never observes another request's not-yet-committed write
    (a dirty read), and never observes a write that later rolls back (a phantom
    read) -- the read simply waits its turn behind whichever write holds the lock.
    """
    async with write_lock:
        yield


@asynccontextmanager
async def write_transaction(db: aiosqlite.Connection):
    """Serialize one write transaction on the shared connection.

    The commit itself runs inside the try, so a commit failure (not just a
    failure in the wrapped writes) also triggers a rollback rather than
    leaving the connection in a half-committed, unknown state.

    Note for tests: `asyncio.Lock` binds to whichever event loop first calls
    `acquire()` on it. Since the app has exactly one event loop for its whole
    lifetime, that's a non-issue in production -- but a test runner that hands
    each test its own loop needs `write_lock` reset between tests (see the
    autouse `_reset_write_lock` fixture in `tests/conftest.py`), or the second
    test to touch it fails with "bound to a different event loop".
    """
    async with write_lock:
        try:
            yield
            await db.commit()
        except Exception:
            await db.rollback()
            raise
