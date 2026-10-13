"""Task 20.6 Step 5 visual shot flow against the fake engine."""

from typing import AsyncGenerator, Generator

import pytest
from playwright.async_api import Browser, async_playwright

from backend.api import visuals as visuals_api
from backend.core.config import settings
from tests.conftest import live_server
from tests.test_visuals_project_api import PROJECT, locked_character


async def choose_cast(page, speaker_index: int, character_id: str) -> None:
    """Task 35.4: Step 5 casts through the shared CharacterSelector (preview a card, then "Choose for <speaker>")."""
    card = page.locator(f'.visual-cast-card[data-speaker="{speaker_index}"]')
    await card.locator('[data-action="choose-character"]').click()
    await page.locator(f'.cs-card[data-id="{character_id}"]').click()
    await page.locator('[data-cs="choose"]').click()
    await card.locator('[data-action="remove-character"]').wait_for()
    close = page.locator('[data-cs="close"]')
    if await close.count() and await close.is_visible():  # the selector stays open for the next speaker, as in Step 1
        await close.click()
    await page.wait_for_function(
        f"!document.querySelector('.visual-cast-card[data-speaker=\"{speaker_index}\"] [data-action=choose-character]').disabled")


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
    scenes_response = await page.request.get(f"{live_server_url}/api/visuals/scenes")
    scene_names = [scene["name"] for scene in (await scenes_response.json())["data"][:2]]
    await page.route(
        f"**/api/projects/{project_id}/audio/status",
        lambda route: route.fulfill(json={"success": True, "data": {"status": "complete", "timestamps": []}}),
    )
    await page.goto(f"{live_server_url}/step5?project_id={project_id}")
    await choose_cast(page, 0, first)
    await choose_cast(page, 1, second)
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
