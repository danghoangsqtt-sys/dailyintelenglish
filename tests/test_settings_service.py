"""Unit tests for settings_service.py (Task 12.1).

config.settings.GEMINI_API_KEY / config.ENV_GEMINI_API_KEY are a shared,
process-wide singleton mutated in place by this service -- each test uses
monkeypatch.setattr to seed a known starting value, which pytest's monkeypatch
correctly restores at teardown even though the service reassigns the attribute
directly afterward (monkeypatch restores whatever value it originally recorded,
regardless of how the attribute changed in between).
"""

import pytest

from app.core import config
from app.core.exceptions import ValidationError
from app.services import settings_service


@pytest.fixture(autouse=True)
def _isolated_gemini_key(monkeypatch):
    monkeypatch.setattr(config.settings, "GEMINI_API_KEY", "env-fallback-key-0000")
    monkeypatch.setattr(config, "ENV_GEMINI_API_KEY", "env-fallback-key-0000")


async def test_status_reports_env_source_when_nothing_stored(db):
    status = await settings_service.get_gemini_api_key_status(db)
    assert status["source"] == "env"
    assert status["masked_key"] == "env-fa••••0000"


async def test_status_reports_none_when_no_env_and_nothing_stored(db, monkeypatch):
    monkeypatch.setattr(config.settings, "GEMINI_API_KEY", "")
    status = await settings_service.get_gemini_api_key_status(db)
    assert status == {"source": "none", "masked_key": None}


async def test_set_key_persists_and_applies_immediately(db):
    status = await settings_service.set_gemini_api_key(db, "AIzaSyRealLookingTestKey123")
    assert status["source"] == "database"
    assert status["masked_key"] == "AIzaSy••••y123"
    # Applied immediately -- no restart needed, exactly what services import and read.
    assert config.settings.GEMINI_API_KEY == "AIzaSyRealLookingTestKey123"


async def test_set_key_strips_surrounding_whitespace(db):
    status = await settings_service.set_gemini_api_key(db, "  spaced-key-value  ")
    assert config.settings.GEMINI_API_KEY == "spaced-key-value"
    assert status["masked_key"] == "spaced••••alue"


async def test_set_key_rejects_empty_or_whitespace_only(db):
    with pytest.raises(ValidationError):
        await settings_service.set_gemini_api_key(db, "   ")


async def test_set_key_overwrites_a_previously_stored_key(db):
    await settings_service.set_gemini_api_key(db, "first-stored-key-111")
    status = await settings_service.set_gemini_api_key(db, "second-stored-key-222")
    assert status["masked_key"] == "second••••-222"
    assert config.settings.GEMINI_API_KEY == "second-stored-key-222"


async def test_clear_reverts_to_original_env_value(db):
    await settings_service.set_gemini_api_key(db, "temporary-stored-key")
    assert config.settings.GEMINI_API_KEY == "temporary-stored-key"

    status = await settings_service.clear_gemini_api_key(db)

    assert config.settings.GEMINI_API_KEY == "env-fallback-key-0000"
    assert status["source"] == "env"
    assert status["masked_key"] == "env-fa••••0000"


async def test_clear_when_nothing_was_ever_stored_is_a_noop(db):
    status = await settings_service.clear_gemini_api_key(db)
    assert config.settings.GEMINI_API_KEY == "env-fallback-key-0000"
    assert status["source"] == "env"


async def test_load_from_db_applies_a_stored_key_over_the_env_default(db):
    await settings_service.set_gemini_api_key(db, "stored-before-restart")
    # Simulate a fresh process: reset the in-memory singleton back to the env value,
    # as it would be right after Settings() is constructed at import time.
    config.settings.GEMINI_API_KEY = "env-fallback-key-0000"

    await settings_service.load_gemini_api_key_from_db(db)

    assert config.settings.GEMINI_API_KEY == "stored-before-restart"


async def test_load_from_db_leaves_env_value_untouched_when_nothing_stored(db):
    await settings_service.load_gemini_api_key_from_db(db)
    assert config.settings.GEMINI_API_KEY == "env-fallback-key-0000"


def test_mask_fully_masks_short_keys():
    from app.services.settings_service import _mask

    assert _mask("short") == "•••••"
    assert _mask("1234567890") == "•" * 10


def test_mask_shows_prefix_and_suffix_for_longer_keys():
    from app.services.settings_service import _mask

    assert _mask("AIzaSyABCDEFGHIJKLMNOP1234") == "AIzaSy••••1234"


# --- AI mode (Task 13.6) --------------------------------------------------------------


@pytest.fixture(autouse=True)
def _isolated_ai_mode(monkeypatch):
    monkeypatch.setattr(config.settings, "AI_MODE", "cloud")


@pytest.fixture(autouse=True)
def _isolated_ai_allow_cloud(monkeypatch):
    """Task 14.7: matches the real default (`False`) unless a test explicitly
    opts in -- `set_ai_mode` now rejects `cloud`/`cloud_first` without this."""
    monkeypatch.setattr(config.settings, "AI_ALLOW_CLOUD", False)


async def test_ai_mode_status_reports_env_default_when_nothing_stored(db):
    status = await settings_service.get_ai_mode_status(db)
    assert status == {"ai_mode": "cloud", "ai_mode_source": "env"}


async def test_set_ai_mode_persists_and_applies_immediately(db, monkeypatch):
    monkeypatch.setattr(config.settings, "AI_ALLOW_CLOUD", True)
    status = await settings_service.set_ai_mode(db, "cloud_first")
    assert status == {"ai_mode": "cloud_first", "ai_mode_source": "database"}
    assert config.settings.AI_MODE == "cloud_first"

    reloaded = await settings_service.get_ai_mode_status(db)
    assert reloaded == {"ai_mode": "cloud_first", "ai_mode_source": "database"}


async def test_set_ai_mode_rejects_an_unknown_value(db):
    with pytest.raises(ValidationError, match="ai_mode must be one of"):
        await settings_service.set_ai_mode(db, "not_a_real_mode")


# --- Task 14.7: cloud gate (ADR-001 A2) -------------------------------------------------


async def test_set_ai_mode_rejects_cloud_without_allow_cloud(db):
    with pytest.raises(ValidationError, match="DIE_AI_ALLOW_CLOUD"):
        await settings_service.set_ai_mode(db, "cloud")


async def test_set_ai_mode_rejects_cloud_first_without_allow_cloud(db):
    with pytest.raises(ValidationError, match="DIE_AI_ALLOW_CLOUD"):
        await settings_service.set_ai_mode(db, "cloud_first")


async def test_set_ai_mode_accepts_cloud_when_allow_cloud_is_true(db, monkeypatch):
    monkeypatch.setattr(config.settings, "AI_ALLOW_CLOUD", True)
    status = await settings_service.set_ai_mode(db, "cloud")
    assert status["ai_mode"] == "cloud"


async def test_set_ai_mode_accepts_local_regardless_of_allow_cloud(db):
    # AI_ALLOW_CLOUD is False by default (see _isolated_ai_allow_cloud) -- local
    # is never gated, it's the only supported mode.
    status = await settings_service.set_ai_mode(db, "local")
    assert status["ai_mode"] == "local"


async def test_set_ai_mode_rejects_legacy_gemini_and_hybrid_as_new_input_values(db, monkeypatch):
    """Phase 18 (was test_set_ai_mode_rejects_gemini_without_allow_cloud/
    ..._rejects_hybrid_without_allow_cloud): "gemini"/"hybrid" are no longer
    valid *inputs* to `set_ai_mode` at all -- only a value already stored from
    before Phase 18 migrates on read (see the migration tests below). Both
    still raise as before, but now because they're not in AI_MODES, not
    because of the allow_cloud gate -- asserted with AI_ALLOW_CLOUD=true to
    prove the gate isn't what's rejecting them."""
    monkeypatch.setattr(config.settings, "AI_ALLOW_CLOUD", True)
    for legacy_mode in ("gemini", "hybrid"):
        with pytest.raises(ValidationError, match="ai_mode must be one of"):
            await settings_service.set_ai_mode(db, legacy_mode)


async def test_load_ai_mode_from_db_applies_a_stored_value(db):
    await settings_service.set_ai_mode(db, "local")
    config.settings.AI_MODE = "cloud"  # simulate a fresh process before the loader runs

    await settings_service.load_ai_mode_from_db(db)

    assert config.settings.AI_MODE == "local"


async def test_load_ai_mode_from_db_leaves_env_value_untouched_when_nothing_stored(db):
    await settings_service.load_ai_mode_from_db(db)
    assert config.settings.AI_MODE == "cloud"


# --- Phase 18: legacy ai_mode migration (gemini->cloud, hybrid->cloud_first) ------------


async def _seed_legacy_ai_mode_value(db, value: str) -> None:
    """Simulates an `app_settings` row persisted before Phase 18's mode
    migration existed -- bypasses `set_ai_mode`'s own validation (which now
    rejects "gemini"/"hybrid" as new inputs) by writing directly, matching
    exactly how a real pre-Phase-18 install's already-stored row looks."""
    from datetime import datetime, timezone

    await db.execute(
        """
        INSERT INTO app_settings (key, value, updated_at) VALUES (?, ?, ?)
        ON CONFLICT(key) DO UPDATE SET value = excluded.value, updated_at = excluded.updated_at
        """,
        (settings_service.AI_MODE_SETTING, value, datetime.now(timezone.utc).isoformat()),
    )
    await db.commit()


async def test_get_ai_mode_status_migrates_a_legacy_gemini_value_stored_in_the_db(db):
    await _seed_legacy_ai_mode_value(db, "gemini")

    status = await settings_service.get_ai_mode_status(db)

    assert status == {"ai_mode": "cloud", "ai_mode_source": "database"}


async def test_get_ai_mode_status_migrates_a_legacy_hybrid_value_stored_in_the_db(db):
    await _seed_legacy_ai_mode_value(db, "hybrid")

    status = await settings_service.get_ai_mode_status(db)

    assert status == {"ai_mode": "cloud_first", "ai_mode_source": "database"}


async def test_load_ai_mode_from_db_migrates_a_legacy_stored_value(db):
    await _seed_legacy_ai_mode_value(db, "hybrid")
    config.settings.AI_MODE = "local"  # simulate a fresh process before the loader runs

    await settings_service.load_ai_mode_from_db(db)

    assert config.settings.AI_MODE == "cloud_first"


async def test_ai_mode_migration_is_logged(db, caplog):
    """"Log it once, never raise" (plan Amendment A/point 5's ruling on
    required behaviour 5) -- confirmed here for the DB-stored read path;
    config.py's mirror-image env-sourced migration (module-level code that
    runs once at import time) is verified by code review instead of an
    automated test, since reloading app.core.config to re-exercise it would
    replace the shared `settings` singleton object mid-test-session for every
    other already-imported module that did `from app.core.config import
    settings` -- an unsafe, cross-test-polluting operation in this
    shared-process suite, not a safe thing to do even in one isolated test."""
    await _seed_legacy_ai_mode_value(db, "gemini")

    with caplog.at_level("INFO", logger="app.services.settings_service"):
        await settings_service.get_ai_mode_status(db)

    migration_lines = [r.getMessage() for r in caplog.records if "ai_mode_migrated" in r.getMessage()]
    assert len(migration_lines) == 1
    assert "from=gemini" in migration_lines[0]
    assert "to=cloud" in migration_lines[0]
