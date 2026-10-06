"""Task 22.7: Playwright coverage for editing a Music Library track's details."""

import subprocess
from typing import AsyncGenerator, Generator

import pytest
from playwright.async_api import Browser, async_playwright

from app.core.config import settings
from tests.conftest import live_server


@pytest.fixture(scope="module")
def live_server_url(tmp_path_factory: pytest.TempPathFactory) -> Generator[str, None, None]:
    with live_server(tmp_path_factory, "music-meta-browser") as url:
        yield url


@pytest.fixture(autouse=True)
def one_track(live_server_url: str) -> None:
    music_dir = settings.DATA_DIR / "music_library"
    music_dir.mkdir(parents=True, exist_ok=True)
    for path in music_dir.iterdir():
        if path.is_file():
            path.unlink()
    subprocess.run([settings.FFMPEG_PATH, "-y", "-loglevel", "error", "-f", "lavfi", "-i",
                    "sine=frequency=330:duration=65", "-b:a", "64k", str(music_dir / "morning_coffee.mp3")],
                   check=True)


@pytest.fixture
async def browser_instance() -> AsyncGenerator[Browser, None]:
    async with async_playwright() as playwright:
        browser = await playwright.chromium.launch(headless=True)
        yield browser
        await browser.close()


@pytest.mark.asyncio
async def test_edit_details_shows_mood_length_and_credit_warning(browser_instance: Browser, live_server_url: str):
    page = await browser_instance.new_page()
    await page.goto(f"{live_server_url}/music")
    card = page.locator("[data-filename='morning_coffee.mp3']")
    await card.wait_for()
    assert await card.locator(".track-name").text_content() == "Morning coffee"
    assert await card.locator(".is-length").text_content() == "1:05"
    # Task 22.9: the new track is analysed after the list renders; a steady tone has no attacks,
    # so it is classified calm (absolute onset floor) and gets an automatic mood suggestion.
    await page.wait_for_selector("#analysis-note", state="hidden", timeout=60000)
    card = page.locator("[data-filename='morning_coffee.mp3']")
    await card.locator(".is-pace").wait_for()
    assert await card.locator(".is-pace").text_content() == "Calm pace · auto"
    assert (await card.locator(".is-mood").text_content()).endswith("· auto")
    assert await card.locator(".details-form").is_hidden()

    await card.locator("[data-action='edit-details']").click()
    form = card.locator(".details-form")
    await form.locator("[name='artist']").fill("Kevin MacLeod")
    await form.locator("[name='mood']").select_option("acoustic")
    await form.locator("[name='tags']").fill("Cafe, morning")
    await form.locator("[name='source']").select_option("incompetech")
    await form.locator("[name='licence']").select_option("cc_by_4")
    await form.locator("button[type='submit']").click()

    await page.locator("#status-message:not([hidden])").wait_for()
    card = page.locator("[data-filename='morning_coffee.mp3']")
    await card.locator(".is-mood").wait_for()
    assert await card.locator(".track-name").text_content() == "Morning coffee — Kevin MacLeod"
    assert await card.locator(".is-mood").text_content() == "Acoustic / warm"
    assert "Credit needed" in await card.locator(".is-warning").text_content()

    await card.locator("[data-action='edit-details']").click()
    await card.locator("[name='tags']").wait_for()
    assert await card.locator("[name='tags']").input_value() == "cafe, morning"
    await card.locator("[name='attribution']").fill("Morning Coffee by Kevin MacLeod (incompetech.com), CC BY 4.0")
    await card.locator("button[type='submit']").click()
    await page.wait_for_function(
        "!document.querySelector(\"[data-filename='morning_coffee.mp3'] .is-warning\")")
    await page.close()


@pytest.mark.asyncio
async def test_bad_link_is_refused_and_cancel_hides_the_form(browser_instance: Browser, live_server_url: str):
    page = await browser_instance.new_page()
    await page.goto(f"{live_server_url}/music")
    card = page.locator("[data-filename='morning_coffee.mp3']")
    await card.wait_for()
    await page.wait_for_selector("#analysis-note", state="hidden", timeout=60000)
    await card.locator("[data-action='edit-details']").click()
    await card.locator("[name='source_url']").fill("ftp://example.com/x")
    await card.locator("button[type='submit']").click()
    error = page.locator("#error-message")
    await error.wait_for()
    assert "could not save" in await error.text_content()
    await card.locator("[data-action='cancel-details']").click()
    assert await card.locator(".details-form").is_hidden()
    await page.close()
