"""HTTP tests for audio mixing routes (Task 1.6, Sub-task 1.6b).

`tts_service._synthesize_edge_tts` is monkeypatched to skip the network, same as
tests/test_tts_api.py — but here it returns a REAL tiny decodable MP3 (a generated tone),
not a fake byte string, because these routes exercise real pydub/ffmpeg mixing and need
real audio to mix.
"""

import io

import pytest
from fastapi.testclient import TestClient
from pydub.generators import Sine

from app.core.config import settings
from app.main import app
from app.services import tts_service

PROJECT_PAYLOAD = {
    "name": "Audio API Test Episode",
    "topic": "Testing audio mixing",
    "cefr_level": "B1",
    "duration_minutes": 5,
    "num_speakers": 2,
    "genre": "small_talk",
    "accent": "american",
    "speakers": [
        {"name": "Alex", "gender": "male", "accent": "american"},
        {"name": "Sam", "gender": "female", "accent": "american"},
    ],
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
        return _real_tone_mp3_bytes(freq=440 if speaker["gender"] == "male" else 550)

    monkeypatch.setattr(tts_service, "_synthesize_edge_tts", fake_edge_tts)


def create_project(client: TestClient) -> dict:
    response = client.post("/api/projects", json=PROJECT_PAYLOAD)
    assert response.status_code == 200
    return response.json()["data"]


def save_script(client: TestClient, project: dict) -> list[dict]:
    speaker_ids = [s["id"] for s in project["speakers"]]
    payload = {
        "lines": [
            {"speaker_id": speaker_ids[0], "text": "Welcome to the show!"},
            {"speaker_id": speaker_ids[1], "text": "Thanks for having me."},
        ]
    }
    response = client.put(f"/api/projects/{project['id']}/script", json=payload)
    assert response.status_code == 200
    return response.json()["data"]


def synthesize_all(client: TestClient, project: dict, lines: list[dict]) -> None:
    for line in lines:
        response = client.post(f"/api/projects/{project['id']}/tts/preview", json={"line_id": line["id"]})
        assert response.status_code == 200


def test_generate_audio_returns_200_and_mixed_result(client: TestClient):
    project = create_project(client)
    lines = save_script(client, project)
    synthesize_all(client, project, lines)

    response = client.post(f"/api/projects/{project['id']}/audio/generate", json={})

    assert response.status_code == 200
    data = response.json()["data"]
    assert data["status"] == "complete"
    assert data["mp3_path"]
    assert data["wav_path"]
    assert len(data["timestamps"]) == 2
    assert data["loudness_lufs"] == pytest.approx(-16, abs=1.0)


def test_generate_audio_advances_project_status_to_audio_generated(client: TestClient):
    project = create_project(client)
    lines = save_script(client, project)
    synthesize_all(client, project, lines)

    client.post(f"/api/projects/{project['id']}/audio/generate", json={})

    response = client.get(f"/api/projects/{project['id']}")
    assert response.json()["data"]["status"] == "audio_generated"


def test_generate_audio_fails_when_a_line_has_no_synthesized_audio(client: TestClient):
    project = create_project(client)
    save_script(client, project)  # no preview calls -> no audio_cache_path

    response = client.post(f"/api/projects/{project['id']}/audio/generate", json={})

    assert response.status_code == 500
    assert response.json()["success"] is False


def test_generate_audio_empty_script_returns_422(client: TestClient):
    project = create_project(client)
    response = client.post(f"/api/projects/{project['id']}/audio/generate", json={})
    assert response.status_code == 422


def test_generate_audio_missing_project_returns_404(client: TestClient):
    response = client.post("/api/projects/does-not-exist/audio/generate", json={})
    assert response.status_code == 404


def test_status_returns_404_before_generate(client: TestClient):
    project = create_project(client)
    response = client.get(f"/api/projects/{project['id']}/audio/status")
    assert response.status_code == 404


def test_status_returns_job_after_generate(client: TestClient):
    project = create_project(client)
    lines = save_script(client, project)
    synthesize_all(client, project, lines)
    client.post(f"/api/projects/{project['id']}/audio/generate", json={})

    response = client.get(f"/api/projects/{project['id']}/audio/status")

    assert response.status_code == 200
    assert response.json()["data"]["status"] == "complete"


def test_download_returns_404_before_generate(client: TestClient):
    project = create_project(client)
    response = client.get(f"/api/projects/{project['id']}/audio/download")
    assert response.status_code == 404


def test_download_mp3_and_wav_after_generate(client: TestClient):
    project = create_project(client)
    lines = save_script(client, project)
    synthesize_all(client, project, lines)
    client.post(f"/api/projects/{project['id']}/audio/generate", json={})

    mp3_response = client.get(f"/api/projects/{project['id']}/audio/download?format=mp3")
    wav_response = client.get(f"/api/projects/{project['id']}/audio/download?format=wav")

    assert mp3_response.status_code == 200
    assert mp3_response.headers["content-type"] == "audio/mpeg"
    assert wav_response.status_code == 200
    assert wav_response.headers["content-type"] == "audio/wav"


def test_download_unsupported_format_returns_422(client: TestClient):
    project = create_project(client)
    lines = save_script(client, project)
    synthesize_all(client, project, lines)
    client.post(f"/api/projects/{project['id']}/audio/generate", json={})

    response = client.get(f"/api/projects/{project['id']}/audio/download?format=ogg")
    assert response.status_code == 422


def test_generate_audio_with_background_music_filename(client: TestClient, tmp_path):
    project = create_project(client)
    lines = save_script(client, project)
    synthesize_all(client, project, lines)
    music_dir = settings.DATA_DIR / "music_library"
    music_dir.mkdir(parents=True, exist_ok=True)
    Sine(220).to_audio_segment(duration=3000).export(str(music_dir / "bg.mp3"), format="mp3", bitrate="192k")

    response = client.post(
        f"/api/projects/{project['id']}/audio/generate", json={"background_music": "bg.mp3"}
    )

    assert response.status_code == 200
    assert response.json()["data"]["background_music"] == "bg.mp3"


def test_generate_audio_with_unknown_background_music_returns_500(client: TestClient):
    project = create_project(client)
    lines = save_script(client, project)
    synthesize_all(client, project, lines)

    response = client.post(
        f"/api/projects/{project['id']}/audio/generate", json={"background_music": "does-not-exist.mp3"}
    )

    assert response.status_code == 500
