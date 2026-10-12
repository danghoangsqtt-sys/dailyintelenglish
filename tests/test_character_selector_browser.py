"""Task 33.7 (D80): the game-style selector -- a click previews, only "Choose for <speaker>" assigns, a character cannot
play two speakers, and a character that is not ready for videos cannot be chosen."""

from __future__ import annotations

from typing import AsyncGenerator, Generator

import pytest
from playwright.async_api import Browser, async_playwright

import tests.test_step1_config_edit_browser as fixture
from tests.conftest import live_server


@pytest.fixture(scope="module")
def live_server_url(tmp_path_factory: pytest.TempPathFactory) -> Generator[str, None, None]:
    with live_server(tmp_path_factory, "character-selector") as url:
        yield url


@pytest.fixture
async def browser_instance() -> AsyncGenerator[Browser, None]:
    async with async_playwright() as playwright:
        browser = await playwright.chromium.launch()
        yield browser
        await browser.close()


async def _open(browser: Browser, base: str, profiles: list[dict]):
    page = await browser.new_page(viewport={"width": 1280, "height": 900})
    original = fixture.PROFILES
    fixture.PROFILES = profiles
    try:
        await fixture._character_routes(page, [], [])
        await page.goto(f"{base}/step1")
        await page.wait_for_function("document.getElementById('speaker-name-1')?.value === 'Lina'")
    finally:
        fixture.PROFILES = original
    return page


@pytest.mark.asyncio
async def test_a_click_only_previews_and_choose_assigns(browser_instance: Browser, live_server_url: str):
    page = await _open(browser_instance, live_server_url, fixture.PROFILES)
    await page.click('[data-choose="0"]')
    await page.locator(".cs-card", has_text="Ben").click()
    assert "Ben" in await page.locator('[data-cs="preview"]').text_content()
    assert "Alex" in await page.locator('.cs-slot[data-slot="0"]').text_content()  # previewing changed nothing
    await page.locator('[data-cs="choose"]').click()
    await page.wait_for_selector('.cs-slot[data-slot="0"]:has-text("Ben")')
    await page.locator('[data-cs="close"]').click()
    assert await page.input_value("#speaker-name-0") == "Ben"
    await page.close()


@pytest.mark.asyncio
async def test_one_character_cannot_play_two_speakers(browser_instance: Browser, live_server_url: str):
    page = await _open(browser_instance, live_server_url, fixture.PROFILES)
    await page.click('[data-choose="0"]')
    await page.locator(".cs-card", has_text="Lina").click()
    assert "Already chosen for Speaker 2" in await page.locator('[data-cs="preview"]').text_content()
    assert await page.locator('[data-cs="choose"]').is_disabled()
    await page.close()


@pytest.mark.asyncio
async def test_a_character_without_its_pictures_cannot_be_chosen(browser_instance: Browser, live_server_url: str):
    unready = fixture._profile("p-new", "Kai", "male", "british")
    unready["readiness"] = {**unready["readiness"], "video_ready": False,
                            "core_visuals": {"ready": False, "missing": ["picture full_body"]}}
    page = await _open(browser_instance, live_server_url, [*fixture.PROFILES, unready])
    await page.click('[data-choose="0"]')
    await page.locator(".cs-card", has_text="Kai").click()
    assert "Not ready for videos yet: picture full_body" in await page.locator('[data-cs="preview"]').text_content()
    assert await page.locator('[data-cs="choose"]').is_disabled()
    await page.close()


@pytest.mark.asyncio
async def test_saving_without_a_character_is_refused(browser_instance: Browser, live_server_url: str):
    page = await _open(browser_instance, live_server_url, fixture.PROFILES)
    await page.fill("#num-speakers", "3")
    await page.dispatch_event("#num-speakers", "input")
    await page.fill("#name", "Three voices")
    await page.fill("#topic", "Travel")
    await page.click("#submit-btn")
    await page.wait_for_selector("#error-banner:not([hidden])")
    assert "Speaker 3: choose a character." in await page.locator("#error-banner").text_content()
    await page.close()
