"""Playwright coverage for Ctrl+Enter triggering a page's primary action (Task 2.3b).

Covers /step2, /step4, /step7 per the task card's acceptance criteria: the one real
hazard this shortcut must avoid is firing "Generate" when the primary button is hidden
because a script/pack/package already exists (step2 and step7 both hide `#generate-btn`
behind `#generate-panel[hidden]` in that case) or genuinely disabled (step4, mid-flight).
"""

import asyncio
import json
from typing import AsyncGenerator

import pytest
from playwright.async_api import Browser, async_playwright

from tests.conftest import live_server

PROJECT_ID = "kb-shortcuts-proj"


@pytest.fixture(scope="module")
def live_server_url(tmp_path_factory: pytest.TempPathFactory):
    with live_server(tmp_path_factory, "keyboard-shortcuts") as url:
        yield url


@pytest.fixture
async def browser_instance() -> AsyncGenerator[Browser, None]:
    async with async_playwright() as playwright:
        browser = await playwright.chromium.launch(headless=True)
        yield browser
        await browser.close()


def _envelope(data, error=None):
    return json.dumps({"success": error is None, "data": data, "error": error, "meta": {}})


async def _press_ctrl_enter(page):
    await page.keyboard.down("Control")
    await page.keyboard.press("Enter")
    await page.keyboard.up("Control")


# ---------------------------------------------------------------------------
# Step 2 — Script Generation
# ---------------------------------------------------------------------------

STEP2_PROJECT = {
    "id": PROJECT_ID,
    "name": "Keyboard Shortcut Test",
    "status": "draft",
    "topic": "Testing keyboard shortcuts",
    "cefr_level": "B1",
    "genre": "small_talk",
    "accent": "american",
    "speakers": [{"id": "sp1", "name": "Alex", "gender": "male", "accent": "american"}],
}


async def _mock_step2_routes(page, *, script_lines):
    """Also mocks the Phase 13 durable-job endpoints Generate now uses (Task
    13.6) instead of the old synchronous `POST .../script/generate` -- that
    legacy route still exists server-side (kept as the compatibility path) but
    the Step 2 UI no longer calls it, so a test asserting on Generate's real
    network effect must mock the job endpoints instead."""

    async def handle(route):
        url, method = route.request.url, route.request.method
        if url.endswith(f"/api/projects/{PROJECT_ID}/script") and method == "GET":
            await route.fulfill(status=200, content_type="application/json", body=_envelope(script_lines))
        elif "/ai-jobs/active" in url and method == "GET":
            await route.fulfill(status=200, content_type="application/json", body=_envelope(None))
        elif url.endswith(f"/api/projects/{PROJECT_ID}") and method == "GET":
            await route.fulfill(status=200, content_type="application/json", body=_envelope(STEP2_PROJECT))
        else:
            await route.continue_()

    await page.route("**/api/**", handle)


def _complete_job_envelope(job_id: str) -> str:
    return _envelope(
        {
            "id": job_id, "project_id": PROJECT_ID, "operation": "script", "status": "complete",
            "stage": "done", "progress": 100, "requested_provider": "gemini", "actual_provider": "gemini",
            "model": "gemini-3.8-flash", "fallback_used": False, "fallback_reason": None,
            "cancel_requested": False, "attempt": 1, "repair_count": 0, "fallback_count": 0,
            "recovery_count": 0, "error_code": None, "error_message": None,
            "created_at": "2026-01-01T00:00:00Z", "started_at": "2026-01-01T00:00:00Z",
            "updated_at": "2026-01-01T00:00:00Z", "finished_at": "2026-01-01T00:00:00Z",
        }
    )


@pytest.mark.asyncio
async def test_step2_ctrl_enter_triggers_generate_when_panel_visible(browser_instance: Browser, live_server_url: str):
    page = await browser_instance.new_page()
    generate_calls = []

    async def count_generate(route):
        generate_calls.append(1)
        await route.fulfill(status=202, content_type="application/json", body=_complete_job_envelope("job-1"))

    await _mock_step2_routes(page, script_lines=[])
    await page.route(f"**/api/projects/{PROJECT_ID}/ai-jobs", count_generate)
    await page.route(
        f"**/api/projects/{PROJECT_ID}/ai-jobs/job-1",
        lambda route: route.fulfill(status=200, content_type="application/json", body=_complete_job_envelope("job-1")),
    )
    await page.goto(f"{live_server_url}/step2?project_id={PROJECT_ID}")
    await page.wait_for_selector("#generate-panel:not([hidden])")

    await _press_ctrl_enter(page)
    await page.wait_for_timeout(300)

    assert len(generate_calls) == 1
    await page.close()


@pytest.mark.asyncio
async def test_step2_ctrl_enter_does_nothing_when_panel_hidden(browser_instance: Browser, live_server_url: str):
    """The one real hazard: an existing script hides #generate-panel — Ctrl+Enter must not fire it."""
    page = await browser_instance.new_page()
    generate_calls = []

    async def count_generate(route):
        generate_calls.append(1)
        await route.fulfill(status=202, content_type="application/json", body=_complete_job_envelope("job-1"))

    existing_lines = [{"id": "l1", "line_index": 0, "speaker_id": "sp1", "text": "Hi!", "language_notes": None}]
    await _mock_step2_routes(page, script_lines=existing_lines)
    await page.route(f"**/api/projects/{PROJECT_ID}/ai-jobs", count_generate)
    await page.goto(f"{live_server_url}/step2?project_id={PROJECT_ID}")
    await page.wait_for_selector("#generate-panel[hidden]", state="attached")

    await _press_ctrl_enter(page)
    await page.wait_for_timeout(300)

    assert len(generate_calls) == 0
    await page.close()


# ---------------------------------------------------------------------------
# Step 4 — TTS Audio Studio
# ---------------------------------------------------------------------------

STEP4_PROJECT = {
    "id": PROJECT_ID,
    "name": "Keyboard Shortcut Test",
    "status": "script_generated",
    "topic": "Testing keyboard shortcuts",
    "cefr_level": "B1",
    "genre": "small_talk",
    "speakers": [
        {
            "id": "sp1", "name": "Alex", "gender": "male", "accent": "american",
            "tts_engine": "edge_tts", "voice_id": None, "voice_description": "",
            "speed": 1.0, "pitch": 0.0, "volume": 1.0, "avatar_image_path": None,
        }
    ],
}
STEP4_LINES = [{"id": "l1", "line_index": 0, "speaker_id": "sp1", "text": "Hi!", "language_notes": None, "duration_seconds": None}]


async def _mock_step4_routes(page, *, generate_delay_ms=0):
    async def handle(route):
        url, method = route.request.url, route.request.method
        if url.endswith(f"/api/projects/{PROJECT_ID}") and method == "GET":
            await route.fulfill(status=200, content_type="application/json", body=_envelope(STEP4_PROJECT))
        elif url.endswith(f"/api/projects/{PROJECT_ID}/script") and method == "GET":
            await route.fulfill(status=200, content_type="application/json", body=_envelope(STEP4_LINES))
        elif url.endswith("/api/music") and method == "GET":
            await route.fulfill(status=200, content_type="application/json", body=_envelope([]))
        elif url.endswith("/audio/status") and method == "GET":
            await route.fulfill(status=404, content_type="application/json", body=_envelope(None, "no audio"))
        elif "/tts/preview" in url and method == "POST":
            await route.fulfill(
                status=200,
                content_type="application/json",
                body=_envelope({"audio_path": "cached.mp3", "engine_used": "edge_tts"}),
            )
        elif "/tts/cache/" in url and method == "GET":
            await route.fulfill(status=200, content_type="audio/mpeg", body=b"")
        else:
            await route.continue_()

    await page.route("**/api/**", handle)


@pytest.mark.asyncio
async def test_step4_ctrl_enter_triggers_generate_when_enabled(browser_instance: Browser, live_server_url: str):
    page = await browser_instance.new_page()
    generate_calls = []

    async def count_generate(route):
        generate_calls.append(1)
        await route.fulfill(
            status=200,
            content_type="application/json",
            body=_envelope({"project_id": PROJECT_ID, "status": "complete", "mp3_path": "x.mp3", "wav_path": "x.wav",
                            "timestamps": [], "background_music": None, "duration_seconds": 1.0,
                            "loudness_lufs": -16.0, "error_message": None, "started_at": "t", "completed_at": "t"}),
        )

    await _mock_step4_routes(page)
    await page.route(f"**/api/projects/{PROJECT_ID}/audio/generate", count_generate)
    await page.goto(f"{live_server_url}/step4?project_id={PROJECT_ID}")
    await page.wait_for_selector("#workspace:not([hidden])")

    await _press_ctrl_enter(page)
    await page.wait_for_timeout(300)

    assert len(generate_calls) == 1
    await page.close()


@pytest.mark.asyncio
async def test_step4_ctrl_enter_does_nothing_while_already_generating(browser_instance: Browser, live_server_url: str):
    """The button goes real-disabled the instant a generate is in flight — a second
    Ctrl+Enter during that window must not fire a second request."""
    page = await browser_instance.new_page()
    generate_calls = []

    async def slow_generate(route):
        generate_calls.append(1)
        await asyncio.sleep(0.5)  # keep isGenerating/disabled true across the 2nd press
        await route.fulfill(
            status=200,
            content_type="application/json",
            body=_envelope({"project_id": PROJECT_ID, "status": "complete", "mp3_path": "x.mp3", "wav_path": "x.wav",
                            "timestamps": [], "background_music": None, "duration_seconds": 1.0,
                            "loudness_lufs": -16.0, "error_message": None, "started_at": "t", "completed_at": "t"}),
        )

    await _mock_step4_routes(page)
    await page.route(f"**/api/projects/{PROJECT_ID}/audio/generate", slow_generate)
    await page.goto(f"{live_server_url}/step4?project_id={PROJECT_ID}")
    await page.wait_for_selector("#workspace:not([hidden])")

    await _press_ctrl_enter(page)
    # Button is now really `.disabled` (synchronous, before the awaited request settles).
    assert await page.locator("#generate-btn").is_disabled()
    await _press_ctrl_enter(page)
    await page.wait_for_timeout(800)

    assert len(generate_calls) == 1
    await page.close()


# ---------------------------------------------------------------------------
# Step 7 — YouTube Package
# ---------------------------------------------------------------------------

STEP7_PROJECT = {"id": PROJECT_ID, "name": "Keyboard Shortcut Test", "status": "video_generated", "cefr_level": "B1", "genre": "small_talk"}
STEP7_PACKAGE = {
    "project_id": PROJECT_ID,
    "title_options": {"click_worthy": "A", "educational": "B", "seo": "C"},
    "description": "desc",
    "tags": ["a", "b"],
    "chapters": [{"start_sec": 0, "title": "Intro"}],
    "chapters_estimated": True,
}


async def _mock_step7_routes(page, *, existing_package):
    async def handle(route):
        url, method = route.request.url, route.request.method
        if url.endswith(f"/api/projects/{PROJECT_ID}/youtube") and method == "GET":
            # GET .../youtube returns 200 with `data: null` for "no package yet" — a
            # 404 here is treated as a genuine load *failure* by step7_youtube.js
            # (unlike video/audio status routes, which do treat 404 as expected).
            package = STEP7_PACKAGE if existing_package else None
            await route.fulfill(status=200, content_type="application/json", body=_envelope(package))
        elif url.endswith(f"/api/projects/{PROJECT_ID}/video/status") and method == "GET":
            await route.fulfill(status=404, content_type="application/json", body=_envelope(None, "no video"))
        elif url.endswith(f"/api/projects/{PROJECT_ID}/thumbnails") and method == "GET":
            await route.fulfill(status=200, content_type="application/json", body=_envelope([]))
        elif url.endswith(f"/api/projects/{PROJECT_ID}") and method == "GET":
            await route.fulfill(status=200, content_type="application/json", body=_envelope(STEP7_PROJECT))
        else:
            await route.continue_()

    await page.route("**/api/**", handle)


@pytest.mark.asyncio
async def test_step7_ctrl_enter_triggers_generate_when_panel_visible(browser_instance: Browser, live_server_url: str):
    page = await browser_instance.new_page()
    generate_calls = []

    async def count_generate(route):
        generate_calls.append(1)
        await route.fulfill(status=200, content_type="application/json", body=_envelope(STEP7_PACKAGE))

    await _mock_step7_routes(page, existing_package=False)
    await page.route(f"**/api/projects/{PROJECT_ID}/youtube/generate", count_generate)
    await page.goto(f"{live_server_url}/step7?project_id={PROJECT_ID}")
    await page.wait_for_selector("#generate-panel:not([hidden])")

    await _press_ctrl_enter(page)
    await page.wait_for_timeout(300)

    assert len(generate_calls) == 1
    await page.close()


@pytest.mark.asyncio
async def test_step7_ctrl_enter_does_nothing_when_panel_hidden(browser_instance: Browser, live_server_url: str):
    """Existing package hides #generate-panel (Regenerate is the only action then) —
    Ctrl+Enter targets `generate-btn` specifically and must stay a no-op."""
    page = await browser_instance.new_page()
    generate_calls = []

    async def count_generate(route):
        generate_calls.append(1)
        await route.fulfill(status=200, content_type="application/json", body=_envelope(STEP7_PACKAGE))

    await _mock_step7_routes(page, existing_package=True)
    await page.route(f"**/api/projects/{PROJECT_ID}/youtube/generate", count_generate)
    await page.goto(f"{live_server_url}/step7?project_id={PROJECT_ID}")
    await page.wait_for_selector("#generate-panel[hidden]", state="attached")

    await _press_ctrl_enter(page)
    await page.wait_for_timeout(300)

    assert len(generate_calls) == 0
    await page.close()
