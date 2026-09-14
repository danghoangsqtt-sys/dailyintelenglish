"""Browser coverage for Task 2.5c: Step 1's accent picker discloses that "Scottish"
currently uses the same Edge TTS voice as "British" (no distinct Scottish voice exists
upstream — see tasks/task-2.1c.md and tasks/task-2.5.md).
"""

import socket
import threading
import time
from typing import AsyncGenerator

import pytest
import uvicorn
from playwright.async_api import Browser, async_playwright

from app.main import app


def _find_free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as listener:
        listener.bind(("127.0.0.1", 0))
        return listener.getsockname()[1]


@pytest.fixture(scope="module")
def live_server_url():
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


@pytest.fixture
async def browser_instance() -> AsyncGenerator[Browser, None]:
    async with async_playwright() as playwright:
        browser = await playwright.chromium.launch(headless=True)
        yield browser
        await browser.close()


@pytest.mark.asyncio
async def test_scottish_accent_chip_discloses_shared_british_voice(browser_instance: Browser, live_server_url: str):
    page = await browser_instance.new_page()
    await page.goto(f"{live_server_url}/step1")
    await page.wait_for_selector("#accent-grid button[data-value='scottish']")

    chip_title = await page.locator("#accent-grid button[data-value='scottish']").get_attribute("title")
    assert chip_title and "British" in chip_title and "Scottish voice" in chip_title

    # Every other accent chip must NOT carry this note (only Scottish has the limitation).
    british_title = await page.locator("#accent-grid button[data-value='british']").get_attribute("title")
    assert not british_title

    await page.close()


@pytest.mark.asyncio
async def test_scottish_per_speaker_accent_option_discloses_shared_british_voice(
    browser_instance: Browser, live_server_url: str
):
    page = await browser_instance.new_page()
    await page.goto(f"{live_server_url}/step1")
    await page.wait_for_selector("#speaker-grid select[data-field='accent']")

    first_speaker_select = page.locator("#speaker-grid select[data-field='accent']").first
    option_title = await first_speaker_select.locator("option[value='scottish']").get_attribute("title")
    assert option_title and "British" in option_title

    american_title = await first_speaker_select.locator("option[value='american']").get_attribute("title")
    assert not american_title

    await page.close()
