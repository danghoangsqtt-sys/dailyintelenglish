"""Unit tests for settings_service.py (Task 12.1; Task 18.3 cloud settings).

config.settings.OPENAI_COMPAT_API_KEY / config.ENV_OPENAI_COMPAT_API_KEY are a
shared, process-wide singleton mutated in place by this service -- each test
uses monkeypatch.setattr to seed a known starting value, which pytest's
monkeypatch correctly restores at teardown even though the service reassigns
the attribute directly afterward (monkeypatch restores whatever value it
originally recorded, regardless of how the attribute changed in between).

The old Gemini-key settings surface (`get_gemini_api_key_status`,
`set_gemini_api_key`, `clear_gemini_api_key`, `load_gemini_api_key_from_db`,
`_mask`) was retired by Task 18.3, not just left untested -- see
`test_old_gemini_key_functions_are_gone` below.
"""

import httpx
import pytest

from app.core import config
from app.core.exceptions import ValidationError
from app.services import settings_service
from app.services.ai import openai_compat_provider as openai_compat_provider_module


def _install_mock_transport(monkeypatch, module, handler) -> None:
    """Same pattern as tests/test_openai_compat_provider.py -- routes
    `module.httpx.AsyncClient` through a MockTransport, never the real network."""
    transport = httpx.MockTransport(handler)
    real_async_client = httpx.AsyncClient

    def _factory(*args, **kwargs):
        kwargs["transport"] = transport
        return real_async_client(*args, **kwargs)

    monkeypatch.setattr(module.httpx, "AsyncClient", _factory)


@pytest.fixture(autouse=True)
def _isolated_cloud_settings(monkeypatch):
    monkeypatch.setattr(config.settings, "OPENAI_COMPAT_API_KEY", "env-fallback-key-0000")
    monkeypatch.setattr(config, "ENV_OPENAI_COMPAT_API_KEY", "env-fallback-key-0000")
    monkeypatch.setattr(config.settings, "OPENAI_COMPAT_BASE_URL", "https://openrouter.ai/api/v1")
    monkeypatch.setattr(config.settings, "OPENAI_COMPAT_MODEL", "nvidia/nemotron-3-super-120b-a12b:free")
    monkeypatch.setattr(config.settings, "OPENAI_COMPAT_FALLBACK_MODELS", "env/fallback-a:free,env/fallback-b:free")


def test_old_gemini_key_functions_are_gone():
    """Task 18.3 retires the old Gemini-key settings surface entirely (plan:
    "removed from the UI and API"), not just stops calling it -- a real
    regression guard, not "no longer tested"."""
    for name in (
        "get_gemini_api_key_status",
        "set_gemini_api_key",
        "clear_gemini_api_key",
        "load_gemini_api_key_from_db",
        "_mask",
        "GEMINI_API_KEY_SETTING",
    ):
        assert not hasattr(settings_service, name), name


async def test_cloud_status_reports_env_source_when_nothing_stored(db):
    status = await settings_service.get_cloud_settings_status(db)
    assert status["cloud_source"] == "env"
    assert status["cloud_configured"] is True
    assert status["cloud_last4"] == settings_service._last4("env-fallback-key-0000")
    assert status["cloud_base_url"] == "https://openrouter.ai/api/v1"
    assert status["cloud_model"] == "nvidia/nemotron-3-super-120b-a12b:free"


async def test_cloud_status_reports_none_when_no_env_and_nothing_stored(db, monkeypatch):
    monkeypatch.setattr(config.settings, "OPENAI_COMPAT_API_KEY", "")
    status = await settings_service.get_cloud_settings_status(db)
    assert status["cloud_source"] == "none"
    assert status["cloud_configured"] is False
    assert status["cloud_last4"] is None


async def test_set_cloud_settings_persists_and_applies_immediately(db):
    status = await settings_service.set_cloud_settings(
        db, "https://custom.example.com/v1", "some/model:free", "AIzaSyRealLookingTestKey123"
    )
    assert status["cloud_source"] == "database"
    assert status["cloud_last4"] == settings_service._last4("AIzaSyRealLookingTestKey123")
    assert status["cloud_base_url"] == "https://custom.example.com/v1"
    assert status["cloud_model"] == "some/model:free"
    # Applied immediately -- no restart needed, exactly what the router builder reads.
    assert config.settings.OPENAI_COMPAT_BASE_URL == "https://custom.example.com/v1"
    assert config.settings.OPENAI_COMPAT_MODEL == "some/model:free"
    assert config.settings.OPENAI_COMPAT_API_KEY == "AIzaSyRealLookingTestKey123"


async def test_set_cloud_settings_strips_surrounding_whitespace_from_model(db):
    status = await settings_service.set_cloud_settings(
        db, "https://openrouter.ai/api/v1", "  spaced/model  ", "a-key"
    )
    assert status["cloud_model"] == "spaced/model"
    assert config.settings.OPENAI_COMPAT_MODEL == "spaced/model"


async def test_set_cloud_settings_none_api_key_leaves_the_stored_key_unchanged(db):
    await settings_service.set_cloud_settings(db, "https://openrouter.ai/api/v1", "model-a", "first-key")
    status = await settings_service.set_cloud_settings(db, "https://openrouter.ai/api/v1", "model-b", None)
    assert status["cloud_model"] == "model-b"
    assert status["cloud_last4"] == settings_service._last4("first-key")
    assert config.settings.OPENAI_COMPAT_API_KEY == "first-key"


async def test_set_cloud_settings_rejects_empty_model(db):
    with pytest.raises(ValidationError):
        await settings_service.set_cloud_settings(db, "https://openrouter.ai/api/v1", "   ", "a-key")


async def test_set_cloud_settings_rejects_model_over_200_chars(db):
    with pytest.raises(ValidationError):
        await settings_service.set_cloud_settings(db, "https://openrouter.ai/api/v1", "m" * 201, "a-key")


async def test_set_cloud_settings_rejects_whitespace_only_api_key(db):
    with pytest.raises(ValidationError):
        await settings_service.set_cloud_settings(db, "https://openrouter.ai/api/v1", "model", "   ")


@pytest.mark.parametrize(
    "bad_base_url",
    [
        "http://example.com/v1",  # http, not loopback
        "http://user:pass@openrouter.ai/api/v1",  # credentials
    ],
)
async def test_set_cloud_settings_rejects_an_invalid_base_url(db, bad_base_url):
    """PM review C2: goes through validate_openai_compat_base_url."""
    with pytest.raises(ValidationError):
        await settings_service.set_cloud_settings(db, bad_base_url, "model", "a-key")


async def test_set_cloud_settings_invalid_input_stores_nothing(db):
    """PM review C2: "nothing is stored" -- the prior values are unchanged
    after a rejected update, not partially applied."""
    await settings_service.set_cloud_settings(db, "https://openrouter.ai/api/v1", "good-model", "good-key")

    with pytest.raises(ValidationError):
        await settings_service.set_cloud_settings(db, "http://not-loopback.example.com/v1", "new-model", "new-key")

    status = await settings_service.get_cloud_settings_status(db)
    assert status["cloud_base_url"] == "https://openrouter.ai/api/v1"
    assert status["cloud_model"] == "good-model"
    assert status["cloud_last4"] == settings_service._last4("good-key")
    assert config.settings.OPENAI_COMPAT_BASE_URL == "https://openrouter.ai/api/v1"
    assert config.settings.OPENAI_COMPAT_MODEL == "good-model"
    assert config.settings.OPENAI_COMPAT_API_KEY == "good-key"


async def test_set_cloud_settings_overwrites_a_previously_stored_key(db):
    await settings_service.set_cloud_settings(db, "https://openrouter.ai/api/v1", "model", "first-stored-key-111")
    status = await settings_service.set_cloud_settings(
        db, "https://openrouter.ai/api/v1", "model", "second-stored-key-222"
    )
    assert status["cloud_last4"] == settings_service._last4("second-stored-key-222")
    assert config.settings.OPENAI_COMPAT_API_KEY == "second-stored-key-222"


async def test_clear_cloud_api_key_reverts_to_original_env_value(db):
    await settings_service.set_cloud_settings(db, "https://openrouter.ai/api/v1", "model", "temporary-stored-key")
    assert config.settings.OPENAI_COMPAT_API_KEY == "temporary-stored-key"

    status = await settings_service.clear_cloud_api_key(db)

    assert config.settings.OPENAI_COMPAT_API_KEY == "env-fallback-key-0000"
    assert status["cloud_source"] == "env"
    assert status["cloud_last4"] == settings_service._last4("env-fallback-key-0000")


async def test_clear_cloud_api_key_when_nothing_was_ever_stored_is_a_noop(db):
    status = await settings_service.clear_cloud_api_key(db)
    assert config.settings.OPENAI_COMPAT_API_KEY == "env-fallback-key-0000"
    assert status["cloud_source"] == "env"


async def test_clear_cloud_api_key_leaves_base_url_and_model_untouched(db):
    await settings_service.set_cloud_settings(db, "https://custom.example.com/v1", "custom-model", "a-key")
    await settings_service.clear_cloud_api_key(db)
    assert config.settings.OPENAI_COMPAT_BASE_URL == "https://custom.example.com/v1"
    assert config.settings.OPENAI_COMPAT_MODEL == "custom-model"


async def test_load_cloud_settings_from_db_applies_stored_values_over_the_env_default(db):
    await settings_service.set_cloud_settings(
        db, "https://custom.example.com/v1", "custom-model", "stored-before-restart"
    )
    # Simulate a fresh process: reset the in-memory singleton back to the env values,
    # as it would be right after Settings() is constructed at import time.
    config.settings.OPENAI_COMPAT_BASE_URL = "https://openrouter.ai/api/v1"
    config.settings.OPENAI_COMPAT_MODEL = "nvidia/nemotron-3-super-120b-a12b:free"
    config.settings.OPENAI_COMPAT_API_KEY = "env-fallback-key-0000"

    await settings_service.load_cloud_settings_from_db(db)

    assert config.settings.OPENAI_COMPAT_BASE_URL == "https://custom.example.com/v1"
    assert config.settings.OPENAI_COMPAT_MODEL == "custom-model"
    assert config.settings.OPENAI_COMPAT_API_KEY == "stored-before-restart"


async def test_load_cloud_settings_from_db_leaves_env_values_untouched_when_nothing_stored(db):
    await settings_service.load_cloud_settings_from_db(db)
    assert config.settings.OPENAI_COMPAT_BASE_URL == "https://openrouter.ai/api/v1"
    assert config.settings.OPENAI_COMPAT_MODEL == "nvidia/nemotron-3-super-120b-a12b:free"
    assert config.settings.OPENAI_COMPAT_API_KEY == "env-fallback-key-0000"


# --- Task 18.6 (D27): fallback model chain ------------------------------------------


async def test_cloud_status_reports_fallback_models_from_env_default(db):
    status = await settings_service.get_cloud_settings_status(db)
    assert status["cloud_fallback_models"] == ["env/fallback-a:free", "env/fallback-b:free"]


async def test_set_cloud_settings_persists_and_applies_fallback_models(db):
    status = await settings_service.set_cloud_settings(
        db, "https://openrouter.ai/api/v1", "model", "a-key", ["one/a:free", "two/b:free"]
    )
    assert status["cloud_fallback_models"] == ["one/a:free", "two/b:free"]
    assert config.settings.OPENAI_COMPAT_FALLBACK_MODELS == "one/a:free,two/b:free"


async def test_set_cloud_settings_strips_whitespace_from_fallback_model_entries(db):
    status = await settings_service.set_cloud_settings(
        db, "https://openrouter.ai/api/v1", "model", "a-key", ["  spaced/one:free  ", "two:free"]
    )
    assert status["cloud_fallback_models"] == ["spaced/one:free", "two:free"]


async def test_set_cloud_settings_none_fallback_models_leaves_stored_chain_unchanged(db):
    await settings_service.set_cloud_settings(
        db, "https://openrouter.ai/api/v1", "model-a", "a-key", ["one/a:free"]
    )
    status = await settings_service.set_cloud_settings(db, "https://openrouter.ai/api/v1", "model-b", None, None)
    assert status["cloud_model"] == "model-b"
    assert status["cloud_fallback_models"] == ["one/a:free"]


async def test_set_cloud_settings_empty_list_explicitly_clears_the_fallback_chain(db):
    await settings_service.set_cloud_settings(
        db, "https://openrouter.ai/api/v1", "model", "a-key", ["one/a:free"]
    )
    status = await settings_service.set_cloud_settings(db, "https://openrouter.ai/api/v1", "model", None, [])
    assert status["cloud_fallback_models"] == []
    assert config.settings.OPENAI_COMPAT_FALLBACK_MODELS == ""


async def test_set_cloud_settings_rejects_too_many_fallback_models(db):
    with pytest.raises(ValidationError):
        await settings_service.set_cloud_settings(
            db, "https://openrouter.ai/api/v1", "model", "a-key", [f"m{i}/x:free" for i in range(6)]
        )


async def test_set_cloud_settings_rejects_an_empty_fallback_model_entry(db):
    with pytest.raises(ValidationError):
        await settings_service.set_cloud_settings(
            db, "https://openrouter.ai/api/v1", "model", "a-key", ["good/model:free", "   "]
        )


async def test_set_cloud_settings_rejects_a_fallback_model_over_200_chars(db):
    with pytest.raises(ValidationError):
        await settings_service.set_cloud_settings(
            db, "https://openrouter.ai/api/v1", "model", "a-key", ["m" * 201]
        )


async def test_set_cloud_settings_invalid_fallback_models_stores_nothing(db):
    await settings_service.set_cloud_settings(
        db, "https://openrouter.ai/api/v1", "good-model", "good-key", ["good/model:free"]
    )
    with pytest.raises(ValidationError):
        await settings_service.set_cloud_settings(
            db, "https://openrouter.ai/api/v1", "good-model", "good-key", ["m" * 201]
        )
    status = await settings_service.get_cloud_settings_status(db)
    assert status["cloud_fallback_models"] == ["good/model:free"]


async def test_load_cloud_settings_from_db_applies_stored_fallback_models(db):
    await settings_service.set_cloud_settings(
        db, "https://openrouter.ai/api/v1", "model", "a-key", ["stored/one:free"]
    )
    config.settings.OPENAI_COMPAT_FALLBACK_MODELS = "env/fallback-a:free,env/fallback-b:free"

    await settings_service.load_cloud_settings_from_db(db)

    assert config.settings.OPENAI_COMPAT_FALLBACK_MODELS == "stored/one:free"


async def test_load_cloud_settings_from_db_applies_an_explicitly_cleared_fallback_chain(db):
    """The exact case set_cloud_settings([]) stores as "" -- `is not None`
    (row exists), not truthiness, must still apply it, or a restart would
    silently revert an intentional clear back to the .env default."""
    await settings_service.set_cloud_settings(db, "https://openrouter.ai/api/v1", "model", "a-key", [])
    config.settings.OPENAI_COMPAT_FALLBACK_MODELS = "env/fallback-a:free,env/fallback-b:free"

    await settings_service.load_cloud_settings_from_db(db)

    assert config.settings.OPENAI_COMPAT_FALLBACK_MODELS == ""


async def test_load_cloud_settings_from_db_leaves_fallback_models_untouched_when_nothing_stored(db):
    await settings_service.load_cloud_settings_from_db(db)
    assert config.settings.OPENAI_COMPAT_FALLBACK_MODELS == "env/fallback-a:free,env/fallback-b:free"


def test_last4_fully_masks_short_keys():
    assert settings_service._last4("abcd") == "••••"
    assert settings_service._last4("ab") == "••"


def test_last4_shows_only_the_last_4_characters_for_longer_keys():
    key = "AIzaSyABCDEFGHIJKLMNOP1234"
    assert settings_service._last4(key) == "•" * (len(key) - 4) + "1234"


# --- test_cloud_connection (Task 18.3, PM review C1) ------------------------------------


async def test_cloud_connection_success(monkeypatch):
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"choices": [{"message": {"content": "ok"}}]})

    _install_mock_transport(monkeypatch, openai_compat_provider_module, handler)
    result = await settings_service.test_cloud_connection("https://openrouter.ai/api/v1", "a-model", "a-key")
    assert result == {"ok": True}


async def test_cloud_connection_failure_reports_error_class_and_status(monkeypatch):
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(401, json={"error": {"message": "invalid key", "code": 401}})

    _install_mock_transport(monkeypatch, openai_compat_provider_module, handler)
    result = await settings_service.test_cloud_connection("https://openrouter.ai/api/v1", "a-model", "bad-key")
    assert result == {"ok": False, "error": "ProviderAuthError", "status": 401}


async def test_cloud_connection_never_includes_the_key_in_its_result(monkeypatch):
    marker = "SECRET_TEST_CONNECTION_KEY_MARKER"

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(401, json={"error": {"message": f"invalid key: {marker}", "code": 401}})

    _install_mock_transport(monkeypatch, openai_compat_provider_module, handler)
    result = await settings_service.test_cloud_connection("https://openrouter.ai/api/v1", "a-model", marker)
    assert marker not in str(result)


async def test_cloud_connection_falls_back_to_currently_effective_values_when_omitted(monkeypatch):
    captured = {}

    def handler(request: httpx.Request) -> httpx.Response:
        import json as json_module

        captured["json"] = json_module.loads(request.content)
        captured["authorization"] = request.headers["authorization"]
        return httpx.Response(200, json={"choices": [{"message": {"content": "ok"}}]})

    _install_mock_transport(monkeypatch, openai_compat_provider_module, handler)
    result = await settings_service.test_cloud_connection(None, None, None)
    assert result == {"ok": True}
    assert captured["json"]["model"] == "nvidia/nemotron-3-super-120b-a12b:free"
    assert captured["authorization"] == "Bearer env-fallback-key-0000"


async def test_cloud_connection_invalid_base_url_returns_ok_false_not_an_exception():
    result = await settings_service.test_cloud_connection("http://not-loopback.example.com", "model", "key")
    assert result["ok"] is False
    assert result["error"] == "ValueError"
    assert result["status"] is None


# --- compute_effective_mode_and_reason (Task 18.3, PM review C3) ------------------------


def test_effective_mode_matches_when_local():
    mode, reason = settings_service.compute_effective_mode_and_reason("local")
    assert mode == "local"
    assert reason is None


def test_effective_mode_matches_when_cloud_first_fully_configured(monkeypatch):
    monkeypatch.setattr(config.settings, "AI_ALLOW_CLOUD", True)
    mode, reason = settings_service.compute_effective_mode_and_reason("cloud_first")
    assert mode == "cloud_first"
    assert reason is None


def test_effective_mode_reason_is_no_api_key_configured(monkeypatch):
    monkeypatch.setattr(config.settings, "AI_ALLOW_CLOUD", True)
    monkeypatch.setattr(config.settings, "OPENAI_COMPAT_API_KEY", "")
    mode, reason = settings_service.compute_effective_mode_and_reason("cloud_first")
    assert mode == "local"
    assert reason == "no API key configured"


def test_effective_mode_reason_is_cloud_disabled_by_allow_cloud(monkeypatch):
    monkeypatch.setattr(config.settings, "AI_ALLOW_CLOUD", False)
    mode, reason = settings_service.compute_effective_mode_and_reason("cloud_first")
    assert mode == "local"
    assert reason == "cloud disabled by DIE_AI_ALLOW_CLOUD"


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
