"""HTTP audition contracts, isolated cache, expiry, errors and quota."""

import asyncio
import hashlib
import os

import pytest
from fastapi.testclient import TestClient

from backend.ai.tts import tts_service, voice_catalog_service, voice_preview_service as previews
from backend.core.config import settings
from backend.main import app
from tests.test_tts_api import PROJECT_PAYLOAD
from tests.test_voice_catalog import ROWS

PAYLOAD = {"voice_id": "en-US-AndrewNeural", "text": "Clear explanations begin with a simple example."}


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "DATA_DIR", tmp_path)

    async def voices():
        return ROWS

    async def synth(text, speaker):
        return f"audio:{speaker['voice_id']}:{text}:{speaker['speed']}".encode(), []

    monkeypatch.setattr(voice_catalog_service.edge_tts, "list_voices", voices)
    monkeypatch.setattr(tts_service, "_synthesize_edge_tts", synth)
    with TestClient(app) as value:
        yield value


def audition(client, payload=None):
    response = client.post("/api/tts/voices/preview", json=payload or PAYLOAD)
    assert response.status_code == 200, response.text
    return response.json()["data"]


def test_routes_serve_typed_catalog_and_opaque_preview(client):
    response = client.get("/api/tts/voices?gender=male&locale=en-US")
    assert response.status_code == 200
    assert len(response.json()["data"]["voices"]) == 2
    result = audition(client)
    assert len(result["id"]) == 64
    assert result["voice"]["voice_id"] == PAYLOAD["voice_id"]
    assert "audio_path" not in result
    media = client.get(result["audio_url"])
    assert media.headers["content-type"] == "audio/mpeg"
    assert PAYLOAD["voice_id"].encode() in media.content
    assert media.headers["cache-control"] == "no-store"


def test_audition_does_not_write_project_or_production_line_cache(client, tmp_path):
    project = client.post("/api/projects", json=PROJECT_PAYLOAD).json()["data"]
    sid = project["speakers"][0]["id"]
    script_url = f"/api/projects/{project['id']}/script"
    lines = client.put(script_url, json={"lines": [{"speaker_id": sid, "text": "Keep this line."}]}).json()["data"]
    production = tmp_path / "tts_cache" / project["id"]
    production.mkdir(parents=True)
    sentinel = production / f"{lines[0]['id']}.mp3"
    sentinel.write_bytes(b"original-production-audio")
    before = client.get(script_url).json()["data"]
    db_hash = hashlib.sha256((tmp_path / "app.db").read_bytes()).hexdigest()
    audition(client)
    assert client.get(script_url).json()["data"] == before
    assert hashlib.sha256((tmp_path / "app.db").read_bytes()).hexdigest() == db_hash
    assert sentinel.read_bytes() == b"original-production-audio"
    assert list(production.iterdir()) == [sentinel]


def test_cache_identity_includes_voice_text_and_parameters(client, monkeypatch):
    first = audition(client)

    async def forbidden(*args):
        raise AssertionError("Identical audition should reuse its isolated cache")

    monkeypatch.setattr(tts_service, "_synthesize_edge_tts", forbidden)
    assert audition(client)["id"] == first["id"]


@pytest.mark.parametrize("patch", [
    {"voice_id": "en-US-GuyNeural"}, {"text": "Another example."},
    {"speed": 1.1}, {"pitch": 0.2}, {"volume": 0.9},
])
def test_different_selection_has_distinct_cache(client, patch):
    assert audition(client)["id"] != audition(client, {**PAYLOAD, **patch})["id"]


@pytest.mark.parametrize("patch", [
    {"voice_id": "en-US-UnknownNeural"}, {"voice_id": "vi-VN-HoaiMyNeural"},
    {"text": " "}, {"text": "x" * 501}, {"speed": 4}, {"pitch": 2}, {"volume": -1},
    {"engine": "paid"}, {"unexpected": "field"},
])
def test_invalid_audition_is_422(client, patch):
    assert client.post("/api/tts/voices/preview", json={**PAYLOAD, **patch}).status_code == 422


def test_expired_and_unknown_media_are_404(client, tmp_path):
    result = audition(client)
    path = tmp_path / "tts_preview" / f"{result['id']}.mp3"
    os.utime(path, (0, 0))
    assert client.get(result["audio_url"]).status_code == 404
    assert client.get("/api/tts/voices/preview/not-an-id.mp3").status_code == 404
    assert client.get("/api/tts/voices/preview/" + "0" * 64 + ".mp3").status_code == 404


def test_cleanup_ttl_and_quota_never_delete_production_files(client, tmp_path, monkeypatch):
    root = tmp_path / "tts_preview"
    root.mkdir()
    expired = root / ("1" * 64 + ".mp3")
    expired.write_bytes(b"expired")
    os.utime(expired, (0, 0))
    old = root / ("2" * 64 + ".mp3")
    old.write_bytes(b"a" * 100)
    unrelated = tmp_path / "tts_cache" / "sentinel.mp3"
    unrelated.parent.mkdir(exist_ok=True)
    unrelated.write_bytes(b"production")
    monkeypatch.setattr(previews, "VOICE_PREVIEW_MAX_BYTES", 110)
    result = audition(client)
    assert not expired.exists() and not old.exists()
    assert (root / f"{result['id']}.mp3").is_file()
    assert unrelated.read_bytes() == b"production"


def test_preview_timeout_is_visible_and_writes_no_audio(client, tmp_path, monkeypatch):
    async def stuck(*args):
        await asyncio.Event().wait()

    monkeypatch.setattr(tts_service, "_synthesize_edge_tts", stuck)
    monkeypatch.setattr(previews, "VOICE_PREVIEW_TIMEOUT_SECONDS", 0.01)
    response = client.post("/api/tts/voices/preview", json=PAYLOAD)
    assert response.status_code == 502 and "timed out" in response.json()["error"]
    assert not list((tmp_path / "tts_preview").glob("*.mp3"))
