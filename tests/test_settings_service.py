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
