"""Task 29.2: an insert that names a cast speaker is drawn as that character (face reference), others stay plain."""

from __future__ import annotations

import pytest

from app.core.config import settings
from app.services.visuals import recipes
from app.services.visuals.engine import FakeImageEngine
from tests.test_storyboard_api import project_with_script
from tests.test_visuals_gaze import SCENE  # noqa: F401
from tests.test_visuals_phase28 import LAN, _real_tokenizer
from tests.test_visuals_project_api import client, data, wait_job  # noqa: F401

BEATS = [
    {"line_from": 0, "line_to": 2, "scene_id": "builtin-cafe", "speakers": [0, 1], "action": "drinking coffee",
     "expression": "smile"},
    {"line_from": 3, "line_to": 3, "kind": "insert", "new_place": "a phone on a table", "speakers": [1],
     "action": "checking a phone", "expression": "calm"},
    {"line_from": 4, "line_to": 4, "kind": "insert", "new_place": "crowded subway at rush hour", "speakers": [],
     "action": "", "expression": "worried"},
    {"line_from": 5, "line_to": 5, "scene_id": "builtin-cafe", "speakers": [0, 1], "action": "drinking coffee",
     "expression": "smile"},
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


def test_the_person_insert_prompt_names_the_character_the_outfit_and_the_action_within_the_clip_budget():
    prompt = recipes.insert_person_prompt(LAN, "checking a phone")
    assert "checking a phone" in prompt and "medium shot" in prompt
    assert recipes.outfit_phrase(LAN) in prompt
    long_action = "sitting by a very large window while slowly stirring a hot cup of coffee on a rainy morning"
    assert len(_real_tokenizer()(recipes.insert_person_prompt(LAN, long_action))["input_ids"]) <= 77


def test_an_insert_with_a_speaker_gets_that_characters_face_and_one_without_stays_plain(client, requests_log):  # noqa: F811
    project = project_with_script(client)
    base = f"/api/projects/{project['id']}"
    data(client.put(f"{base}/storyboard", json={"beats": BEATS, "status": "approved"}))
    wait_job(client, data(client.post(f"{base}/visuals/shots")))
    shots = data(client.get(f"{base}/visuals"))["shots"]
    assert all(shot["status"] == "complete" for shot in shots)
    person = [p for p in requests_log if "checking a phone" in p.get("prompt", "") and p.get("command") == "generate"]
    plain = [p for p in requests_log if "crowded subway at rush hour" in p.get("prompt", "")]
    assert len(person) == 1 and len(plain) == 1
    assert person[0]["ip_adapter_image"].endswith("face.png") and person[0]["ip_adapter_scale"] == 0.5
    assert person[0]["negative_prompt"] != recipes.PLATE_NEGATIVE and "init_image" not in person[0]
    assert "ip_adapter_image" not in plain[0] and plain[0]["negative_prompt"] == recipes.PLATE_NEGATIVE
    cast = data(client.get(f"{base}/visuals"))["cast"]
    second = next(member for member in cast if member["speaker_index"] == 1)
    assert second["character_id"] in person[0]["ip_adapter_image"]  # speaker 1's own face, not the other character's
