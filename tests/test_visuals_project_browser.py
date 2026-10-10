"""Step 5 visual shot flow against the fake engine."""

import sqlite3
import uuid
from typing import AsyncGenerator, Generator

import pytest
from playwright.async_api import Browser, async_playwright

from app.api import visuals as visuals_api
from app.core.config import settings
from tests.conftest import live_server
from tests.test_visuals_project_api import PROJECT, locked_character


def make_core_ready(character_id: str) -> None:
    """Give a minimal locked-character fixture every approved Phase 33 core slot."""
    path = settings.DATA_DIR / "library" / "characters" / character_id / "face.png"
    with sqlite3.connect(settings.db_path) as connection:
        for slot in ("full_body", "portrait_calm", "portrait_smile", "portrait_surprised"):
            asset_id = str(uuid.uuid4())
            connection.execute(
                "INSERT INTO character_assets "
                "(id, character_id, kind, path, approved, created_at, slot_key, source, original_filename, "
                "review_state, validation_json, identity_version, is_current, updated_at) "
                "VALUES (?, ?, ?, ?, 1, 'now', ?, 'test', 'face.png', 'approved', '{}', 1, 1, 'now')",
                (asset_id, character_id, slot, str(path), slot),
            )


@pytest.fixture(scope="module")
def live_server_url(tmp_path_factory: pytest.TempPathFactory) -> Generator[str, None, None]:
    pretend_image_python = tmp_path_factory.mktemp("visuals-project-venv") / "python.exe"
    pretend_image_python.touch()
    with pytest.MonkeyPatch.context() as patch:
        patch.setattr(settings, "IMAGE_ENGINE", "fake")
        patch.setattr(settings, "AI_VISUALS_ENABLED", True)
        # The fake engine paints solid random colours, so every person fails the Task 20.11
        # colour check and retries twice: the job outgrew this UI test's 30 s wait. The retry
        # itself is covered by tests/test_visuals_colour_check.py.
        patch.setattr(settings, "VISUALS_COLOUR_RETRIES", 0)
        patch.setattr(visuals_api, "IMAGE_PYTHON", pretend_image_python)
        with live_server(tmp_path_factory, "visuals-project-browser") as url:
            yield url


@pytest.fixture
async def browser_instance() -> AsyncGenerator[Browser, None]:
    async with async_playwright() as playwright:
        browser = await playwright.chromium.launch(headless=True)
        yield browser
        await browser.close()


@pytest.mark.asyncio
async def test_step5_cast_scenes_generate_grid_and_regenerate(browser_instance: Browser, live_server_url: str):
    page = await browser_instance.new_page()
    response = await page.request.post(f"{live_server_url}/api/projects", data=PROJECT)
    assert response.ok, await response.text()
    project_id = (await response.json())["data"]["id"]
    first = locked_character("Nova", "yellow")
    second = locked_character("Mira", "green")
    make_core_ready(first)
    make_core_ready(second)
    scenes_response = await page.request.get(f"{live_server_url}/api/visuals/scenes")
    scene_names = [scene["name"] for scene in (await scenes_response.json())["data"][:2]]
    await page.route(
        f"**/api/projects/{project_id}/audio/status",
        lambda route: route.fulfill(json={"success": True, "data": {"status": "complete", "timestamps": []}}),
    )
    await page.goto(f"{live_server_url}/step5?project_id={project_id}")
    slots = page.locator("#visual-cast-grid .cast-speaker-slot")
    await slots.first.wait_for()
    await page.locator(f'.cast-roster-card[data-character-id="{first}"]').click()
    await page.locator('[data-action="choose-profile"]').click()
    await page.wait_for_function(
        "id => [...document.querySelectorAll('.cast-speaker-slot')][0]?.textContent.includes(id)", arg="Nova",
    )
    await slots.nth(1).click()
    await page.locator(f'.cast-roster-card[data-character-id="{second}"]').click()
    await page.locator('[data-action="choose-profile"]').click()
    await page.wait_for_function(
        "id => [...document.querySelectorAll('.cast-speaker-slot')][1]?.textContent.includes(id)", arg="Mira",
    )
    await page.locator("#visual-scene-options button", has_text=scene_names[0]).click()
    await page.wait_for_function("document.querySelectorAll('#visual-scene-order span').length === 1")
    await page.locator("#visual-scene-options button", has_text=scene_names[1]).click()
    await page.wait_for_function("document.querySelectorAll('#visual-scene-order span').length === 2")
    assert await page.locator("#visual-scene-order span").all_text_contents() == [
        f"1. {scene_names[0]}", f"2. {scene_names[1]}",
    ]
    await page.get_by_role("button", name="Generate shots").click()
    await page.wait_for_function("document.querySelectorAll('#visual-shot-grid .visual-shot-card').length === 8")
    first_card = page.locator("#visual-shot-grid .visual-shot-card").first
    await first_card.get_by_role("button", name="Show raw").click()
    assert await first_card.get_by_role("button", name="Show final").is_visible()
    old_image = await first_card.locator("img").get_attribute("src")
    await first_card.get_by_role("button", name="Regenerate").click()
    await page.wait_for_function(
        "old => document.querySelector('#visual-shot-grid .visual-shot-card img')?.getAttribute('src') !== old",
        arg=old_image,
    )
    assert await first_card.locator("img").get_attribute("src") != old_image
    await page.close()
