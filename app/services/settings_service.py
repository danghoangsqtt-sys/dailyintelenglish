"""App-level settings (Task 12.1; Task 18.3 cloud provider settings).

Precedence: a database-stored value (set through the Settings page) always wins
over `.env`/the process environment, and takes effect immediately (no restart) by
mutating the shared `config.settings.*` fields in place -- the router builder
(`app.services.ai.router.build_ai_router_from_settings`, called fresh on every job
dispatch by `app.main._build_ai_router`) already reads `settings.*` live, so no
separate propagation mechanism is needed here.
"""

import logging
from datetime import datetime, timezone

import aiosqlite

from app.core import config
from app.core.constants import AI_LEGACY_MODE_ALIASES, AI_MODES
from app.core.exceptions import ProviderError, ValidationError
from app.services.ai.contracts import GenerationRequest
from app.services.ai.openai_compat_provider import OpenAICompatProvider, validate_openai_compat_base_url

logger = logging.getLogger(__name__)

AI_MODE_SETTING = "ai_mode"
CLOUD_BASE_URL_SETTING = "openai_compat_base_url"
CLOUD_MODEL_SETTING = "openai_compat_model"
CLOUD_API_KEY_SETTING = "openai_compat_api_key"

_CLOUD_MODEL_MAX_LENGTH = 200
_TEST_CONNECTION_TIMEOUT_SECONDS = 15.0


async def _stored_value(db: aiosqlite.Connection, key: str) -> str | None:
    """Return one raw DB-stored `app_settings` value, or `None` if no row exists."""
    cursor = await db.execute("SELECT value FROM app_settings WHERE key = ?", (key,))
    row = await cursor.fetchone()
    return row["value"] if row is not None else None


async def _upsert_value(db: aiosqlite.Connection, key: str, value: str) -> None:
    await db.execute(
        """
        INSERT INTO app_settings (key, value, updated_at) VALUES (?, ?, ?)
        ON CONFLICT(key) DO UPDATE SET value = excluded.value, updated_at = excluded.updated_at
        """,
        (key, value, datetime.now(timezone.utc).isoformat()),
    )


# --- Cloud provider settings (Task 18.3, D22-D24) --------------------------------------


def _last4(key: str) -> str:
    """Mask a secret to its last 4 characters only -- no prefix (unlike the old
    Gemini `_mask()`'s 6-char-prefix format, retired with it), matching the
    plan's literal `{set, last4, source}` status shape."""
    if len(key) <= 4:
        return "•" * len(key)
    return "•" * (len(key) - 4) + key[-4:]


async def get_cloud_settings_status(db: aiosqlite.Connection) -> dict:
    """Report the cloud provider's current configuration -- never the raw key.

    `base_url`/`model` aren't secret, returned in full; only the key is masked.
    """
    stored_key = await _stored_value(db, CLOUD_API_KEY_SETTING)
    if stored_key:
        cloud_source = "database"
        effective_key = stored_key
    elif config.settings.OPENAI_COMPAT_API_KEY:
        cloud_source = "env"
        effective_key = config.settings.OPENAI_COMPAT_API_KEY
    else:
        cloud_source = "none"
        effective_key = ""
    return {
        "cloud_configured": bool(effective_key) and bool(config.settings.OPENAI_COMPAT_MODEL),
        "cloud_last4": _last4(effective_key) if effective_key else None,
        "cloud_source": cloud_source,
        "cloud_base_url": config.settings.OPENAI_COMPAT_BASE_URL,
        "cloud_model": config.settings.OPENAI_COMPAT_MODEL,
    }


async def set_cloud_settings(
    db: aiosqlite.Connection, base_url: str, model: str, api_key: str | None = None
) -> dict:
    """Validate, persist, and immediately apply the cloud provider's base URL,
    model, and (optionally) API key.

    Caller must run this inside a `write_transaction` block, same as `set_ai_mode`.

    Args:
        api_key: `None` means "leave the stored key unchanged" -- lets a caller
            update just the base URL or model without re-entering a write-only
            key. An empty/whitespace-only string is rejected (distinct from
            `None`), same as a missing base_url/model.

    Raises:
        ValidationError: If `base_url` fails `validate_openai_compat_base_url`
            (PM review C2: https-or-loopback, no credentials), `model` is empty
            after stripping or over 200 characters, or a provided `api_key` is
            empty after stripping. Nothing is written on any of these --
            validation runs fully before the first database write.
    """
    cleaned_model = model.strip()
    if not cleaned_model:
        raise ValidationError("Cloud model cannot be empty.")
    if len(cleaned_model) > _CLOUD_MODEL_MAX_LENGTH:
        raise ValidationError(f"Cloud model must be at most {_CLOUD_MODEL_MAX_LENGTH} characters.")
    try:
        cleaned_base_url = validate_openai_compat_base_url(base_url)
    except ValueError as exc:
        raise ValidationError(str(exc)) from exc
    cleaned_key: str | None = None
    if api_key is not None:
        cleaned_key = api_key.strip()
        if not cleaned_key:
            raise ValidationError("Cloud API key cannot be empty.")

    await _upsert_value(db, CLOUD_BASE_URL_SETTING, cleaned_base_url)
    await _upsert_value(db, CLOUD_MODEL_SETTING, cleaned_model)
    config.settings.OPENAI_COMPAT_BASE_URL = cleaned_base_url
    config.settings.OPENAI_COMPAT_MODEL = cleaned_model
    if cleaned_key is not None:
        await _upsert_value(db, CLOUD_API_KEY_SETTING, cleaned_key)
        config.settings.OPENAI_COMPAT_API_KEY = cleaned_key

    return await get_cloud_settings_status(db)


async def clear_cloud_api_key(db: aiosqlite.Connection) -> dict:
    """Remove the DB-stored key and revert to the original .env/environment value.

    Caller must run this inside a `write_transaction` block, same as `set_cloud_settings`.
    """
    await db.execute("DELETE FROM app_settings WHERE key = ?", (CLOUD_API_KEY_SETTING,))
    config.settings.OPENAI_COMPAT_API_KEY = config.ENV_OPENAI_COMPAT_API_KEY
    return await get_cloud_settings_status(db)


async def load_cloud_settings_from_db(db: aiosqlite.Connection) -> None:
    """Startup-time loader: apply any DB-stored cloud settings over the
    .env-sourced defaults. Same missing-table tolerance as `load_ai_mode_from_db`.
    """
    try:
        stored_base_url = await _stored_value(db, CLOUD_BASE_URL_SETTING)
        stored_model = await _stored_value(db, CLOUD_MODEL_SETTING)
        stored_key = await _stored_value(db, CLOUD_API_KEY_SETTING)
    except aiosqlite.OperationalError:
        return
    if stored_base_url:
        config.settings.OPENAI_COMPAT_BASE_URL = stored_base_url
    if stored_model:
        config.settings.OPENAI_COMPAT_MODEL = stored_model
    if stored_key:
        config.settings.OPENAI_COMPAT_API_KEY = stored_key


async def test_cloud_connection(
    base_url: str | None, model: str | None, api_key: str | None
) -> dict:
    """One real, tiny probe call through `OpenAICompatProvider` -- never persists
    anything. Any argument left `None` falls back to the currently *effective*
    `settings.OPENAI_COMPAT_*` value, so a caller can test "does my saved key
    still work with this new model" without retyping the key.

    Returns `{"ok": True}` on success, or `{"ok": False, "error":
    "<ProviderError subclass name>", "status": <int | None>}` on failure --
    never the key, never a response body/message (PM review C1: `status` is
    `OpenAICompatProvider`'s own structured `upstream_status` attribute, not a
    parsed message string).
    """
    effective_base_url = base_url if base_url is not None else config.settings.OPENAI_COMPAT_BASE_URL
    effective_model = model if model is not None else config.settings.OPENAI_COMPAT_MODEL
    effective_key = api_key if api_key is not None else config.settings.OPENAI_COMPAT_API_KEY

    try:
        provider = OpenAICompatProvider(
            base_url=effective_base_url,
            api_key=effective_key,
            model=effective_model,
            timeout=_TEST_CONNECTION_TIMEOUT_SECONDS,
        )
    except ValueError as exc:
        return {"ok": False, "error": type(exc).__name__, "status": None}

    request = GenerationRequest(
        prompt="Reply with the single word: ok.",
        deadline_seconds=_TEST_CONNECTION_TIMEOUT_SECONDS,
        purpose="settings_test_connection",
    )
    try:
        await provider.generate(request)
    except ProviderError as exc:
        return {"ok": False, "error": type(exc).__name__, "status": getattr(exc, "upstream_status", None)}
    return {"ok": True}


def compute_effective_mode_and_reason(ai_mode: str) -> tuple[str, str | None]:
    """PM review C3: explains *why* the effective mode differs from the
    selected/stored one, when it does. Reuses `router.compute_effective_mode`
    for the actual collapse decision (reading real `settings.*` values
    server-side only) -- returns just the resulting mode name and a
    human-readable reason string, never any key material."""
    from app.services.ai.contracts import AIMode
    from app.services.ai.router import compute_effective_mode

    configured = AIMode(ai_mode)
    effective = compute_effective_mode(
        configured,
        config.settings.AI_ALLOW_CLOUD,
        config.settings.OPENAI_COMPAT_API_KEY,
        config.settings.OPENAI_COMPAT_MODEL,
    )
    if effective is configured:
        return effective.value, None
    if not config.settings.AI_ALLOW_CLOUD:
        return effective.value, "cloud disabled by DIE_AI_ALLOW_CLOUD"
    return effective.value, "no API key configured"


# --- AI mode (Phase 13, ADR-001) -- same non-secret app_settings table, same
# DB-overrides-env precedence pattern as the cloud settings above, but never
# masked since it carries no secret. --------------------------------------


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

    Uses `ai_mode_source` (not a bare `source`) so this can be merged into one
    `GET /api/settings` payload without colliding with the cloud status's own
    `cloud_source` field.
    """
    cursor = await db.execute("SELECT value FROM app_settings WHERE key = ?", (AI_MODE_SETTING,))
    row = await cursor.fetchone()
    if row is not None:
        return {"ai_mode": _migrate_legacy_mode(row["value"]), "ai_mode_source": "database"}
    return {"ai_mode": config.settings.AI_MODE, "ai_mode_source": "env"}


async def set_ai_mode(db: aiosqlite.Connection, ai_mode: str) -> dict:
    """Validate, persist, and immediately apply a new AI_MODE.

    Caller must run this inside a `write_transaction` block, same as
    `set_cloud_settings`.

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
    await _upsert_value(db, AI_MODE_SETTING, ai_mode)
    config.settings.AI_MODE = ai_mode
    return {"ai_mode": ai_mode, "ai_mode_source": "database"}


async def load_ai_mode_from_db(db: aiosqlite.Connection) -> None:
    """Startup-time loader: apply a DB-stored AI_MODE over the env/.env default.

    Same missing-table tolerance as `load_cloud_settings_from_db` -- called
    from the same place in app.main's lifespan, right after it.
    """
    try:
        cursor = await db.execute("SELECT value FROM app_settings WHERE key = ?", (AI_MODE_SETTING,))
        row = await cursor.fetchone()
    except aiosqlite.OperationalError:
        return
    if row is not None:
        config.settings.AI_MODE = _migrate_legacy_mode(row["value"])
