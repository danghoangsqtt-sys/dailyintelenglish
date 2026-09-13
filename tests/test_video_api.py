"""HTTP tests for video generation routes (Task 1.7, Sub-task 1.7a).

Same real-tone-MP3 approach as tests/test_audio_api.py: only the Edge TTS network call is
mocked (with real decodable audio), so the audio mix -> video render chain underneath is
exercised for real (real ffmpeg, real pydub, real subtitle burn-in).
"""

import io

import pytest
from fastapi.testclient import TestClient
from pydub.generators import Sine

from app.core.config import settings
from app.main import app
from app.services import tts_service

PROJECT_PAYLOAD = {
    "name": "Video API Test Episode",
    "topic": "Testing video generation",
    "cefr_level": "B1",
    "duration_minutes": 5,
    "num_speakers": 1,
    "genre": "small_talk",
    "accent": "american",
    "speakers": [{"name": "Alex", "gender": "male", "accent": "american"}],
}


def _real_tone_mp3_bytes(freq: int = 440) -> bytes:
    buffer = io.BytesIO()
    Sine(freq).to_audio_segment(duration=500).apply_gain(-20).export(buffer, format="mp3", bitrate="192k")
    return buffer.getvalue()


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "DATA_DIR", tmp_path)
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture(autouse=True)
def _fake_edge_tts(monkeypatch):
    async def fake_edge_tts(text: str, speaker: dict) -> bytes:
        return _real_tone_mp3_bytes()

    monkeypatch.setattr(tts_service, "_synthesize_edge_tts", fake_edge_tts)


def create_project(client: TestClient) -> dict:
    response = client.post("/api/projects", json=PROJECT_PAYLOAD)
    assert response.status_code == 200
    return response.json()["data"]


def save_script(client: TestClient, project: dict) -> list[dict]:
    speaker_id = project["speakers"][0]["id"]
    payload = {"lines": [{"speaker_id": speaker_id, "text": "Welcome to the show!"}]}
    response = client.put(f"/api/projects/{project['id']}/script", json=payload)
    assert response.status_code == 200
    return response.json()["data"]


def generate_audio(client: TestClient, project: dict, lines: list[dict]) -> None:
    for line in lines:
        response = client.post(f"/api/projects/{project['id']}/tts/preview", json={"line_id": line["id"]})
        assert response.status_code == 200
    response = client.post(f"/api/projects/{project['id']}/audio/generate", json={})
    assert response.status_code == 200


def test_list_templates_returns_three_options(client: TestClient):
    response = client.get("/api/video/templates")
    assert response.status_code == 200
    ids = {t["id"] for t in response.json()["data"]}
    assert ids == {"midnight", "deep_purple", "charcoal_wave"}


def test_generate_video_returns_200_after_audio_exists(client: TestClient):
    project = create_project(client)
    lines = save_script(client, project)
    generate_audio(client, project, lines)

    response = client.post(f"/api/projects/{project['id']}/video/generate", json={"template_id": "midnight"})

    assert response.status_code == 200
    data = response.json()["data"]
    assert data["status"] == "complete"
    assert data["mp4_path"]
    assert data["srt_path"]
    assert data["background_image"] == "midnight"


def test_generate_video_advances_project_status_to_video_generated(client: TestClient):
    project = create_project(client)
    lines = save_script(client, project)
    generate_audio(client, project, lines)

    client.post(f"/api/projects/{project['id']}/video/generate", json={"template_id": "midnight"})

    response = client.get(f"/api/projects/{project['id']}")
    assert response.json()["data"]["status"] == "video_generated"


def test_generate_video_before_audio_returns_422(client: TestClient):
    project = create_project(client)
    save_script(client, project)  # no audio generated yet

    response = client.post(f"/api/projects/{project['id']}/video/generate", json={"template_id": "midnight"})

    assert response.status_code == 422


def test_generate_video_unknown_template_returns_422(client: TestClient):
    project = create_project(client)
    lines = save_script(client, project)
    generate_audio(client, project, lines)

    response = client.post(
        f"/api/projects/{project['id']}/video/generate", json={"template_id": "not-a-real-template"}
    )

    assert response.status_code == 422


def test_generate_video_missing_project_returns_404(client: TestClient):
    response = client.post("/api/projects/does-not-exist/video/generate", json={"template_id": "midnight"})
    assert response.status_code == 404


def test_status_returns_404_before_generate(client: TestClient):
    project = create_project(client)
    response = client.get(f"/api/projects/{project['id']}/video/status")
    assert response.status_code == 404


def test_status_returns_job_after_generate(client: TestClient):
    project = create_project(client)
    lines = save_script(client, project)
    generate_audio(client, project, lines)
    client.post(f"/api/projects/{project['id']}/video/generate", json={"template_id": "charcoal_wave"})

    response = client.get(f"/api/projects/{project['id']}/video/status")

    assert response.status_code == 200
    assert response.json()["data"]["status"] == "complete"


def test_download_returns_404_before_generate(client: TestClient):
    project = create_project(client)
    response = client.get(f"/api/projects/{project['id']}/video/download")
    assert response.status_code == 404


def test_download_mp4_and_srt_after_generate(client: TestClient):
    project = create_project(client)
    lines = save_script(client, project)
    generate_audio(client, project, lines)
    client.post(f"/api/projects/{project['id']}/video/generate", json={"template_id": "deep_purple"})

    mp4_response = client.get(f"/api/projects/{project['id']}/video/download?format=mp4")
    srt_response = client.get(f"/api/projects/{project['id']}/video/download?format=srt")

    assert mp4_response.status_code == 200
    assert mp4_response.headers["content-type"] == "video/mp4"
    assert srt_response.status_code == 200
    assert "Alex: Welcome to the show!" in srt_response.text


def test_download_unsupported_format_returns_422(client: TestClient):
    project = create_project(client)
    lines = save_script(client, project)
    generate_audio(client, project, lines)
    client.post(f"/api/projects/{project['id']}/video/generate", json={"template_id": "midnight"})

    response = client.get(f"/api/projects/{project['id']}/video/download?format=avi")
    assert response.status_code == 422
