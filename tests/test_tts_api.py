"""HTTP tests for TTS routes (Task 1.6, Sub-task 1.6a).

tts_service._synthesize_edge_tts is monkeypatched — no real network calls in the
suite, same approach as tests/test_learning_api.py for Gemini.
"""

import pytest
from fastapi.testclient import TestClient

from app.core.config import settings
from app.main import app
from app.services import tts_service

PROJECT_PAYLOAD = {
    "name": "TTS API Test Episode",
    "topic": "Testing preview route",
    "cefr_level": "B1",
    "duration_minutes": 5,
    "num_speakers": 1,
    "genre": "small_talk",
    "accent": "american",
    "speakers": [{"name": "Alex", "gender": "male", "accent": "american"}],
}

FAKE_MP3_BYTES = b"fake-mp3-bytes"


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "DATA_DIR", tmp_path)
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture(autouse=True)
def _fake_edge_tts(monkeypatch):
    async def fake_edge_tts(text: str, speaker: dict) -> bytes:
        return FAKE_MP3_BYTES

    monkeypatch.setattr(tts_service, "_synthesize_edge_tts", fake_edge_tts)


def create_project(client: TestClient) -> dict:
    response = client.post("/api/projects", json=PROJECT_PAYLOAD)
    assert response.status_code == 200
    return response.json()["data"]


def save_script(client: TestClient, project: dict) -> dict:
    speaker_id = project["speakers"][0]["id"]
    payload = {"lines": [{"speaker_id": speaker_id, "text": "Hello, this is a test line."}]}
    response = client.put(f"/api/projects/{project['id']}/script", json=payload)
    assert response.status_code == 200
    return response.json()["data"][0]


def test_preview_line_returns_200_with_audio_path_and_engine(client: TestClient):
    project = create_project(client)
    line = save_script(client, project)

    response = client.post(f"/api/projects/{project['id']}/tts/preview", json={"line_id": line["id"]})

    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    assert body["data"]["engine_used"] == "edge_tts"
    assert body["data"]["audio_path"]


def test_preview_line_missing_project_returns_404(client: TestClient):
    response = client.post("/api/projects/does-not-exist/tts/preview", json={"line_id": "line-1"})
    assert response.status_code == 404


def test_preview_line_unknown_line_id_returns_404(client: TestClient):
    project = create_project(client)
    response = client.post(f"/api/projects/{project['id']}/tts/preview", json={"line_id": "does-not-exist"})
    assert response.status_code == 404


def test_preview_line_missing_body_returns_422(client: TestClient):
    project = create_project(client)
    response = client.post(f"/api/projects/{project['id']}/tts/preview", json={})
    assert response.status_code == 422


def test_get_cached_audio_returns_404_before_preview_generated(client: TestClient):
    project = create_project(client)
    line = save_script(client, project)
    response = client.get(f"/api/projects/{project['id']}/tts/cache/{line['id']}.mp3")
    assert response.status_code == 404


def test_get_cached_audio_returns_audio_after_preview(client: TestClient):
    project = create_project(client)
    line = save_script(client, project)
    client.post(f"/api/projects/{project['id']}/tts/preview", json={"line_id": line["id"]})

    response = client.get(f"/api/projects/{project['id']}/tts/cache/{line['id']}.mp3")

    assert response.status_code == 200
    assert response.content == FAKE_MP3_BYTES


def test_engines_endpoint_still_works(client: TestClient):
    response = client.get("/api/tts/engines")
    assert response.status_code == 200
    ids = [engine["id"] for engine in response.json()["data"]]
    assert "omnivoice" in ids
    assert "edge_tts" in ids
