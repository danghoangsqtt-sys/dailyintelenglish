"""App-level settings (Task 12.1) — currently just the Gemini API key.

Precedence: a database-stored key (set through the Settings page) always wins over
`.env`/the process environment, and takes effect immediately (no restart) by
mutating the shared `config.settings.GEMINI_API_KEY` in place — the 4 Gemini-calling
services (`script_service.py`, `learning_service.py`, `thumbnail_service.py`,
`youtube_service.py`) keep reading `settings.GEMINI_API_KEY` exactly as before and
need no changes. Clearing the stored key reverts to `config.ENV_GEMINI_API_KEY`, the
value captured once at import time before any database override could run.
"""

import logging
from datetime import datetime, timezone

import aiosqlite

from app.core import config
from app.core.constants import AI_LEGACY_MODE_ALIASES, AI_MODES
from app.core.exceptions import ValidationError

logger = logging.getLogger(__name__)

GEMINI_API_KEY_SETTING = "gemini_api_key"
AI_MODE_SETTING = "ai_mode"


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

    Caller must run this inside a `write_transaction` block (see app/api/settings.py)
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

    Caller must run this inside a `write_transaction` block, same as `set_gemini_api_key`.
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


# --- AI mode (Phase 13, ADR-001) -- same non-secret app_settings table, same
# DB-overrides-env precedence pattern as the Gemini key above, but never masked
# since it carries no secret. ------------------------------------------------


def _migrate_legacy_mode(raw_mode: str) -> str:
    """Phase 18/D21: a stored value from before Phase 18 ("gemini"/"hybrid",
    naming a specific provider) migrates to its role-based successor
    ("cloud"/"cloud_first"). Logged once per call, never raised -- an old
    install must never fail to start over this. The DB row itself is left
    as-is (not rewritten here); `set_ai_mode` already rejects the legacy
    names as new *inputs*, so this translation only ever applies to a value
    written before the migration existed."""
    if raw_mode in AI_LEGACY_MODE_ALIASES:
        migrated = AI_LEGACY_MODE_ALIASES[raw_mode]
        logger.info("ai_mode_migrated from=%s to=%s", raw_mode, migrated)
        return migrated
    return raw_mode


async def get_ai_mode_status(db: aiosqlite.Connection) -> dict:
    """Report the current effective AI_MODE and whether it's DB-stored or env-default.

    Uses `ai_mode_source` (not the bare `source` the Gemini-key status above
    uses) so the two can be merged into one `GET /api/settings` payload without
    one silently overwriting the other's `source` field.
    """
    cursor = await db.execute("SELECT value FROM app_settings WHERE key = ?", (AI_MODE_SETTING,))
    row = await cursor.fetchone()
    if row is not None:
        return {"ai_mode": _migrate_legacy_mode(row["value"]), "ai_mode_source": "database"}
    return {"ai_mode": config.settings.AI_MODE, "ai_mode_source": "env"}


async def set_ai_mode(db: aiosqlite.Connection, ai_mode: str) -> dict:
    """Validate, persist, and immediately apply a new AI_MODE.

    Caller must run this inside a `write_transaction` block, same as
    `set_gemini_api_key`.

    Raises:
        ValidationError: If `ai_mode` isn't a known mode (a legacy `gemini`/
            `hybrid` value is no longer a valid *input* -- only a stored value
            from before Phase 18 migrates, via `_migrate_legacy_mode`), or if
            it's `cloud`/`cloud_first` while cloud is disabled -- Task 14.7
            (ADR-001 A2): cloud requires the explicit `DIE_AI_ALLOW_CLOUD=true`
            env var, never just a mode change.
    """
    if ai_mode not in AI_MODES:
        raise ValidationError(f"ai_mode must be one of {AI_MODES}, got {ai_mode!r}")
    if ai_mode != "local" and not config.settings.AI_ALLOW_CLOUD:
        raise ValidationError(
            f"ai_mode {ai_mode!r} requires DIE_AI_ALLOW_CLOUD=true -- cloud is disabled "
            "by default (ADR-001 amendment A2); local is the default supported mode."
        )
    await db.execute(
        """
        INSERT INTO app_settings (key, value, updated_at) VALUES (?, ?, ?)
        ON CONFLICT(key) DO UPDATE SET value = excluded.value, updated_at = excluded.updated_at
        """,
        (AI_MODE_SETTING, ai_mode, datetime.now(timezone.utc).isoformat()),
    )
    config.settings.AI_MODE = ai_mode
    return {"ai_mode": ai_mode, "ai_mode_source": "database"}


async def load_ai_mode_from_db(db: aiosqlite.Connection) -> None:
    """Startup-time loader: apply a DB-stored AI_MODE over the env/.env default.

    Same missing-table tolerance as `load_gemini_api_key_from_db` -- called
    from the same place in app.main's lifespan, right after it.
    """
    try:
        cursor = await db.execute("SELECT value FROM app_settings WHERE key = ?", (AI_MODE_SETTING,))
        row = await cursor.fetchone()
    except aiosqlite.OperationalError:
        return
    if row is not None:
        config.settings.AI_MODE = _migrate_legacy_mode(row["value"])
