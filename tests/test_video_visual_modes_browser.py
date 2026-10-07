"""Phase 30 (ENH-021): Step 5 "Video pictures" modes (drawn story, podcast black, with characters, one still)."""

import json
from typing import AsyncGenerator

import pytest
from playwright.async_api import Browser, async_playwright

from tests.conftest import live_server
from tests.test_video_studio_browser import PROJECT, TEMPLATES, VIDEO_JOB

SCENES = [
    {"id": "builtin-cafe", "name": "Cafe", "place": "a cozy cafe", "preview_url": "/api/visuals/scenes/builtin-cafe/preview?v=1"},
    {"id": "builtin-park", "name": "Park", "place": "a green park", "preview_url": None},
    {"id": "builtin-beach", "name": "Beach", "place": "a sunny beach", "preview_url": "/api/visuals/scenes/builtin-beach/preview?v=1"},
]


@pytest.fixture(scope="module")
def live_server_url(tmp_path_factory: pytest.TempPathFactory):
    with live_server(tmp_path_factory, "video-visual-modes") as url:
        yield url


@pytest.fixture
async def browser_instance() -> AsyncGenerator[Browser, None]:
    async with async_playwright() as playwright:
        browser = await playwright.chromium.launch(headless=True)
        yield browser
        await browser.close()


def _envelope(data, error=None):
    return json.dumps({"success": error is None, "data": data, "error": error, "meta": {}})


async def _open(browser: Browser, url: str, bodies: list):
    page = await browser.new_page()

    async def handle(route):
        link, method = route.request.url, route.request.method
        ok = lambda data: route.fulfill(status=200, content_type="application/json", body=_envelope(data))  # noqa: E731
        if link.endswith(f"/api/projects/{PROJECT['id']}") and method == "GET":
            await ok(PROJECT)
        elif link.endswith("/audio/status") and method == "GET":
            await ok({"status": "complete"})
        elif link.endswith("/api/video/templates") and method == "GET":
            await ok(TEMPLATES)
        elif link.endswith("/api/video/health") and method == "GET":
            await ok({"remotion_configured": True})
        elif link.endswith("/api/visuals/scenes") and method == "GET":
            await ok(SCENES)
        elif link.endswith("/video/status") and method == "GET":
            await route.fulfill(status=404, content_type="application/json", body=_envelope(None, "no video"))
        elif link.endswith("/video/generate") and method == "POST":
            bodies.append(json.loads(route.request.post_data))
            await ok(VIDEO_JOB)
        else:
            await route.continue_()

    await page.route("**/api/**", handle)
    await page.goto(f"{url}/step5?project_id={PROJECT['id']}")
    await page.wait_for_selector("#workspace:not([hidden])")
    await page.evaluate("for (const k of ['die-video-renderer','die-caption-style','die-visual-mode','die-still-scene']) localStorage.removeItem(k)")
    await page.reload()
    await page.wait_for_selector("#workspace:not([hidden])")
    return page


async def _generate(page):
    await page.wait_for_function("!document.getElementById('generate-btn').disabled")
    await page.click("#generate-btn")
    await page.wait_for_function("document.getElementById('generate-btn').textContent.includes('Generate video')")


@pytest.mark.asyncio
async def test_four_modes_the_drawn_story_is_the_default_and_its_request_is_unchanged(browser_instance, live_server_url):
    bodies: list = []
    page = await _open(browser_instance, live_server_url, bodies)
    labels = await page.locator("#visual-mode-group .chip").all_text_contents()
    assert [text.strip() for text in labels] == [
        "Podcast: with characters", "Podcast: black screen", "Podcast: one still scene"]
    assert await page.locator("[data-visual-mode='illustrated']").get_attribute("aria-pressed") == "true"
    assert await page.locator("#still-scene-row").is_hidden()
    await _generate(page)
    assert bodies == [{"template_id": "midnight", "aspect_ratio": "16:9", "renderer": "remotion", "caption_style": "outline"}]
    await page.close()


@pytest.mark.asyncio
async def test_each_podcast_mode_is_sent_and_remembered(browser_instance, live_server_url):
    bodies: list = []
    page = await _open(browser_instance, live_server_url, bodies)
    await page.click("[data-visual-mode='podcast_black']")
    assert await page.locator("[data-visual-mode='podcast_black']").get_attribute("aria-pressed") == "true"
    assert await page.locator("[data-visual-mode='illustrated']").get_attribute("aria-pressed") == "false"
    assert await page.locator("#still-scene-row").is_hidden()
    await _generate(page)
    assert [body["visual_mode"] for body in bodies] == ["podcast_black"]
    assert "still_scene_id" not in bodies[0]
    await page.reload()
    await page.wait_for_selector("#workspace:not([hidden])")
    assert await page.locator("[data-visual-mode='podcast_black']").get_attribute("aria-pressed") == "true"
    await page.click("[data-visual-mode='illustrated']")  # back to the story pictures: the old request again
    await _generate(page)
    assert "visual_mode" not in bodies[-1]
    await page.close()


@pytest.mark.asyncio
async def test_the_still_mode_offers_only_scenes_with_a_plate_and_sends_the_choice(browser_instance, live_server_url):
    bodies: list = []
    page = await _open(browser_instance, live_server_url, bodies)
    await page.click("[data-visual-mode='podcast_still']")
    row = page.locator("#still-scene-row")
    await row.wait_for(state="visible")
    options = await page.locator("#still-scene option").all_text_contents()
    assert [text.strip() for text in options] == ["Automatic (first scene with a plate)", "Cafe", "Beach"]  # not Park: no plate yet
    await page.select_option("#still-scene", "builtin-beach")
    await _generate(page)
    assert bodies[-1]["visual_mode"] == "podcast_still" and bodies[-1]["still_scene_id"] == "builtin-beach"
    await page.select_option("#still-scene", "")
    await _generate(page)
    assert "still_scene_id" not in bodies[-1]
    await page.close()


@pytest.mark.asyncio
async def test_the_modes_need_the_enhanced_renderer(browser_instance, live_server_url):
    bodies: list = []
    page = await _open(browser_instance, live_server_url, bodies)
    await page.click("[data-visual-mode='podcast_black']")
    await page.click("[data-renderer='ffmpeg']")
    for mode in ("illustrated", "podcast_black", "podcast_still"):
        assert await page.locator(f"[data-visual-mode='{mode}']").is_disabled()
    assert "Enhanced" in (await page.locator("#visual-mode-group").get_attribute("title") or "") \
        or "Enhanced" in (await page.locator("[data-visual-mode='podcast_black']").get_attribute("title") or "")
    await _generate(page)
    assert bodies == [{"template_id": "midnight", "aspect_ratio": "16:9", "renderer": "ffmpeg"}]  # nothing extra on Standard
    await page.click("[data-renderer='remotion']")
    assert await page.locator("[data-visual-mode='podcast_black']").is_enabled()
    assert await page.locator("[data-visual-mode='podcast_black']").get_attribute("aria-pressed") == "true"  # remembered
    await page.close()
