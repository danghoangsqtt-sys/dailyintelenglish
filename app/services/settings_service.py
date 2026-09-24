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
from app.services.ai.openai_compat_provider import (
    OpenAICompatProvider,
    parse_fallback_models,
    validate_openai_compat_base_url,
)

logger = logging.getLogger(__name__)

AI_MODE_SETTING = "ai_mode"
CLOUD_BASE_URL_SETTING = "openai_compat_base_url"
CLOUD_MODEL_SETTING = "openai_compat_model"
CLOUD_API_KEY_SETTING = "openai_compat_api_key"
CLOUD_FALLBACK_MODELS_SETTING = "openai_compat_fallback_models"

# Task 18.8 (D28): new `app_settings` keys, deliberately prefixed `cloud_provider_`
# -- distinct from any pre-18.3 legacy `gemini_api_key` row a very old install might
# still carry (18.3 explicitly left that stale row "ignored and never migrated");
# reusing that exact key name here would have made a years-old, forgotten key spring
# back to life on upgrade, which nothing about this task asks for.
ZEN_BASE_URL_SETTING = "cloud_provider_opencode_zen_base_url"
ZEN_MODEL_SETTING = "cloud_provider_opencode_zen_model"
ZEN_API_KEY_SETTING = "cloud_provider_opencode_zen_api_key"
GEMINI_BASE_URL_SETTING = "cloud_provider_gemini_base_url"
GEMINI_MODELS_SETTING = "cloud_provider_gemini_models"
# Named GEMINI_CLOUD_API_KEY_SETTING, not GEMINI_API_KEY_SETTING -- the latter name
# was deleted by Task 18.3 (test_old_gemini_key_functions_are_gone asserts it's
# absent); reusing it here would silently break that regression guard.
GEMINI_CLOUD_API_KEY_SETTING = "cloud_provider_gemini_api_key"
CLOUD_PROVIDER_ORDER_SETTING = "cloud_provider_order"

_CLOUD_MODEL_MAX_LENGTH = 200
_CLOUD_FALLBACK_MODELS_MAX_ENTRIES = 5
_KNOWN_CLOUD_PROVIDER_NAMES = ("openrouter", "opencode-zen", "gemini")
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
        "cloud_fallback_models": parse_fallback_models(config.settings.OPENAI_COMPAT_FALLBACK_MODELS),
    }


async def set_cloud_settings(
    db: aiosqlite.Connection,
    base_url: str,
    model: str,
    api_key: str | None = None,
    fallback_models: list[str] | None = None,
) -> dict:
    """Validate, persist, and immediately apply the cloud provider's base URL,
    model, (optionally) API key, and (optionally) fallback model chain.

    Caller must run this inside a `write_transaction` block, same as `set_ai_mode`.

    Args:
        api_key: `None` means "leave the stored key unchanged" -- lets a caller
            update just the base URL or model without re-entering a write-only
            key. An empty/whitespace-only string is rejected (distinct from
            `None`), same as a missing base_url/model.
        fallback_models: Task 18.6 (D27). `None` means "leave the stored chain
            unchanged" (same convention as `api_key`); `[]` explicitly clears
            it to "primary model only" -- a legitimate value, distinct from
            `None`.

    Raises:
        ValidationError: If `base_url` fails `validate_openai_compat_base_url`
            (PM review C2: https-or-loopback, no credentials), `model` is empty
            after stripping or over 200 characters, a provided `api_key` is
            empty after stripping, or a provided `fallback_models` has more
            than 5 entries or any entry that's empty after stripping or over
            200 characters. Nothing is written on any of these -- validation
            runs fully before the first database write.
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
    cleaned_fallback_models: list[str] | None = None
    if fallback_models is not None:
        cleaned_fallback_models = [entry.strip() for entry in fallback_models]
        if len(cleaned_fallback_models) > _CLOUD_FALLBACK_MODELS_MAX_ENTRIES:
            raise ValidationError(
                f"Cloud fallback chain must have at most {_CLOUD_FALLBACK_MODELS_MAX_ENTRIES} entries."
            )
        for entry in cleaned_fallback_models:
            if not entry:
                raise ValidationError("Cloud fallback model entries cannot be empty.")
            if len(entry) > _CLOUD_MODEL_MAX_LENGTH:
                raise ValidationError(f"Each cloud fallback model must be at most {_CLOUD_MODEL_MAX_LENGTH} characters.")

    await _upsert_value(db, CLOUD_BASE_URL_SETTING, cleaned_base_url)
    await _upsert_value(db, CLOUD_MODEL_SETTING, cleaned_model)
    config.settings.OPENAI_COMPAT_BASE_URL = cleaned_base_url
    config.settings.OPENAI_COMPAT_MODEL = cleaned_model
    if cleaned_key is not None:
        await _upsert_value(db, CLOUD_API_KEY_SETTING, cleaned_key)
        config.settings.OPENAI_COMPAT_API_KEY = cleaned_key
    if cleaned_fallback_models is not None:
        await _upsert_value(db, CLOUD_FALLBACK_MODELS_SETTING, ",".join(cleaned_fallback_models))
        config.settings.OPENAI_COMPAT_FALLBACK_MODELS = ",".join(cleaned_fallback_models)

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
        stored_fallback_models = await _stored_value(db, CLOUD_FALLBACK_MODELS_SETTING)
    except aiosqlite.OperationalError:
        return
    if stored_base_url:
        config.settings.OPENAI_COMPAT_BASE_URL = stored_base_url
    if stored_model:
        config.settings.OPENAI_COMPAT_MODEL = stored_model
    if stored_key:
        config.settings.OPENAI_COMPAT_API_KEY = stored_key
    # Unlike base_url/model/key above, an explicitly-cleared fallback chain is
    # legitimately stored as "" (set_cloud_settings([]) -- "primary only") --
    # `is not None` (row exists at all) rather than truthiness, so that clear
    # survives a restart instead of silently reverting to the .env default.
    if stored_fallback_models is not None:
        config.settings.OPENAI_COMPAT_FALLBACK_MODELS = stored_fallback_models


# --- Task 18.8 (D28): the multi-provider chain -- OpenCode Zen + Gemini + order ---------


def _last4_or_none(key: str) -> str | None:
    return _last4(key) if key else None


async def get_provider_chain_status(db: aiosqlite.Connection) -> dict:
    """Report OpenCode Zen's and Gemini's current configuration (never a raw
    key) plus the stored dispatch order -- the sibling of `get_cloud_settings_
    status` above, which already covers openrouter. Kept separate rather than
    merged into one payload since the two were built in different tasks and
    the API layer merges them into one `GET /api/settings` response anyway."""
    zen_key = config.settings.OPENCODE_ZEN_API_KEY
    gemini_key = config.settings.GEMINI_API_KEY
    return {
        "cloud_provider_order": parse_fallback_models(config.settings.CLOUD_PROVIDER_ORDER),
        "opencode_zen": {
            "configured": bool(zen_key and config.settings.OPENCODE_ZEN_MODEL),
            "base_url": config.settings.OPENCODE_ZEN_BASE_URL,
            "model": config.settings.OPENCODE_ZEN_MODEL,
            "key_last4": _last4_or_none(zen_key),
        },
        "gemini": {
            "configured": bool(gemini_key and config.settings.GEMINI_MODELS),
            "base_url": config.settings.GEMINI_BASE_URL,
            "models": parse_fallback_models(config.settings.GEMINI_MODELS),
            "key_last4": _last4_or_none(gemini_key),
        },
    }


async def set_opencode_zen_settings(
    db: aiosqlite.Connection, base_url: str, model: str, api_key: str | None = None
) -> dict:
    """Validate, persist, and immediately apply OpenCode Zen's base URL, model,
    and (optionally) API key -- same shape/validation as `set_cloud_settings`
    (openrouter), reused via the same helpers.

    Caller must run this inside a `write_transaction` block.
    """
    cleaned_model = model.strip()
    if not cleaned_model:
        raise ValidationError("OpenCode Zen model cannot be empty.")
    if len(cleaned_model) > _CLOUD_MODEL_MAX_LENGTH:
        raise ValidationError(f"OpenCode Zen model must be at most {_CLOUD_MODEL_MAX_LENGTH} characters.")
    try:
        cleaned_base_url = validate_openai_compat_base_url(base_url)
    except ValueError as exc:
        raise ValidationError(str(exc)) from exc
    cleaned_key: str | None = None
    if api_key is not None:
        cleaned_key = api_key.strip()
        if not cleaned_key:
            raise ValidationError("OpenCode Zen API key cannot be empty.")

    await _upsert_value(db, ZEN_BASE_URL_SETTING, cleaned_base_url)
    await _upsert_value(db, ZEN_MODEL_SETTING, cleaned_model)
    config.settings.OPENCODE_ZEN_BASE_URL = cleaned_base_url
    config.settings.OPENCODE_ZEN_MODEL = cleaned_model
    if cleaned_key is not None:
        await _upsert_value(db, ZEN_API_KEY_SETTING, cleaned_key)
        config.settings.OPENCODE_ZEN_API_KEY = cleaned_key

    return (await get_provider_chain_status(db))["opencode_zen"]


async def clear_opencode_zen_api_key(db: aiosqlite.Connection) -> dict:
    """Remove the DB-stored Zen key and revert to the original .env/environment value."""
    await db.execute("DELETE FROM app_settings WHERE key = ?", (ZEN_API_KEY_SETTING,))
    config.settings.OPENCODE_ZEN_API_KEY = config.ENV_OPENCODE_ZEN_API_KEY
    return (await get_provider_chain_status(db))["opencode_zen"]


async def set_gemini_settings(
    db: aiosqlite.Connection, base_url: str, models: list[str] | None, api_key: str | None = None
) -> dict:
    """Validate, persist, and immediately apply Gemini's base URL, model chain,
    and (optionally) API key. `models` follows the exact same `None`-means-
    unchanged / `[]`-means-explicitly-cleared / validated-≤5-entries-≤200-chars
    convention as `set_cloud_settings`'s `fallback_models` (Task 18.6) -- Gemini
    dispatches each configured model as its own chain entry with its own
    circuit (Amendment F), so an empty list here means "no Gemini entries at
    all," not "use some default."

    Caller must run this inside a `write_transaction` block.
    """
    try:
        cleaned_base_url = validate_openai_compat_base_url(base_url)
    except ValueError as exc:
        raise ValidationError(str(exc)) from exc
    cleaned_key: str | None = None
    if api_key is not None:
        cleaned_key = api_key.strip()
        if not cleaned_key:
            raise ValidationError("Gemini API key cannot be empty.")
    cleaned_models: list[str] | None = None
    if models is not None:
        cleaned_models = [entry.strip() for entry in models]
        if len(cleaned_models) > _CLOUD_FALLBACK_MODELS_MAX_ENTRIES:
            raise ValidationError(f"Gemini model list must have at most {_CLOUD_FALLBACK_MODELS_MAX_ENTRIES} entries.")
        for entry in cleaned_models:
            if not entry:
                raise ValidationError("Gemini model entries cannot be empty.")
            if len(entry) > _CLOUD_MODEL_MAX_LENGTH:
                raise ValidationError(f"Each Gemini model must be at most {_CLOUD_MODEL_MAX_LENGTH} characters.")

    await _upsert_value(db, GEMINI_BASE_URL_SETTING, cleaned_base_url)
    config.settings.GEMINI_BASE_URL = cleaned_base_url
    if cleaned_key is not None:
        await _upsert_value(db, GEMINI_CLOUD_API_KEY_SETTING, cleaned_key)
        config.settings.GEMINI_API_KEY = cleaned_key
    if cleaned_models is not None:
        await _upsert_value(db, GEMINI_MODELS_SETTING, ",".join(cleaned_models))
        config.settings.GEMINI_MODELS = ",".join(cleaned_models)

    return (await get_provider_chain_status(db))["gemini"]


async def clear_gemini_cloud_api_key(db: aiosqlite.Connection) -> dict:
    """Remove the DB-stored Gemini key and revert to the original .env/environment
    value. Named `..._cloud_...` (not `clear_gemini_api_key`) -- that name is
    the one Task 18.3 deleted."""
    await db.execute("DELETE FROM app_settings WHERE key = ?", (GEMINI_CLOUD_API_KEY_SETTING,))
    config.settings.GEMINI_API_KEY = config.ENV_GEMINI_API_KEY
    return (await get_provider_chain_status(db))["gemini"]


async def set_cloud_provider_order(db: aiosqlite.Connection, order: list[str]) -> dict:
    """Validate, persist, and immediately apply the cloud dispatch order.

    Raises:
        ValidationError: If `order` contains an unknown provider name, or a
            duplicate. An empty list is allowed (every provider effectively
            disabled, cloud collapses to local via `compute_effective_mode`).
    """
    cleaned = [entry.strip() for entry in order]
    for entry in cleaned:
        if entry not in _KNOWN_CLOUD_PROVIDER_NAMES:
            raise ValidationError(f"Unknown cloud provider {entry!r}; must be one of {_KNOWN_CLOUD_PROVIDER_NAMES}.")
    if len(set(cleaned)) != len(cleaned):
        raise ValidationError("cloud_provider_order cannot contain duplicates.")

    await _upsert_value(db, CLOUD_PROVIDER_ORDER_SETTING, ",".join(cleaned))
    config.settings.CLOUD_PROVIDER_ORDER = ",".join(cleaned)
    return {"cloud_provider_order": cleaned}


async def load_provider_chain_from_db(db: aiosqlite.Connection) -> None:
    """Startup-time loader: apply any DB-stored Zen/Gemini/order settings over
    the .env-sourced defaults. Same missing-table tolerance and `is not None`
    (not truthiness, for the two comma-list fields that can be legitimately
    empty) pattern as `load_cloud_settings_from_db`."""
    try:
        stored_zen_base_url = await _stored_value(db, ZEN_BASE_URL_SETTING)
        stored_zen_model = await _stored_value(db, ZEN_MODEL_SETTING)
        stored_zen_key = await _stored_value(db, ZEN_API_KEY_SETTING)
        stored_gemini_base_url = await _stored_value(db, GEMINI_BASE_URL_SETTING)
        stored_gemini_models = await _stored_value(db, GEMINI_MODELS_SETTING)
        stored_gemini_key = await _stored_value(db, GEMINI_CLOUD_API_KEY_SETTING)
        stored_order = await _stored_value(db, CLOUD_PROVIDER_ORDER_SETTING)
    except aiosqlite.OperationalError:
        return
    if stored_zen_base_url:
        config.settings.OPENCODE_ZEN_BASE_URL = stored_zen_base_url
    if stored_zen_model:
        config.settings.OPENCODE_ZEN_MODEL = stored_zen_model
    if stored_zen_key:
        config.settings.OPENCODE_ZEN_API_KEY = stored_zen_key
    if stored_gemini_base_url:
        config.settings.GEMINI_BASE_URL = stored_gemini_base_url
    if stored_gemini_models is not None:
        config.settings.GEMINI_MODELS = stored_gemini_models
    if stored_gemini_key:
        config.settings.GEMINI_API_KEY = stored_gemini_key
    if stored_order is not None:
        config.settings.CLOUD_PROVIDER_ORDER = stored_order


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
    from app.services.ai.router import _configured_chain_entry_names, compute_effective_mode

    configured = AIMode(ai_mode)
    any_provider_configured = bool(_configured_chain_entry_names(config.settings))
    effective = compute_effective_mode(configured, config.settings.AI_ALLOW_CLOUD, any_provider_configured)
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
