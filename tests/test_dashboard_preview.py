"""Task 26.3: the dashboard card's real picture (selected thumbnail, else first finished shot)."""

import sqlite3

import pytest
from fastapi.testclient import TestClient

from app.core.config import settings
from app.main import app


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "DATA_DIR", tmp_path)
    with TestClient(app) as test_client:
        yield test_client


def listed(client, project_id):
    projects = client.get("/api/projects").json()["data"]
    return next(project for project in projects if project["id"] == project_id)


def test_preview_url_prefers_the_selected_thumbnail_then_the_first_shot(client):
    project = client.post("/api/projects", json={
        "name": "Preview", "topic": "Morning routines", "cefr_level": "B1", "duration_minutes": 2,
        "num_speakers": 2, "genre": "small_talk", "accent": "american",
        "speakers": [{"name": "Lan", "gender": "female", "accent": "american"},
                     {"name": "Minh", "gender": "male", "accent": "american"}],
    }).json()["data"]
    pid = project["id"]
    first = listed(client, pid)
    assert first["preview_url"] is None and first["topic"] == "Morning routines"

    with sqlite3.connect(settings.DATA_DIR / "app.db") as connection:
        for shot_id, created in (("s2", "2026-10-06T10:00:02"), ("s1", "2026-10-06T10:00:01")):
            connection.execute(
                "INSERT INTO project_shots (id, project_id, scene_id, kind, speaker_indexes, seed, final_path, status, "
                "created_at, updated_at) VALUES (?, ?, 'scene', 'wide', '[]', 1, 'x.png', 'complete', ?, ?)",
                (shot_id, pid, created, created))
        connection.execute(
            "INSERT INTO project_shots (id, project_id, scene_id, kind, speaker_indexes, seed, status, created_at, "
            "updated_at) VALUES ('s0', ?, 'scene', 'wide', '[]', 1, 'pending', '2026-10-06T09:00:00', 't')", (pid,))
    assert listed(client, pid)["preview_url"] == f"/api/projects/{pid}/visuals/shots/s1/content?variant=final"

    with sqlite3.connect(settings.DATA_DIR / "app.db") as connection:
        connection.execute("INSERT INTO thumbnails (id, project_id, image_path_16x9, is_selected) "
                           "VALUES ('t1', ?, 'a/16x9.jpg', 0)", (pid,))
        connection.execute("INSERT INTO thumbnails (id, project_id, image_path_16x9, is_selected) "
                           "VALUES ('t2', ?, 'b/16x9.png', 1)", (pid,))
    assert listed(client, pid)["preview_url"] == f"/api/projects/{pid}/thumbnails/t2/16x9.png"
