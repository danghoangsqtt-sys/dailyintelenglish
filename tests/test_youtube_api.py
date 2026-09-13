"""HTTP tests for YouTube Package routes (Task 1.9, Sub-task 1.9a).

youtube_service.generate_package is monkeypatched — no real network calls,
mirrors tests/test_learning_api.py's approach for Learning Content.
"""

import pytest
from fastapi.testclient import TestClient

from app.core.config import settings
from app.core.exceptions import YouTubePackageGenerationError
from app.main import app
from app.services import youtube_service

PROJECT_PAYLOAD = {
    "name": "YouTube API Test Episode",
    "topic": "Remote work culture",
    "cefr_level": "B1",
    "duration_minutes": 8,
    "num_speakers": 2,
    "genre": "interview",
    "accent": "american",
    "speakers": [
        {"name": "Alex", "gender": "male", "accent": "american"},
        {"name": "Sam", "gender": "female", "accent": "american"},
    ],
}

VALID_PACKAGE = {
    "titles": [
        {"variant": "click_worthy", "text": "You Won't Believe How Remote Work Changed"},
        {"variant": "educational", "text": "Learn English: Remote Work Vocabulary (B1)"},
        {"variant": "seo", "text": "Remote Work English Podcast B1 Interview"},
    ],
    "description": "An English-learning podcast episode about remote work culture, B1 level.",
    "tags": ["remote work", "english learning", "b1 podcast"],
    "chapters_text": "00:00 Introduction",
}


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "DATA_DIR", tmp_path)
    with TestClient(app) as test_client:
        yield test_client


def create_project(client: TestClient) -> dict:
    response = client.post("/api/projects", json=PROJECT_PAYLOAD)
    assert response.status_code == 200
    return response.json()["data"]


def save_script(client: TestClient, project: dict) -> None:
    speaker_ids = [s["id"] for s in project["speakers"]]
    payload = {
        "lines": [
            {"speaker_id": speaker_ids[0], "text": "Welcome to the show!"},
            {"speaker_id": speaker_ids[1], "text": "Thanks for having me."},
        ]
    }
    response = client.put(f"/api/projects/{project['id']}/script", json=payload)
    assert response.status_code == 200


def _envelope_ok(body: dict) -> None:
    assert body["success"] is True
    assert body["error"] is None


def _envelope_error(body: dict) -> None:
    assert body["success"] is False
    assert body["data"] is None
    assert isinstance(body["error"], str) and body["error"]


# --- POST /youtube/generate ---


def test_generate_returns_200_and_persists(client: TestClient, monkeypatch):
    project = create_project(client)
    save_script(client, project)

    async def fake_generate_package(project_dict, script_lines, timestamps=None):
        assert project_dict["id"] == project["id"]
        assert len(script_lines) == 2
        return VALID_PACKAGE

    monkeypatch.setattr(youtube_service, "generate_package", fake_generate_package)

    response = client.post(f"/api/projects/{project['id']}/youtube/generate")

    assert response.status_code == 200
    body = response.json()
    _envelope_ok(body)
    assert len(body["data"]["titles"]) == 3
    assert body["data"]["chapters_text"] == "00:00 Introduction"
    assert body["data"]["tags"] == VALID_PACKAGE["tags"]


def test_generate_empty_script_returns_422(client: TestClient):
    project = create_project(client)

    response = client.post(f"/api/projects/{project['id']}/youtube/generate")

    assert response.status_code == 422
    _envelope_error(response.json())


def test_generate_missing_project_returns_404(client: TestClient):
    response = client.post("/api/projects/does-not-exist/youtube/generate")

    assert response.status_code == 404
    _envelope_error(response.json())


def test_generate_gemini_failure_returns_502(client: TestClient, monkeypatch):
    project = create_project(client)
    save_script(client, project)

    async def failing_generate_package(project_dict, script_lines, timestamps=None):
        raise YouTubePackageGenerationError("Gemini API returned HTTP 429 after 4 attempt(s): rate limited")

    monkeypatch.setattr(youtube_service, "generate_package", failing_generate_package)

    response = client.post(f"/api/projects/{project['id']}/youtube/generate")

    assert response.status_code == 502
    _envelope_error(response.json())


# --- GET /youtube ---


def test_get_returns_null_before_generation(client: TestClient):
    project = create_project(client)

    response = client.get(f"/api/projects/{project['id']}/youtube")

    assert response.status_code == 200
    body = response.json()
    _envelope_ok(body)
    assert body["data"] is None


def test_get_returns_package_after_generate(client: TestClient, monkeypatch):
    project = create_project(client)
    save_script(client, project)

    async def fake_generate_package(project_dict, script_lines, timestamps=None):
        return VALID_PACKAGE

    monkeypatch.setattr(youtube_service, "generate_package", fake_generate_package)
    client.post(f"/api/projects/{project['id']}/youtube/generate")

    response = client.get(f"/api/projects/{project['id']}/youtube")

    assert response.status_code == 200
    body = response.json()
    _envelope_ok(body)
    assert len(body["data"]["titles"]) == 3


def test_get_missing_project_returns_404(client: TestClient):
    response = client.get("/api/projects/does-not-exist/youtube")

    assert response.status_code == 404
    _envelope_error(response.json())


def test_regenerate_replaces_previous_package(client: TestClient, monkeypatch):
    project = create_project(client)
    save_script(client, project)

    async def fake_generate_package(project_dict, script_lines, timestamps=None):
        return VALID_PACKAGE

    monkeypatch.setattr(youtube_service, "generate_package", fake_generate_package)
    first = client.post(f"/api/projects/{project['id']}/youtube/generate").json()["data"]

    async def fake_generate_package_v2(project_dict, script_lines, timestamps=None):
        return {**VALID_PACKAGE, "description": "A regenerated description."}

    monkeypatch.setattr(youtube_service, "generate_package", fake_generate_package_v2)
    second = client.post(f"/api/projects/{project['id']}/youtube/generate").json()["data"]

    assert first["id"] == second["id"]
    assert second["description"] == "A regenerated description."
