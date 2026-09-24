"""HTTP tests for the durable AI job routes and GET /api/ai/health."""

import pytest
from fastapi.testclient import TestClient

from app.core.config import settings
from app.main import app

PROJECT_PAYLOAD = {
    "name": "AI Jobs API Test",
    "topic": "Remote work",
    "cefr_level": "B1",
    "duration_minutes": 5,
    "num_speakers": 1,
    "genre": "interview",
    "accent": "american",
    "speakers": [{"name": "Alex", "gender": "male", "accent": "american"}],
}


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "DATA_DIR", tmp_path)
    with TestClient(app) as test_client:
        yield test_client


def _create_project(client: TestClient) -> str:
    response = client.post("/api/projects", json=PROJECT_PAYLOAD)
    assert response.status_code == 200
    return response.json()["data"]["id"]


def test_create_ai_job_returns_202_for_a_new_job(client):
    project_id = _create_project(client)
    response = client.post(f"/api/projects/{project_id}/ai-jobs", json={"operation": "script"})
    assert response.status_code == 202
    body = response.json()
    assert body["success"] is True
    assert body["data"]["status"] == "pending"
    assert body["data"]["operation"] == "script"
    assert body["data"]["project_id"] == project_id


def test_create_ai_job_returns_200_for_an_existing_active_job(client):
    project_id = _create_project(client)
    first = client.post(f"/api/projects/{project_id}/ai-jobs", json={"operation": "script"})
    second = client.post(f"/api/projects/{project_id}/ai-jobs", json={"operation": "script"})
    assert first.status_code == 202
    assert second.status_code == 200
    assert second.json()["data"]["id"] == first.json()["data"]["id"]


def test_create_ai_job_rejects_an_unknown_operation(client):
    project_id = _create_project(client)
    response = client.post(f"/api/projects/{project_id}/ai-jobs", json={"operation": "not_real"})
    assert response.status_code == 422


def test_create_ai_job_for_missing_project_404s(client):
    response = client.post("/api/projects/does-not-exist/ai-jobs", json={"operation": "script"})
    assert response.status_code == 404


def test_get_active_ai_job_returns_null_when_none_exists(client):
    project_id = _create_project(client)
    response = client.get(f"/api/projects/{project_id}/ai-jobs/active", params={"operation": "script"})
    assert response.status_code == 200
    assert response.json()["data"] is None


def test_get_active_ai_job_returns_the_job_once_one_exists(client):
    project_id = _create_project(client)
    created = client.post(f"/api/projects/{project_id}/ai-jobs", json={"operation": "script"})
    active = client.get(f"/api/projects/{project_id}/ai-jobs/active", params={"operation": "script"})
    assert active.json()["data"]["id"] == created.json()["data"]["id"]


def test_get_ai_job_by_id(client):
    project_id = _create_project(client)
    created = client.post(f"/api/projects/{project_id}/ai-jobs", json={"operation": "script"})
    job_id = created.json()["data"]["id"]
    response = client.get(f"/api/projects/{project_id}/ai-jobs/{job_id}")
    assert response.status_code == 200
    assert response.json()["data"]["id"] == job_id


def test_get_ai_job_from_a_different_project_404s(client):
    project_id = _create_project(client)
    other_project_id = _create_project(client)
    created = client.post(f"/api/projects/{project_id}/ai-jobs", json={"operation": "script"})
    job_id = created.json()["data"]["id"]

    response = client.get(f"/api/projects/{other_project_id}/ai-jobs/{job_id}")
    assert response.status_code == 404


def test_ai_job_response_never_exposes_internal_fields(client):
    project_id = _create_project(client)
    created = client.post(f"/api/projects/{project_id}/ai-jobs", json={"operation": "script"})
    data = created.json()["data"]
    for forbidden_field in (
        "input_snapshot_json",
        "remote_interaction_id",
        "lease_owner",
        "lease_expires_at",
        "heartbeat_at",
        "metrics_json",  # Task 14.2: the raw TEXT column never leaks -- only the
        # parsed `metrics` dict (see test_ai_job_service.py for a populated one).
    ):
        assert forbidden_field not in data


def test_ai_job_response_has_an_empty_metrics_dict_before_any_generation_call(client):
    """Task 14.2: `metrics` is always present, derived from `metrics_json`
    (`'{}'` for a freshly created job that hasn't run through a pipeline yet) --
    the deep `metrics.calls[]`-populated case is covered in
    tests/test_ai_job_service.py, which can drive `record_generation_call`
    directly against the same async db this app uses (see task-14.2.md's
    execution record for why that test lives there and not here)."""
    project_id = _create_project(client)
    created = client.post(f"/api/projects/{project_id}/ai-jobs", json={"operation": "script"})
    data = created.json()["data"]
    assert data["metrics"] == {}

    fetched = client.get(f"/api/projects/{project_id}/ai-jobs/{data['id']}")
    assert fetched.json()["data"]["metrics"] == {}


def test_cancel_ai_job_is_idempotent(client):
    project_id = _create_project(client)
    created = client.post(f"/api/projects/{project_id}/ai-jobs", json={"operation": "script"})
    job_id = created.json()["data"]["id"]

    first = client.post(f"/api/projects/{project_id}/ai-jobs/{job_id}/cancel")
    second = client.post(f"/api/projects/{project_id}/ai-jobs/{job_id}/cancel")
    assert first.status_code == 200
    assert second.status_code == 200
    assert first.json()["data"]["cancel_requested"] is True
    assert second.json()["data"]["cancel_requested"] is True


def test_cancel_ai_job_wrong_project_404s(client):
    project_id = _create_project(client)
    other_project_id = _create_project(client)
    created = client.post(f"/api/projects/{project_id}/ai-jobs", json={"operation": "script"})
    job_id = created.json()["data"]["id"]

    response = client.post(f"/api/projects/{other_project_id}/ai-jobs/{job_id}/cancel")
    assert response.status_code == 404


def test_ai_health_never_exposes_the_gemini_key(client, monkeypatch):
    # Pointed at a guaranteed-unreachable loopback port so this test is deterministic
    # regardless of whether a real Ollama server happens to be running on this machine.
    monkeypatch.setattr(settings, "OLLAMA_BASE_URL", "http://127.0.0.1:1")
    monkeypatch.setattr(settings, "GEMINI_API_KEY", "super-secret-key-value")
    # Task 18.3, plan Amendment C flipped the real AI_ALLOW_CLOUD default to
    # true -- pinned false here so this assertion stays deterministic rather
    # than silently depending on that default.
    monkeypatch.setattr(settings, "AI_ALLOW_CLOUD", False)
    # Task 18.3: the cloud key is the key this endpoint could plausibly leak now.
    monkeypatch.setattr(settings, "OPENAI_COMPAT_API_KEY", "super-secret-cloud-key-value")
    response = client.get("/api/ai/health")
    assert response.status_code == 200
    assert "super-secret-key-value" not in response.text
    assert "super-secret-cloud-key-value" not in response.text
    data = response.json()["data"]
    assert data["cloud_enabled"] is False
    assert "mode" in data
    assert "ollama_reachable" in data


def test_ai_health_degrades_gracefully_when_ollama_is_unreachable(client, monkeypatch):
    monkeypatch.setattr(settings, "OLLAMA_BASE_URL", "http://127.0.0.1:1")  # nothing listens here
    response = client.get("/api/ai/health")
    assert response.status_code == 200  # never a 500, per the plan's "does not fail startup" rule
    data = response.json()["data"]
    assert data["ollama_reachable"] is False
    assert data["model_present"] is False
