"""Task 22.5: the music credit line at the end of the YouTube description."""

import sqlite3
import subprocess

import pytest
from fastapi.testclient import TestClient

from app.core.config import settings
from app.main import app
from app.services import music_library_service as library
from app.services import youtube_service


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "DATA_DIR", tmp_path)
    with TestClient(app) as test_client:
        yield test_client


def data(response):
    assert response.status_code == 200, response.text
    return response.json()["data"]


# --- formats --------------------------------------------------------------------------------

def test_credit_text_wins_and_lines_are_built_from_details():
    assert library.credit_line("a.mp3", {"attribution": "Morning Coffee by Kevin MacLeod, CC BY 4.0"}) == \
        "🎵 Music: Morning Coffee by Kevin MacLeod, CC BY 4.0"
    full = {"title": "Sunny Walk", "artist": "Lexin", "source": "pixabay", "licence": "pixabay",
            "source_url": "https://pixabay.com/music/sunny-walk"}
    assert library.credit_line("x.mp3", full) == (
        '🎵 Music: "Sunny Walk" by Lexin — Pixabay Music (Pixabay Content License) https://pixabay.com/music/sunny-walk')
    assert library.credit_line("calm_piano-loop.mp3", None) == '🎵 Music: "Calm piano loop"'


def test_with_music_credit_appends_once_and_never_stores():
    package = {"description": "Learn English with us.\n", "titles": []}
    credited = youtube_service.with_music_credit(package, "🎵 Music: X")
    assert credited["description"] == "Learn English with us.\n\n🎵 Music: X"
    assert youtube_service.with_music_credit(credited, "🎵 Music: X")["description"] == credited["description"]
    assert package["description"] == "Learn English with us.\n"  # the stored text is untouched
    assert youtube_service.with_music_credit(package, None)["description"] == package["description"]
    assert youtube_service.with_music_credit(None, "x") is None


# --- through the API ------------------------------------------------------------------------

def test_get_package_carries_the_credit_of_the_mixed_track(client):
    project = data(client.post("/api/projects", json={
        "name": "Credit", "topic": "Coffee", "cefr_level": "B1", "duration_minutes": 2, "num_speakers": 2,
        "genre": "interview", "accent": "american",
        "speakers": [{"name": "Lan", "gender": "female", "accent": "american"},
                     {"name": "Minh", "gender": "male", "accent": "american"}],
    }))
    music = settings.DATA_DIR / "music_library"
    music.mkdir(parents=True, exist_ok=True)
    for name in ("morning.mp3", "night.mp3"):
        subprocess.run([settings.FFMPEG_PATH, "-y", "-loglevel", "error", "-f", "lavfi", "-i",
                        "anullsrc=r=8000:cl=mono", "-t", "3", "-b:a", "16k", str(music / name)], check=True)
    data(client.get("/api/music"))
    data(client.patch("/api/music/morning.mp3", json={"artist": "Kevin MacLeod", "licence": "cc_by_4",
                                                      "attribution": "Morning by Kevin MacLeod, CC BY 4.0"}))
    with sqlite3.connect(settings.DATA_DIR / "app.db") as connection:
        connection.execute(
            "INSERT INTO youtube_packages (id, project_id, title_options_json, description, chapters_text, tags, "
            "created_at, updated_at) VALUES ('y1', ?, '[]', 'Learn with us.', '', '[]', 't', 't')",
            (project["id"],))
        connection.execute("INSERT INTO audio_jobs (id, project_id, status, background_music) "
                           "VALUES ('a1', ?, 'complete', 'morning.mp3')", (project["id"],))
    package = data(client.get(f"/api/projects/{project['id']}/youtube"))
    assert package["description"] == "Learn with us.\n\n🎵 Music: Morning by Kevin MacLeod, CC BY 4.0"
    assert package["music_credit"].endswith("CC BY 4.0")

    with sqlite3.connect(settings.DATA_DIR / "app.db") as connection:
        connection.execute("UPDATE audio_jobs SET background_music = 'night.mp3' WHERE id = 'a1'")
    assert data(client.get(f"/api/projects/{project['id']}/youtube"))["description"] == \
        'Learn with us.\n\n🎵 Music: "Night"'

    with sqlite3.connect(settings.DATA_DIR / "app.db") as connection:
        connection.execute("UPDATE audio_jobs SET background_music = NULL WHERE id = 'a1'")
        stored = connection.execute("SELECT description FROM youtube_packages").fetchone()[0]
    package = data(client.get(f"/api/projects/{project['id']}/youtube"))
    assert package["description"] == "Learn with us." and package["music_credit"] is None
    assert stored == "Learn with us."
