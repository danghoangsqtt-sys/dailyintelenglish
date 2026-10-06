"""Task 23.2: scene model v2 (category, time of day, seed, plate) and the plate as a scene reference."""

import sqlite3

import pytest
from PIL import Image

from app.core.config import settings
from app.services.visuals import geometry, recipes
from app.services.visuals.engine import FakeImageEngine
from tests.test_visuals_project_api import client, data, setup_project, wait_job  # noqa: F401

SIZE = (1344, 768)


@pytest.fixture
def requests_log(monkeypatch):
    log = []
    original = FakeImageEngine.request

    async def recording(self, payload):
        log.append(dict(payload))
        return await original(self, payload)

    monkeypatch.setattr(FakeImageEngine, "request", recording)
    return log


def test_builtins_get_category_and_seed(client):  # noqa: F811
    scenes = {scene["id"]: scene for scene in data(client.get("/api/visuals/scenes"))}
    assert scenes["builtin-classroom"]["category"] == "school"
    assert scenes["builtin-park"]["category"] == "city"
    assert scenes["builtin-rice-fields"]["category"] == "countryside"
    assert all(scene["time_of_day"] == "day" and scene["seed"] for scene in scenes.values())
    options = data(client.get("/api/visuals/options"))
    assert "nature" in options["scene_categories"] and options["times_of_day"][-1] == "night"


def test_create_validate_and_stale_plate(client):  # noqa: F811
    body = {"name": "Night market", "place": "a busy night market", "staging": "standing",
            "category": "food", "time_of_day": "night"}
    scene = data(client.post("/api/visuals/scenes", json=body))
    assert scene["category"] == "food" and scene["time_of_day"] == "night" and scene["seed"]
    assert client.post("/api/visuals/scenes", json={**body, "name": "X", "category": "space"}).status_code == 422
    with sqlite3.connect(settings.db_path) as connection:
        connection.execute("UPDATE scenes SET preview_path = 'p.png' WHERE id = ?", (scene["id"],))
    renamed = data(client.patch(f"/api/visuals/scenes/{scene['id']}", json={"name": "Evening market"}))
    assert renamed["preview_url"]  # a rename keeps the plate
    moved = data(client.patch(f"/api/visuals/scenes/{scene['id']}", json={"time_of_day": "sunset"}))
    assert moved["preview_url"] is None  # the plate showed night: stale


def test_preview_prompt_time_of_day_and_budget():
    scene = {"place": "a cozy Vietnamese street cafe", "time_of_day": "sunset"}
    prompt = recipes.scene_preview_prompt(scene)
    assert "golden sunset light" in prompt and prompt.endswith("wide view, empty scene, no people")
    day = recipes.scene_preview_prompt({**scene, "time_of_day": "day"})
    assert not any(word in day for word in ("morning", "sunset", "night", "lamps"))
    assert recipes.token_count(prompt) <= 75


def test_background_mask_excludes_people():
    people = geometry.shot_people("duo_close", "seated", SIZE)
    mask = geometry.background_mask(people, SIZE)
    assert mask.getpixel((5, 5)) == 255
    for person in people:
        nose = dict(zip(geometry._KEYS, person["points"]))["nose"]
        assert mask.getpixel((round(nose[0]), round(nose[1]))) == 0


def test_shots_make_missing_plates_once_and_pass_the_scene(client, monkeypatch, requests_log):  # noqa: F811
    monkeypatch.setattr(settings, "VISUALS_COLOUR_RETRIES", 0)
    project, _, scenes = setup_project(client, 2, 2)
    base = f"/api/projects/{project['id']}/visuals"
    wait_job(client, data(client.post(f"{base}/shots")))
    plates = [p for p in requests_log if p["command"] == "generate" and "empty scene" in p.get("prompt", "")]
    assert len(plates) == 2
    for scene in data(client.get("/api/visuals/scenes")):
        if scene["id"] in {s["id"] for s in scenes}:
            assert scene["preview_url"]
            assert Image.open(settings.DATA_DIR / "library" / "scenes" / scene["id"] / "preview.png").size == SIZE
    encodes = [p for p in requests_log if p["command"] == "encode"]
    assert encodes and all(p["ip_adapter_scene_image"].endswith("preview.png") for p in encodes)
    renders = [p for p in requests_log if p.get("embeds_path")]
    assert renders and all(p["ip_adapter_scene_scale"] == 0.4 and p["ip_adapter_scene_mask"] for p in renders)
    requests_log.clear()
    wait_job(client, data(client.post(f"{base}/shots")))
    assert not [p for p in requests_log if "empty scene" in p.get("prompt", "")]  # plates are reused


def test_scene_reference_off_keeps_the_old_path(client, monkeypatch, requests_log):  # noqa: F811
    monkeypatch.setattr(settings, "VISUALS_SCENE_REFERENCE_SCALE", 0.0)
    project, _, _ = setup_project(client, 2, 1)
    wait_job(client, data(client.post(f"/api/projects/{project['id']}/visuals/shots")))
    assert not [p for p in requests_log if "empty scene" in p.get("prompt", "")]
    assert not [p for p in requests_log if "ip_adapter_scene_image" in p or "ip_adapter_scene_mask" in p]


def test_plates_use_the_people_free_negative(client, monkeypatch, requests_log):  # noqa: F811
    monkeypatch.setattr(settings, "VISUALS_COLOUR_RETRIES", 0)
    project, _, _ = setup_project(client, 1, 1)
    wait_job(client, data(client.post(f"/api/projects/{project['id']}/visuals/shots")))
    plates = [p for p in requests_log if "empty scene" in p.get("prompt", "")]
    assert plates and all(p["negative_prompt"] == recipes.PLATE_NEGATIVE for p in plates)
    assert "people" in recipes.PLATE_NEGATIVE and recipes.token_count(recipes.PLATE_NEGATIVE) <= 72


def test_used_count_duplicate_and_versioned_plate_url(client):  # noqa: F811
    project, _, scenes = setup_project(client, 1, 2)
    listed = {scene["id"]: scene for scene in data(client.get("/api/visuals/scenes"))}
    assert all(listed[scene["id"]]["used_count"] == 1 for scene in scenes)
    unused = next(scene for scene in listed.values() if scene["id"] not in {s["id"] for s in scenes})
    assert unused["used_count"] == 0
    first = data(client.post(f"/api/visuals/scenes/{scenes[0]['id']}/duplicate"))
    second = data(client.post(f"/api/visuals/scenes/{scenes[0]['id']}/duplicate"))
    assert first["name"] == f"{scenes[0]['name']} copy" and second["name"] == f"{scenes[0]['name']} copy 2"
    assert not first["is_builtin"] and first["preview_url"] is None and first["seed"] != listed[scenes[0]["id"]]["seed"]
    assert (first["place"], first["category"]) == (listed[scenes[0]["id"]]["place"], listed[scenes[0]["id"]]["category"])
    assert client.post("/api/visuals/scenes/missing/duplicate").status_code == 404
    with sqlite3.connect(settings.db_path) as connection:
        connection.execute("UPDATE scenes SET preview_path = 'p.png', updated_at = '2026-10-05T01:02:03+00:00' "
                           "WHERE id = ?", (first["id"],))
    copy = next(s for s in data(client.get("/api/visuals/scenes")) if s["id"] == first["id"])
    assert copy["preview_url"].endswith("/preview?v=2026-10-05T01%3A02%3A03%2B00%3A00")


async def test_builtin_category_moves_respect_user_choices(tmp_path, monkeypatch):
    """Task 23.3b: a built-in still on its previously seeded category moves to the owner's
    grouping; one the user re-categorised keeps the user's choice."""
    from app.db.database import Database, init_db

    monkeypatch.setattr(settings, "DATA_DIR", tmp_path)
    old = Database._instance
    Database._instance = None
    try:
        await init_db()
        db = Database.instance().connection
        await db.execute("UPDATE scenes SET category = 'food' WHERE id = 'builtin-cafe'")
        await db.execute("UPDATE scenes SET category = 'home' WHERE id = 'builtin-restaurant'")
        await db.commit()
        await init_db()
        cursor = await db.execute("SELECT id, category FROM scenes WHERE id IN ('builtin-cafe', 'builtin-restaurant')")
        assert dict(await cursor.fetchall()) == {"builtin-cafe": "city", "builtin-restaurant": "home"}
    finally:
        await Database.instance().close()
        Database._instance = old


async def test_builtin_place_upgrade_keeps_user_edits(tmp_path, monkeypatch):
    """Task 23.3b: a built-in still holding a replaced place text gets the new text and loses its
    stale plate; a place the user edited is kept with its plate."""
    from app.db.database import Database, init_db

    monkeypatch.setattr(settings, "DATA_DIR", tmp_path)
    old = Database._instance
    Database._instance = None
    try:
        await init_db()
        db = Database.instance().connection
        await db.execute("UPDATE scenes SET place = 'a city zoo', preview_path = 'z.png' WHERE id = 'builtin-zoo'")
        await db.execute("UPDATE scenes SET place = 'my own camp', preview_path = 'c.png' "
                         "WHERE id = 'builtin-summer-camp'")
        await db.commit()
        await init_db()
        cursor = await db.execute(
            "SELECT id, place, preview_path FROM scenes WHERE id IN ('builtin-zoo', 'builtin-summer-camp')")
        rows = {row[0]: (row[1], row[2]) for row in await cursor.fetchall()}
        assert rows == {"builtin-zoo": ("a zoo with elephants", None), "builtin-summer-camp": ("my own camp", "c.png")}
    finally:
        await Database.instance().close()
        Database._instance = old
