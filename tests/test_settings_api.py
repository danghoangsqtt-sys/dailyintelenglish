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
