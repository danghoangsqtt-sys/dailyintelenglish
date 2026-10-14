"""Task 26.3: the dashboard card's real picture: the selected thumbnail, else none (the first-shot fallback went with
the two-person shots, Phase 44 / D123)."""

import sqlite3

import pytest
from fastapi.testclient import TestClient

from backend.core.config import settings
from backend.main import app


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "DATA_DIR", tmp_path)
    with TestClient(app) as test_client:
        yield test_client


def listed(client, project_id):
    projects = client.get("/api/projects").json()["data"]
    return next(project for project in projects if project["id"] == project_id)


def test_preview_url_is_the_selected_thumbnail(client):
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
        connection.execute("INSERT INTO thumbnails (id, project_id, image_path_16x9, is_selected) "
                           "VALUES ('t1', ?, 'a/16x9.jpg', 0)", (pid,))
        connection.execute("INSERT INTO thumbnails (id, project_id, image_path_16x9, is_selected) "
                           "VALUES ('t2', ?, 'b/16x9.png', 1)", (pid,))
    assert listed(client, pid)["preview_url"] == f"/api/projects/{pid}/thumbnails/t2/16x9.png"
