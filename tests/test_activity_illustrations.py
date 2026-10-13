"""Task 33.10 (Gate B-23, D102): inserts without a library picture -- closest activities, outside-AI prompt, GPU drawing,
upload, approval in Step 5, then a match."""

from __future__ import annotations

import io
import json
import sqlite3

from PIL import Image

from app.core.config import settings
from app.services.visuals import recipes
from tests.test_visuals_project_api import client, data, setup_project, wait_job  # noqa: F401


def _project_with_inserts(client) -> dict:  # noqa: F811
    project, _, _ = setup_project(client, 2, 1)
    speaker_ids = [speaker["id"] for speaker in project["speakers"]]
    folder = settings.DATA_DIR / "library" / "activities"
    folder.mkdir(parents=True, exist_ok=True)
    picture = folder / "generic-pack.png"
    Image.new("RGB", (1344, 768), (40, 80, 120)).save(picture)
    with sqlite3.connect(settings.db_path) as connection:
        for index, text in enumerate(("We could rent a cabin, cheaper than a fancy hotel.",
                                      "Remember to start packing warm clothes tonight.")):
            connection.execute(
                "INSERT INTO script_lines (id, project_id, line_index, speaker_id, text) VALUES (?, ?, ?, ?, ?)",
                (f"ill-line-{index}", project["id"], index, speaker_ids[index], text),
            )
        connection.execute(
            "INSERT INTO project_storyboards (project_id, status, source, updated_at) VALUES (?, 'approved', 'owner', 'now')",
            (project["id"],),
        )
        for index, (action, place) in enumerate((("searching for travel accommodation", "cabin rentals on tablet"),
                                                 ("packing", None))):
            connection.execute(
                "INSERT INTO project_beats (id, project_id, position, line_from, line_to, kind, new_place, speakers_json, "
                "action, expression, created_at, updated_at) VALUES (?, ?, ?, ?, ?, 'insert', ?, '[]', ?, 'calm', 'now', 'now')",
                (f"ill-beat-{index}", project["id"], index, index, index, place, action),
            )
        connection.execute(
            "INSERT INTO activity_library (id, activity, context_tags_json, path, content_sha, review_state, created_at, "
            "updated_at) VALUES ('generic-pack', 'packing', ?, ?, 'sha-pack', 'approved', 'now', 'now')",
            (json.dumps(["bedroom"]), str(picture)),
        )
        connection.execute(
            "INSERT INTO activity_library (id, activity, path, content_sha, review_state, created_at, updated_at) "
            "VALUES ('generic-hotel', 'find hotel', ?, 'sha-hotel', 'approved', 'now', 'now')", (str(picture),),
        )
    return project


def test_a_missing_insert_names_the_closest_activities_and_an_outside_ai_prompt(client):  # noqa: F811
    project = _project_with_inserts(client)
    coverage = data(client.get(f"/api/projects/{project['id']}/visuals/activity-coverage"))
    assert [item["status"] for item in coverage["items"]] == ["missing", "generic"]
    missing = coverage["items"][0]
    assert missing["activity"] == "searching for travel accommodation" and missing["pending"] is None
    assert missing["suggestions"][0] == "find hotel"
    assert "one ordinary adult searching for travel accommodation in cabin rentals on tablet" in missing["prompt"]
    assert "No text" in missing["prompt"] and coverage["to_draw"] == 1


def test_the_gpu_draws_a_pending_picture_that_matches_once_approved(client):  # noqa: F811
    project = _project_with_inserts(client)
    job = data(client.post(f"/api/projects/{project['id']}/visuals/activity-illustrations"))
    finished = wait_job(client, job)
    created = finished["result"]["created"] if "result" in finished else json.loads(finished["result_json"])["created"]
    assert len(created) == 1
    coverage = data(client.get(f"/api/projects/{project['id']}/visuals/activity-coverage"))
    missing = coverage["items"][0]
    assert missing["pending"]["id"] == created[0] and coverage["to_draw"] == 0
    response = client.get(missing["pending"]["url"])
    assert response.status_code == 200 and response.headers["content-type"].startswith("image/")
    assert client.post(f"/api/projects/{project['id']}/visuals/activity-illustrations").status_code == 422  # nothing to draw
    data(client.patch(f"/api/visuals/library/activities/{created[0]}/review", json={"review_state": "approved"}))
    coverage = data(client.get(f"/api/projects/{project['id']}/visuals/activity-coverage"))
    assert [item["status"] for item in coverage["items"]] == ["generic", "generic"] and coverage["missing"] == 0


def test_an_outside_ai_upload_becomes_the_pending_picture(client):  # noqa: F811
    project = _project_with_inserts(client)
    buffer = io.BytesIO()
    Image.new("RGB", (1344, 768), (200, 120, 40)).save(buffer, format="PNG")
    response = client.post("/api/visuals/library/activities/upload", data={
        "activity": "searching for travel accommodation", "context_tags": "cabin rentals on tablet"},
        files={"file": ("outside.png", buffer.getvalue(), "image/png")})
    assert response.status_code == 201, response.text
    coverage = data(client.get(f"/api/projects/{project['id']}/visuals/activity-coverage"))
    assert coverage["items"][0]["pending"]["id"] == response.json()["data"]["id"] and coverage["to_draw"] == 0


def test_the_gpu_prompt_shows_any_person_never_a_cast_character():
    prompt = recipes.activity_illustration_prompt("packing a suitcase", "a bright bedroom")
    assert prompt.startswith(recipes.STYLE_EDITORIAL) and "one ordinary adult person, packing a suitcase" in prompt
    assert "in a bright bedroom" in prompt and "text" in recipes.ACTIVITY_NEGATIVE
    assert "person," not in recipes.ACTIVITY_NEGATIVE  # people are wanted here, unlike a scene plate
