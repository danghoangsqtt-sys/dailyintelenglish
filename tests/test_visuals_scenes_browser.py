"""Task 23.4 Scene Library UI v2 browser flow (fake engine)."""

import re
from typing import AsyncGenerator, Generator

import pytest
from playwright.async_api import Browser, async_playwright

from app.api import visuals as visuals_api
from app.core.config import settings
from tests.conftest import live_server


@pytest.fixture(scope="module")
def live_server_url(tmp_path_factory: pytest.TempPathFactory) -> Generator[str, None, None]:
    pretend_image_python = tmp_path_factory.mktemp("scenes-browser-venv") / "python.exe"
    pretend_image_python.touch()
    with pytest.MonkeyPatch.context() as patch:
        patch.setattr(settings, "IMAGE_ENGINE", "fake")
        patch.setattr(settings, "AI_VISUALS_ENABLED", True)
        patch.setattr(visuals_api, "IMAGE_PYTHON", pretend_image_python)
        with live_server(tmp_path_factory, "visuals-scenes-browser") as url:
            yield url


@pytest.fixture
async def browser_instance() -> AsyncGenerator[Browser, None]:
    async with async_playwright() as playwright:
        browser = await playwright.chromium.launch(headless=True)
        yield browser
        await browser.close()


async def test_scene_fields_filter_duplicate_and_stale_warning(browser_instance: Browser, live_server_url: str):
    page = await browser_instance.new_page()
    await page.goto(f"{live_server_url}/characters")
    await page.locator("#scenes-tab").click()
    grid = page.locator("#scene-grid")
    await grid.locator(".library-scene").first.wait_for()
    assert await grid.locator(".library-scene").count() == 55
    assert await grid.locator(".scene-placeholder").count() == 55  # no plates yet

    form = page.locator("#scene-form")
    await form.locator("[name=name]").fill("Night market")
    await form.locator("[name=place]").fill("a busy night market")
    await form.locator("[name=category]").select_option("food")
    await form.locator("[name=time_of_day]").select_option("night")
    await page.locator("#save-scene").click()
    card = grid.locator(".library-scene").filter(has=page.locator("h3", has_text=re.compile(r"^Night market$")))
    await card.wait_for()
    assert "food · night · standing · Used in 0 projects" in await card.locator(".scene-meta").inner_text()

    await page.locator("#scene-filters button[data-category=travel]").click()
    names = await grid.locator(".library-scene h3").all_inner_texts()
    assert len(names) == 5 and any("Bus stop" in name for name in names)
    await page.locator("#scene-filters button[data-category=all]").click()

    await card.get_by_role("button", name="Duplicate").click()
    await grid.locator(".library-scene", has_text="Night market copy").wait_for()

    await card.get_by_role("button", name="Make plate").click()
    await card.locator("img").wait_for(timeout=15000)
    await card.get_by_role("button", name="Edit").click()
    warning = page.locator("#scene-stale-warning")
    assert await warning.is_hidden()
    await form.locator("[name=place]").fill("a quiet night market")
    assert await warning.is_visible()
    await form.locator("[name=place]").fill("a busy night market")
    assert await warning.is_hidden()
