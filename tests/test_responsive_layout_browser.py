"""Regression suite: no horizontal overflow at 1024px width minimum (Task 2.3d).

A real Playwright audit (see task-2.3d.md) found every page already avoids horizontal
overflow at 1024px — this app's CSS consistently uses `repeat(auto-fit, minmax(...))`
grids (self-reflowing by construction) and `/step6`'s one fixed two-column layout already
has a `@media (max-width: 1180px)` rule stacking it well before 1024px. This suite pins
that finding as a permanent regression check, one test per page, each with realistic
mocked data reused from that page's own existing browser test fixtures.
"""

import json
from typing import AsyncGenerator

import pytest
from playwright.async_api import Browser, async_playwright

from tests.conftest import live_server

VIEWPORT = {"width": 1024, "height": 800}
PID = "responsive-audit-project"


@pytest.fixture(scope="module")
def live_server_url(tmp_path_factory: pytest.TempPathFactory):
    with live_server(tmp_path_factory, "responsive-layout") as url:
        yield url


@pytest.fixture
async def browser_instance() -> AsyncGenerator[Browser, None]:
    async with async_playwright() as playwright:
        browser = await playwright.chromium.launch(headless=True)
        yield browser
        await browser.close()


def _envelope(data, error=None):
    return json.dumps({"success": error is None, "data": data, "error": error, "meta": {}})


async def _assert_no_horizontal_overflow(page):
    scroll_width = await page.evaluate("document.documentElement.scrollWidth")
    client_width = await page.evaluate("document.documentElement.clientWidth")
    assert scroll_width <= client_width, (
        f"Horizontal overflow at 1024px: scrollWidth={scroll_width} > clientWidth={client_width}"
    )


PROJECT = {
    "id": PID,
    "name": "Responsive Audit Project",
    "status": "video_generated",
    "topic": "Testing responsive layout",
    "cefr_level": "B1",
    "genre": "small_talk",
    "accent": "american",
    "speakers": [
        {
            "id": "sp1", "name": "Alex", "gender": "male", "accent": "american",
            "tts_engine": "edge_tts", "voice_id": None, "voice_description": "",
            "speed": 1.0, "pitch": 0.0, "volume": 1.0, "avatar_image_path": None,
        },
        {
            "id": "sp2", "name": "Sam", "gender": "female", "accent": "american",
            "tts_engine": "edge_tts", "voice_id": None, "voice_description": "",
            "speed": 1.0, "pitch": 0.0, "volume": 1.0, "avatar_image_path": None,
        },
    ],
}
LINES = [
    {
        "id": "l1", "line_index": 0, "speaker_id": "sp1",
        "text": "Welcome to the show, this is a fairly long line to check wrapping at narrow widths.",
        "language_notes": {"collocations": ["welcome to"], "idioms": [], "grammar_point": "Present Simple"},
        "duration_seconds": None,
    },
    {
        "id": "l2", "line_index": 1, "speaker_id": "sp2",
        "text": "Thanks for having me, I am excited to be here today.",
        "language_notes": None, "duration_seconds": None,
    },
]
LEARNING_PACK = {
    "vocabulary": [
        {"word": "diagnostic", "part_of_speech": "adj", "ipa": "/x/", "definition_en": "d", "definition_vi": "d", "example_sentence": "e"}
    ],
    "idioms": [{"phrase": "at the cutting edge", "meaning_en": "m", "meaning_vi": "m", "example_sentence": "e"}],
    "grammar": [{"point": "p", "structure": "s", "explanation_en": "e", "explanation_vi": "e", "examples": ["ex"]}],
    "questions": [{"question": "q?", "options": ["a", "b", "c", "d"], "correct_answer": "a"}],
}
VIDEO_TEMPLATES = [{"id": "midnight", "display_name": "Midnight", "preview_url": "/static/video_backgrounds/midnight.png"}]
THUMBNAIL_TEMPLATES = [
    {
        "id": template_id,
        "display_name": display_name,
        "description": f"{display_name} thumbnail layout",
        "preview_url": f"/static/thumbnail_templates/{template_id}.png",
    }
    for template_id, display_name in (
        ("minimal_clean", "Minimal Clean"),
        ("gradient_bold", "Gradient Bold"),
        ("modern_split", "Modern Split"),
        ("dynamic_wave", "Dynamic Wave"),
        ("podcast_classic", "Podcast Classic"),
    )
]
YOUTUBE_PACKAGE = {
    "id": "pkg-1",
    "project_id": PID,
    "titles": [
        {"variant": "click_worthy", "text": "You Won't Believe This Remote Work Secret"},
        {"variant": "educational", "text": "Learn English: Remote Work Vocabulary (B1)"},
        {"variant": "seo", "text": "Remote Work English Podcast B1 Interview"},
    ],
    "description": "An English-learning podcast episode about remote work culture.",
    "chapters_text": "00:00 Introduction\n01:20 Working from home",
    "chapters_estimated": True,
    "tags": ["remote work", "english learning", "b1 podcast"],
    "created_at": "2026-09-12T00:00:00Z",
    "updated_at": "2026-09-12T00:00:00Z",
}


async def _mock_all_routes(page):
    """One catch-all mock covering every route any of the 9 pages might call."""

    async def handle(route):
        url, method = route.request.url, route.request.method
        if url.endswith("/api/projects") and method == "GET":
            await route.fulfill(status=200, content_type="application/json", body=_envelope([PROJECT]))
        elif url.endswith(f"/api/projects/{PID}") and method == "GET":
            await route.fulfill(status=200, content_type="application/json", body=_envelope(PROJECT))
        elif url.endswith(f"/api/projects/{PID}/script") and method == "GET":
            await route.fulfill(status=200, content_type="application/json", body=_envelope(LINES))
        elif url.endswith(f"/api/projects/{PID}/learning") and method == "GET":
            await route.fulfill(status=200, content_type="application/json", body=_envelope(LEARNING_PACK))
        elif url.endswith("/api/music") and method == "GET":
            await route.fulfill(status=200, content_type="application/json", body=_envelope([]))
        elif url.endswith("/audio/status") and method == "GET":
            await route.fulfill(
                status=200, content_type="application/json",
                body=_envelope({
                    "project_id": PID, "status": "complete", "mp3_path": "x.mp3", "wav_path": "x.wav",
                    "timestamps": [], "background_music": None, "duration_seconds": 2.0,
                    "loudness_lufs": -16.0, "error_message": None, "started_at": "t", "completed_at": "t",
                }),
            )
        elif url.endswith("/api/video/templates") and method == "GET":
            await route.fulfill(status=200, content_type="application/json", body=_envelope(VIDEO_TEMPLATES))
        elif url.endswith("/video/status") and method == "GET":
            await route.fulfill(
                status=200, content_type="application/json",
                body=_envelope({
                    "project_id": PID, "status": "complete", "mode": "background", "mp4_path": "x.mp4",
                    "srt_path": "x.srt", "background_image": "midnight", "error_message": None,
                    "started_at": "t", "completed_at": "t",
                }),
            )
        elif url.endswith("/api/thumbnails/templates") and method == "GET":
            await route.fulfill(status=200, content_type="application/json", body=_envelope(THUMBNAIL_TEMPLATES))
        elif url.endswith(f"/api/projects/{PID}/thumbnails") and method == "GET":
            await route.fulfill(status=200, content_type="application/json", body=_envelope([]))
        elif url.endswith(f"/api/projects/{PID}/youtube") and method == "GET":
            await route.fulfill(status=200, content_type="application/json", body=_envelope(YOUTUBE_PACKAGE))
        else:
            await route.continue_()

    await page.route("**/api/**", handle)


@pytest.mark.asyncio
async def test_dashboard_no_overflow_at_1024(browser_instance: Browser, live_server_url: str):
    page = await browser_instance.new_page(viewport=VIEWPORT)
    await _mock_all_routes(page)
    await page.goto(f"{live_server_url}/")
    await page.wait_for_selector("#project-grid")
    await _assert_no_horizontal_overflow(page)
    await page.close()


@pytest.mark.asyncio
async def test_music_library_no_overflow_at_1024(browser_instance: Browser, live_server_url: str):
    page = await browser_instance.new_page(viewport=VIEWPORT)
    await _mock_all_routes(page)
    await page.goto(f"{live_server_url}/music")
    await page.wait_for_selector("#empty-state:not([hidden])")
    await _assert_no_horizontal_overflow(page)
    await page.close()


@pytest.mark.asyncio
async def test_step1_no_overflow_at_1024(browser_instance: Browser, live_server_url: str):
    page = await browser_instance.new_page(viewport=VIEWPORT)
    await page.goto(f"{live_server_url}/step1")
    await page.wait_for_selector("#submit-btn")
    await _assert_no_horizontal_overflow(page)
    await page.close()


@pytest.mark.asyncio
async def test_step2_no_overflow_at_1024(browser_instance: Browser, live_server_url: str):
    page = await browser_instance.new_page(viewport=VIEWPORT)
    await _mock_all_routes(page)
    await page.goto(f"{live_server_url}/step2?project_id={PID}")
    await page.wait_for_selector("[data-line-id]")
    await _assert_no_horizontal_overflow(page)
    await page.close()


@pytest.mark.asyncio
async def test_step3_no_overflow_at_1024(browser_instance: Browser, live_server_url: str):
    page = await browser_instance.new_page(viewport=VIEWPORT)
    await _mock_all_routes(page)
    await page.goto(f"{live_server_url}/step3?project_id={PID}")
    await page.wait_for_selector("#content-wrap:not([hidden])")
    await _assert_no_horizontal_overflow(page)
    await page.close()


@pytest.mark.asyncio
async def test_step4_no_overflow_at_1024(browser_instance: Browser, live_server_url: str):
    page = await browser_instance.new_page(viewport=VIEWPORT)
    await _mock_all_routes(page)
    await page.goto(f"{live_server_url}/step4?project_id={PID}")
    await page.wait_for_selector("#workspace:not([hidden])")
    await _assert_no_horizontal_overflow(page)
    await page.close()


@pytest.mark.asyncio
async def test_step5_no_overflow_at_1024(browser_instance: Browser, live_server_url: str):
    page = await browser_instance.new_page(viewport=VIEWPORT)
    await _mock_all_routes(page)
    await page.goto(f"{live_server_url}/step5?project_id={PID}")
    await page.wait_for_selector("#workspace:not([hidden])")
    await _assert_no_horizontal_overflow(page)
    await page.close()


@pytest.mark.asyncio
async def test_step6_no_overflow_at_1024(browser_instance: Browser, live_server_url: str):
    page = await browser_instance.new_page(viewport=VIEWPORT)
    await _mock_all_routes(page)
    await page.goto(f"{live_server_url}/step6?project_id={PID}")
    await page.wait_for_selector("#template-gallery")
    await _assert_no_horizontal_overflow(page)
    await page.close()


@pytest.mark.asyncio
async def test_step7_no_overflow_at_1024(browser_instance: Browser, live_server_url: str):
    page = await browser_instance.new_page(viewport=VIEWPORT)
    await _mock_all_routes(page)
    await page.goto(f"{live_server_url}/step7?project_id={PID}")
    await page.wait_for_selector("#content-wrap:not([hidden])")
    await _assert_no_horizontal_overflow(page)
    await page.close()
