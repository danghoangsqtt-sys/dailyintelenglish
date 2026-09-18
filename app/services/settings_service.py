"""App-level settings (Task 12.1) — currently just the Gemini API key.

Precedence: a database-stored key (set through the Settings page) always wins over
`.env`/the process environment, and takes effect immediately (no restart) by
mutating the shared `config.settings.GEMINI_API_KEY` in place — the 4 Gemini-calling
services (`script_service.py`, `learning_service.py`, `thumbnail_service.py`,
`youtube_service.py`) keep reading `settings.GEMINI_API_KEY` exactly as before and
need no changes. Clearing the stored key reverts to `config.ENV_GEMINI_API_KEY`, the
value captured once at import time before any database override could run.
"""

from datetime import datetime, timezone

import aiosqlite

from app.core import config
from app.core.exceptions import ValidationError

GEMINI_API_KEY_SETTING = "gemini_api_key"


def _mask(raw_key: str) -> str:
    """Mask a secret for display: first 6 + last 4 chars, `••••` between.

    Short keys (<= 10 chars, shorter than the visible prefix+suffix) are fully
    masked instead of accidentally revealing the whole thing.
    """
    if len(raw_key) <= 10:
        return "•" * len(raw_key)
    return f"{raw_key[:6]}••••{raw_key[-4:]}"


async def _stored_key(db: aiosqlite.Connection) -> str | None:
    """Return the raw DB-stored key, or None if no row exists."""
    cursor = await db.execute(
        "SELECT value FROM app_settings WHERE key = ?", (GEMINI_API_KEY_SETTING,)
    )
    row = await cursor.fetchone()
    return row["value"] if row is not None else None


async def get_gemini_api_key_status(db: aiosqlite.Connection) -> dict:
    """Report the current key's source and a masked preview -- never the raw value."""
    stored = await _stored_key(db)
    if stored:
        return {"source": "database", "masked_key": _mask(stored)}
    if config.settings.GEMINI_API_KEY:
        return {"source": "env", "masked_key": _mask(config.settings.GEMINI_API_KEY)}
    return {"source": "none", "masked_key": None}


async def set_gemini_api_key(db: aiosqlite.Connection, raw_key: str) -> dict:
    """Validate, persist, and immediately apply a new Gemini API key.

    Caller must run this inside a `_write_transaction` block (see app/api/settings.py)
    so the upsert is committed the same way every other write in this app is.
    """
    cleaned = raw_key.strip()
    if not cleaned:
        raise ValidationError("API key cannot be empty.")
    await db.execute(
        """
        INSERT INTO app_settings (key, value, updated_at) VALUES (?, ?, ?)
        ON CONFLICT(key) DO UPDATE SET value = excluded.value, updated_at = excluded.updated_at
        """,
        (GEMINI_API_KEY_SETTING, cleaned, datetime.now(timezone.utc).isoformat()),
    )
    config.settings.GEMINI_API_KEY = cleaned
    return {"source": "database", "masked_key": _mask(cleaned)}


async def clear_gemini_api_key(db: aiosqlite.Connection) -> dict:
    """Remove the DB-stored key and revert to the original .env/environment value.

    Caller must run this inside a `_write_transaction` block, same as `set_gemini_api_key`.
    """
    await db.execute(
        "DELETE FROM app_settings WHERE key = ?", (GEMINI_API_KEY_SETTING,)
    )
    config.settings.GEMINI_API_KEY = config.ENV_GEMINI_API_KEY
    return await get_gemini_api_key_status(db)


async def load_gemini_api_key_from_db(db: aiosqlite.Connection) -> None:
    """Startup-time loader: apply a DB-stored key over the .env-sourced default.

    Called once from app.main's lifespan, after init_db() has run the
    004_app_settings.sql migration. A missing table (e.g. a test DB that never ran
    migrations) is treated the same as "no stored key" rather than crashing startup.
    """
    try:
        stored = await _stored_key(db)
    except aiosqlite.OperationalError:
        return
    if stored:
        config.settings.GEMINI_API_KEY = stored
