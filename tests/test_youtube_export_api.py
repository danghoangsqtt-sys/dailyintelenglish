"""HTTP tests for the full YouTube package .zip export (Task 1.9, Sub-task 1.9b).

Exercises the real chain end-to-end: real script -> real Edge TTS (network mocked, real
decodable audio) -> real AudioService mix -> real VideoService render -> real Pillow
thumbnail render (only the Gemini text call is mocked) -> real zip assembly. Only the two
Gemini-backed calls (YouTube package text, thumbnail suggestions) are mocked.
"""

import io
import json
import zipfile

import pytest
from fastapi.testclient import TestClient
from pydub.generators import Sine

from app.core.config import settings
from app.main import app
from app.services import thumbnail_service, tts_service, youtube_service

PROJECT_PAYLOAD = {
    "name": "Export API Test Episode",
    "topic": "Testing full package export",
    "cefr_level": "B1",
    "duration_minutes": 5,
    "num_speakers": 1,
    "genre": "small_talk",
    "accent": "american",
    "speakers": [{"name": "Alex", "gender": "male", "accent": "american"}],
}

VALID_YOUTUBE_PACKAGE = {
    "titles": [
        {"variant": "click_worthy", "text": "You Won't Believe This Test Episode"},
        {"variant": "educational", "text": "Learn English: Export Testing (B1)"},
        {"variant": "seo", "text": "Export Testing English Podcast B1"},
    ],
    "description": "A test episode about full package export.",
    "tags": ["testing", "export", "b1 podcast"],
}


def _thumbnail_suggestion_json() -> str:
    colors = [
        ("#111827", "#60A5FA", "#F59E0B"),
        ("#3B0764", "#C084FC", "#22D3EE"),
        ("#052E16", "#4ADE80", "#FDE047"),
    ]
    variants = [
        {
            "headline": f"Concept {i + 1}",
            "supporting_text": "Practical English",
            "topic_keywords": ["testing", f"concept-{i + 1}"],
            "palette": {"primary": p, "secondary": s, "accent": a, "text": "#FFFFFF"},
        }
        for i, (p, s, a) in enumerate(colors)
    ]
    return json.dumps({"variants": variants})


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "DATA_DIR", tmp_path)
    monkeypatch.setattr(settings, "GEMINI_API_KEY", "test-key")

    async def fake_edge_tts(text: str, speaker: dict) -> bytes:
        buffer = io.BytesIO()
        Sine(440).to_audio_segment(duration=500).apply_gain(-20).export(buffer, format="mp3", bitrate="192k")
        return buffer.getvalue()

    async def fake_generate_package(project_dict, script_lines, timestamps=None):
        return {**VALID_YOUTUBE_PACKAGE, "chapters_text": "00:00 Introduction", "chapters_estimated": timestamps is None}

    async def fake_thumbnail_generate(prompt: str, schema: dict) -> str:
        return _thumbnail_suggestion_json()

    monkeypatch.setattr(tts_service, "_synthesize_edge_tts", fake_edge_tts)
    monkeypatch.setattr(youtube_service, "generate_package", fake_generate_package)
    monkeypatch.setattr(thumbnail_service, "_generate_with_retry", fake_thumbnail_generate)

    with TestClient(app) as test_client:
        yield test_client


def create_project(client: TestClient) -> dict:
    response = client.post("/api/projects", json=PROJECT_PAYLOAD)
    assert response.status_code == 200
    return response.json()["data"]


def save_script(client: TestClient, project: dict) -> list[dict]:
    speaker_id = project["speakers"][0]["id"]
    response = client.put(
        f"/api/projects/{project['id']}/script", json={"lines": [{"speaker_id": speaker_id, "text": "Welcome!"}]}
    )
    assert response.status_code == 200
    return response.json()["data"]


def build_full_pipeline(client: TestClient, project: dict, lines: list[dict]) -> None:
    for line in lines:
        assert client.post(f"/api/projects/{project['id']}/tts/preview", json={"line_id": line["id"]}).status_code == 200
    assert client.post(f"/api/projects/{project['id']}/audio/generate", json={}).status_code == 200
    assert (
        client.post(f"/api/projects/{project['id']}/video/generate", json={"template_id": "midnight"}).status_code
        == 200
    )
    thumbnails = client.post(
        f"/api/projects/{project['id']}/thumbnails/generate",
        json={"template_name": "minimal_clean", "variant_count": 3},
    ).json()["data"]
    favorite_id = thumbnails[0]["id"]
    assert client.put(f"/api/projects/{project['id']}/thumbnails/{favorite_id}/favorite").status_code == 200
    assert client.post(f"/api/projects/{project['id']}/youtube/generate").status_code == 200


def test_export_returns_a_real_zip_with_all_four_files(client: TestClient):
    project = create_project(client)
    lines = save_script(client, project)
    build_full_pipeline(client, project, lines)

    response = client.get(f"/api/projects/{project['id']}/youtube/export")

    assert response.status_code == 200
    assert response.headers["content-type"] == "application/zip"
    with zipfile.ZipFile(io.BytesIO(response.content)) as archive:
        names = set(archive.namelist())
        assert names == {"video.mp4", "subtitles.srt", "thumbnail.png", "metadata.txt"}
        assert len(archive.read("video.mp4")) > 0
        assert len(archive.read("thumbnail.png")) > 0
        metadata = archive.read("metadata.txt").decode("utf-8")
        assert "Measured (from real audio)" in metadata
        assert VALID_YOUTUBE_PACKAGE["description"] in metadata


def test_export_before_anything_generated_returns_422_naming_all_missing_pieces(client: TestClient):
    project = create_project(client)

    response = client.get(f"/api/projects/{project['id']}/youtube/export")

    assert response.status_code == 422
    error = response.json()["error"]
    assert "YouTube package" in error
    assert "video" in error
    assert "thumbnail" in error


def test_export_missing_video_returns_422(client: TestClient):
    project = create_project(client)
    lines = save_script(client, project)
    for line in lines:
        client.post(f"/api/projects/{project['id']}/tts/preview", json={"line_id": line["id"]})
    client.post(f"/api/projects/{project['id']}/audio/generate", json={})
    thumbnails = client.post(
        f"/api/projects/{project['id']}/thumbnails/generate",
        json={"template_name": "minimal_clean", "variant_count": 3},
    ).json()["data"]
    client.put(f"/api/projects/{project['id']}/thumbnails/{thumbnails[0]['id']}/favorite")
    client.post(f"/api/projects/{project['id']}/youtube/generate")

    response = client.get(f"/api/projects/{project['id']}/youtube/export")

    assert response.status_code == 422
    assert "video" in response.json()["error"]


def test_export_missing_project_returns_404(client: TestClient):
    response = client.get("/api/projects/does-not-exist/youtube/export")
    assert response.status_code == 404
