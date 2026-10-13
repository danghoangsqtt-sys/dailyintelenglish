"""Phase 39 (D118): Qwen-Image-2.1-Turbo draws illustrations, plates and topic pictures, Qwen-Image-Edit-2511 character
inserts; RealVisXL is the fallback. GPU-free: the fake engine records the Qwen batches."""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest
from PIL import Image

from backend.ai.image import recipes
from backend.ai.image.engine import FakeImageEngine
from backend.core.config import settings
from backend.core.paths import AI_DIR
from tests.test_activity_illustrations import _project_with_inserts
from tests.test_visuals_project_api import client, data, setup_project, wait_job  # noqa: F401


@pytest.fixture
def qwen_log(monkeypatch):
    monkeypatch.setattr(FakeImageEngine, "qwen_calls", [])
    monkeypatch.setattr(FakeImageEngine, "qwen_available", True)
    return FakeImageEngine.qwen_calls


def _created(job: dict) -> list[str]:
    return job["result"]["created"] if "result" in job else json.loads(job["result_json"])["created"]


# --- prompts -------------------------------------------------------------------------------------------------------

def test_the_qwen_prompts_describe_the_picture_in_sentences():
    activity = recipes.qwen_activity_prompt("choosing vegetables at a market stall", "an outdoor market")
    assert "ordinary people choosing vegetables at a market stall in an outdoor market" in activity
    assert "different ages, genders and looks" in activity and "No text" in activity  # D110 + the benchmark's repeated face
    plate = recipes.qwen_scene_prompt({"place": "a small family restaurant", "time_of_day": "night"})
    assert "a small family restaurant, night, warm lamps" in plate and "no people at all" in plate
    character = {"gender": "female", "top_item": "mini dress", "bottom_item": "mini dress", "top_color": "white",
                 "bottom_color": "white"}
    insert = recipes.qwen_insert_person_prompt(character, "cooking vegetables")
    assert "the same woman as in the reference picture" in insert and "cooking vegetables" in insert
    assert recipes.outfit_phrase(character) in insert
    topic = recipes.qwen_topic_prompt("Choosing the Menu", "cooking, grocery shopping")
    assert "about choosing the menu: cooking, grocery shopping" in topic and "left half" in topic and "no text" in topic
    assert "thumbnail" not in topic and "title" not in topic and "no people" in topic.lower()


def test_the_worker_side_validates_a_qwen_request_without_a_gpu():
    spec = importlib.util.spec_from_file_location("qwen_runner_under_test", AI_DIR / "image" / "qwen_runner.py")
    runner = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(runner)
    item = {"prompt": "p", "seed": 1, "width": 1344, "height": 768, "output_path": "x.png"}
    assert runner.validate({"model": "qwen21", "items": [item]}) == ("qwen21", [item])
    with pytest.raises(ValueError, match="multiples of 16"):
        runner.validate({"model": "qwen21", "items": [{**item, "width": 1280 + 8}]})
    with pytest.raises(ValueError, match="reference"):
        runner.validate({"model": "qwen_edit", "items": [item]})
    with pytest.raises(ValueError, match="model must be"):
        runner.validate({"model": "flux", "items": [item]})


# --- activity illustrations ------------------------------------------------------------------------------------------

def test_missing_illustrations_are_drawn_by_qwen21_in_one_batch(client, qwen_log):  # noqa: F811
    project = _project_with_inserts(client)
    job = wait_job(client, data(client.post(f"/api/projects/{project['id']}/visuals/activity-illustrations")))
    assert len(_created(job)) == 1
    assert [call["model"] for call in qwen_log] == ["qwen21"] and len(qwen_log[0]["items"]) == 1
    item = qwen_log[0]["items"][0]
    assert "searching for travel accommodation" in item["prompt"] and (item["width"], item["height"]) == (1344, 768)


def test_without_qwen_the_illustrations_fall_back_to_realvisxl(client, qwen_log, monkeypatch):  # noqa: F811
    monkeypatch.setattr(FakeImageEngine, "qwen_available", False)
    project = _project_with_inserts(client)
    job = wait_job(client, data(client.post(f"/api/projects/{project['id']}/visuals/activity-illustrations")))
    assert len(_created(job)) == 1 and [call["model"] for call in qwen_log] == ["qwen21"]


def test_the_setting_can_keep_realvisxl_for_illustrations(client, qwen_log, monkeypatch):  # noqa: F811
    monkeypatch.setattr(settings, "IMAGE_ILLUSTRATION_ENGINE", "realvisxl")
    project = _project_with_inserts(client)
    job = wait_job(client, data(client.post(f"/api/projects/{project['id']}/visuals/activity-illustrations")))
    assert len(_created(job)) == 1 and qwen_log == []


# --- scene plates ---------------------------------------------------------------------------------------------------

def test_missing_scene_plates_are_drawn_by_qwen21_once_and_reused(client, qwen_log, monkeypatch):  # noqa: F811
    monkeypatch.setattr(settings, "VISUALS_COLOUR_RETRIES", 0)
    project, _, scenes = setup_project(client, 2, 2)
    wait_job(client, data(client.post(f"/api/projects/{project['id']}/visuals/shots")))
    plates = [call for call in qwen_log if call["model"] == "qwen21"]
    assert len(plates) == 1 and len(plates[0]["items"]) == 2
    assert all("completely empty, with no people" in item["prompt"] for item in plates[0]["items"])
    for scene in scenes:
        with Image.open(settings.DATA_DIR / "library" / "scenes" / scene["id"] / "preview.png") as image:
            assert image.size == (1344, 768)
    qwen_log.clear()
    wait_job(client, data(client.post(f"/api/projects/{project['id']}/visuals/shots")))
    assert not [call for call in qwen_log if call["model"] == "qwen21"]  # plates are reused


# --- thumbnail topic picture ---------------------------------------------------------------------------------------

def test_the_topic_picture_is_drawn_locally_and_becomes_the_first_thumbnail_background(client, qwen_log):  # noqa: F811
    project = _project_with_inserts(client)
    response = client.post(f"/api/projects/{project['id']}/thumbnails/topic-picture")
    assert response.status_code == 201, response.text
    assert [call["model"] for call in qwen_log] == ["qwen21"]
    item = qwen_log[0]["items"][0]
    assert (item["width"], item["height"]) == (1280, 720) and project["topic"].split(". ")[0].lower() in item["prompt"]
    picture = client.get(f"/api/projects/{project['id']}/thumbnails/topic-picture")
    assert picture.status_code == 200 and picture.headers["content-type"] == "image/png"
    path = Path(item["output_path"])
    with Image.open(path) as image:
        assert image.size == (1280, 720)

    import asyncio

    import aiosqlite

    from backend.media import thumbnail_compose

    async def backgrounds() -> list[str]:
        async with aiosqlite.connect(settings.db_path) as db:
            db.row_factory = aiosqlite.Row
            return (await thumbnail_compose.composition_inputs(db, project))["backgrounds"]

    assert asyncio.run(backgrounds())[0] == str(path)


def test_without_qwen_the_topic_picture_says_so(client, qwen_log, monkeypatch):  # noqa: F811
    monkeypatch.setattr(FakeImageEngine, "qwen_available", False)
    project = _project_with_inserts(client)
    response = client.post(f"/api/projects/{project['id']}/thumbnails/topic-picture")
    assert response.status_code == 422 and "not installed" in response.json()["error"]
    assert client.get(f"/api/projects/{project['id']}/thumbnails/topic-picture").status_code == 404
