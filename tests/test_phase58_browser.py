"""Phase 58 (ENH-040): the interface language, the Settings menu, the character profile tabs and the music list."""

import io
import wave
from typing import AsyncGenerator, Generator

import pytest
from playwright.async_api import Browser, async_playwright, expect

from tests.conftest import live_server


@pytest.fixture(scope="module")
def live_server_url(tmp_path_factory: pytest.TempPathFactory) -> Generator[str, None, None]:
    with live_server(tmp_path_factory, "phase58-browser") as url:
        yield url


@pytest.fixture
async def browser_instance() -> AsyncGenerator[Browser, None]:
    async with async_playwright() as playwright:
        browser = await playwright.chromium.launch(headless=True)
        yield browser
        await browser.close()


async def result(response):
    assert response.status == 200, await response.text()
    return (await response.json())["data"]


@pytest.mark.asyncio
async def test_the_interface_switches_to_vietnamese_and_back(browser_instance: Browser, live_server_url: str):
    page = await browser_instance.new_page(viewport={"width": 1400, "height": 900})
    await page.goto(f"{live_server_url}/")
    sidebar = page.locator("#app-sidebar")
    await expect(sidebar.get_by_text("Character Library", exact=True)).to_be_visible()  # English by default
    assert await page.evaluate("document.documentElement.lang") == "en"
    await page.locator("#lang-switch [data-lang='vi']").click()
    await expect(sidebar.get_by_text("Thư viện nhân vật", exact=True)).to_be_visible()
    await expect(page.locator("#start-title")).to_have_text("Bắt đầu từ đây")
    assert await page.evaluate("document.documentElement.lang") == "vi"
    assert (await page.title()).startswith("Daily Beyond English")
    # the brand is a name: never translated
    await expect(page.locator("a.brand small")).to_have_text("English")
    # a text a script adds after load is translated too, and a translate="no" area is left alone
    await page.evaluate("""() => {
        const p = document.createElement('p'); p.id = 'late'; p.textContent = 'Settings'; document.querySelector('main').append(p);
        const q = document.createElement('p'); q.id = 'kept'; q.setAttribute('translate', 'no'); q.textContent = 'Settings';
        document.querySelector('main').append(q);
    }""")
    await expect(page.locator("#late")).to_have_text("Cài đặt")
    await expect(page.locator("#kept")).to_have_text("Settings")
    await page.reload()  # the choice is remembered
    await expect(sidebar.get_by_text("Thư viện nhạc", exact=True)).to_be_visible()
    await page.locator("#lang-switch [data-lang='en']").click()
    await page.wait_for_load_state("load")
    await expect(sidebar.get_by_text("Music Library", exact=True)).to_be_visible()
    await page.close()


@pytest.mark.asyncio
async def test_settings_has_a_left_menu_with_language_and_theme(browser_instance: Browser, live_server_url: str):
    page = await browser_instance.new_page(viewport={"width": 1400, "height": 900})
    await page.goto(f"{live_server_url}/settings")
    await expect(page.locator("#settings-general")).to_be_visible()
    await expect(page.locator("#settings-ai")).to_be_hidden()
    await page.locator("#settings-nav [data-section='providers']").click()
    await expect(page.locator("#settings-providers")).to_be_visible()
    await expect(page.locator("#settings-general")).to_be_hidden()
    assert page.url.endswith("#providers")
    await expect(page.locator("#dot-openrouter")).to_have_attribute("data-state", "none")
    await page.locator("#settings-nav [data-section='general']").click()
    await page.get_by_role("radio", name="Dark").check()
    assert await page.evaluate("document.documentElement.getAttribute('data-theme')") == "dark"
    await page.get_by_role("radio", name="Tiếng Việt").check()
    await expect(page.locator("#settings-nav [data-section='ai']")).to_contain_text("AI")
    await expect(page.locator("#settings-nav [data-section='general']")).to_contain_text("Chung")
    await page.evaluate("localStorage.setItem('dbe.lang', 'en'); localStorage.setItem('die-theme', 'light')")
    await page.close()


@pytest.mark.asyncio
async def test_a_character_profile_shows_one_tab_at_a_time(browser_instance: Browser, live_server_url: str):
    page = await browser_instance.new_page(viewport={"width": 1400, "height": 900})
    profile = await result(await page.request.post(f"{live_server_url}/api/visuals/profiles", data={
        "name": "Tab Presenter", "gender": "female", "accent": "american", "appearance": "long hair", "outfit": "red coat",
    }))
    await page.goto(f"{live_server_url}/characters")
    await page.locator(f".profile-card[data-id='{profile['id']}']").click()
    await expect(page.locator(".slot-card")).to_have_count(29)
    await expect(page.locator("#profile-voice-panel")).to_be_hidden()
    await page.locator("#profile-tab-voice").click()
    await expect(page.locator("#profile-voice-panel")).to_be_visible()
    await expect(page.locator("#profile-pictures-panel")).to_be_hidden()
    await expect(page.locator("#profile-tab-voice")).to_have_attribute("aria-selected", "true")
    await expect(page.locator("#profile-view-native")).to_have_attribute("aria-selected", "false")
    await page.locator("#profile-tab-details").click()
    await page.locator("#profile-intro").fill("Explains things calmly.")
    await expect(page.locator("#profile-save-state")).to_contain_text("Saved", timeout=10000)
    await page.locator("#profile-view-front").click()
    await expect(page.locator(".slot-card")).to_have_count(21)
    await expect(page.locator("#profile-pictures-panel")).to_be_visible()
    saved = await result(await page.request.get(f"{live_server_url}/api/visuals/profiles/{profile['id']}"))
    assert saved["intro"] == "Explains things calmly."
    await page.close()


def _wav(seconds: float = 0.5) -> bytes:
    buffer = io.BytesIO()
    with wave.open(buffer, "wb") as audio:
        audio.setnchannels(1)
        audio.setsampwidth(2)
        audio.setframerate(8000)
        audio.writeframes(b"\x00\x00" * int(8000 * seconds))
    return buffer.getvalue()


@pytest.mark.asyncio
async def test_music_rows_filter_and_play_in_the_shared_player(browser_instance: Browser, live_server_url: str):
    page = await browser_instance.new_page(viewport={"width": 1400, "height": 900})
    await page.goto(f"{live_server_url}/music")
    await page.locator("#music-file-input").set_input_files([
        {"name": "sunrise walk.wav", "mimeType": "audio/wav", "buffer": _wav()},
        {"name": "night study.wav", "mimeType": "audio/wav", "buffer": _wav()},
    ])
    rows = page.locator("#track-list .track-card")
    await expect(rows).to_have_count(2)
    await page.locator("#music-search").fill("night")
    await expect(page.locator("#track-list .track-card:visible")).to_have_count(1)
    await expect(page.locator("#track-list .track-card:visible .track-name")).to_contain_text("Night study")
    await page.locator("#music-search").fill("nothing like this")
    await expect(page.locator("#no-match")).to_be_visible()
    await page.locator("#music-search").fill("")
    await expect(page.locator("#mood-chips .mood-chip").first).to_contain_text("All")
    await expect(page.locator("#track-list .track-card .is-warning").first).to_contain_text("No licence")
    await rows.nth(0).locator("button.track-play").click()
    await expect(page.locator("#music-player")).to_be_visible()
    await expect(page.locator("#player-title")).not_to_have_text("Nothing playing")
    await rows.nth(1).locator("[data-action='edit-details']").click()
    form = rows.nth(1).locator(".details-form")
    await expect(form).to_be_visible()
    await rows.nth(0).locator("[data-action='edit-details']").click()
    await expect(form).to_be_hidden()  # one side panel at a time
    await expect(rows.nth(0).locator(".details-form")).to_be_visible()
    await page.keyboard.press("Escape")
    await expect(rows.nth(0).locator(".details-form")).to_be_hidden()
    await page.close()
