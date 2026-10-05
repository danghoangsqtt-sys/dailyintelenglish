"""Task 22.7: Music Library track details -- measured length, guessed title, mood/tags, licence."""

import sqlite3
import subprocess
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.core.config import settings
from app.main import app
from app.services import music_library_service as library


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "DATA_DIR", tmp_path)
    with TestClient(app) as test_client:
        yield test_client


def data(response):
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["success"] is True
    return body["data"]


def make_mp3(path: Path, seconds: float) -> bytes:
    path.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run([settings.FFMPEG_PATH, "-y", "-loglevel", "error", "-f", "lavfi", "-i",
                    f"sine=frequency=330:duration={seconds}", "-b:a", "96k", str(path)], check=True)
    return path.read_bytes()


def rows():
    with sqlite3.connect(settings.DATA_DIR / "app.db") as connection:
        return connection.execute("SELECT filename, title, duration_s FROM music_tracks ORDER BY filename").fetchall()


def test_files_get_a_row_with_a_measured_length(client):
    make_mp3(settings.DATA_DIR / "music_library" / "calm_morning-piano.mp3", 6.0)
    [track] = data(client.get("/api/music"))
    assert track["title"] == "Calm morning piano"
    assert track["duration_s"] == pytest.approx(6.0, abs=0.1)
    assert track["mood"] is None and track["needs_attribution"] is False
    assert rows() == [("calm_morning-piano.mp3", "Calm morning piano", track["duration_s"])]
    data(client.get("/api/music"))  # a second listing does not duplicate or re-probe
    assert len(rows()) == 1


def test_upload_measures_and_delete_removes_the_row(client, tmp_path):
    content = make_mp3(tmp_path / "src" / "Sunny Walk.mp3", 4.0)
    uploaded = data(client.post("/api/music", files={"file": ("Sunny Walk.mp3", content)}))
    assert uploaded["title"] == "Sunny Walk" and uploaded["duration_s"] == pytest.approx(4.0, abs=0.1)
    data(client.delete("/api/music/Sunny%20Walk.mp3"))
    assert rows() == []


def test_edit_details_and_the_credit_warning(client):
    make_mp3(settings.DATA_DIR / "music_library" / "track.mp3", 3.0)
    base = "/api/music/track.mp3"
    track = data(client.patch(base, json={
        "title": " Morning   Coffee ", "artist": "Kevin MacLeod", "mood": "acoustic",
        "tags": "Cafe, morning ,cafe, Study", "source": "incompetech", "licence": "cc_by_4",
        "source_url": "https://incompetech.com/music/x",
    }))
    assert (track["title"], track["artist"], track["mood"], track["mood_label"]) == (
        "Morning Coffee", "Kevin MacLeod", "acoustic", "Acoustic / warm")
    assert track["tags"] == "cafe, morning, study"
    assert track["licence_label"].startswith("CC BY 4.0")
    assert track["attribution_required"] is True and track["needs_attribution"] is True

    track = data(client.patch(base, json={"attribution": "Morning Coffee by Kevin MacLeod (incompetech.com), CC BY 4.0"}))
    assert track["needs_attribution"] is False
    assert track["mood"] == "acoustic"  # fields not sent are kept

    track = data(client.patch(base, json={"mood": "", "tags": "", "source_url": ""}))
    assert (track["mood"], track["tags"], track["source_url"]) == (None, None, None)
    assert track["duration_s"] == pytest.approx(3.0, abs=0.1)  # never editable

    track = data(client.patch(base, json={"licence": "pixabay"}))
    assert track["attribution_required"] is False and track["needs_attribution"] is False
    track = data(client.patch(base, json={"licence": "other"}))
    assert track["attribution_required"] is None and track["needs_attribution"] is False


@pytest.mark.parametrize("body", [
    {"mood": "jazz"}, {"licence": "cc_by_nc"}, {"source": "spotify"},
    {"source_url": "javascript:alert(1)"}, {"duration_s": 99}, {"title": "x" * 121},
    {"tags": ",".join(f"t{i}" for i in range(13))},
])
def test_edit_rejects_invalid_details(client, body):
    make_mp3(settings.DATA_DIR / "music_library" / "track.mp3", 2.0)
    assert client.patch("/api/music/track.mp3", json=body).status_code == 422


def test_edit_unknown_or_unsafe_track(client):
    assert client.patch("/api/music/missing.mp3", json={"mood": "calm"}).status_code == 404
    assert client.patch("/api/music/..%5Csecret.mp3", json={"mood": "calm"}).status_code in (404, 422)


def test_options_list_moods_sources_and_licences(client):
    options = data(client.get("/api/music/options"))
    assert [mood["id"] for mood in options["moods"]] == ["lofi", "acoustic", "upbeat", "calm", "inspiring"]
    licences = {licence["id"]: licence["attribution_required"] for licence in options["licences"]}
    assert licences["cc_by_4"] is True and licences["pixabay"] is False and licences["other"] is None


def test_guess_title_and_ffprobe_failure(tmp_path):
    assert library.guess_title("calm_morning-piano (2).mp3") == "Calm morning piano"
    assert library.guess_title("---.mp3") == "---.mp3"
    (tmp_path / "bad.mp3").write_bytes(b"ID3 not audio")
    assert library.probe_duration(tmp_path / "bad.mp3") is None
