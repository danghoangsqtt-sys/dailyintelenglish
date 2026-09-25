"""Shared pytest fixtures — an in-memory database with migrations applied."""

import socket
import threading
import time
from asyncio import Lock, Semaphore
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator

import aiosqlite
import pytest
import uvicorn

from app.core.paths import get_project_root
from app.db.database import Database

MIGRATIONS_DIR = Path(__file__).resolve().parent.parent / "app" / "db" / "migrations"

# Task 16.3 (BUG-023): the one real data/app.db this whole suite must never open,
# computed independently of `settings.DATA_DIR` -- the very thing the guard below
# exists to catch a test failing to override.
_REAL_DB_PATH = (get_project_root() / "data" / "app.db").resolve()


def _install_real_db_guard() -> None:
    """Patch `Database.connect` (never `app/db/database.py` itself -- outside this
    task's allowed files) so no test can ever open, or silently keep reusing, the
    real database. Applied once at conftest import time, before any test or fixture
    runs (including module-scoped ones), and never restored: nothing in this suite
    should legitimately touch the real DB through the app's own connection
    machinery for the life of the process.

    Two failure modes guarded against, both discovered investigating BUG-023:
    (a) opening a brand new connection straight against the real path (a fixture
        that never overrode `settings.DATA_DIR` at all); (b) a call that finds a
        connection already open and reuses it as-is -- `Database.connect()`'s own
        behavior -- while `settings.DATA_DIR` now points somewhere else than where
        that connection was actually opened. (b) is the exact stale-reuse mechanism
        that caused BUG-023's leak: a live-server fixture's connection, opened
        against whatever DATA_DIR happened to be current at the time, silently
        outliving that fixture and getting reused by a later, differently-configured
        test. Checking it this way catches a stale mismatch onto ANY path (not only
        the real one), so a bug in the isolation helper below trips this immediately
        instead of quietly corrupting some other test's tmp database.
    """
    original_connect = Database.connect

    async def guarded_connect(self: Database) -> aiosqlite.Connection:
        from app.core.config import settings

        current_path = settings.db_path.resolve()
        if self._connection is not None:
            opened_for = getattr(self, "_opened_for_path", None)
            if opened_for is not None and opened_for != current_path:
                raise RuntimeError(
                    f"Database.connect(): reusing a connection opened against "
                    f"{opened_for}, but settings.DATA_DIR now points at "
                    f"{current_path} -- a stale connection is about to silently "
                    "read/write the wrong database (Task 16.3, BUG-023)."
                )
            return self._connection
        if current_path == _REAL_DB_PATH:
            raise RuntimeError(
                f"A test tried to open the real database at {_REAL_DB_PATH} -- "
                "settings.DATA_DIR was never overridden to an isolated tmp "
                "directory before this connection was opened (Task 16.3, BUG-023)."
            )
        connection = await original_connect(self)
        self._opened_for_path = current_path
        return connection

    Database.connect = guarded_connect


_install_real_db_guard()


def _neutralize_cloud_config() -> None:
    """Task 18.3 (PM review N1): `app.core.config` loads the real `.env` at
    import time, so without this, `settings.OPENAI_COMPAT_*` holds the
    owner's real OpenRouter key and base URL for this whole pytest process.
    Investigating the browser test's route-glob bug during 18.3, a debug
    script's mock slipped and an unmocked request reached the real
    OpenRouter API with the owner's real key. Now that `AI_ALLOW_CLOUD`
    defaults to true (plan Amendment C), any test whose mock slips the same
    way can spend the owner's free-tier quota or send real project data to a
    third party -- invariant 31/33 territory, not just test hygiene.

    Neutralised once here, before any test or fixture runs, same as the
    real-DB guard above -- and never restored, for the same reason. Tests
    that need cloud behaviour set their own fake key/URL via `monkeypatch`,
    which every cloud-related test in this suite already does.
    """
    from app.core import config

    config.settings.OPENAI_COMPAT_API_KEY = ""
    config.ENV_OPENAI_COMPAT_API_KEY = ""
    # .invalid is reserved (RFC 2606) to never resolve -- an accidental,
    # unmocked request fails fast and offline instead of silently reaching a
    # real host.
    config.settings.OPENAI_COMPAT_BASE_URL = "https://openrouter.invalid/api/v1"
    config.settings.AI_ALLOW_CLOUD = False
    # Task 18.8 (D28): GEMINI_API_KEY is no longer just "the legacy key nothing
    # reads" (that was true post-18.3, pre-18.8) -- it's the real key the new
    # Gemini chain entries dispatch against, so this neutralization now matters
    # exactly as much as OPENAI_COMPAT_API_KEY above.
    config.settings.GEMINI_API_KEY = ""
    # PM review N1 (18.8): ENV_GEMINI_API_KEY (app/core/config.py) was never
    # blanked here, unlike ENV_OPENAI_COMPAT_API_KEY/ENV_OPENCODE_ZEN_API_KEY
    # below -- a "clear the Gemini key" code path reverts to this value, which
    # would have put the owner's real key back into the test process (the
    # .invalid base URL stops any actual call, but the rule is that tests
    # never hold a real key at all, not just that calls with it fail).
    config.ENV_GEMINI_API_KEY = ""
    config.settings.GEMINI_BASE_URL = "https://gemini.invalid/v1beta/openai"
    # Task 18.8: OpenCode Zen, same pattern.
    config.settings.OPENCODE_ZEN_API_KEY = ""
    config.ENV_OPENCODE_ZEN_API_KEY = ""
    config.settings.OPENCODE_ZEN_BASE_URL = "https://opencode-zen.invalid/v1"


_neutralize_cloud_config()


def _find_free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as listener:
        listener.bind(("127.0.0.1", 0))
        return listener.getsockname()[1]


@contextmanager
def live_server(tmp_path_factory: pytest.TempPathFactory, slug: str) -> Iterator[str]:
    """Shared live-uvicorn-server helper for every `*_browser.py` Playwright
    fixture (Task 16.3, BUG-023): starts a real uvicorn server hosting the real
    `app` in a background thread, with `settings.DATA_DIR` isolated to a fresh tmp
    directory for the server's whole lifetime, and yields its base URL.

    Replaces 24 independently copy-pasted `live_server_url` fixtures -- the drift
    between them (3 correctly isolated `DATA_DIR`, 21 didn't) was BUG-023's root
    cause, so the fix is one shared implementation each file's thin fixture
    delegates to, not a 22nd variant to keep in sync by hand.

    On teardown, fails loudly (`pytest.fail`, not a log line) if the server thread
    is still alive after a bounded join, or if `Database`'s connection is still
    open afterward -- rather than silently leaving a stale connection for
    whatever test runs next to inherit, which is exactly how BUG-023 leaked.
    `slug` names the tmp directory so failures are traceable to their caller.
    """
    from app.core.config import settings
    from app.main import app

    original_data_dir = settings.DATA_DIR
    settings.DATA_DIR = tmp_path_factory.mktemp(f"{slug}-data")
    port = _find_free_port()
    server = uvicorn.Server(uvicorn.Config(app, host="127.0.0.1", port=port, log_level="warning"))
    thread = threading.Thread(target=server.run, daemon=True)
    thread.start()

    started_at = time.time()
    while time.time() - started_at < 10.0:
        if not thread.is_alive():
            # The server thread already exited -- almost always a lifespan startup
            # error (e.g. the real-DB guard above tripping). Fail fast instead of
            # waiting out the full timeout for a port that will never open.
            settings.DATA_DIR = original_data_dir
            raise RuntimeError(
                f"live_server({slug!r}): server thread exited before it started listening "
                "-- check for a lifespan startup error"
            )
        try:
            with socket.create_connection(("127.0.0.1", port), timeout=0.5):
                break
        except OSError:
            time.sleep(0.1)
    else:
        settings.DATA_DIR = original_data_dir
        raise RuntimeError(f"live_server({slug!r}): server failed to start within 10 seconds")

    try:
        yield f"http://127.0.0.1:{port}"
    finally:
        server.should_exit = True
        thread.join(timeout=10.0)
        settings.DATA_DIR = original_data_dir
        if thread.is_alive():
            pytest.fail(f"live_server({slug!r}): server thread did not stop within the join timeout")
        instance = Database._instance
        if instance is not None and instance._connection is not None:
            pytest.fail(
                f"live_server({slug!r}): Database connection is still open after shutdown -- "
                "close_db() did not run (or didn't finish) during lifespan shutdown"
            )


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
    """Give every test a fresh app.db.transactions.write_lock.

    asyncio.Lock binds to whichever event loop first calls acquire() on it,
    and pytest-asyncio hands each test function its own loop (function-scoped
    by default). Without this, the second test to exercise a write endpoint
    would fail with "Lock ... is bound to a different event loop" — an
    artifact of the test runner, never reachable in production where the app
    has exactly one event loop for its entire lifetime.
    """
    from app.db import transactions

    transactions.write_lock = Lock()
    yield


@pytest.fixture(autouse=True)
def _reset_omnivoice_semaphore():
    """Give every test a fresh tts_service._omnivoice_semaphore — same event-loop-binding
    hazard as `write_lock` above (module-level asyncio primitive constructed once at
    import time, reused across pytest-asyncio's per-test event loops)."""
    from app.core.constants import MAX_CONCURRENT_TTS
    from app.services import tts_service

    tts_service._omnivoice_semaphore = Semaphore(MAX_CONCURRENT_TTS)
    yield
