"""Task 27.3a: several tracks at once, more formats and one-at-a-time listening on the Music Library page."""

import io
import wave
from typing import AsyncGenerator

import pytest
from playwright.async_api import Browser, Page, async_playwright

from app.core.config import settings
from tests.conftest import live_server

VALID_MP3 = b"ID3\x04\x00\x00\x00\x00\x00\x00music-data"


@pytest.fixture(scope="module")
def live_server_url(tmp_path_factory: pytest.TempPathFactory):
    with live_server(tmp_path_factory, "music-multi") as url:
        yield url


@pytest.fixture
async def browser_instance() -> AsyncGenerator[Browser, None]:
    async with async_playwright() as playwright:
        browser = await playwright.chromium.launch(headless=True, args=["--autoplay-policy=no-user-gesture-required"])
        yield browser
        await browser.close()


@pytest.fixture(autouse=True)
def clean_library():
    folder = settings.DATA_DIR / "music_library"
    if folder.exists():
        for path in folder.iterdir():
            path.unlink()
    yield


def _mp3(name: str, content: bytes = VALID_MP3) -> dict:
    return {"name": name, "mimeType": "audio/mpeg", "buffer": content}


def _silent_wav(seconds: float = 2.0) -> bytes:
    buffer = io.BytesIO()
    with wave.open(buffer, "wb") as handle:
        handle.setnchannels(1)
        handle.setsampwidth(2)
        handle.setframerate(8000)
        handle.writeframes(b"\x00\x00" * int(8000 * seconds))
    return buffer.getvalue()


async def _open(browser: Browser, url: str) -> Page:
    page = await browser.new_page()
    await page.goto(f"{url}/music")
    await page.locator("#music-file-input").wait_for(state="attached")
    return page


async def _states(page: Page) -> list[str]:
    return await page.locator("#upload-queue li").evaluate_all("items => items.map(item => item.dataset.state)")


@pytest.mark.asyncio
async def test_the_zone_takes_many_files_in_four_formats(browser_instance, live_server_url):
    page = await _open(browser_instance, live_server_url)
    input_element = page.locator("#music-file-input")
    assert await input_element.get_attribute("multiple") is not None
    accept = await input_element.get_attribute("accept")
    assert all(extension in accept for extension in (".mp3", ".wav", ".ogg", ".m4a"))
    assert "MP3, WAV, OGG or M4A" in await page.locator(".upload-title").text_content()
    await page.close()


@pytest.mark.asyncio
async def test_choosing_three_files_adds_three_tracks_with_a_queue_and_a_summary(browser_instance, live_server_url):
    page = await _open(browser_instance, live_server_url)
    await page.locator("#music-file-input").set_input_files([_mp3("one.mp3"), _mp3("two.mp3"), _mp3("three.mp3")])
    await page.locator("#status-message").wait_for(state="visible")
    assert await page.locator("#status-message").text_content() == "3 tracks added to your library."
    assert await _states(page) == ["added", "added", "added"]
    await page.locator(".track-card").nth(2).wait_for()  # the list reloads right after the message
    assert await page.locator(".track-card").count() == 3
    await page.close()


@pytest.mark.asyncio
async def test_a_mixed_batch_reports_each_file_and_still_adds_the_good_one(browser_instance, live_server_url):
    page = await _open(browser_instance, live_server_url)
    await page.locator("#music-file-input").set_input_files([
        _mp3("good.mp3"),
        {"name": "notes.txt", "mimeType": "text/plain", "buffer": b"hello"},
        _mp3("empty.mp3", b""),
        _mp3("fake.mp3", b"not-an-mp3"),
    ])
    await page.locator("#status-message, #error-message").first.wait_for(state="visible")
    assert await _states(page) == ["added", "skipped", "skipped", "error"]
    notes = await page.locator("#upload-queue li .queue-note").all_text_contents()
    # only the three files with something to say have a note: the .txt, the empty file, the spoofed one
    assert "MP3, WAV, OGG or M4A" in notes[0] and "empty" in notes[1].lower() and len(notes) == 3
    summary = await page.locator("#status-message").text_content()
    assert summary == "1 track added, 3 skipped."
    await page.locator(".track-card").first.wait_for()
    assert await page.locator(".track-card").count() == 1
    await page.close()


@pytest.mark.asyncio
async def test_the_same_name_twice_in_one_batch_keeps_both(browser_instance, live_server_url):
    page = await _open(browser_instance, live_server_url)
    await page.locator("#music-file-input").set_input_files([_mp3("same.mp3"), _mp3("same.mp3")])
    await page.locator("#status-message").wait_for(state="visible")
    assert await _states(page) == ["added", "added"]
    await page.locator(".track-card").nth(1).wait_for()
    assert await page.locator(".track-card").count() == 2
    notes = await page.locator("#upload-queue li .queue-note").all_text_contents()
    assert len(notes) == 1 and "saved as" in notes[0]  # only the renamed duplicate has a note
    await page.close()


@pytest.mark.asyncio
async def test_ogg_and_m4a_files_are_accepted(browser_instance, live_server_url):
    page = await _open(browser_instance, live_server_url)
    await page.locator("#music-file-input").set_input_files([
        {"name": "a.ogg", "mimeType": "audio/ogg", "buffer": b"OggS\x00\x02\x00\x00data"},
        {"name": "b.m4a", "mimeType": "audio/mp4", "buffer": b"\x00\x00\x00\x20ftypM4A \x00\x00\x00\x00data"},
    ])
    await page.locator("#status-message").wait_for(state="visible")
    assert await _states(page) == ["added", "added"]
    await page.close()


@pytest.mark.asyncio
async def test_one_play_button_per_track_and_only_one_track_plays(browser_instance, live_server_url):
    page = await _open(browser_instance, live_server_url)
    await page.locator("#music-file-input").set_input_files([
        {"name": "alpha.wav", "mimeType": "audio/wav", "buffer": _silent_wav()},
        {"name": "beta.wav", "mimeType": "audio/wav", "buffer": _silent_wav()},
    ])
    await page.locator(".track-card").nth(1).wait_for()
    cards = page.locator(".track-card")
    first = cards.nth(0).locator("button.track-play")
    second = cards.nth(1).locator("button.track-play")
    assert await first.get_attribute("aria-pressed") == "false"
    assert (await first.get_attribute("aria-label")).startswith("Play ")
    await first.click()
    await page.wait_for_function("document.querySelectorAll('audio')[0].paused === false")
    await page.wait_for_function(
        "document.querySelectorAll('.track-play')[0].getAttribute('aria-pressed') === 'true'")
    assert (await first.get_attribute("aria-label")).startswith("Pause ")
    await second.click()
    await page.wait_for_function("document.querySelectorAll('audio')[1].paused === false")
    await page.wait_for_function("document.querySelectorAll('audio')[0].paused === true")
    await page.wait_for_function(
        "document.querySelectorAll('.track-play')[0].getAttribute('aria-pressed') === 'false'")
    assert await second.get_attribute("aria-pressed") == "true"
    await second.click()
    await page.wait_for_function(
        "document.querySelectorAll('.track-play')[1].getAttribute('aria-pressed') === 'false'")
    assert (await second.get_attribute("aria-label")).startswith("Play ")
    await page.close()


@pytest.mark.asyncio
async def test_a_single_bad_file_keeps_the_old_friendly_message(browser_instance, live_server_url):
    page = await _open(browser_instance, live_server_url)
    await page.locator("#music-file-input").set_input_files(_mp3("fake.mp3", b"not-an-mp3"))
    await page.locator("#error-message").wait_for(state="visible")
    assert await page.locator("#error-message").text_content() == (
        "We couldn't upload that music file. Check the format and try again.")
    assert await page.locator("#upload-queue").is_hidden()  # one file needs no queue
    await page.close()
