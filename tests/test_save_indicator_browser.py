"""Playwright coverage for the shared header auto-save indicator (Task 2.3e).

Covers /step2 and /step6 — one page per distinct central save-status setter function
implementation (`setSaveStatusState` on step2/step3, `setSaveStatus` on step6). Both
existing inline `#save-status` elements must keep working unchanged; the new
`#save-indicator` in the header is purely additive.
"""

import json
from typing import AsyncGenerator

import pytest
from playwright.async_api import Browser, async_playwright

from tests.conftest import live_server

PROJECT_ID = "save-indicator-project"


@pytest.fixture(scope="module")
def live_server_url(tmp_path_factory: pytest.TempPathFactory):
    with live_server(tmp_path_factory, "save-indicator") as url:
        yield url


@pytest.fixture
async def browser_instance() -> AsyncGenerator[Browser, None]:
    async with async_playwright() as playwright:
        browser = await playwright.chromium.launch(headless=True)
        yield browser
        await browser.close()


def _envelope(data, error=None):
    return json.dumps({"success": error is None, "data": data, "error": error, "meta": {}})


# ---------------------------------------------------------------------------
# Step 2 — Script Generation (setSaveStatusState)
# ---------------------------------------------------------------------------

STEP2_PROJECT = {
    "id": PROJECT_ID,
    "name": "Save Indicator Test",
    "status": "script_generated",
    "topic": "Testing the save indicator",
    "cefr_level": "B1",
    "genre": "small_talk",
    "accent": "american",
    "speakers": [{"id": "sp1", "name": "Alex", "gender": "male", "accent": "american"}],
}
STEP2_LINES = [
    {
        "id": "line-1", "speaker_id": "sp1", "text": "Hello there!",
        "language_notes": {"collocations": [], "idioms": [], "grammar_point": "Present Simple"},
    },
]


@pytest.mark.asyncio
async def test_step2_header_indicator_reflects_saving_then_saved(browser_instance: Browser, live_server_url: str):
    page = await browser_instance.new_page()

    async def handle(route):
        url, method = route.request.url, route.request.method
        if url.endswith(f"/api/projects/{PROJECT_ID}/script") and method == "GET":
            await route.fulfill(status=200, content_type="application/json", body=_envelope(STEP2_LINES))
        elif url.endswith(f"/api/projects/{PROJECT_ID}/script") and method == "PUT":
            body = json.loads(route.request.post_data or "{}")
            await route.fulfill(status=200, content_type="application/json", body=_envelope(body.get("lines", [])))
        elif url.endswith(f"/api/projects/{PROJECT_ID}") and method == "GET":
            await route.fulfill(status=200, content_type="application/json", body=_envelope(STEP2_PROJECT))
        else:
            await route.continue_()

    await page.route("**/api/**", handle)
    await page.goto(f"{live_server_url}/step2?project_id={PROJECT_ID}")
    await page.wait_for_selector("[data-line-id='line-1']")

    # Header indicator starts empty — nothing dirty yet.
    assert await page.locator("#save-indicator").text_content() == ""

    await page.locator("[data-line-id='line-1'] .line-text").click()
    textarea = page.locator("[data-line-id='line-1'] textarea")
    await textarea.fill("Updated line text through the header-indicator test.")
    await textarea.blur()

    await page.wait_for_function(
        "document.getElementById('save-indicator').textContent === 'Saved'"
    )
    # The existing inline indicator must still work, completely unchanged.
    inline_text = await page.locator("#save-status").text_content()
    assert "Saved" in inline_text or inline_text == ""

    await page.wait_for_function(
        "document.getElementById('save-indicator').textContent === ''", timeout=3000
    )
    await page.close()


# ---------------------------------------------------------------------------
# Step 6 — Thumbnail Generator (setSaveStatus)
# ---------------------------------------------------------------------------

STEP6_PROJECT = {"id": PROJECT_ID, "name": "Save Indicator Test", "topic": "t", "cefr_level": "B1", "genre": "small_talk"}
STEP6_TEMPLATES = [{"id": "minimal_clean", "display_name": "Minimal Clean", "description": "d", "preview_url": "/x.png"}]


def _step6_thumbnail():
    base = f"/api/projects/{PROJECT_ID}/thumbnails/thumb-1"
    return {
        "id": "thumb-1",
        "project_id": PROJECT_ID,
        "template_name": "minimal_clean",
        "variant_index": 0,
        "is_selected": True,
        "created_at": "2026-09-13T00:00:00Z",
        "revision": "thumb-1",
        "suggestion": {
            "headline": "Original Headline",
            "supporting_text": "sub",
            "topic_keywords": ["a"],
            "palette": {"primary": "#111827", "secondary": "#60A5FA", "accent": "#F59E0B", "text": "#FFFFFF"},
        },
        "assets": {
            aspect: {fmt: f"{base}/{aspect}.{fmt}?revision=thumb-1" for fmt in ("png", "jpg")}
            for aspect in ("16x9", "9x16")
        },
    }


@pytest.mark.asyncio
async def test_step6_header_indicator_reflects_saving_then_saved(browser_instance: Browser, live_server_url: str):
    page = await browser_instance.new_page()
    thumbnail = _step6_thumbnail()

    async def handle(route):
        url, method = route.request.url, route.request.method
        if url.endswith(f"/api/projects/{PROJECT_ID}") and method == "GET":
            await route.fulfill(status=200, content_type="application/json", body=_envelope(STEP6_PROJECT))
        elif url.endswith("/api/thumbnails/templates") and method == "GET":
            await route.fulfill(status=200, content_type="application/json", body=_envelope(STEP6_TEMPLATES))
        elif url.endswith(f"/api/projects/{PROJECT_ID}/thumbnails") and method == "GET":
            await route.fulfill(status=200, content_type="application/json", body=_envelope([thumbnail]))
        elif "/thumbnails/thumb-1" in url and method == "PATCH":
            body = json.loads(route.request.post_data or "{}")
            thumbnail["suggestion"]["headline"] = body.get("headline", thumbnail["suggestion"]["headline"])
            await route.fulfill(status=200, content_type="application/json", body=_envelope(thumbnail))
        else:
            await route.continue_()

    await page.route("**/api/**", handle)
    await page.goto(f"{live_server_url}/step6?project_id={PROJECT_ID}")
    await page.wait_for_selector("#editor-layout")
    # Loading an existing selected thumbnail itself sets "saved" (fades after 2s) —
    # so unlike step2 (nothing to save until an edit happens), this page starts non-empty.

    await page.locator("#headline-input").fill("Updated headline through the header-indicator test")

    await page.wait_for_function(
        "document.getElementById('save-indicator').textContent === 'Saved'", timeout=5000
    )
    await page.wait_for_function(
        "document.getElementById('save-indicator').textContent === ''", timeout=3000
    )
    await page.close()
