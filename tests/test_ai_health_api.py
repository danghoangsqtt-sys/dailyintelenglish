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
    monkeypatch.setattr(settings, "AI_MODE", "cloud")
    # Task 14.7: matches the real default (False) unless a test explicitly opts in.
    monkeypatch.setattr(settings, "AI_ALLOW_CLOUD", False)
    # Task 18.3: isolate the cloud settings this health payload now also reads,
    # so these tests don't depend on (or leak) this machine's real .env values.
    monkeypatch.setattr(settings, "OPENAI_COMPAT_API_KEY", "test-cloud-key")
    monkeypatch.setattr(settings, "OPENAI_COMPAT_MODEL", "nvidia/nemotron-3-super-120b-a12b:free")
    with TestClient(app) as test_client:
        yield test_client


def test_health_reports_the_current_ai_mode(client):
    response = client.get("/api/ai/health")
    assert response.status_code == 200
    assert response.json()["data"]["mode"] == "cloud"


def test_health_reflects_an_ai_mode_change_without_restart(client, monkeypatch):
    monkeypatch.setattr(settings, "AI_ALLOW_CLOUD", True)
    client.put("/api/settings/ai-mode", json={"ai_mode": "cloud_first"})
    response = client.get("/api/ai/health")
    assert response.json()["data"]["mode"] == "cloud_first"


def test_health_reports_cloud_enabled_false_by_default(client):
    response = client.get("/api/ai/health")
    assert response.json()["data"]["cloud_enabled"] is False


def test_health_reports_cloud_enabled_true_when_allow_cloud_is_set(client, monkeypatch):
    monkeypatch.setattr(settings, "AI_ALLOW_CLOUD", True)
    response = client.get("/api/ai/health")
    assert response.json()["data"]["cloud_enabled"] is True


def test_health_response_has_no_extra_undeclared_fields(client):
    """Locks the safe-field allowlist so a future change can't accidentally
    widen the payload with something sensitive (remote path, raw error, etc.).

    Task 16.3 (BUG-023, Amendment D): previously built its own bare
    `TestClient(app)` here instead of using this file's `client` fixture, so it
    never overrode `settings.DATA_DIR` -- silently opening a lifespan connection
    against the real `data/app.db` on every run (never visibly leaked a project
    row, since this test only ever GETs). Caught by the new real-DB guard in
    `tests/conftest.py`; fixed by using the same isolated `client` fixture every
    other test in this file already uses."""
    expected_keys = {
        "mode",
        "ollama_reachable",
        "model",
        "model_present",
        "model_digest",
        "cloud_enabled",
        "worker_alive",
        "cloud_configured",
        "cloud_model",
        "effective_mode",
        "circuit_open",
    }
    response = client.get("/api/ai/health")
    assert set(response.json()["data"].keys()) == expected_keys


# --- Task 18.3: cloud_configured, cloud_model, effective_mode, circuit_open ------------


def test_health_reports_cloud_configured_true_when_key_and_model_present(client):
    response = client.get("/api/ai/health")
    assert response.json()["data"]["cloud_configured"] is True


def test_health_reports_cloud_configured_false_when_no_key(client, monkeypatch):
    monkeypatch.setattr(settings, "OPENAI_COMPAT_API_KEY", "")
    response = client.get("/api/ai/health")
    assert response.json()["data"]["cloud_configured"] is False


def test_health_reports_cloud_model(client):
    response = client.get("/api/ai/health")
    assert response.json()["data"]["cloud_model"] == "nvidia/nemotron-3-super-120b-a12b:free"


def test_health_effective_mode_collapses_to_local_without_allow_cloud(client):
    # AI_ALLOW_CLOUD is False (the client fixture's default), AI_MODE is "cloud".
    response = client.get("/api/ai/health")
    assert response.json()["data"]["effective_mode"] == "local"


def test_health_effective_mode_matches_when_fully_configured(client, monkeypatch):
    monkeypatch.setattr(settings, "AI_ALLOW_CLOUD", True)
    monkeypatch.setattr(settings, "AI_MODE", "cloud_first")
    response = client.get("/api/ai/health")
    assert response.json()["data"]["effective_mode"] == "cloud_first"


def test_health_reports_circuit_open_false_by_default(client):
    response = client.get("/api/ai/health")
    assert response.json()["data"]["circuit_open"] is False


def test_health_reports_circuit_open_true_when_the_breaker_is_open(client):
    """Whitebox: forces `app.main`'s app-lifetime `_ai_circuit` open directly,
    matching this file's existing pattern of reaching into `app.main`'s real
    singletons (see `test_health_reports_worker_alive_false_...` below) rather
    than trying to actually exhaust the primary provider through a live job."""
    from app.main import _ai_circuit

    _ai_circuit.open_immediately()
    try:
        response = client.get("/api/ai/health")
        assert response.json()["data"]["circuit_open"] is True
    finally:
        _ai_circuit.record_success()


def test_health_reports_worker_alive_true_during_normal_operation(client):
    """Task 16.1 (BUG-022): the app's real AIWorker singleton is running for the
    whole `TestClient(app)` lifespan."""
    response = client.get("/api/ai/health")
    assert response.json()["data"]["worker_alive"] is True


def test_health_reports_worker_alive_false_when_the_worker_task_is_dead(client):
    """Whitebox: forces `AIWorker.is_alive` to `False` by clearing the real
    singleton's task, since stopping it for real would tear down the shared app
    (app/main.py, which constructs it, is outside this task's allowed files).

    Task 16.2 (N3): restores the real task in a `finally` here rather than
    relying on `monkeypatch`'s own fixture-teardown revert, whose timing
    relative to the `client` fixture's teardown (lifespan shutdown ->
    `ai_worker.stop()`) isn't guaranteed -- if `_task` were still `None` when
    `stop()` runs, its `if self._task is None: return` guard would return
    immediately and orphan the real loop task instead of awaiting/cancelling
    it."""
    from app.main import ai_worker

    real_task = ai_worker._task
    ai_worker._task = None
    try:
        response = client.get("/api/ai/health")
        assert response.json()["data"]["worker_alive"] is False
    finally:
        ai_worker._task = real_task
