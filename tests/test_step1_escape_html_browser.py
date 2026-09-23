"""Browser coverage for Task 2.6c: `escapeHtml()` must be safe for the HTML-attribute-
value contexts it's actually used in (`value="..."`, `title="..."`) -- the DOM
`textContent` -> `innerHTML` trick alone escapes `&`/`<`/`>` but leaves `"`/`'` untouched,
since neither is special in text-node content. A speaker name containing `"` must not
break out of the rendered `<input value="...">` attribute.
"""

from typing import AsyncGenerator

import pytest
from playwright.async_api import Browser, async_playwright

from tests.conftest import live_server

MALICIOUS_NAME = '"><img src=x onerror="window.__xss_fired = true">'


@pytest.fixture(scope="module")
def live_server_url(tmp_path_factory: pytest.TempPathFactory):
    with live_server(tmp_path_factory, "step1-escape-html") as url:
        yield url


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
