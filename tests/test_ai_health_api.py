"""HTTP tests for GET /api/ai/health (Task 13.6).

The route itself lives in app/api/ai_jobs.py (built in Task 13.3, before
app/api/ai_health.py was ever locked into a task's allowed-file list -- see
task-13.6.md's "deviation #1"). This file adds the Task 13.6-specific checks
(the health payload reflecting a live AI_MODE setting change) rather than
duplicating the baseline reachability/key-redaction tests already covered in
tests/test_ai_jobs_api.py, which is not in this task's allowed files to edit.
"""

import pytest
from fastapi.testclient import TestClient

from app.core.config import settings
from app.main import app


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "DATA_DIR", tmp_path)
    monkeypatch.setattr(settings, "AI_MODE", "gemini")
    # Task 14.7: matches the real default (False) unless a test explicitly opts in.
    monkeypatch.setattr(settings, "AI_ALLOW_CLOUD", False)
    with TestClient(app) as test_client:
        yield test_client


def test_health_reports_the_current_ai_mode(client):
    response = client.get("/api/ai/health")
    assert response.status_code == 200
    assert response.json()["data"]["mode"] == "gemini"


def test_health_reflects_an_ai_mode_change_without_restart(client, monkeypatch):
    monkeypatch.setattr(settings, "AI_ALLOW_CLOUD", True)
    client.put("/api/settings/ai-mode", json={"ai_mode": "hybrid"})
    response = client.get("/api/ai/health")
    assert response.json()["data"]["mode"] == "hybrid"


def test_health_reports_cloud_enabled_false_by_default(client):
    response = client.get("/api/ai/health")
    assert response.json()["data"]["cloud_enabled"] is False


def test_health_reports_cloud_enabled_true_when_allow_cloud_is_set(client, monkeypatch):
    monkeypatch.setattr(settings, "AI_ALLOW_CLOUD", True)
    response = client.get("/api/ai/health")
    assert response.json()["data"]["cloud_enabled"] is True


def test_health_response_has_no_extra_undeclared_fields():
    """Locks the safe-field allowlist so a future change can't accidentally
    widen the payload with something sensitive (remote path, raw error, etc.)."""
    expected_keys = {
        "mode",
        "ollama_reachable",
        "model",
        "model_present",
        "model_digest",
        "cloud_enabled",
    }
    with TestClient(app) as client:
        response = client.get("/api/ai/health")
    assert set(response.json()["data"].keys()) == expected_keys
