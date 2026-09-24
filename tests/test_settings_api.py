"""HTTP tests for /api/settings routes (Task 12.1; Task 18.3 cloud settings)."""

import pytest
from fastapi.testclient import TestClient

from app.core import config
from app.core.config import settings
from app.main import app


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "DATA_DIR", tmp_path)
    monkeypatch.setattr(settings, "OPENAI_COMPAT_API_KEY", "env-default-key-9999")
    # config.ENV_OPENAI_COMPAT_API_KEY is captured once at process import time from the
    # real .env file and never changes afterward (see app/core/config.py) -- clearing a
    # stored key reverts to it in production, so it must be isolated here too, or
    # "clear" tests would revert to (and leak parts of) this machine's real key.
    monkeypatch.setattr(config, "ENV_OPENAI_COMPAT_API_KEY", "env-default-key-9999")
    monkeypatch.setattr(settings, "OPENAI_COMPAT_BASE_URL", "https://openrouter.ai/api/v1")
    monkeypatch.setattr(settings, "OPENAI_COMPAT_MODEL", "nvidia/nemotron-3-super-120b-a12b:free")
    monkeypatch.setattr(settings, "OPENAI_COMPAT_FALLBACK_MODELS", "env/fallback-a:free,env/fallback-b:free")
    # Task 18.8 (D28): same isolation pattern for the new provider chain fields.
    monkeypatch.setattr(settings, "OPENCODE_ZEN_API_KEY", "")
    monkeypatch.setattr(config, "ENV_OPENCODE_ZEN_API_KEY", "")
    monkeypatch.setattr(settings, "OPENCODE_ZEN_BASE_URL", "https://opencode.ai/zen/v1")
    monkeypatch.setattr(settings, "OPENCODE_ZEN_MODEL", "")
    monkeypatch.setattr(settings, "GEMINI_API_KEY", "")
    monkeypatch.setattr(config, "ENV_GEMINI_API_KEY", "")
    monkeypatch.setattr(settings, "GEMINI_BASE_URL", "https://generativelanguage.googleapis.com/v1beta/openai")
    monkeypatch.setattr(settings, "GEMINI_MODELS", "gemini-3.1-flash-lite,gemini-flash-lite-latest")
    monkeypatch.setattr(settings, "CLOUD_PROVIDER_ORDER", "openrouter,gemini")
    # AI_MODE (Task 13.6) is the same kind of mutable-singleton setting -- reset to
    # a deterministic value so a PUT in one test can't leak into another.
    monkeypatch.setattr(settings, "AI_MODE", "cloud")
    # Task 14.7: matches the pre-Amendment-C default unless a test explicitly opts in
    # (Amendment C flips the real default to true, but the gate itself is unchanged) --
    # PUT .../ai-mode now rejects cloud/cloud_first without this.
    monkeypatch.setattr(settings, "AI_ALLOW_CLOUD", False)
    with TestClient(app) as test_client:
        yield test_client


def test_get_reports_env_source_before_anything_is_saved(client):
    response = client.get("/api/settings")
    assert response.status_code == 200
    data = response.json()["data"]
    assert data["cloud_source"] == "env"
    assert data["cloud_configured"] is True
    assert data["cloud_last4"].endswith("9999")
    assert data["cloud_base_url"] == "https://openrouter.ai/api/v1"
    assert data["cloud_model"] == "nvidia/nemotron-3-super-120b-a12b:free"
    assert data["cloud_fallback_models"] == ["env/fallback-a:free", "env/fallback-b:free"]
    assert data["allow_cloud"] is False
    assert data["cloud_provider_order"] == ["openrouter", "gemini"]
    assert data["opencode_zen"]["configured"] is False
    assert data["gemini"]["configured"] is False
    assert data["gemini"]["models"] == ["gemini-3.1-flash-lite", "gemini-flash-lite-latest"]


def test_put_cloud_saves_and_never_echoes_the_raw_key(client):
    response = client.put(
        "/api/settings/cloud",
        json={"base_url": "https://custom.example.com/v1", "model": "some/model", "api_key": "AIzaSyBrandNewRealKey0001"},
    )
    assert response.status_code == 200
    body = response.text
    assert "AIzaSyBrandNewRealKey0001" not in body
    data = response.json()["data"]
    assert data["cloud_source"] == "database"
    assert data["cloud_last4"].endswith("0001")
    assert data["cloud_base_url"] == "https://custom.example.com/v1"
    assert data["cloud_model"] == "some/model"


def test_put_cloud_then_get_reflects_the_saved_settings_without_restart(client):
    client.put(
        "/api/settings/cloud",
        json={"base_url": "https://custom.example.com/v1", "model": "some/model", "api_key": "AIzaSyBrandNewRealKey0001"},
    )
    response = client.get("/api/settings")
    data = response.json()["data"]
    assert data["cloud_source"] == "database"
    assert data["cloud_last4"].endswith("0001")
    assert data["cloud_base_url"] == "https://custom.example.com/v1"


def test_put_cloud_omitted_api_key_leaves_the_stored_key_unchanged(client):
    client.put(
        "/api/settings/cloud",
        json={"base_url": "https://openrouter.ai/api/v1", "model": "model-a", "api_key": "first-key"},
    )
    response = client.put(
        "/api/settings/cloud", json={"base_url": "https://openrouter.ai/api/v1", "model": "model-b"}
    )
    assert response.status_code == 200
    data = response.json()["data"]
    assert data["cloud_model"] == "model-b"
    assert data["cloud_last4"].endswith("-key")


def test_put_cloud_rejects_whitespace_only_key(client):
    response = client.put(
        "/api/settings/cloud", json={"base_url": "https://openrouter.ai/api/v1", "model": "m", "api_key": "   "}
    )
    assert response.status_code == 422
    assert response.json()["success"] is False


def test_put_cloud_rejects_empty_model(client):
    response = client.put("/api/settings/cloud", json={"base_url": "https://openrouter.ai/api/v1", "model": "  "})
    assert response.status_code == 422


def test_put_cloud_rejects_an_invalid_base_url(client):
    """PM review C2."""
    response = client.put("/api/settings/cloud", json={"base_url": "http://not-loopback.example.com", "model": "m"})
    assert response.status_code == 422


def test_put_cloud_rejects_missing_field(client):
    response = client.put("/api/settings/cloud", json={"model": "m"})
    assert response.status_code == 422


def test_put_cloud_invalid_input_stores_nothing(client):
    """PM review C2: the prior values are unchanged after a rejected update."""
    client.put(
        "/api/settings/cloud",
        json={"base_url": "https://openrouter.ai/api/v1", "model": "good-model", "api_key": "good-key"},
    )
    rejected = client.put(
        "/api/settings/cloud", json={"base_url": "http://not-loopback.example.com", "model": "new-model"}
    )
    assert rejected.status_code == 422

    data = client.get("/api/settings").json()["data"]
    assert data["cloud_base_url"] == "https://openrouter.ai/api/v1"
    assert data["cloud_model"] == "good-model"
    assert data["cloud_last4"].endswith("-key")


# --- Task 18.6 (D27): fallback model chain ------------------------------------------


def test_put_cloud_saves_fallback_models(client):
    response = client.put(
        "/api/settings/cloud",
        json={
            "base_url": "https://openrouter.ai/api/v1",
            "model": "some/model",
            "fallback_models": ["one/a:free", "two/b:free"],
        },
    )
    assert response.status_code == 200
    assert response.json()["data"]["cloud_fallback_models"] == ["one/a:free", "two/b:free"]


def test_put_cloud_omitted_fallback_models_leaves_it_unchanged(client):
    client.put(
        "/api/settings/cloud",
        json={"base_url": "https://openrouter.ai/api/v1", "model": "m", "fallback_models": ["one/a:free"]},
    )
    response = client.put("/api/settings/cloud", json={"base_url": "https://openrouter.ai/api/v1", "model": "m2"})
    assert response.json()["data"]["cloud_fallback_models"] == ["one/a:free"]


def test_put_cloud_empty_fallback_models_list_clears_it(client):
    client.put(
        "/api/settings/cloud",
        json={"base_url": "https://openrouter.ai/api/v1", "model": "m", "fallback_models": ["one/a:free"]},
    )
    response = client.put(
        "/api/settings/cloud",
        json={"base_url": "https://openrouter.ai/api/v1", "model": "m", "fallback_models": []},
    )
    assert response.json()["data"]["cloud_fallback_models"] == []


def test_put_cloud_rejects_too_many_fallback_models(client):
    response = client.put(
        "/api/settings/cloud",
        json={
            "base_url": "https://openrouter.ai/api/v1",
            "model": "m",
            "fallback_models": [f"m{i}/x:free" for i in range(6)],
        },
    )
    assert response.status_code == 422


def test_delete_cloud_api_key_reverts_to_env_source(client):
    client.put(
        "/api/settings/cloud",
        json={"base_url": "https://openrouter.ai/api/v1", "model": "m", "api_key": "AIzaSyBrandNewRealKey0001"},
    )

    response = client.delete("/api/settings/cloud/api-key")

    assert response.status_code == 200
    data = response.json()["data"]
    assert data["cloud_source"] == "env"
    assert data["cloud_last4"].endswith("9999")


def test_delete_cloud_api_key_when_nothing_stored_is_a_noop(client):
    response = client.delete("/api/settings/cloud/api-key")
    assert response.status_code == 200
    assert response.json()["data"]["cloud_source"] == "env"


def test_old_gemini_routes_are_gone(client):
    """Task 18.3: the old Gemini-key settings routes are removed, not just
    stopped, matching "removed from the UI and API". PUT /api/settings is
    405 (the path still exists for GET, but no PUT handler is registered on
    it anymore); the old DELETE path has no route at all, so 404."""
    assert client.put("/api/settings", json={"gemini_api_key": "x"}).status_code == 405
    assert client.delete("/api/settings/gemini-api-key").status_code == 404


# --- test connection (Task 18.3, PM review C1) -------------------------------------------


def test_post_test_connection_reports_ok_true_on_success(client, monkeypatch):
    import httpx

    from app.services.ai import openai_compat_provider as openai_compat_provider_module

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"choices": [{"message": {"content": "ok"}}]})

    transport = httpx.MockTransport(handler)
    real_async_client = httpx.AsyncClient

    def _factory(*args, **kwargs):
        kwargs["transport"] = transport
        return real_async_client(*args, **kwargs)

    monkeypatch.setattr(openai_compat_provider_module.httpx, "AsyncClient", _factory)

    response = client.post(
        "/api/settings/cloud/test-connection",
        json={"base_url": "https://openrouter.ai/api/v1", "model": "m", "api_key": "a-key"},
    )
    assert response.status_code == 200
    assert response.json()["data"] == {"ok": True}


def test_post_test_connection_reports_error_class_and_status_never_the_key(client, monkeypatch):
    import httpx

    from app.services.ai import openai_compat_provider as openai_compat_provider_module

    marker = "SECRET_TEST_CONNECTION_KEY_MARKER"

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(401, json={"error": {"message": f"invalid key: {marker}", "code": 401}})

    transport = httpx.MockTransport(handler)
    real_async_client = httpx.AsyncClient

    def _factory(*args, **kwargs):
        kwargs["transport"] = transport
        return real_async_client(*args, **kwargs)

    monkeypatch.setattr(openai_compat_provider_module.httpx, "AsyncClient", _factory)

    response = client.post(
        "/api/settings/cloud/test-connection",
        json={"base_url": "https://openrouter.ai/api/v1", "model": "m", "api_key": marker},
    )
    assert response.status_code == 200
    data = response.json()["data"]
    assert data == {"ok": False, "error": "ProviderAuthError", "status": 401}
    assert marker not in response.text


# --- AI mode (Task 13.6) --------------------------------------------------------------


def test_get_settings_reports_ai_mode_env_default(client):
    response = client.get("/api/settings")
    data = response.json()["data"]
    assert data["ai_mode"] == "cloud"
    assert data["ai_mode_source"] == "env"


def test_put_ai_mode_saves_and_applies_immediately(client, monkeypatch):
    monkeypatch.setattr(settings, "AI_ALLOW_CLOUD", True)
    response = client.put("/api/settings/ai-mode", json={"ai_mode": "cloud_first"})
    assert response.status_code == 200
    data = response.json()["data"]
    assert data["ai_mode"] == "cloud_first"
    assert data["ai_mode_source"] == "database"
    assert settings.AI_MODE == "cloud_first"


def test_put_then_get_reflects_the_saved_ai_mode(client):
    client.put("/api/settings/ai-mode", json={"ai_mode": "local"})
    response = client.get("/api/settings")
    data = response.json()["data"]
    assert data["ai_mode"] == "local"
    assert data["ai_mode_source"] == "database"


def test_put_ai_mode_rejects_an_unknown_value(client):
    response = client.put("/api/settings/ai-mode", json={"ai_mode": "not_a_real_mode"})
    assert response.status_code == 422


def test_ai_mode_change_does_not_disturb_the_cloud_status(client, monkeypatch):
    """Regression guard for a field-name collision this task's get_settings
    merge could introduce ('cloud_source' vs 'ai_mode_source')."""
    monkeypatch.setattr(settings, "AI_ALLOW_CLOUD", True)
    client.put(
        "/api/settings/cloud",
        json={"base_url": "https://openrouter.ai/api/v1", "model": "m", "api_key": "AIzaSyBrandNewRealKey0001"},
    )
    client.put("/api/settings/ai-mode", json={"ai_mode": "cloud_first"})
    response = client.get("/api/settings")
    data = response.json()["data"]
    assert data["cloud_source"] == "database"  # cloud key status, unaffected by ai_mode
    assert data["ai_mode_source"] == "database"


# --- Task 14.7: cloud gate (ADR-001 A2) -------------------------------------------------


def test_put_ai_mode_rejects_cloud_without_allow_cloud(client):
    response = client.put("/api/settings/ai-mode", json={"ai_mode": "cloud"})
    assert response.status_code == 422


def test_put_ai_mode_rejects_cloud_first_without_allow_cloud(client):
    response = client.put("/api/settings/ai-mode", json={"ai_mode": "cloud_first"})
    assert response.status_code == 422


def test_put_ai_mode_accepts_cloud_when_allow_cloud_is_true(client, monkeypatch):
    monkeypatch.setattr(settings, "AI_ALLOW_CLOUD", True)
    response = client.put("/api/settings/ai-mode", json={"ai_mode": "cloud"})
    assert response.status_code == 200
    assert response.json()["data"]["ai_mode"] == "cloud"


def test_put_ai_mode_accepts_local_regardless_of_allow_cloud(client):
    # AI_ALLOW_CLOUD is False by default (see the client fixture) -- local is
    # never gated, it's the only supported mode.
    response = client.put("/api/settings/ai-mode", json={"ai_mode": "local"})
    assert response.status_code == 200
    assert response.json()["data"]["ai_mode"] == "local"


def test_put_ai_mode_rejects_legacy_gemini_and_hybrid_as_new_input_values(client, monkeypatch):
    """Phase 18 (was test_put_ai_mode_rejects_gemini_without_allow_cloud/
    ..._rejects_hybrid_without_allow_cloud): "gemini"/"hybrid" are no longer
    valid *inputs* to this endpoint at all -- only a value already stored from
    before Phase 18 migrates on read (tests/test_settings_service.py). Both
    still return 422 as before, but now because they're not in AI_MODES,
    not because of the allow_cloud gate -- so this is asserted with
    AI_ALLOW_CLOUD=true, proving the gate isn't what's rejecting them."""
    monkeypatch.setattr(settings, "AI_ALLOW_CLOUD", True)
    for legacy_mode in ("gemini", "hybrid"):
        response = client.put("/api/settings/ai-mode", json={"ai_mode": legacy_mode})
        assert response.status_code == 422, legacy_mode


# --- effective mode + reason (Task 18.3, PM review C3) ------------------------------------


def test_get_settings_effective_mode_matches_when_local_and_no_discrepancy(client):
    client.put("/api/settings/ai-mode", json={"ai_mode": "local"})
    response = client.get("/api/settings")
    data = response.json()["data"]
    assert data["ai_mode"] == "local"
    assert data["effective_mode"] == "local"
    assert data["effective_reason"] is None


def test_get_settings_effective_reason_is_no_api_key_when_cloud_first_has_no_key(client, monkeypatch):
    monkeypatch.setattr(settings, "AI_ALLOW_CLOUD", True)
    monkeypatch.setattr(settings, "OPENAI_COMPAT_API_KEY", "")
    client.put("/api/settings/ai-mode", json={"ai_mode": "cloud_first"})

    response = client.get("/api/settings")
    data = response.json()["data"]
    assert data["ai_mode"] == "cloud_first"
    assert data["effective_mode"] == "local"
    assert data["effective_reason"] == "no API key configured"


def test_get_settings_effective_reason_is_cloud_disabled_when_allow_cloud_false(client, monkeypatch):
    """AI_ALLOW_CLOUD stays False (the client fixture's default). Setting
    ai_mode to cloud_first is normally rejected by set_ai_mode's own gate
    while allow_cloud is false, so this drives config.settings.AI_MODE
    directly (as load_ai_mode_from_db would for a value stored before the
    owner disabled cloud) to isolate this one reason."""
    monkeypatch.setattr(settings, "AI_MODE", "cloud_first")

    response = client.get("/api/settings")
    data = response.json()["data"]
    assert data["ai_mode"] == "cloud_first"
    assert data["effective_mode"] == "local"
    assert data["effective_reason"] == "cloud disabled by DIE_AI_ALLOW_CLOUD"


def test_get_settings_effective_mode_matches_when_only_gemini_is_configured(client, monkeypatch):
    """Task 18.8 (D28): effective_mode is no longer OpenRouter-specific --
    cloud is effective as soon as ANY configured provider has a key, even
    with OpenRouter itself unconfigured."""
    monkeypatch.setattr(settings, "OPENAI_COMPAT_API_KEY", "")
    monkeypatch.setattr(settings, "GEMINI_API_KEY", "gemini-key")
    monkeypatch.setattr(settings, "AI_ALLOW_CLOUD", True)
    monkeypatch.setattr(settings, "AI_MODE", "cloud_first")

    response = client.get("/api/settings")
    assert response.json()["data"]["effective_mode"] == "cloud_first"


# --- Task 18.8 (D28): OpenCode Zen / Gemini / dispatch order -------------------------


def test_put_opencode_zen_saves_and_never_echoes_the_raw_key(client):
    response = client.put(
        "/api/settings/cloud/opencode-zen",
        json={"base_url": "https://opencode.ai/zen/v1", "model": "some/zen-model", "api_key": "ZenRealKey0001"},
    )
    assert response.status_code == 200
    assert "ZenRealKey0001" not in response.text
    data = response.json()["data"]
    assert data["configured"] is True
    assert data["key_last4"].endswith("0001")


def test_put_opencode_zen_rejects_empty_model(client):
    response = client.put(
        "/api/settings/cloud/opencode-zen",
        json={"base_url": "https://opencode.ai/zen/v1", "model": "   "},
    )
    assert response.status_code == 422


def test_delete_opencode_zen_api_key_reverts_to_env_source(client):
    client.put(
        "/api/settings/cloud/opencode-zen",
        json={"base_url": "https://opencode.ai/zen/v1", "model": "m", "api_key": "ZenRealKey0001"},
    )
    response = client.delete("/api/settings/cloud/opencode-zen/api-key")
    assert response.status_code == 200
    assert response.json()["data"]["configured"] is False


def test_put_gemini_saves_multiple_models_and_never_echoes_the_raw_key(client):
    response = client.put(
        "/api/settings/cloud/gemini",
        json={
            "base_url": "https://generativelanguage.googleapis.com/v1beta/openai",
            "models": ["model-a", "model-b"],
            "api_key": "GeminiRealKey0001",
        },
    )
    assert response.status_code == 200
    assert "GeminiRealKey0001" not in response.text
    data = response.json()["data"]
    assert data["configured"] is True
    assert data["models"] == ["model-a", "model-b"]
    assert data["key_last4"].endswith("0001")


def test_put_gemini_rejects_too_many_models(client):
    response = client.put(
        "/api/settings/cloud/gemini",
        json={"base_url": "https://a.example/v1", "models": [f"m{i}" for i in range(6)], "api_key": "k"},
    )
    assert response.status_code == 422


def test_delete_gemini_cloud_api_key_reverts_to_env_source(client):
    client.put(
        "/api/settings/cloud/gemini",
        json={"base_url": "https://a.example/v1", "models": ["m"], "api_key": "GeminiRealKey0001"},
    )
    response = client.delete("/api/settings/cloud/gemini/api-key")
    assert response.status_code == 200
    assert response.json()["data"]["configured"] is False


def test_put_cloud_provider_order_saves_and_applies(client):
    response = client.put("/api/settings/cloud/order", json={"order": ["gemini", "openrouter"]})
    assert response.status_code == 200
    assert response.json()["data"]["cloud_provider_order"] == ["gemini", "openrouter"]

    follow_up = client.get("/api/settings")
    assert follow_up.json()["data"]["cloud_provider_order"] == ["gemini", "openrouter"]


def test_put_cloud_provider_order_rejects_an_unknown_name(client):
    response = client.put("/api/settings/cloud/order", json={"order": ["openrouter", "not-a-real-provider"]})
    assert response.status_code == 422
