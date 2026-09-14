"""Browser coverage for Task 2.6c: `escapeHtml()` must be safe for the HTML-attribute-
value contexts it's actually used in (`value="..."`, `title="..."`) -- the DOM
`textContent` -> `innerHTML` trick alone escapes `&`/`<`/`>` but leaves `"`/`'` untouched,
since neither is special in text-node content. A speaker name containing `"` must not
break out of the rendered `<input value="...">` attribute.
"""

import socket
import threading
import time
from typing import AsyncGenerator

import pytest
import uvicorn
from playwright.async_api import Browser, async_playwright

from app.main import app

MALICIOUS_NAME = '"><img src=x onerror="window.__xss_fired = true">'


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
async def test_speaker_name_with_quote_cannot_break_out_of_value_attribute(
    browser_instance: Browser, live_server_url: str
):
    page = await browser_instance.new_page()
    await page.goto(f"{live_server_url}/step1")
    await page.wait_for_selector("#speaker-name-0")

    await page.fill("#speaker-name-0", MALICIOUS_NAME)
    # Changing speaker count forces renderSpeakerCards() to re-serialize state.speakers
    # (the only path that would actually re-inject the name into innerHTML-built markup).
    await page.fill("#num-speakers", "3")
    await page.dispatch_event("#num-speakers", "input")
    await page.wait_for_selector("#speaker-name-2")

    fired = await page.evaluate("() => window.__xss_fired === true")
    assert fired is False, "escapeHtml() failed to neutralize a quote-breakout payload"

    # The name must still round-trip correctly through the value attribute (not silently
    # truncated or mis-escaped into something unusable).
    assert await page.locator("#speaker-name-0").input_value() == MALICIOUS_NAME
    await page.close()


@pytest.mark.asyncio
async def test_scottish_note_tooltip_still_renders_correctly_after_escaping_fix(
    browser_instance: Browser, live_server_url: str
):
    """Regression guard: the quote-escaping fix must not corrupt the normal (quote-free)
    Task 2.5c tooltip text."""
    page = await browser_instance.new_page()
    await page.goto(f"{live_server_url}/step1")
    await page.wait_for_selector("#accent-grid button[data-value='scottish']")

    title = await page.locator("#accent-grid button[data-value='scottish']").get_attribute("title")
    assert title == "Uses the same voice as British — Edge TTS has no distinct Scottish voice yet"
    await page.close()
