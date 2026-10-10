"""Task 20.6 cast, scenes and shot jobs with fake image generation."""

import sqlite3
import time
import uuid

import pytest
from fastapi.testclient import TestClient
from PIL import Image

from app.core.config import settings
from app.main import app

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
    monkeypatch.setattr(settings, "VISUALS_DUO_REFINE", True)
    with TestClient(app) as test_client:
        yield test_client


def data(response):
    assert response.status_code == 200, response.text
    assert response.json()["success"] is True
    return response.json()["data"]


def wait_job(client, job):
    # 30 s: a shot job now also renders missing scene plates (Task 23.2), and the full suite
    # runs these on a loaded machine (two 8 s timeouts seen in one full run).
    for _ in range(1500):
        current = data(client.get(f"/api/visuals/jobs/{job['id']}"))
        if current["status"] in ("complete", "error", "cancelled"):
            assert current["status"] == "complete", current["error"]
            return current
        time.sleep(0.02)
    pytest.fail("shot job did not finish")


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
    visuals = data(client.put(f"{base}/cast", json=[
        {"speaker_index": 0, "character_id": first}, {"speaker_index": 1, "character_id": second},
    ]))
    assert visuals["warnings"]
    updated = {"num_speakers": 2, "speakers": [
        {"name": "New One", "gender": "female", "accent": "american"},
        {"name": "New Two", "gender": "male", "accent": "american"},
    ]}
    data(client.put(f"/api/projects/{project['id']}", json=updated))
    assert [member["character_id"] for member in data(client.get(base))["cast"]] == [first, second]
    assert client.put(f"{base}/scenes", json=[]).status_code == 422
    assert client.put(f"{base}/scenes", json=["missing"]).status_code == 404


def test_cast_uses_distinct_profile_ids_and_copies_defaults_only_when_requested(client):
    project = data(client.post("/api/projects", json=PROJECT))
    first = locked_character("Nova", "yellow")
    second = locked_character("Mira", "green")
    with sqlite3.connect(settings.db_path) as connection:
        connection.execute(
            "UPDATE characters SET default_accent = 'british', default_tts_engine = 'edge_tts', "
            "default_voice_id = 'en-GB-SoniaNeural', default_voice_description = 'warm and clear', "
            "default_speed = 0.92, default_pitch = 0.1, default_volume = 0.8, identity_version = 3 "
            "WHERE id = ?",
            (first,),
        )
    base = f"/api/projects/{project['id']}/visuals"

    duplicate = client.put(f"{base}/cast", json=[
        {"speaker_index": 0, "character_id": first},
        {"speaker_index": 1, "character_id": first},
    ])
    assert duplicate.status_code == 422

    visuals = data(client.put(f"{base}/cast", json=[{
        "speaker_index": 0, "character_id": first, "copy_profile_defaults": True,
    }]))
    assert visuals["cast"][0]["character_id"] == first
    assert visuals["cast"][0]["profile_version"] == 3
    assigned = data(client.get(f"/api/projects/{project['id']}"))["speakers"][0]
    assert assigned["name"] == "Nova"
    assert assigned["accent"] == "british"
    assert assigned["voice_id"] == "en-GB-SoniaNeural"
    assert assigned["voice_description"] == "warm and clear"
    assert (assigned["speed"], assigned["pitch"], assigned["volume"]) == (0.92, 0.1, 0.8)

    speaker_id = assigned["id"]
    data(client.patch(f"/api/projects/{project['id']}/speakers/{speaker_id}", json={
        "voice_description": "project-specific voice", "speed": 1.15,
    }))
    data(client.put(f"{base}/cast", json=[{
        "speaker_index": 0, "character_id": second, "copy_profile_defaults": False,
    }]))
    preserved = data(client.get(f"/api/projects/{project['id']}"))["speakers"][0]
    assert preserved["voice_description"] == "project-specific voice"
    assert preserved["speed"] == 1.15
    assert preserved["name"] == "Nova"


@pytest.mark.parametrize("cast_count,scene_count", [(1, 1), (2, 2), (2, 3)])
def test_shot_sets_regenerate_and_content_guard(client, cast_count, scene_count, tmp_path):
    project, ids, scenes = setup_project(client, cast_count, scene_count)
    base = f"/api/projects/{project['id']}/visuals"
    wait_job(client, data(client.post(f"{base}/shots")))
    shots = data(client.get(base))["shots"]
    expected_per_scene = cast_count + (2 if cast_count == 2 else 0)
    assert len(shots) == expected_per_scene * scene_count
    for scene in scenes:
        group = [shot for shot in shots if shot["scene_id"] == scene["id"]]
        assert [shot["kind"] for shot in group] == (
            ["single"] if cast_count == 1 else ["single", "single", "duo_close", "duo_wide"]
        )
    assert all(shot["status"] == "complete" and shot["raw_url"] and shot["final_url"] for shot in shots)
    shot = shots[-1]
    assert client.get(shot["final_url"]).headers["content-type"] == "image/png"
    folder = settings.DATA_DIR / "visuals" / project["id"] / "shots" / shot["id"]
    assert (folder / "pose.png").is_file() and (folder / "raw.png").is_file()
    assert (folder / "final.png").is_file()
    if shot["kind"] != "single":
        assert (folder / "refine_mask_0.png").is_file()
    old_seed = shot["seed"]
    wait_job(client, data(client.post(f"{base}/shots/{shot['id']}/regenerate")))
    regenerated = next(item for item in data(client.get(base))["shots"] if item["id"] == shot["id"])
    assert regenerated["seed"] != old_seed and regenerated["status"] == "complete"
    outside = tmp_path.parent / "outside_shot.png"
    Image.new("RGB", (8, 8), "red").save(outside)
    with sqlite3.connect(settings.db_path) as connection:
        connection.execute("UPDATE project_shots SET final_path = ? WHERE id = ?", (str(outside), shot["id"]))
    assert client.get(regenerated["final_url"]).status_code == 404


def test_project_delete_removes_visual_files(client):
    project, _, _ = setup_project(client, 1, 1)
    base = f"/api/projects/{project['id']}/visuals"
    wait_job(client, data(client.post(f"{base}/shots")))
    directory = settings.DATA_DIR / "visuals" / project["id"]
    assert directory.is_dir()
    data(client.delete(f"/api/projects/{project['id']}"))
    assert not directory.exists()


def test_shot_prompt_truncation_from_fake_encode(client, monkeypatch):
    from app.services.visuals import recipes

    project, _, _ = setup_project(client, 1, 1)
    monkeypatch.setattr(recipes, "single_prompt", lambda character, scene, **kwargs: "word " * 80)
    base = f"/api/projects/{project['id']}/visuals"
    wait_job(client, data(client.post(f"{base}/shots")))
    shot = data(client.get(base))["shots"][0]
    assert shot["prompt_truncated"] == 1
    assert shot["prompt_tokens"] == 80
