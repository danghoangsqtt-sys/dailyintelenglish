"""Full HTTP CRUD tests for /api/projects via TestClient (ROADMAP Task 1.2/1.3 gate)."""

import json

import pytest
from fastapi.testclient import TestClient

from app.core.config import settings
from app.main import app

VALID_PAYLOAD = {
    "name": "Smoke Test Episode",
    "topic": "Testing the API",
    "cefr_level": "B2",
    "duration_minutes": 5,
    "num_speakers": 2,
    "genre": "interview",
    "accent": "british",
    "speakers": [
        {"name": "Alex", "gender": "male", "accent": "british"},
        {"name": "Sam", "gender": "female", "accent": "british"},
    ],
}


@pytest.fixture
def client(tmp_path, monkeypatch):
    """A TestClient running the real app lifespan against an isolated tmp DATA_DIR."""
    monkeypatch.setattr(settings, "DATA_DIR", tmp_path)
    with TestClient(app) as test_client:
        yield test_client


def _envelope_ok(body: dict) -> None:
    assert body["success"] is True
    assert body["error"] is None
    assert "processing_time_ms" in body["meta"]


def _envelope_error(body: dict) -> None:
    assert body["success"] is False
    assert body["data"] is None
    assert isinstance(body["error"], str) and body["error"]


def test_health_returns_200(client):
    response = client.get("/health")
    assert response.status_code == 200
    body = response.json()
    _envelope_ok(body)
    assert body["data"]["status"] == "ok"
    assert body["data"]["database"] is True


def test_full_project_crud_flow(client):
    create_response = client.post("/api/projects", json=VALID_PAYLOAD)
    assert create_response.status_code == 200
    created = create_response.json()
    _envelope_ok(created)
    project = created["data"]
    assert project["name"] == "Smoke Test Episode"
    assert project["status"] == "draft"
    assert len(project["speakers"]) == 2
    project_id = project["id"]

    list_response = client.get("/api/projects")
    assert list_response.status_code == 200
    listed = list_response.json()
    _envelope_ok(listed)
    assert any(p["id"] == project_id for p in listed["data"])

    get_response = client.get(f"/api/projects/{project_id}")
    assert get_response.status_code == 200
    fetched = get_response.json()
    _envelope_ok(fetched)
    assert fetched["data"]["id"] == project_id

    update_response = client.put(f"/api/projects/{project_id}", json={"name": "Renamed"})
    assert update_response.status_code == 200
    updated = update_response.json()
    _envelope_ok(updated)
    assert updated["data"]["name"] == "Renamed"

    delete_response = client.delete(f"/api/projects/{project_id}")
    assert delete_response.status_code == 200
    deleted = delete_response.json()
    _envelope_ok(deleted)

    get_after_delete = client.get(f"/api/projects/{project_id}")
    assert get_after_delete.status_code == 404
    _envelope_error(get_after_delete.json())


def test_get_missing_project_returns_404_envelope(client):
    response = client.get("/api/projects/does-not-exist")
    assert response.status_code == 404
    _envelope_error(response.json())


def test_create_project_invalid_cefr_returns_422_envelope(client):
    payload = {**VALID_PAYLOAD, "cefr_level": "Z9"}
    response = client.post("/api/projects", json=payload)
    assert response.status_code == 422
    body = response.json()
    _envelope_error(body)
    assert "cefr_level" in body["error"]


def test_create_project_speaker_count_mismatch_returns_422(client):
    payload = {**VALID_PAYLOAD, "num_speakers": 3}
    response = client.post("/api/projects", json=payload)
    assert response.status_code == 422
    _envelope_error(response.json())


def test_update_project_invalid_status_returns_422(client):
    create_response = client.post("/api/projects", json=VALID_PAYLOAD)
    project_id = create_response.json()["data"]["id"]

    response = client.put(f"/api/projects/{project_id}", json={"status": "not_a_real_status"})
    assert response.status_code == 422
    _envelope_error(response.json())


def test_update_project_explicit_null_returns_422(client):
    create_response = client.post("/api/projects", json=VALID_PAYLOAD)
    project_id = create_response.json()["data"]["id"]

    response = client.put(f"/api/projects/{project_id}", json={"name": None})
    assert response.status_code == 422
    body = response.json()
    _envelope_error(body)
    assert "name" in body["error"]


def test_update_project_status_skip_returns_422(client):
    create_response = client.post("/api/projects", json=VALID_PAYLOAD)
    project_id = create_response.json()["data"]["id"]

    response = client.put(f"/api/projects/{project_id}", json={"status": "audio_generated"})
    assert response.status_code == 422
    _envelope_error(response.json())


def test_update_project_status_one_step_forward_succeeds(client):
    create_response = client.post("/api/projects", json=VALID_PAYLOAD)
    project_id = create_response.json()["data"]["id"]

    response = client.put(f"/api/projects/{project_id}", json={"status": "script_generated"})
    assert response.status_code == 200
    body = response.json()
    _envelope_ok(body)
    assert body["data"]["status"] == "script_generated"


def test_update_project_config_json_stays_in_sync(client):
    create_response = client.post("/api/projects", json=VALID_PAYLOAD)
    project_id = create_response.json()["data"]["id"]

    response = client.put(f"/api/projects/{project_id}", json={"topic": "Updated topic"})
    assert response.status_code == 200
    project = response.json()["data"]

    snapshot = json.loads(project["config_json"])
    assert snapshot["topic"] == "Updated topic"
    assert snapshot["name"] == project["name"]
    assert len(snapshot["speakers"]) == project["num_speakers"]


def test_create_project_rejects_blank_name(client):
    payload = dict(VALID_PAYLOAD, name="   ")
    response = client.post("/api/projects", json=payload)
    assert response.status_code == 422
    _envelope_error(response.json())


def test_create_project_rejects_empty_or_blank_topic(client):
    for topic in ["", "   "]:
        payload = dict(VALID_PAYLOAD, topic=topic)
        response = client.post("/api/projects", json=payload)
        assert response.status_code == 422
        _envelope_error(response.json())


def test_create_project_rejects_blank_speaker_name(client):
    speakers = [
        {"name": "   ", "gender": "male", "accent": "british"},
        {"name": "Sam", "gender": "female", "accent": "british"},
    ]
    payload = dict(VALID_PAYLOAD, speakers=speakers)
    response = client.post("/api/projects", json=payload)
    assert response.status_code == 422
    _envelope_error(response.json())


def test_create_and_update_strips_surrounding_whitespace(client):
    payload = dict(
        VALID_PAYLOAD,
        name="  Trimmed Episode  ",
        topic="  Trimmed Topic  ",
        speakers=[
            {"name": "  Alex  ", "gender": "male", "accent": "british"},
            {"name": "  Sam  ", "gender": "female", "accent": "british"},
        ],
    )
    response = client.post("/api/projects", json=payload)
    assert response.status_code == 200
    data = response.json()["data"]
    assert data["name"] == "Trimmed Episode"
    assert data["topic"] == "Trimmed Topic"
    assert data["speakers"][0]["name"] == "Alex"
    assert data["speakers"][1]["name"] == "Sam"

    # Also test update strips whitespace
    update_response = client.put(
        f"/api/projects/{data['id']}", json={"name": "  Updated Name  ", "topic": "  Updated Topic  "}
    )
    assert update_response.status_code == 200
    updated_data = update_response.json()["data"]
    assert updated_data["name"] == "Updated Name"
    assert updated_data["topic"] == "Updated Topic"


def test_update_speaker_persists_engine_and_slider_changes(client):
    project = client.post("/api/projects", json=VALID_PAYLOAD).json()["data"]
    speaker_id = project["speakers"][0]["id"]

    response = client.patch(
        f"/api/projects/{project['id']}/speakers/{speaker_id}",
        json={"tts_engine": "edge_tts", "speed": 1.25, "pitch": 0.5, "volume": 0.5},
    )

    assert response.status_code == 200
    updated = next(s for s in response.json()["data"]["speakers"] if s["id"] == speaker_id)
    assert updated["tts_engine"] == "edge_tts"
    assert updated["speed"] == 1.25
    assert updated["pitch"] == 0.5
    assert updated["volume"] == 0.5
    # Untouched speaker (and untouched fields) must survive unchanged.
    other = next(s for s in response.json()["data"]["speakers"] if s["id"] != speaker_id)
    assert other["tts_engine"] == "omnivoice"


def test_update_speaker_partial_patch_leaves_other_fields_untouched(client):
    project = client.post("/api/projects", json=VALID_PAYLOAD).json()["data"]
    speaker_id = project["speakers"][0]["id"]
    client.patch(f"/api/projects/{project['id']}/speakers/{speaker_id}", json={"speed": 1.3})

    response = client.patch(f"/api/projects/{project['id']}/speakers/{speaker_id}", json={"pitch": -0.2})

    updated = next(s for s in response.json()["data"]["speakers"] if s["id"] == speaker_id)
    assert updated["speed"] == 1.3  # from the first patch, not reset
    assert updated["pitch"] == -0.2


def test_update_speaker_unknown_speaker_returns_404(client):
    project = client.post("/api/projects", json=VALID_PAYLOAD).json()["data"]
    response = client.patch(f"/api/projects/{project['id']}/speakers/does-not-exist", json={"speed": 1.1})
    assert response.status_code == 404


def test_update_speaker_unknown_project_returns_404(client):
    project = client.post("/api/projects", json=VALID_PAYLOAD).json()["data"]
    speaker_id = project["speakers"][0]["id"]
    response = client.patch(f"/api/projects/does-not-exist/speakers/{speaker_id}", json={"speed": 1.1})
    assert response.status_code == 404


def test_update_speaker_rejects_invalid_engine_and_out_of_range_slider(client):
    project = client.post("/api/projects", json=VALID_PAYLOAD).json()["data"]
    speaker_id = project["speakers"][0]["id"]

    bad_engine = client.patch(
        f"/api/projects/{project['id']}/speakers/{speaker_id}", json={"tts_engine": "not-a-real-engine"}
    )
    bad_speed = client.patch(f"/api/projects/{project['id']}/speakers/{speaker_id}", json={"speed": 99.0})

    assert bad_engine.status_code == 422
    assert bad_speed.status_code == 422


def test_update_speaker_after_script_exists_does_not_delete_script_lines(client):
    """Regression test for the exact landmine this route exists to avoid: unlike
    PUT /{project_id} with `speakers` (full delete-and-reinsert, new ids), this route
    must never cascade-delete script_lines when a script already exists."""
    project = client.post("/api/projects", json=VALID_PAYLOAD).json()["data"]
    speaker_id = project["speakers"][0]["id"]
    script_payload = {
        "lines": [
            {"speaker_id": speaker_id, "text": "Welcome to the show!"},
            {"speaker_id": project["speakers"][1]["id"], "text": "Thanks for having me."},
        ]
    }
    client.put(f"/api/projects/{project['id']}/script", json=script_payload)

    response = client.patch(
        f"/api/projects/{project['id']}/speakers/{speaker_id}", json={"speed": 1.4, "tts_engine": "edge_tts"}
    )
    assert response.status_code == 200

    script_response = client.get(f"/api/projects/{project['id']}/script")
    lines = script_response.json()["data"]
    assert len(lines) == 2
    # The speaker id itself must be unchanged too (proves no delete/reinsert happened).
    updated_speaker_id = next(
        s["id"] for s in response.json()["data"]["speakers"] if s["speed"] == 1.4
    )
    assert updated_speaker_id == speaker_id
