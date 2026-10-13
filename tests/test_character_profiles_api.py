"""Task 33.2 (Amendment A D79): character profile API -- Quick create, autosave, readiness, duplicate, archive, delete."""

from __future__ import annotations

import json
import sqlite3
import uuid

import pytest
from fastapi.testclient import TestClient

from backend.core.config import settings
from backend.main import app
from backend.library.character_profile_service import TIER1_SPRITES

QUICK = {"name": "Kai", "gender": "male", "accent": "british", "nationality": "Japanese",
         "appearance": "tall, short black hair, round glasses", "outfit": "grey hoodie and jeans"}


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "DATA_DIR", tmp_path)
    with TestClient(app) as test_client:
        yield test_client


def data(response, status=200):
    assert response.status_code == status, response.text
    return response.json()["data"] if status == 200 else response.json()


def create(client, **changes):
    return data(client.post("/api/visuals/profiles", json={**QUICK, **changes}))


def test_quick_create_derives_voice_facing_and_explains_what_is_missing(client):
    kai = create(client)
    lena = create(client, name="Lena", gender="female", accent="american")

    assert (kai["voice"]["voice_id"], kai["sprite_facing"], kai["wizard_step"]) == ("en-GB-RyanNeural", "right", 1)
    assert (lena["voice"]["voice_id"], lena["sprite_facing"]) == ("en-US-JennyNeural", "left")
    readiness = kai["readiness"]
    assert readiness["profile"]["ready"] and readiness["voice"]["ready"]
    assert readiness["core_visuals"]["missing"] == ["picture full_body", "picture portrait_calm", "picture portrait_smile",
                                                    "picture portrait_surprised"]
    assert readiness["talking_starter"]["have"] == 0 and len(readiness["talking_starter"]["missing"]) == 7
    assert not readiness["video_ready"] and not readiness["talking_ready"]


@pytest.mark.parametrize("change", [{"appearance": "   "}, {"accent": "martian"}, {"gender": "robot"}, {"name": ""},
                                    {"nationality": "very long nationality"}])
def test_quick_create_rejects_invalid_input(client, change):
    data(client.post("/api/visuals/profiles", json={**QUICK, **change}), status=422)


def test_names_are_unique_among_active_profiles(client):
    create(client)
    data(client.post("/api/visuals/profiles", json={**QUICK, "name": "  KAI "}), status=409)


def test_autosave_patch_persists_and_keeps_voice_matching_accent_and_gender(client):
    kai = create(client)
    patched = data(client.patch(f"/api/visuals/profiles/{kai['id']}", json={
        "intro": "A barista who loves jazz.", "personality": ["calm", " curious "], "wizard_step": 3,
    }))
    assert patched["personality"] == ["calm", "curious"] and patched["wizard_step"] == 3
    refreshed = data(client.get(f"/api/visuals/profiles/{kai['id']}"))
    assert refreshed["intro"] == "A barista who loves jazz."

    switched = data(client.patch(f"/api/visuals/profiles/{kai['id']}", json={"accent": "indian", "gender": "female"}))
    assert (switched["voice"]["voice_id"], switched["sprite_facing"]) == ("en-IN-NeerjaNeural", "left")
    custom = data(client.patch(f"/api/visuals/profiles/{kai['id']}", json={"accent": "irish",
                                                                           "default_voice_id": "en-IE-ConnorNeural"}))
    assert custom["voice"]["voice_id"] == "en-IE-ConnorNeural"  # an explicit voice wins over the derived one


def test_duplicate_gets_a_new_id_and_a_free_name_without_pictures(client):
    kai = create(client)
    first = data(client.post(f"/api/visuals/profiles/{kai['id']}/duplicate"))
    second = data(client.post(f"/api/visuals/profiles/{kai['id']}/duplicate"))
    assert first["id"] != kai["id"] and (first["name"], second["name"]) == ("Kai copy", "Kai copy 2")
    assert first["appearance"] == kai["appearance"] and first["readiness"]["core_visuals"]["have"] == 0
    assert not first["is_seed"]


def test_archive_frees_the_name_and_restore_rechecks_it(client):
    kai = create(client)
    data(client.post(f"/api/visuals/profiles/{kai['id']}/archive"))
    assert [p["id"] for p in data(client.get("/api/visuals/profiles"))] == []
    assert [p["id"] for p in data(client.get("/api/visuals/profiles?state=archived"))] == [kai["id"]]
    create(client)  # the name is free while the first Kai is archived
    data(client.post(f"/api/visuals/profiles/{kai['id']}/restore"), status=409)


def test_search_filters_by_normalized_name(client):
    create(client)
    create(client, name="Lena", gender="female")
    assert [p["name"] for p in data(client.get("/api/visuals/profiles?q=LE"))] == ["Lena"]


def test_delete_refuses_seeds_and_used_profiles_and_removes_free_ones(client):
    seed, used, free = create(client, name="Seed"), create(client, name="Used"), create(client, name="Free")
    with sqlite3.connect(settings.db_path) as connection:
        connection.execute("UPDATE characters SET is_seed = 1 WHERE id = ?", (seed["id"],))
        connection.execute(
            "INSERT INTO activity_library (id, character_id, activity, path, content_sha, review_state, created_at, "
            "updated_at) VALUES ('a1', ?, 'cooking', 'x.png', 'sha-a1', 'approved', 'now', 'now')", (used["id"],))
    data(client.delete(f"/api/visuals/profiles/{seed['id']}"), status=409)
    report = data(client.get(f"/api/visuals/profiles/{used['id']}/dependencies"))
    assert report["activities"] == 1 and report["blocking"]
    data(client.delete(f"/api/visuals/profiles/{used['id']}"), status=409)
    data(client.delete(f"/api/visuals/profiles/{free['id']}"))
    data(client.get(f"/api/visuals/profiles/{free['id']}"), status=404)


def test_readiness_counts_approved_current_assets_and_legacy_sprite_sets(client):
    kai = create(client)
    lena = create(client, name="Lena", gender="female")
    with sqlite3.connect(settings.db_path) as connection:
        for slot in ("full_body", "portrait_calm", "portrait_smile", "portrait_surprised",
                     *(f"sprite/{name}" for name in TIER1_SPRITES)):
            connection.execute(
                "INSERT INTO character_assets (id, character_id, kind, path, approved, created_at, slot_key, review_state) "
                "VALUES (?, ?, ?, 'x.png', 1, 'now', ?, 'approved')",
                (str(uuid.uuid4()), kai["id"], "sprite" if slot.startswith("sprite/") else slot, slot),
            )
        connection.execute(  # a picture still under review never counts
            "INSERT INTO character_assets (id, character_id, kind, path, approved, created_at, slot_key, review_state) "
            "VALUES ('pending', ?, 'full_body', 'x.png', 0, 'now', 'full_body', 'needs_review')", (lena["id"],))
    folder = settings.DATA_DIR / "library" / "sprites" / lena["id"]
    folder.mkdir(parents=True)
    (folder / "sprite_set.json").write_text(json.dumps({"pictures": {name: {} for name in TIER1_SPRITES}}))

    kai_ready = data(client.get(f"/api/visuals/profiles/{kai['id']}"))["readiness"]
    lena_ready = data(client.get(f"/api/visuals/profiles/{lena['id']}"))["readiness"]
    assert kai_ready["video_ready"] and kai_ready["talking_ready"]
    assert kai_ready["full_expressions"]["have"] == 7 and not kai_ready["full_expressions"]["ready"]
    assert lena_ready["talking_starter"]["ready"]  # legacy sprite_set.json fallback
    assert lena_ready["core_visuals"]["have"] == 0 and not lena_ready["video_ready"]


def test_legacy_character_routes_still_work_beside_profiles(client):
    create(client)
    assert [row["name"] for row in data(client.get("/api/visuals/characters"))] == ["Kai"]


def test_legacy_routes_never_wipe_a_profile_or_delete_a_seed(client):
    """Phase 35 (D89): the old edit route wiped every picture on an appearance change, the old delete ignored `is_seed`."""
    kai, seed = create(client), create(client, name="Seed")
    with sqlite3.connect(settings.db_path) as connection:
        connection.execute("UPDATE characters SET is_seed = 1 WHERE id = ?", (seed["id"],))
        connection.execute(
            "INSERT INTO character_assets (id, character_id, kind, path, approved, created_at, slot_key, review_state) "
            "VALUES ('kai-base', ?, 'sprite', 'x.png', 1, 'now', 'sprite/calm__closed', 'approved')", (kai["id"],))
    for character in (kai, seed):
        refused = data(client.patch(f"/api/visuals/characters/{character['id']}", json={"hair": "long red hair"}), status=409)
        assert "Profiles tab" in refused["error"]
    with sqlite3.connect(settings.db_path) as connection:
        assert connection.execute("SELECT COUNT(*) FROM character_assets WHERE character_id = ?", (kai["id"],)).fetchone()[0] == 1
    data(client.delete(f"/api/visuals/characters/{seed['id']}?force=true"), status=409)
    data(client.get(f"/api/visuals/profiles/{seed['id']}"))


def test_a_cast_accepts_a_video_ready_profile_and_explains_a_profile_that_is_not(client):
    """Task 33.7: profiles made from outside-AI pictures are never 'locked'; video readiness lets them join a cast."""
    kai, lena = create(client), create(client, name="Lena", gender="female")
    with sqlite3.connect(settings.db_path) as connection:
        for slot in ("full_body", "portrait_calm", "portrait_smile", "portrait_surprised"):
            connection.execute(
                "INSERT INTO character_assets (id, character_id, kind, path, approved, created_at, slot_key, review_state) "
                "VALUES (?, ?, ?, 'x.png', 1, 'now', ?, 'approved')", (str(uuid.uuid4()), kai["id"], slot, slot))
    project = data(client.post("/api/projects", json={
        "name": "Cast", "topic": "Coffee", "cefr_level": "B1", "duration_minutes": 5, "num_speakers": 2, "genre": "small_talk",
        "accent": "american", "speakers": [{"name": "Kai", "gender": "male", "accent": "british"},
                                           {"name": "Lena", "gender": "female", "accent": "american"}]}))
    url = f"/api/projects/{project['id']}/visuals/cast"
    cast = data(client.put(url, json=[{"speaker_index": 0, "character_id": kai["id"]}]))["cast"]
    assert [(member["speaker_index"], member["character_id"]) for member in cast] == [(0, kai["id"])]
    refused = client.put(url, json=[{"speaker_index": 1, "character_id": lena["id"]}])
    assert refused.status_code == 422 and "Lena is not ready for videos yet: picture full_body" in refused.json()["error"]
