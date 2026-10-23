"""Task 23.2: scene model v2 (category, time of day, seed, plate) and the plate as a scene reference."""

import sqlite3

import pytest

from backend.core.config import settings
from backend.ai.image.engine import FakeImageEngine
from tests.test_storyboard_api import project_with_script
from tests.test_visuals_project_api import client, data, setup_project, wait_job  # noqa: F401

SIZE = (1344, 768)


def test_archive_restore_delete_preserve_preview_and_protect_builtins(client):  # noqa: F811
    scene = data(client.post("/api/visuals/scenes/builtin-cafe/duplicate"))
    base = f"/api/visuals/scenes/{scene['id']}"
    job = data(client.post(f"{base}/preview"))
    wait_job(client, job)
    before = next(s for s in data(client.get("/api/visuals/scenes")) if s["id"] == scene["id"])
    preview = client.get(f"{base}/preview")
    assert preview.status_code == 200
    archived = data(client.post(f"{base}/archive"))
    assert archived["archived_at"] and archived["preview_url"] == before["preview_url"]
    assert data(client.post(f"{base}/archive"))["archived_at"] == archived["archived_at"]
    assert scene["id"] not in {s["id"] for s in data(client.get("/api/visuals/scenes"))}
    assert scene["id"] in {s["id"] for s in data(client.get("/api/visuals/scenes?include_archived=true"))}
    assert client.get(f"{base}/preview").content == preview.content
    restored = data(client.post(f"{base}/restore"))
    assert restored["archived_at"] is None and restored["preview_url"] == before["preview_url"]
    assert data(client.post(f"{base}/restore"))["archived_at"] is None
    assert scene["id"] in {s["id"] for s in data(client.get("/api/visuals/scenes"))}
    data(client.delete(base))
    assert client.get(f"{base}/preview").content == preview.content
    assert any(s["id"] == scene["id"] and s["archived_at"] for s in data(client.get("/api/visuals/scenes?include_archived=true")))
    copy = data(client.post(f"{base}/duplicate"))
    assert copy["archived_at"] is None and copy["preview_url"] is None
    assert client.delete("/api/visuals/scenes/builtin-cafe").status_code == 409
    assert client.post("/api/visuals/scenes/builtin-cafe/archive").status_code == 409
    assert client.post("/api/visuals/scenes/missing/archive").status_code == 404
    assert client.post("/api/visuals/scenes/missing/restore").status_code == 404


@pytest.mark.parametrize("source", ["beat", "shortlist", "explainer", "none"])
@pytest.mark.parametrize("operation", ["archive", "delete"])
def test_storyboard_archive_choices_require_existing_project_reference(client, source, operation):  # noqa: F811
    project = project_with_script(client, cast=0)
    other = project_with_script(client, cast=0)
    scene = data(client.post("/api/visuals/scenes/builtin-cafe/duplicate"))
    body = {"beats": [{"line_from": 0, "line_to": 5, "scene_id": scene["id"]}], "status": "approved"}
    base = f"/api/projects/{project['id']}/storyboard"
    if source == "beat":
        data(client.put(base, json=body))
    elif source == "shortlist":
        data(client.put(f"/api/projects/{project['id']}/visuals/scenes", json=[scene["id"]]))
    elif source == "explainer":
        import json

        with sqlite3.connect(settings.db_path) as connection:
            connection.execute(
                "INSERT INTO project_explainer_plans "
                "(project_id, revision, status, source_fingerprint, plan_json, updated_at) "
                "VALUES (?, 1, 'draft', ?, ?, 'now')",
                (project["id"], "a" * 64, json.dumps({"segments": [{"scene": {"scene_id": scene["id"]}}]})),
            )
    if operation == "archive":
        data(client.post(f"/api/visuals/scenes/{scene['id']}/archive"))
    else:
        data(client.delete(f"/api/visuals/scenes/{scene['id']}"))
    response = client.put(base, json=body)
    scoped = {s["id"] for s in data(client.get("/api/visuals/scenes", params={"project_id": project["id"]}))}
    if source == "none":
        assert response.status_code == 422 and "Archived scene" in response.text
        assert scene["id"] not in scoped
    else:
        assert data(response)["beats"][0]["scene_id"] == scene["id"]
        assert scene["id"] in scoped
        data(client.put(f"/api/projects/{project['id']}/visuals/scenes", json=[scene["id"]]))
    other_base = f"/api/projects/{other['id']}"
    assert client.put(f"{other_base}/storyboard", json=body).status_code == 422
    assert client.put(f"{other_base}/visuals/scenes", json=[scene["id"]]).status_code == 422
    assert scene["id"] not in {s["id"] for s in data(client.get("/api/visuals/scenes", params={"project_id": other["id"]}))}
    data(client.post(f"/api/visuals/scenes/{scene['id']}/restore"))
    assert data(client.put(f"{other_base}/storyboard", json=body))["beats"][0]["scene_id"] == scene["id"]


def test_storyboard_uses_more_than_three_library_scenes_without_shortlist(client):  # noqa: F811
    project = project_with_script(client, cast=0)
    scenes = data(client.get("/api/visuals/scenes"))[:4]
    body = {"beats": [{"line_from": index, "line_to": index if index < 3 else 5, "scene_id": scene["id"]}
                      for index, scene in enumerate(scenes)]}
    saved = data(client.put(f"/api/projects/{project['id']}/storyboard", json=body))
    assert len({beat["scene_id"] for beat in saved["beats"]}) == saved["estimate"]["images"] == 4
    assert data(client.get(f"/api/projects/{project['id']}/visuals"))["scenes"] == []


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
    from backend.db.database import Database, init_db

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
    from backend.db.database import Database, init_db

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
