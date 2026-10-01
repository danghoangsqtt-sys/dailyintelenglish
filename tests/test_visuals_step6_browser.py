"""Task 20.7 Step 6 shows AI scene only for projects with a complete shot."""

from typing import AsyncGenerator, Generator

import pytest
from playwright.async_api import Browser, async_playwright

from app.core.config import settings
from tests.conftest import live_server
from tests.test_thumbnail_api import PROJECT_PAYLOAD
from tests.test_visuals_thumbnail import add_complete_shot


@pytest.fixture(scope="module")
def live_server_url(tmp_path_factory: pytest.TempPathFactory) -> Generator[str, None, None]:
    with pytest.MonkeyPatch.context() as patch:
        patch.setattr(settings, "IMAGE_ENGINE", "fake")
        with live_server(tmp_path_factory, "visuals-step6-browser") as url:
            yield url


@pytest.fixture
async def browser_instance() -> AsyncGenerator[Browser, None]:
    async with async_playwright() as playwright:
        browser = await playwright.chromium.launch(headless=True)
        yield browser
        await browser.close()


@pytest.mark.asyncio
async def test_step6_ai_scene_option_appears_with_shot(browser_instance: Browser, live_server_url: str):
    page = await browser_instance.new_page()
    response = await page.request.post(f"{live_server_url}/api/projects", data=PROJECT_PAYLOAD)
    assert response.ok, await response.text()
    project_id = (await response.json())["data"]["id"]
    url = f"{live_server_url}/step6?project_id={project_id}"
    await page.goto(url)
    await page.locator("#template-gallery .template-option").first.wait_for()
    assert await page.locator("#template-gallery .template-option").count() == 5
    add_complete_shot(project_id)
    await page.reload()
    await page.wait_for_function("document.querySelectorAll('#template-gallery .template-option').length === 6")
    option = page.locator("#template-gallery .template-option[data-template-id='ai_scene']")
    assert await option.is_visible()
    await option.click()
    assert await option.get_attribute("aria-pressed") == "true"
    await page.close()
