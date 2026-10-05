"""Task 24.5a: shots from the approved storyboard (fake engine)."""

import pytest

from app.core.config import settings
from app.services.visuals import recipes
from app.services.visuals.engine import FakeImageEngine
from app.services.visuals.project_visuals_service import storyboard_shot_specs
from tests.test_storyboard_api import project_with_script
from tests.test_visuals_project_api import client, data, wait_job  # noqa: F401

BEATS = [
    {"line_from": 0, "line_to": 1, "scene_id": "builtin-cafe", "speakers": [0, 1], "action": "drinking coffee",
     "expression": "smile"},
    {"line_from": 2, "line_to": 2, "scene_id": "builtin-cafe", "speakers": [0, 1], "action": "reading city plans",
     "expression": "thinking"},
    {"line_from": 3, "line_to": 3, "kind": "insert", "new_place": "crowded subway at rush hour",
     "expression": "worried"},
    {"line_from": 4, "line_to": 5, "new_place": "a quiet tea house", "speakers": [1], "action": "",
     "expression": "calm"},
]


@pytest.fixture
def requests_log(monkeypatch):
    log = []
    original = FakeImageEngine.request

    async def recording(self, payload):
        log.append(dict(payload))
        return await original(self, payload)

    monkeypatch.setattr(FakeImageEngine, "request", recording)
    monkeypatch.setattr(settings, "VISUALS_COLOUR_RETRIES", 0)
    return log


def test_specs_follow_places_actions_and_inserts():
    cast = [{"speaker_index": 0}, {"speaker_index": 1}]
    beats = [{**beat, "kind": beat.get("kind", "scene"), "scene_id": beat.get("scene_id") or "s-tea"} for beat in BEATS]
    specs = storyboard_shot_specs(beats, cast)
    assert [(spec["scene_id"], spec["kind"], spec["action"]) for spec in specs] == [
        ("builtin-cafe", "single", "drinking coffee"), ("builtin-cafe", "single", "drinking coffee"),
        ("builtin-cafe", "duo_close", "drinking coffee"), ("builtin-cafe", "duo_wide", "drinking coffee"),
        ("builtin-cafe", "duo_wide", "reading city plans"),
        ("", "insert", ""),
        ("s-tea", "single", ""), ("s-tea", "single", ""), ("s-tea", "duo_close", ""), ("s-tea", "duo_wide", ""),
    ]
    assert specs[4]["beat_position"] == 1 and specs[5]["subject"] == "crowded subway at rush hour"
    solo = storyboard_shot_specs([{"kind": "scene", "scene_id": "a", "speakers": [1], "action": "x"},
                                  {"kind": "scene", "scene_id": "a", "speakers": [1], "action": "y"}], cast)
    assert (solo[-1]["kind"], solo[-1]["speakers"]) == ("single", [1])


def test_draft_storyboard_keeps_the_legacy_path(client):  # noqa: F811
    project = project_with_script(client)
    data(client.put(f"/api/projects/{project['id']}/storyboard", json={"beats": BEATS}))  # draft only
    response = client.post(f"/api/projects/{project['id']}/visuals/shots")
    assert response.status_code == 422 and "approve a storyboard" in response.text  # legacy needs scenes


def test_approved_storyboard_generates_beat_shots(client, requests_log):  # noqa: F811
    project = project_with_script(client)
    base = f"/api/projects/{project['id']}"
    data(client.put(f"{base}/storyboard", json={"beats": BEATS, "status": "approved"}))
    wait_job(client, data(client.post(f"{base}/visuals/shots")))
    shots = data(client.get(f"{base}/visuals"))["shots"]
    assert len(shots) == 10 and all(shot["status"] == "complete" for shot in shots)
    insert = next(shot for shot in shots if shot["kind"] == "insert")
    assert (insert["scene_name"], insert["subject"]) == ("Inserts", "crowded subway at rush hour")
    tea = next(scene for scene in data(client.get("/api/visuals/scenes")) if scene["place"] == "a quiet tea house")
    assert tea["name"] == "Quiet tea house" and not tea["is_builtin"] and tea["preview_url"]
    beats = data(client.get(f"{base}/storyboard"))["beats"]
    assert beats[3]["scene_id"] == tea["id"] and beats[3]["new_place"] is None
    insert_calls = [p for p in requests_log if "crowded subway at rush hour" in p.get("prompt", "")]
    assert len(insert_calls) == 1 and insert_calls[0]["negative_prompt"] == recipes.PLATE_NEGATIVE
    assert not any(key.startswith("ip_adapter") for key in insert_calls[0])
    encodes = [p["items"][0]["prompt"] for p in requests_log if p["command"] == "encode"]
    assert any("warm smile, drinking coffee" in prompt for prompt in encodes)
    assert any("thoughtful look, reading city plans" in prompt for prompt in encodes)
    data(client.post(f"{base}/visuals/shots/{insert['id']}/regenerate"))  # an insert can be regenerated
