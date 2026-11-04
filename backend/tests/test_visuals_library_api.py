"""Task 20.4 library API with the deterministic fake image engine (the SDXL candidate/sheet flow went in Phase 44, D123)."""

import sqlite3
import time

import pytest
from fastapi.testclient import TestClient
from PIL import Image

from backend.core.config import settings
from backend.main import app

CHARACTER = {
    "name": "Linh", "gender": "female", "age_group": "young", "ethnicity": "Vietnamese",
    "role": "English teacher", "hair": "long black hair", "eyes": "brown eyes",
    "top_color": "yellow", "top_item": "sweater", "bottom_color": "navy blue",
    "bottom_item": "jeans",
}


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "DATA_DIR", tmp_path)
    monkeypatch.setattr(settings, "IMAGE_ENGINE", "fake")
    monkeypatch.setattr(settings, "AI_VISUALS_ENABLED", True)
    with TestClient(app) as test_client:
        yield test_client


def data(response):
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["success"] is True
    return body["data"]


def wait_job(client, job):
    for _ in range(150):
        current = data(client.get(f"/api/visuals/jobs/{job['id']}"))
        if current["status"] in ("complete", "error", "cancelled"):
            assert current["status"] == "complete", current["error"]
            return current
        time.sleep(0.02)
    pytest.fail("image job did not finish")


def test_scene_crud_preview_builtin_and_kill_switch(client, monkeypatch):
    scenes = data(client.get("/api/visuals/scenes"))
    assert len([scene for scene in scenes if scene["is_builtin"]]) == 55
    builtin = scenes[0]
    assert client.delete(f"/api/visuals/scenes/{builtin['id']}").status_code == 409
    assert data(client.patch(f"/api/visuals/scenes/{builtin['id']}", json={"name": "New classroom"}))["name"] == "New classroom"
    scene = data(client.post("/api/visuals/scenes", json={
        "name": "Station", "place": "a bright train station", "staging": "standing",
    }))
    scene_id = scene["id"]
    assert client.post("/api/visuals/scenes", json={
        "name": "Station", "place": "a bright train station", "staging": "standing",
    }).status_code == 409
    assert client.patch(f"/api/visuals/scenes/{scene_id}", json={"place": "too many words for this place name"}).status_code == 422
    wait_job(client, data(client.post(f"/api/visuals/scenes/{scene_id}/preview")))
    assert client.get(f"/api/visuals/scenes/{scene_id}/preview").headers["content-type"] == "image/png"
    outside = settings.DATA_DIR.parent / "outside_scene.png"
    Image.new("RGB", (8, 8), "red").save(outside)
    with sqlite3.connect(settings.db_path) as connection:
        connection.execute("UPDATE scenes SET preview_path = ? WHERE id = ?", (str(outside), scene_id))
    assert client.get(f"/api/visuals/scenes/{scene_id}/preview").status_code == 404
    monkeypatch.setattr(settings, "AI_VISUALS_ENABLED", False)
    assert client.post(f"/api/visuals/scenes/{scene_id}/preview").status_code == 409
    assert data(client.get("/api/visuals/health"))["enabled"] is False
    assert data(client.delete(f"/api/visuals/scenes/{scene_id}"))["deleted"] == scene_id


def test_character_delete_force_and_content_path_guard(client, tmp_path):
    character = data(client.post("/api/visuals/characters", json=CHARACTER))
    character_id = character["id"]
    outside = tmp_path.parent / "outside_visual.png"
    Image.new("RGB", (8, 8), "red").save(outside)
    with sqlite3.connect(settings.db_path) as connection:  # an asset whose path points outside the library
        connection.execute("INSERT INTO character_assets (id, character_id, kind, path, created_at) "
                           "VALUES ('asset-out', ?, 'face', ?, 'now')", (character_id, str(outside)))
        connection.execute(
            "INSERT INTO projects (id, name, created_at, updated_at) VALUES ('project-test', 'Test', 'now', 'now')"
        )
        connection.execute(
            "INSERT INTO project_cast (project_id, speaker_index, character_id) VALUES (?, 0, ?)",
            ("project-test", character_id),
        )
    assert client.get("/api/visuals/assets/asset-out/content").status_code == 404
    assert client.delete(f"/api/visuals/characters/{character_id}").status_code == 409
    assert data(client.delete(f"/api/visuals/characters/{character_id}?force=true"))["deleted"] == character_id

