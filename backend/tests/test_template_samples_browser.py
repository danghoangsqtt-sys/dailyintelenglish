"""Phase 92: an example clip on every kind card (Step 1 and the Shorts batch page)."""

import json
from pathlib import Path
from typing import AsyncGenerator, Generator

import pytest
from playwright.async_api import Browser, async_playwright

from backend.tests.conftest import live_server

SAMPLES = Path(__file__).resolve().parents[2] / "frontend" / "static" / "samples"
KINDS = ("conversation", "presenter", "vox", "news", "blur", "mistakes", "wordday", "top5", "quiz", "listen", "slowpod",
         "flashcards", "roots", "grammar", "chat", "wyr")


def test_every_kind_has_its_clips_and_the_set_stays_small():
    index = json.loads((SAMPLES / "index.json").read_text(encoding="utf-8"))
    assert set(KINDS) <= set(index)
    total = 0
    for kind in KINDS:
        entry = index[kind]
        for key in ("vi", "en", "poster_vi", "poster_en"):
            assert (SAMPLES / entry[key]).is_file(), (kind, key)
        total += entry["bytes"]
    assert total < 8 * 1024 * 1024  # D134: the whole set ships with the app
    spec = (SAMPLES.parents[2] / "installer" / "daily_intel_english_studio.spec").read_text(encoding="utf-8")
    assert '("frontend", "frontend")' in spec  # the samples are packaged with frontend/static


@pytest.fixture(scope="module")
def live_server_url(tmp_path_factory: pytest.TempPathFactory) -> Generator[str, None, None]:
    with live_server(tmp_path_factory, "template-samples-browser") as url:
        yield url


@pytest.fixture
async def browser_instance() -> AsyncGenerator[Browser, None]:
    async with async_playwright() as playwright:
        browser = await playwright.chromium.launch(headless=True)
        yield browser
        await browser.close()


async def test_the_batch_cards_show_a_clip_that_opens_a_larger_example(browser_instance: Browser, live_server_url: str):
    page = await browser_instance.new_page(viewport={"width": 1400, "height": 1000})
    await page.goto(f"{live_server_url}/shorts-batch")
    await page.locator("#template-grid .sample-thumb").nth(15).wait_for(state="attached")
    assert await page.locator("#template-grid .sample-thumb").count() == 16
    card = page.locator("#template-grid [data-template='grammar']")
    await card.hover()
    await page.wait_for_function("!document.querySelector(\"#template-grid [data-template='grammar'] video\").paused")
    await card.locator(".sample-thumb-badge").click()
    dialog = page.locator(".sample-dialog")
    await dialog.wait_for()
    assert await card.get_attribute("aria-checked") == "false"  # looking at the example does not choose the kind
    assert "Example only" in await dialog.inner_text() or "Ví dụ minh hoạ" in await dialog.inner_text()
    await page.keyboard.press("Escape")
    await dialog.wait_for(state="hidden")
    await page.close()


async def test_step1_cards_have_clips_and_reduced_motion_keeps_the_poster(browser_instance: Browser, live_server_url: str):
    context = await browser_instance.new_context(reduced_motion="reduce", viewport={"width": 1400, "height": 1000})
    page = await context.new_page()
    await page.goto(f"{live_server_url}/step1")
    await page.locator("[data-mode='vox'] .sample-thumb").wait_for(state="attached")
    assert await page.locator("[data-template] .sample-thumb").count() == 13
    await page.locator("[data-mode='shorts']").click()
    card = page.locator("[data-template='roots']")
    await card.hover()
    await page.wait_for_timeout(400)
    assert await card.locator("video").evaluate("video => video.paused && !!video.poster")
    await context.close()
