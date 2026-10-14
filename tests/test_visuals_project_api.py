"""Task 20.6 cast and scenes with fake image generation (Phase 44: the shot jobs are gone); shared fixtures."""

import sqlite3
import time
import uuid

import pytest
from fastapi.testclient import TestClient
from PIL import Image

from backend.core.config import settings
from backend.main import app

PROJECT = {
    "name": "Conversation lesson", "topic": "Meeting at a cafe", "cefr_level": "B1",
    "duration_minutes": 2, "num_speakers": 2, "genre": "small_talk", "accent": "american",
    "speakers": [{"name": "Speaker One", "gender": "female", "accent": "american"},
                 {"name": "Speaker Two", "gender": "male", "accent": "american"}],
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
    assert response.json()["success"] is True
    return response.json()["data"]


def wait_job(client, job):
    # 30 s: the full suite runs these on a loaded machine.
    for _ in range(1500):
        current = data(client.get(f"/api/visuals/jobs/{job['id']}"))
        if current["status"] in ("complete", "error", "cancelled"):
            assert current["status"] == "complete", current["error"]
            return current
        time.sleep(0.02)
    pytest.fail("image job did not finish")


def locked_character(name: str, color: str) -> str:
    character_id, face_id = str(uuid.uuid4()), str(uuid.uuid4())
    path = settings.DATA_DIR / "library" / "characters" / character_id / "face.png"
    path.parent.mkdir(parents=True, exist_ok=True)
    Image.new("RGB", (512, 512), color).save(path)
    with sqlite3.connect(settings.db_path) as connection:
        connection.execute(
            "INSERT INTO characters (id, name, gender, age_group, role, hair, eyes, top_color, top_item, "
            "bottom_color, bottom_item, status, base_seed, created_at, updated_at) "
            "VALUES (?, ?, 'female', 'young', 'English teacher', 'long black hair', 'brown eyes', "
            "?, 'shirt', 'navy blue', 'jeans', 'locked', 100, 'now', 'now')",
            (character_id, name, color),
        )
        connection.execute(
            "INSERT INTO character_assets (id, character_id, kind, path, created_at) "
            "VALUES (?, ?, 'face', ?, 'now')",
            (face_id, character_id, str(path)),
        )
    return character_id


def setup_project(client, cast_count=2, scene_count=2, same_color=False):
    project = data(client.post("/api/projects", json=PROJECT))
    ids = [locked_character("Nova", "yellow")]
    if cast_count == 2:
        ids.append(locked_character("Mira", "yellow" if same_color else "green"))
    scenes = data(client.get("/api/visuals/scenes"))[:scene_count]
    visuals = data(client.put(f"/api/projects/{project['id']}/visuals/cast", json=[
        {"speaker_index": index, "character_id": character_id}
        for index, character_id in enumerate(ids)
    ]))
    assert len(visuals["cast"]) == cast_count
    visuals = data(client.put(f"/api/projects/{project['id']}/visuals/scenes", json=[s["id"] for s in scenes]))
    assert len(visuals["scenes"]) == scene_count
    return project, ids, scenes


def test_cast_validation_warning_and_speaker_replacement(client):
    project = data(client.post("/api/projects", json=PROJECT))
    draft = data(client.post("/api/visuals/characters", json={
        "name": "Draft", "gender": "female", "age_group": "young", "role": "English teacher",
        "hair": "long black hair", "eyes": "brown eyes", "top_color": "yellow", "top_item": "shirt",
        "bottom_color": "navy blue", "bottom_item": "jeans",
    }))
    base = f"/api/projects/{project['id']}/visuals"
    assert client.put(f"{base}/cast", json=[{"speaker_index": 0, "character_id": draft['id']}]).status_code == 422
    first = locked_character("Nova", "yellow")
    second = locked_character("Mira", "yellow")
    assert client.put(f"{base}/cast", json=[{"speaker_index": 9, "character_id": first}]).status_code == 422
    data(client.put(f"{base}/cast", json=[
        {"speaker_index": 0, "character_id": first}, {"speaker_index": 1, "character_id": second},
    ]))
    updated = {"num_speakers": 2, "speakers": [
        {"name": "New One", "gender": "female", "accent": "american"},
        {"name": "New Two", "gender": "male", "accent": "american"},
    ]}
    data(client.put(f"/api/projects/{project['id']}", json=updated))
    assert [member["character_id"] for member in data(client.get(base))["cast"]] == [first, second]
    assert client.put(f"{base}/scenes", json=[]).status_code == 422
    assert client.put(f"{base}/scenes", json=["missing"]).status_code == 404


def test_project_delete_removes_visual_files(client):
    project, _, _ = setup_project(client, 1, 1)
    directory = settings.DATA_DIR / "visuals" / project["id"] / "activity_drafts"
    directory.mkdir(parents=True)
    (directory / "draft.png").write_bytes(b"x")
    data(client.delete(f"/api/projects/{project['id']}"))
    assert not directory.parent.exists()


def test_the_shot_routes_and_the_visual_warnings_are_gone(client):
    """Phase 44 (D123): no two-person shots, no "Generate shots", no duo colour warning."""
    project, _, _ = setup_project(client, 2, 1)
    base = f"/api/projects/{project['id']}/visuals"
    assert set(data(client.get(base))) == {"cast", "scenes"}
    assert client.post(f"{base}/shots").status_code in (404, 405)
    assert client.get("/api/visuals/library/shots").status_code == 404
