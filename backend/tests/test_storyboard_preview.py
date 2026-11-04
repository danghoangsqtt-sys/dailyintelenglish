"""Phase 78 (Task 78.1): the Step 5 beat thumbnails show what the talking-characters video will show."""

import sqlite3

from PIL import Image

from backend.core.config import settings
from backend.tests.test_podcast_modes import _make_a_plate
from backend.tests.test_sprite_video_props import _give_sprites
from backend.tests.test_storyboard_api import beat, project_with_script
from backend.tests.test_visuals_project_api import client, data  # noqa: F401


def _cast(client, project_id):  # noqa: F811
    return {member["speaker_index"]: member for member in data(client.get(f"/api/projects/{project_id}/visuals"))["cast"]}


def test_scene_beat_shows_its_plate_and_the_speaking_pair(client):  # noqa: F811
    project = project_with_script(client)
    cast = _cast(client, project["id"])
    _give_sprites(cast[0]["character_id"])  # speaker 1 has no sprites yet
    _make_a_plate("builtin-park")
    result = data(client.post(f"/api/projects/{project['id']}/storyboard/preview", json={"beats": [
        beat(0, 2, scene_id="builtin-park", speakers=[0, 1], expression="smile"),
        beat(3, 5, scene_id="builtin-cafe", speakers=[0, 1]),
    ]}))
    first, second = result["beats"]
    assert first["scene"]["id"] == "builtin-park" and first["scene"]["preview_url"]
    assert [member["slot"] for member in first["characters"]] == [0, 1]
    ready = next(member for member in first["characters"] if member["speaker_index"] == 0)
    assert ready["picture_url"].endswith(f"/sprites/{cast[0]['character_id']}/smile__closed/content")
    assert 0 <= ready["top_fraction"] < 1 and isinstance(ready["mirror"], bool)
    assert next(member for member in first["characters"] if member["speaker_index"] == 1)["missing"] == "sprites"
    # the cafe has no plate: the beat names it but has no picture (the render keeps the place before)
    assert second["scene"]["id"] == "builtin-cafe" and second["scene"]["preview_url"] is None


def test_insert_keeps_the_place_before_and_reports_its_illustration(client):  # noqa: F811
    project = project_with_script(client)
    _make_a_plate("builtin-park")
    beats = [beat(0, 2, scene_id="builtin-park"),
             {"line_from": 3, "line_to": 3, "kind": "insert", "new_place": "a busy subway", "action": "packing suitcase"},
             beat(4, 5, scene_id="builtin-park")]
    missing = data(client.post(f"/api/projects/{project['id']}/storyboard/preview", json={"beats": beats}))["beats"][1]
    assert missing["kind"] == "insert" and missing["scene"]["id"] == "builtin-park"
    assert missing["illustration"] == {"status": "missing"}

    path = settings.DATA_DIR / "library" / "activities" / "packing-preview.png"
    path.parent.mkdir(parents=True, exist_ok=True)
    Image.new("RGB", (1280, 720), (30, 60, 90)).save(path)
    with sqlite3.connect(settings.db_path) as connection:
        connection.execute(
            "INSERT INTO activity_library (id, activity, aliases_json, path, content_sha, review_state, created_at, updated_at) "
            "VALUES ('packing-preview', 'packing', '[\"packing suitcase\"]', ?, 'sha-packing-preview', 'approved', 'now', 'now')",
            (str(path),))
    found = data(client.post(f"/api/projects/{project['id']}/storyboard/preview", json={"beats": beats}))["beats"][1]
    assert found["illustration"]["status"] == "generic"
    assert found["illustration"]["url"] == "/api/visuals/library/activities/packing-preview/content"
    assert found["illustration"]["max_seconds"] == 6.0


def test_saved_storyboard_by_default_and_bad_ranges_per_beat(client):  # noqa: F811
    project = project_with_script(client)
    base = f"/api/projects/{project['id']}/storyboard"
    data(client.put(base, json={"beats": [beat(0, 5, speakers=[0, 1])]}))
    saved = data(client.post(f"{base}/preview", json={}))
    assert [item["line_to"] for item in saved["beats"]] == [5] and saved["lines"] == 6
    drafts = data(client.post(f"{base}/preview", json={"beats": [beat(0, 2), beat(3, 9)]}))["beats"]
    assert "error" not in drafts[0] and drafts[1]["error"] == "Its lines are outside the script."
    assert client.post("/api/projects/nope/storyboard/preview", json={}).status_code == 404
