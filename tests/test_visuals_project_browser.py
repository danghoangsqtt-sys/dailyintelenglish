"""Task 20.6 Step 5 cast and scenes against the fake engine (Phase 44, D123: no drawn shots any more)."""

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
async def test_step5_cast_and_scenes_without_drawn_shots(browser_instance: Browser, live_server_url: str):
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
    assert await page.get_by_role("button", name="Generate shots").count() == 0
    assert await page.locator("#visual-shot-grid").count() == 0
    await page.close()
