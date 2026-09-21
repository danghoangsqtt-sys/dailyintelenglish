"""HTTP tests for /api/settings routes (Task 12.1)."""

import pytest
from fastapi.testclient import TestClient

from app.core import config
from app.core.config import settings
from app.main import app


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "DATA_DIR", tmp_path)
    monkeypatch.setattr(settings, "GEMINI_API_KEY", "env-default-key-9999")
    # config.ENV_GEMINI_API_KEY is captured once at process import time from the real
    # .env file and never changes afterward (see app/core/config.py) -- clearing a
    # stored key reverts to it in production, so it must be isolated here too, or
    # "clear" tests would revert to (and leak parts of) this machine's real key.
    monkeypatch.setattr(config, "ENV_GEMINI_API_KEY", "env-default-key-9999")
    # AI_MODE (Task 13.6) is the same kind of mutable-singleton setting -- reset to
    # its documented packaged default so a PUT in one test can't leak into another.
    monkeypatch.setattr(settings, "AI_MODE", "gemini")
    # Task 14.7: matches the real default (False) unless a test explicitly opts in --
    # PUT .../ai-mode now rejects gemini/hybrid without this.
    monkeypatch.setattr(settings, "AI_ALLOW_CLOUD", False)
    with TestClient(app) as test_client:
        yield test_client


def test_get_reports_env_source_before_anything_is_saved(client):
    response = client.get("/api/settings")
    assert response.status_code == 200
    data = response.json()["data"]
    assert data["source"] == "env"
    assert data["masked_key"] == "env-de••••9999"


def test_put_saves_key_and_never_echoes_the_raw_value(client):
    response = client.put("/api/settings", json={"gemini_api_key": "AIzaSyBrandNewRealKey0001"})
    assert response.status_code == 200
    body = response.text
    assert "AIzaSyBrandNewRealKey0001" not in body
    data = response.json()["data"]
    assert data["source"] == "database"
    assert data["masked_key"] == "AIzaSy••••0001"


def test_put_then_get_reflects_the_saved_key_without_restart(client):
    client.put("/api/settings", json={"gemini_api_key": "AIzaSyBrandNewRealKey0001"})
    response = client.get("/api/settings")
    data = response.json()["data"]
    assert data["source"] == "database"
    assert data["masked_key"] == "AIzaSy••••0001"


def test_put_rejects_whitespace_only_key(client):
    response = client.put("/api/settings", json={"gemini_api_key": "   "})
    assert response.status_code == 422
    assert response.json()["success"] is False


def test_put_rejects_missing_field(client):
    response = client.put("/api/settings", json={})
    assert response.status_code == 422


def test_delete_reverts_to_env_source(client):
    client.put("/api/settings", json={"gemini_api_key": "AIzaSyBrandNewRealKey0001"})

    response = client.delete("/api/settings/gemini-api-key")

    assert response.status_code == 200
    data = response.json()["data"]
    assert data["source"] == "env"
    assert data["masked_key"] == "env-de••••9999"


def test_delete_when_nothing_stored_is_a_noop(client):
    response = client.delete("/api/settings/gemini-api-key")
    assert response.status_code == 200
    assert response.json()["data"]["source"] == "env"


# --- AI mode (Task 13.6) --------------------------------------------------------------


def test_get_settings_reports_ai_mode_env_default(client):
    response = client.get("/api/settings")
    data = response.json()["data"]
    assert data["ai_mode"] == "gemini"
    assert data["ai_mode_source"] == "env"


def test_put_ai_mode_saves_and_applies_immediately(client, monkeypatch):
    monkeypatch.setattr(settings, "AI_ALLOW_CLOUD", True)
    response = client.put("/api/settings/ai-mode", json={"ai_mode": "hybrid"})
    assert response.status_code == 200
    data = response.json()["data"]
    assert data["ai_mode"] == "hybrid"
    assert data["ai_mode_source"] == "database"
    assert settings.AI_MODE == "hybrid"


def test_put_then_get_reflects_the_saved_ai_mode(client):
    client.put("/api/settings/ai-mode", json={"ai_mode": "local"})
    response = client.get("/api/settings")
    data = response.json()["data"]
    assert data["ai_mode"] == "local"
    assert data["ai_mode_source"] == "database"


def test_put_ai_mode_rejects_an_unknown_value(client):
    response = client.put("/api/settings/ai-mode", json={"ai_mode": "not_a_real_mode"})
    assert response.status_code == 422


def test_ai_mode_change_does_not_disturb_the_gemini_key_status(client, monkeypatch):
    """Regression guard for the field-name collision this task's own get_settings
    merge could have introduced ('source' vs 'ai_mode_source')."""
    monkeypatch.setattr(settings, "AI_ALLOW_CLOUD", True)
    client.put("/api/settings", json={"gemini_api_key": "AIzaSyBrandNewRealKey0001"})
    client.put("/api/settings/ai-mode", json={"ai_mode": "hybrid"})
    response = client.get("/api/settings")
    data = response.json()["data"]
    assert data["source"] == "database"  # gemini key status, unaffected by ai_mode
    assert data["ai_mode_source"] == "database"


# --- Task 14.7: cloud gate (ADR-001 A2) -------------------------------------------------


def test_put_ai_mode_rejects_gemini_without_allow_cloud(client):
    response = client.put("/api/settings/ai-mode", json={"ai_mode": "gemini"})
    assert response.status_code == 422


def test_put_ai_mode_rejects_hybrid_without_allow_cloud(client):
    response = client.put("/api/settings/ai-mode", json={"ai_mode": "hybrid"})
    assert response.status_code == 422


def test_put_ai_mode_accepts_gemini_when_allow_cloud_is_true(client, monkeypatch):
    monkeypatch.setattr(settings, "AI_ALLOW_CLOUD", True)
    response = client.put("/api/settings/ai-mode", json={"ai_mode": "gemini"})
    assert response.status_code == 200
    assert response.json()["data"]["ai_mode"] == "gemini"


def test_put_ai_mode_accepts_local_regardless_of_allow_cloud(client):
    # AI_ALLOW_CLOUD is False by default (see the client fixture) -- local is
    # never gated, it's the only supported mode.
    response = client.put("/api/settings/ai-mode", json={"ai_mode": "local"})
    assert response.status_code == 200
    assert response.json()["data"]["ai_mode"] == "local"
