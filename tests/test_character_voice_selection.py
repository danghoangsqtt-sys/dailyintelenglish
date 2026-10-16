"""Voice persistence, explicit application and optimistic concurrency contracts."""

import asyncio
import json
import sqlite3

import pytest

from backend.ai.tts import voice_catalog_service
from backend.api import projects as projects_api
from backend.core.config import settings
from backend.core.exceptions import ConflictError
from backend.db import transactions
from backend.schemas.project import ScriptConfig, SpeakerUpdate
from backend.content import project_service
from tests.test_visuals_project_api import client, data, locked_character  # noqa: F401

GUY = "en-US-GuyNeural"
ANDREW = "en-US-AndrewNeural"


def config():
    return {
        "name": "Individual voices", "topic": "Explain a simple idea", "cefr_level": "B1",
        "duration_minutes": 2, "num_speakers": 2, "genre": "small_talk", "accent": "american",
        "speakers": [
            {"name": "Alex", "gender": "male", "accent": "american", "voice_id": GUY},
            {"name": "Brian", "gender": "male", "accent": "american", "voice_id": ANDREW},
        ],
    }


def test_same_gender_voices_round_trip_config_copy_and_speaker_patch(client):  # noqa: F811
    project = data(client.post("/api/projects", json=config()))
    ids = [s["id"] for s in project["speakers"]]
    assert [s["voice_id"] for s in project["speakers"]] == [GUY, ANDREW]
    assert all(len(s["voice_revision"]) == 64 for s in project["speakers"])
    saved = data(client.put(f"/api/projects/{project['id']}/script", json={"lines": [
        {"speaker_id": ids[0], "text": "A first example."}, {"speaker_id": ids[1], "text": "Another example."},
    ]}))
    first = project["speakers"][0]
    updated = data(client.patch(f"/api/projects/{project['id']}/speakers/{first['id']}", json={
        "voice_id": ANDREW, "expected_voice_revision": first["voice_revision"],
    }))
    assert [s["id"] for s in updated["speakers"]] == ids
    assert data(client.get(f"/api/projects/{project['id']}/script")) == saved
    assert updated["speakers"][0]["speed"] == first["speed"]
    snapshot = json.loads(updated["config_json"])
    assert snapshot["speakers"][0]["voice_id"] == ANDREW
    copied = data(client.post("/api/projects", json={**snapshot, "name": "Copy"}))
    assert [s["voice_id"] for s in copied["speakers"]] == [ANDREW, ANDREW]
    with sqlite3.connect(settings.db_path) as connection:
        assert connection.execute("SELECT voice_id FROM speakers WHERE id = ?", (ids[0],)).fetchone()[0] == ANDREW


def test_profile_default_is_pinned_and_duplicate_preserves_selection(client):  # noqa: F811
    profile = data(client.post("/api/visuals/profiles", json={
        "name": "Presenter", "gender": "male", "accent": "american",
        "appearance": "short dark hair", "outfit": "blue shirt",
    }))
    url = f"/api/visuals/profiles/{profile['id']}"
    selected = data(client.patch(url, json={
        "default_voice_id": ANDREW, "expected_voice_revision": profile["voice_revision"],
    }))
    changed = data(client.patch(url, json={"accent": "british", "gender": "female"}))
    assert changed["voice"]["voice_id"] == ANDREW
    assert changed["sprite_facing"] == "left"
    assert changed["voice_revision"] != selected["voice_revision"]
    duplicate = data(client.post(url + "/duplicate"))
    assert duplicate["voice"]["voice_id"] == ANDREW
    stale = client.patch(url, json={"default_voice_id": GUY, "expected_voice_revision": profile["voice_revision"]})
    assert stale.status_code == 409
    assert data(client.get(url))["voice"]["voice_id"] == ANDREW


def test_edit_profile_does_not_reapply_to_same_cast_but_explicit_apply_does(client):  # noqa: F811
    project = data(client.post("/api/projects", json=config()))
    character = locked_character("Alex", "blue")
    with sqlite3.connect(settings.db_path) as connection:
        connection.execute(
            "UPDATE characters SET default_accent='american', gender='male', default_voice_id=? WHERE id=?",
            (GUY, character),
        )
    cast_url = f"/api/projects/{project['id']}/visuals/cast"
    members = [{"speaker_index": 0, "character_id": character}]
    data(client.put(cast_url, json=members))
    before = data(client.get(f"/api/projects/{project['id']}"))["speakers"][0]
    profile = data(client.get(f"/api/visuals/profiles/{character}"))
    data(client.patch(f"/api/visuals/profiles/{character}", json={
        "default_voice_id": ANDREW, "default_speed": 1.2, "expected_voice_revision": profile["voice_revision"],
    }))
    data(client.put(cast_url, json=members))
    current = data(client.get(f"/api/projects/{project['id']}"))["speakers"][0]
    assert current["voice_id"] == GUY and current["profile_voice_id"] == ANDREW
    result = data(client.patch(f"/api/projects/{project['id']}/speakers/{before['id']}", json={
        "apply_profile_voice": True, "expected_voice_revision": current["voice_revision"],
    }))
    after = result["speakers"][0]
    assert after["voice_id"] == ANDREW
    assert (after["speed"], after["pitch"], after["volume"]) == (before["speed"], before["pitch"], before["volume"])


@pytest.mark.parametrize("voice_id", ["vi-VN-HoaiMyNeural", "en-US-UnknownNeural", "../voice"])
def test_invalid_voice_never_persists(client, voice_id):  # noqa: F811
    payload = config()
    payload["speakers"][0]["voice_id"] = voice_id
    response = client.post("/api/projects", json=payload)
    assert response.status_code == 422
    assert data(client.get("/api/projects")) == []


@pytest.mark.asyncio
async def test_voice_validation_is_outside_lock_and_stale_write_is_rejected(db, monkeypatch):
    project = await project_service.create_project(db, ScriptConfig(**config()))
    speaker = project["speakers"][0]
    entered, release = asyncio.Event(), asyncio.Event()

    async def verify(voice_id):
        assert not transactions.write_lock.locked()
        entered.set()
        await release.wait()
        return {"voice_id": voice_id}

    monkeypatch.setattr(voice_catalog_service, "require_voice", verify)
    pending = asyncio.create_task(projects_api.update_speaker(
        project["id"], speaker["id"],
        SpeakerUpdate(voice_id=ANDREW, expected_voice_revision=speaker["voice_revision"]), db,
    ))
    await asyncio.wait_for(entered.wait(), timeout=2)
    newer = await projects_api.update_speaker(
        project["id"], speaker["id"], SpeakerUpdate(speed=1.1), db,
    )
    release.set()
    with pytest.raises(ConflictError):
        await pending
    assert newer["data"]["speakers"][0]["speed"] == 1.1
    current = (await project_service.get_project(db, project["id"]))["speakers"][0]
    assert current["voice_id"] == GUY and current["speed"] == 1.1
