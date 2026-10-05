"""HTTP and filesystem safety tests for the Music Library API."""

from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from threading import Barrier

import pytest
from fastapi.testclient import TestClient

from app.api import music as music_api
from app.core.config import settings
from app.core.constants import MAX_MUSIC_UPLOAD_MB
from app.core.exceptions import ValidationError
from app.main import app

VALID_MP3 = b"ID3\x04\x00\x00\x00\x00\x00\x00music-data"
VALID_FRAME_MP3 = b"\xff\xfb\x90\x64music-data"
VALID_WAV = b"RIFF\x10\x00\x00\x00WAVEfmt music-data"


@pytest.fixture
def client(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    """Run the API against an isolated music-library directory."""
    monkeypatch.setattr(settings, "DATA_DIR", tmp_path)
    with TestClient(app) as test_client:
        yield test_client


def upload(client: TestClient, filename: str, content: bytes) -> object:
    """Upload one fixture file through the multipart API."""
    return client.post("/api/music", files={"file": (filename, content)})


def test_list_music_returns_only_supported_audio_with_preview_urls(client: TestClient):
    music_dir = settings.DATA_DIR / "music_library"
    (music_dir / "theme.mp3").write_bytes(VALID_MP3)
    (music_dir / "notes.txt").write_text("not audio", encoding="utf-8")

    response = client.get("/api/music")

    assert response.status_code == 200
    assert response.json()["data"] == [
        {
            "filename": "theme.mp3",
            "size_bytes": len(VALID_MP3),
            "content_url": "/api/music/theme.mp3",
        }
    ]


@pytest.mark.parametrize(
    ("filename", "content"),
    [("theme.mp3", VALID_MP3), ("frame.mp3", VALID_FRAME_MP3), ("theme.wav", VALID_WAV)],
)
def test_upload_accepts_valid_mp3_and_wav(client: TestClient, filename: str, content: bytes):
    response = upload(client, filename, content)

    assert response.status_code == 200
    stored = settings.DATA_DIR / "music_library" / filename
    assert stored.read_bytes() == content
    assert response.json()["data"]["filename"] == filename


def test_upload_auto_suffixes_duplicate_names_without_overwrite(client: TestClient):
    first = upload(client, "theme.mp3", VALID_MP3)
    second = upload(client, "theme.mp3", VALID_FRAME_MP3)

    assert first.json()["data"]["filename"] == "theme.mp3"
    assert second.json()["data"]["filename"] == "theme (1).mp3"
    music_dir = settings.DATA_DIR / "music_library"
    assert (music_dir / "theme.mp3").read_bytes() == VALID_MP3
    assert (music_dir / "theme (1).mp3").read_bytes() == VALID_FRAME_MP3


def test_atomic_placement_preserves_concurrent_same_name_uploads(tmp_path: Path):
    music_dir = tmp_path / "music_library"
    music_dir.mkdir()
    temporary_paths = [music_dir / ".first.upload", music_dir / ".second.upload"]
    temporary_paths[0].write_bytes(VALID_MP3)
    temporary_paths[1].write_bytes(VALID_FRAME_MP3)
    ready = Barrier(len(temporary_paths))

    def place(temporary_path: Path) -> Path:
        ready.wait()
        return music_api._place_without_overwrite(temporary_path, "theme.mp3")

    with ThreadPoolExecutor(max_workers=len(temporary_paths)) as executor:
        stored_paths = list(executor.map(place, temporary_paths))

    assert {path.name for path in stored_paths} == {"theme.mp3", "theme (1).mp3"}
    assert {path.read_bytes() for path in stored_paths} == {VALID_MP3, VALID_FRAME_MP3}


@pytest.mark.parametrize(
    ("filename", "content"),
    [("fake.mp3", b"not-an-mp3"), ("fake.wav", b"RIFFmissing-wave")],
)
def test_upload_rejects_spoofed_extensions_and_cleans_temporary_file(
    client: TestClient, filename: str, content: bytes
):
    response = upload(client, filename, content)

    assert response.status_code == 422
    assert response.json()["success"] is False
    assert list((settings.DATA_DIR / "music_library").iterdir()) == []


def test_upload_rejects_unsupported_and_empty_files(client: TestClient):
    unsupported = upload(client, "track.txt", b"ID3data")
    empty = upload(client, "track.mp3", b"")

    assert unsupported.status_code == 422
    assert empty.status_code == 422
    assert list((settings.DATA_DIR / "music_library").iterdir()) == []


def test_upload_rejects_files_over_configured_limit_and_cleans_partial_file(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
):
    monkeypatch.setattr(music_api, "MAX_MUSIC_UPLOAD_BYTES", len(VALID_MP3) - 1)

    response = upload(client, "large.mp3", VALID_MP3)

    assert response.status_code == 413
    assert f"{MAX_MUSIC_UPLOAD_MB} MB or smaller" in response.json()["error"]
    assert list((settings.DATA_DIR / "music_library").iterdir()) == []


def test_preview_streams_audio_bytes_with_media_type(client: TestClient):
    upload(client, "theme.mp3", VALID_MP3)

    response = client.get("/api/music/theme.mp3")

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("audio/mpeg")
    assert response.content == VALID_MP3


def test_delete_removes_track_and_missing_track_returns_404(client: TestClient):
    upload(client, "theme.wav", VALID_WAV)

    deleted = client.delete("/api/music/theme.wav")
    missing = client.delete("/api/music/theme.wav")

    assert deleted.status_code == 200
    assert deleted.json()["data"] == {"filename": "theme.wav"}
    assert not (settings.DATA_DIR / "music_library" / "theme.wav").exists()
    assert missing.status_code == 404
    assert missing.json()["error"] == "Music track not found."


@pytest.mark.parametrize("filename", ["../outside.mp3", "folder/track.mp3", "folder\\track.mp3"])
def test_filename_validation_rejects_path_traversal(filename: str):
    with pytest.raises(ValidationError, match="safe filename"):
        music_api._validate_filename(filename, music_api.UPLOAD_EXTENSIONS)
