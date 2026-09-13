"""Playwright E2E coverage for the Music Library waveform visualization (Task 1.10 —
the "Audio wave preview" acceptance criterion, closing Task 1.10).

Uses a real, decodable MP3 (not the fake `ID3...` bytes tests/test_music_library_browser.py
uses for its upload/list/delete-only assertions) because waveform.js genuinely decodes the
audio via the Web Audio API — a fake byte string would only prove the graceful-failure
path, not the feature itself.
"""

import io
import socket
import threading
import time
from typing import AsyncGenerator, Generator

import pytest
import uvicorn
from playwright.async_api import Browser, async_playwright
from pydub.generators import Sine

from app.core.config import settings
from app.main import app


def _real_mp3_bytes(duration_ms: int = 3000, freq: int = 440) -> bytes:
    buffer = io.BytesIO()
    Sine(freq).to_audio_segment(duration=duration_ms).apply_gain(-12).export(buffer, format="mp3", bitrate="192k")
    return buffer.getvalue()


def _find_free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as listener:
        listener.bind(("127.0.0.1", 0))
        return listener.getsockname()[1]


@pytest.fixture(scope="module")
def live_server_url(tmp_path_factory: pytest.TempPathFactory) -> Generator[str, None, None]:
    original_data_dir = settings.DATA_DIR
    settings.DATA_DIR = tmp_path_factory.mktemp("waveform-browser-data")
    port = _find_free_port()
    server = uvicorn.Server(uvicorn.Config(app, host="127.0.0.1", port=port, log_level="warning"))
    thread = threading.Thread(target=server.run, daemon=True)
    thread.start()

    started_at = time.time()
    while time.time() - started_at < 10.0:
        try:
            with socket.create_connection(("127.0.0.1", port), timeout=0.5):
                break
        except OSError:
            time.sleep(0.1)
    else:
        raise RuntimeError("Live test server failed to start within 10 seconds")

    yield f"http://127.0.0.1:{port}"
    server.should_exit = True
    thread.join(timeout=10)
    settings.DATA_DIR = original_data_dir


@pytest.fixture(autouse=True)
def empty_music_library(live_server_url: str) -> None:
    """Reset browser-test storage between tests — the module-scoped live_server_url
    fixture shares one DATA_DIR/music_library across every test in this file."""
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


async def _canvas_has_drawn_pixels(page) -> bool:
    return await page.evaluate(
        """
        () => {
            const canvas = document.querySelector('.track-waveform');
            if (!canvas) return false;
            const ctx = canvas.getContext('2d');
            const data = ctx.getImageData(0, 0, canvas.width, canvas.height).data;
            for (let i = 3; i < data.length; i += 4) {
                if (data[i] !== 0) return true;
            }
            return false;
        }
        """
    )


@pytest.mark.asyncio
async def test_waveform_renders_real_pixels_for_a_real_audio_file(browser_instance: Browser, live_server_url: str):
    page = await browser_instance.new_page()
    await page.goto(f"{live_server_url}/music")

    await page.locator("#music-file-input").set_input_files(
        {"name": "real-tone.mp3", "mimeType": "audio/mpeg", "buffer": _real_mp3_bytes()}
    )
    await page.locator(".track-waveform").wait_for()
    await page.wait_for_timeout(1000)  # let async decode+draw finish

    assert await _canvas_has_drawn_pixels(page)
    await page.close()


@pytest.mark.asyncio
async def test_clicking_waveform_seeks_the_audio_element(browser_instance: Browser, live_server_url: str):
    page = await browser_instance.new_page()
    await page.goto(f"{live_server_url}/music")
    await page.locator("#music-file-input").set_input_files(
        {"name": "seek-test.mp3", "mimeType": "audio/mpeg", "buffer": _real_mp3_bytes(duration_ms=4000)}
    )
    await page.locator(".track-waveform").wait_for()
    await page.wait_for_function("document.querySelector('audio').duration > 0")

    canvas = page.locator(".track-waveform")
    box = await canvas.bounding_box()
    await canvas.click(position={"x": box["width"] * 0.5, "y": box["height"] / 2})
    await page.wait_for_timeout(300)

    current_time = await page.evaluate("document.querySelector('audio').currentTime")
    duration = await page.evaluate("document.querySelector('audio').duration")
    assert current_time == pytest.approx(duration * 0.5, abs=0.5)
    await page.close()


@pytest.mark.asyncio
async def test_waveform_does_not_break_page_on_undecodable_audio(browser_instance: Browser, live_server_url: str):
    """A track whose bytes fail to decode (e.g. corrupted upload) must not crash the page
    or block the native <audio> control — only the waveform visualization is skipped."""
    page = await browser_instance.new_page()
    await page.goto(f"{live_server_url}/music")

    await page.locator("#music-file-input").set_input_files(
        {"name": "not-real-audio.mp3", "mimeType": "audio/mpeg", "buffer": b"ID3\x04\x00\x00\x00\x00\x00\x00fake"}
    )
    await page.locator("[data-filename='not-real-audio.mp3']").wait_for()
    await page.wait_for_timeout(500)

    # The native audio control must still be present and usable even though decoding failed.
    assert await page.locator("[data-filename='not-real-audio.mp3'] audio").count() == 1
    await page.close()


@pytest.mark.asyncio
async def test_multiple_tracks_each_get_their_own_independent_waveform(browser_instance: Browser, live_server_url: str):
    page = await browser_instance.new_page()
    await page.goto(f"{live_server_url}/music")

    await page.locator("#music-file-input").set_input_files(
        {"name": "track-a.mp3", "mimeType": "audio/mpeg", "buffer": _real_mp3_bytes(freq=440)}
    )
    await page.locator("[data-filename='track-a.mp3']").wait_for()
    await page.locator("#music-file-input").set_input_files(
        {"name": "track-b.mp3", "mimeType": "audio/mpeg", "buffer": _real_mp3_bytes(freq=880)}
    )
    await page.locator("[data-filename='track-b.mp3']").wait_for()
    await page.wait_for_timeout(1000)

    assert await page.locator(".track-waveform").count() == 2
    await page.close()
