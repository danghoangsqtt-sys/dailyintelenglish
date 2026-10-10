"""Phase 33.8 integration for dynamic profiles and three-speaker visual planning."""

from typing import AsyncGenerator

import pytest
from playwright.async_api import Browser, async_playwright

from app.services.visuals.activity_matcher import match_activity
from app.services.visuals.project_visuals_service import storyboard_shot_specs
from tests.conftest import live_server
from tests.test_visuals_project_api import client, data, locked_character  # noqa: F401


def three_speaker_project(client):  # noqa: F811
    project = data(client.post("/api/projects", json={
        "name": "Three profile story", "topic": "Planning a city trip", "cefr_level": "B1",
        "duration_minutes": 2, "num_speakers": 3, "genre": "small_talk", "accent": "american",
        "speakers": [
            {"name": "Host", "gender": "female", "accent": "american"},
            {"name": "Guest", "gender": "male", "accent": "american"},
            {"name": "Guide", "gender": "female", "accent": "american"},
        ],
    }))
    detail = data(client.get(f"/api/projects/{project['id']}"))
    speaker_ids = {speaker["speaker_index"]: speaker["id"] for speaker in detail["speakers"]}
    order = [0, 1, 2, 1, 2, 0]
    data(client.put(f"/api/projects/{project['id']}/script", json={"lines": [
        {"speaker_id": speaker_ids[index], "text": f"Dialogue line {position + 1}."}
        for position, index in enumerate(order)
    ]}))
    character_ids = [locked_character(f"Profile {index}", color) for index, color in enumerate(
        ("yellow", "green", "blue"), start=1,
    )]
    data(client.put(f"/api/projects/{project['id']}/visuals/cast", json=[
        {"speaker_index": index, "character_id": character_id}
        for index, character_id in enumerate(character_ids)
    ]))
    return project


def test_three_speaker_storyboard_derives_active_pairs_and_rejects_three_visible(client):  # noqa: F811
    project = three_speaker_project(client)
    base = f"/api/projects/{project['id']}/storyboard"
    beats = [
        {"line_from": 0, "line_to": 1, "scene_id": "builtin-cafe", "action": "planning"},
        {"line_from": 2, "line_to": 3, "scene_id": "builtin-cafe", "action": "planning"},
        {"line_from": 4, "line_to": 5, "scene_id": "builtin-cafe", "speakers": [2, 0], "action": "walking"},
    ]

    saved = data(client.put(base, json={"beats": beats, "status": "approved"}))

    assert [beat["speakers"] for beat in saved["beats"]] == [[0, 1], [2, 1], [2, 0]]
    assert saved["estimate"]["images"] == 7
    specs = storyboard_shot_specs(saved["beats"], [{"speaker_index": index} for index in range(3)])
    assert [spec["speakers"] for spec in specs if spec["kind"] == "duo_wide"] == [[0, 1], [2, 1], [2, 0]]

    invalid = client.put(base, json={"beats": [{
        "line_from": 0, "line_to": 5, "scene_id": "builtin-cafe", "speakers": [0, 1, 2],
    }]})
    assert invalid.status_code == 422


def test_new_profile_with_no_specific_activity_uses_generic_then_sprite_fallback():
    candidates = [
        {"id": "other", "character_id": "other-profile", "activity": "walking", "aliases": [],
         "context_tags": [], "use_count": 0, "last_used_at": None},
        {"id": "generic", "character_id": None, "activity": "walking", "aliases": [],
         "context_tags": [], "use_count": 0, "last_used_at": None},
    ]
    matched = match_activity(candidates, "new-profile", "walking outdoors", "We are walking outdoors.")
    assert matched["activity_id"] == "generic" and matched["match_type"] == "generic"
    assert match_activity(candidates[:1], "new-profile", "walking outdoors", "We are walking outdoors.") is None


@pytest.fixture(scope="module")
def profile_filter_server(tmp_path_factory: pytest.TempPathFactory):
    with live_server(tmp_path_factory, "profile-filter") as url:
        yield url


@pytest.fixture
async def profile_filter_browser() -> AsyncGenerator[Browser, None]:
    async with async_playwright() as playwright:
        browser = await playwright.chromium.launch(headless=True)
        yield browser
        await browser.close()


@pytest.mark.asyncio
async def test_new_profile_appears_in_activity_filter_without_frontend_name_changes(
    profile_filter_browser: Browser, profile_filter_server: str,
):
    page = await profile_filter_browser.new_page()
    response = await page.request.post(
        f"{profile_filter_server}/api/visuals/characters", data={"name": "Dynamic Rowan"},
    )
    assert response.ok
    profile_id = (await response.json())["data"]["id"]

    await page.goto(f"{profile_filter_server}/shots")
    option = page.locator(f'#activity-filter-scope option[value="{profile_id}"]')
    await option.wait_for(state="attached")
    assert await option.text_content() == "Dynamic Rowan"
    summary = page.locator("#activity-profile-counts", has_text="Dynamic Rowan")
    await summary.wait_for()
    assert "0 approved · 0 pending · 0 rejected" in await summary.text_content()
    await page.locator('#sprite-sets [data-character="Dynamic Rowan"]').wait_for(state="attached")
    await page.close()
