"""Task 20.5 Character Library browser flow with fake local images."""

from typing import AsyncGenerator, Generator

import pytest
from playwright.async_api import Browser, async_playwright

from app.api import visuals as visuals_api
from app.core.config import settings
from tests.conftest import live_server


@pytest.fixture(scope="module")
def live_server_url(tmp_path_factory: pytest.TempPathFactory) -> Generator[str, None, None]:
    pretend_image_python = tmp_path_factory.mktemp("visuals-browser-venv") / "python.exe"
    pretend_image_python.touch()
    with pytest.MonkeyPatch.context() as patch:
        patch.setattr(settings, "IMAGE_ENGINE", "fake")
        patch.setattr(settings, "AI_VISUALS_ENABLED", True)
        patch.setattr(visuals_api, "IMAGE_PYTHON", pretend_image_python)
        with live_server(tmp_path_factory, "visuals-library-browser") as url:
            yield url


@pytest.fixture
async def browser_instance() -> AsyncGenerator[Browser, None]:
    async with async_playwright() as playwright:
        browser = await playwright.chromium.launch(headless=True)
        yield browser
        await browser.close()


async def _create_character(page, name: str):
    await page.locator("#character-form [name=name]").fill(name)
    await page.locator("#character-form [name=role]").fill("English teacher")
    await page.locator("#character-form [name=hair]").fill("long black hair")
    await page.locator("#character-form [name=eyes]").fill("brown eyes")
    await page.locator("#character-form [name=top_color]").select_option("yellow")
    await page.locator("#character-form [name=bottom_color]").select_option("navy blue")
    await page.get_by_role("button", name="Create character").click()
    await page.get_by_role("button", name="Generate 4").wait_for()


@pytest.mark.asyncio
async def test_library_create_pick_approve_lock_and_read_only(browser_instance: Browser, live_server_url: str):
    page = await browser_instance.new_page()
    await page.goto(live_server_url)
    await page.get_by_role("link", name="Character Library").click()
    assert page.url.endswith("/characters")
    await page.locator("#character-form [name=gender] option").first.wait_for(state="attached")
    await _create_character(page, "Nova")
    await page.get_by_role("button", name="Generate 4").click()
    await page.wait_for_function("document.querySelectorAll('#candidate-grid .library-asset').length === 4")
    await page.get_by_role("button", name="Choose this portrait").first.click()
    await page.get_by_role("button", name="Generate sheet").click()
    await page.wait_for_function("document.querySelectorAll('#sheet-grid .library-asset').length === 4")
    for _ in range(4):
        await page.get_by_role("button", name="✓ Approve", exact=True).first.click()
    await page.get_by_role("button", name="Lock character").click()
    await page.wait_for_function("document.querySelector('#character-form [name=hair]').disabled")
    assert await page.locator("#character-form [name=hair]").is_disabled()
    assert await page.get_by_role("button", name="Unlock").is_visible()
    await page.close()


@pytest.mark.asyncio
async def test_library_health_off_disables_generate_but_keeps_browsing(
    browser_instance: Browser, live_server_url: str, monkeypatch,
):
    page = await browser_instance.new_page()
    await page.goto(f"{live_server_url}/characters")
    await page.get_by_role("button", name="New character").click()
    await _create_character(page, "Mira")
    monkeypatch.setattr(settings, "AI_VISUALS_ENABLED", False)
    await page.reload()
    await page.get_by_role("button", name="Mira draft").click()
    generate = page.get_by_role("button", name="Generate 4")
    assert await generate.is_disabled()
    assert "disabled" in (await generate.get_attribute("title")).lower()
    await page.get_by_role("tab", name="Scenes").click()
    assert await page.get_by_text("Built-in").count() >= 6
    assert await page.get_by_role("button", name="Preview").first.is_disabled()
    await page.goto(f"{live_server_url}/step5")
    assert await page.get_by_role("link", name="Character Library").count() == 1
    await page.close()
