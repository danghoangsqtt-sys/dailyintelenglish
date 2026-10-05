"""Task 22.2: Playwright coverage for the Music Library "Generate from a brief" panel (fake engine)."""

from typing import AsyncGenerator, Generator

import pytest
from playwright.async_api import Browser, async_playwright

from app.core.config import settings
from tests.conftest import live_server


@pytest.fixture(scope="module")
def live_server_url(tmp_path_factory: pytest.TempPathFactory) -> Generator[str, None, None]:
    with pytest.MonkeyPatch.context() as patch:
        patch.setattr(settings, "MUSIC_ENGINE", "fake")
        patch.setattr(settings, "AI_MUSIC_ENABLED", True)
        patch.setattr(settings, "MUSIC_LENGTH_STRATEGY", "full")
        with live_server(tmp_path_factory, "music-generate-browser") as url:
            yield url


@pytest.fixture(autouse=True)
def empty_music_library(live_server_url: str) -> None:
    music_dir = settings.DATA_DIR / "music_library"
    music_dir.mkdir(parents=True, exist_ok=True)
    for path in music_dir.iterdir():
        if path.is_file():
            path.unlink()


@pytest.fixture
async def browser_instance() -> AsyncGenerator[Browser, None]:
    async with async_playwright() as playwright:
        browser = await playwright.chromium.launch(headless=True)
        yield browser
        await browser.close()


@pytest.mark.asyncio
async def test_generate_from_a_brief_adds_an_ai_track(browser_instance: Browser, live_server_url: str):
    page = await browser_instance.new_page()
    await page.goto(f"{live_server_url}/music")
    await page.locator("#music-style option[value='acoustic']").wait_for(state="attached")
    assert await page.locator("#generate-unavailable").is_hidden()
    await page.select_option("#music-style", "acoustic")
    await page.fill("#music-brief", "calm morning study")
    await page.fill("#music-minutes", "0")
    await page.fill("#music-seconds", "30")
    await page.click("#generate-button")

    card = page.locator(".track-card", has=page.locator(".track-source.is-ai"))
    await card.wait_for(timeout=30000)
    assert (await card.get_attribute("data-filename")).startswith("acoustic-calm-morning-study-")
    assert await card.locator(".track-source").text_content() == "AI generated"
    provenance = await card.locator(".track-provenance").text_content()
    assert "calm morning study" in provenance
    assert "Acoustic / piano" in provenance and "0:30" in provenance and "MIT" in provenance
    assert (await page.locator("#generate-progress").text_content()).startswith("Done:")
    assert await page.locator("#generate-button").is_enabled()
    assert await page.locator("#generate-cancel").is_hidden()

    await page.reload()  # provenance is stored, not page state
    await page.locator(".track-source.is-ai").wait_for()
    await page.close()


@pytest.mark.asyncio
async def test_length_outside_the_limits_is_refused(browser_instance: Browser, live_server_url: str):
    page = await browser_instance.new_page()
    await page.goto(f"{live_server_url}/music")
    await page.locator("#music-style option").first.wait_for(state="attached")
    await page.fill("#music-minutes", "0")
    await page.fill("#music-seconds", "5")
    await page.click("#generate-button")
    error = page.locator("#error-message")
    await error.wait_for()
    assert "between 0:10 and 20:00" in await error.text_content()
    assert await page.locator(".track-card").count() == 0
    await page.close()


@pytest.mark.asyncio
async def test_unavailable_generation_disables_the_panel(
    browser_instance: Browser, live_server_url: str, monkeypatch: pytest.MonkeyPatch,
):
    monkeypatch.setattr(settings, "AI_MUSIC_ENABLED", False)
    page = await browser_instance.new_page()
    await page.goto(f"{live_server_url}/music")
    unavailable = page.locator("#generate-unavailable")
    await unavailable.wait_for()
    assert "disabled" in await unavailable.text_content()
    assert await page.locator("#generate-button").is_disabled()
    assert await page.locator("#generate-cancel").is_hidden()
    # Upload still works when generation is off.
    assert await page.locator("#music-file-input").is_enabled()
    await page.close()
