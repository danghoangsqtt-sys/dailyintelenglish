"""Playwright E2E coverage for the Step 5 Video Studio UI (Task 1.7, Sub-task 1.7b).

Same network-mocking approach as tests/test_tts_audio_browser.py: `page.route()`
intercepts fetches before they reach the real server, so this exercises only the
frontend JS state machine — no real ffmpeg call needed.
"""

import json
import socket
import threading
import time
from typing import AsyncGenerator

import pytest
import uvicorn
from playwright.async_api import Browser, async_playwright

from app.main import app

PROJECT = {"id": "video-proj-e2e", "name": "Video Studio E2E Test Episode", "status": "audio_generated", "cefr_level": "B1", "genre": "small_talk"}

TEMPLATES = [
    {"id": "midnight", "display_name": "Midnight", "preview_url": "/static/video_backgrounds/midnight.png"},
    {"id": "deep_purple", "display_name": "Deep Purple", "preview_url": "/static/video_backgrounds/deep_purple.png"},
    {"id": "charcoal_wave", "display_name": "Charcoal Wave", "preview_url": "/static/video_backgrounds/charcoal_wave.png"},
]

VIDEO_JOB = {
    "project_id": PROJECT["id"],
    "status": "complete",
    "mode": "background",
    "mp4_path": "data/video/video-proj-e2e/video.mp4",
    "srt_path": "data/video/video-proj-e2e/subtitles.srt",
    "background_image": "midnight",
    "error_message": None,
    "started_at": "2026-09-13T00:00:00Z",
    "completed_at": "2026-09-13T00:00:01Z",
}


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


def _envelope(data, error=None):
    return json.dumps({"success": error is None, "data": data, "error": error, "meta": {}})


async def _default_routes(page, *, audio_status=200, video_job_status=404, video_job=None, generate_status=200):
    async def handle_routes(route):
        url = route.request.url
        method = route.request.method

        if url.endswith(f"/api/projects/{PROJECT['id']}") and method == "GET":
            await route.fulfill(status=200, content_type="application/json", body=_envelope(PROJECT))
        elif url.endswith("/audio/status") and method == "GET":
            if audio_status == 200:
                await route.fulfill(status=200, content_type="application/json", body=_envelope({"status": "complete"}))
            else:
                await route.fulfill(status=404, content_type="application/json", body=_envelope(None, "no audio"))
        elif url.endswith("/api/video/templates") and method == "GET":
            await route.fulfill(status=200, content_type="application/json", body=_envelope(TEMPLATES))
        elif url.endswith("/video/status") and method == "GET":
            if video_job_status == 200:
                await route.fulfill(status=200, content_type="application/json", body=_envelope(video_job or VIDEO_JOB))
            else:
                await route.fulfill(status=404, content_type="application/json", body=_envelope(None, "no video"))
        elif url.endswith("/video/generate") and method == "POST":
            await route.fulfill(
                status=generate_status,
                content_type="application/json",
                body=_envelope(None, "boom") if generate_status != 200 else _envelope(VIDEO_JOB),
            )
        else:
            await route.continue_()

    await page.route("**/api/**", handle_routes)


@pytest.mark.asyncio
async def test_empty_state_shown_when_no_audio_yet(browser_instance: Browser, live_server_url: str):
    page = await browser_instance.new_page()
    await _default_routes(page, audio_status=404)

    await page.goto(f"{live_server_url}/step5?project_id={PROJECT['id']}")

    await page.wait_for_selector("#empty-state:not([hidden])")
    assert await page.locator("#workspace").is_hidden()
    href = await page.locator("#empty-state-link").get_attribute("href")
    assert href.startswith("/step4")
    await page.close()


@pytest.mark.asyncio
async def test_workspace_loads_templates_when_audio_ready(browser_instance: Browser, live_server_url: str):
    page = await browser_instance.new_page()
    await _default_routes(page)

    await page.goto(f"{live_server_url}/step5?project_id={PROJECT['id']}")

    await page.wait_for_selector("#workspace:not([hidden])")
    assert await page.locator(".template-option").count() == 3
    assert await page.locator("#no-result-yet").is_visible()
    await page.close()


@pytest.mark.asyncio
async def test_generate_happy_path_shows_player_and_downloads(browser_instance: Browser, live_server_url: str):
    page = await browser_instance.new_page()
    await _default_routes(page)
    await page.goto(f"{live_server_url}/step5?project_id={PROJECT['id']}")
    await page.wait_for_selector("#workspace:not([hidden])")

    await page.click("#generate-btn")

    await page.wait_for_selector("#result-card:not([hidden])", timeout=5000)
    mp4_href = await page.locator("#download-mp4").get_attribute("href")
    srt_href = await page.locator("#download-srt").get_attribute("href")
    assert "format=mp4" in mp4_href
    assert "format=srt" in srt_href
    progress_text = await page.locator("#generate-progress").text_content()
    assert "Done" in progress_text
    await page.close()


@pytest.mark.asyncio
async def test_existing_completed_job_shown_on_load(browser_instance: Browser, live_server_url: str):
    page = await browser_instance.new_page()
    await _default_routes(page, video_job_status=200)
    await page.goto(f"{live_server_url}/step5?project_id={PROJECT['id']}")

    await page.wait_for_selector("#result-card:not([hidden])")
    await page.close()


@pytest.mark.asyncio
async def test_generate_failure_shows_friendly_error_only(browser_instance: Browser, live_server_url: str):
    page = await browser_instance.new_page()
    await _default_routes(page, generate_status=502)
    await page.goto(f"{live_server_url}/step5?project_id={PROJECT['id']}")
    await page.wait_for_selector("#workspace:not([hidden])")

    await page.click("#generate-btn")

    await page.wait_for_selector("#error-banner:not([hidden])", timeout=5000)
    banner_text = await page.locator("#error-banner").text_content()
    assert "couldn't generate" in banner_text.lower()
    assert "boom" not in banner_text
    await page.close()


@pytest.mark.asyncio
async def test_step4_next_step_link_points_to_step5(browser_instance: Browser, live_server_url: str):
    page = await browser_instance.new_page()
    project_with_speaker = {**PROJECT, "speakers": [{"id": "sp1", "name": "Alex", "gender": "male", "accent": "american", "tts_engine": "edge_tts", "voice_id": None, "voice_description": "", "speed": 1.0, "pitch": 0.0, "volume": 1.0, "avatar_image_path": None}]}
    one_line = [{"id": "l1", "line_index": 0, "speaker_id": "sp1", "text": "Welcome!", "language_notes": None, "duration_seconds": None}]

    async def handle_step4_routes(route):
        url = route.request.url
        method = route.request.method
        if url.endswith(f"/api/projects/{PROJECT['id']}") and method == "GET":
            await route.fulfill(status=200, content_type="application/json", body=_envelope(project_with_speaker))
        elif url.endswith("/script") and method == "GET":
            await route.fulfill(status=200, content_type="application/json", body=_envelope(one_line))
        elif url.endswith("/api/music") and method == "GET":
            await route.fulfill(status=200, content_type="application/json", body=_envelope([]))
        elif url.endswith("/audio/status") and method == "GET":
            await route.fulfill(status=404, content_type="application/json", body=_envelope(None, "no audio"))
        else:
            await route.continue_()

    await page.route("**/api/**", handle_step4_routes)
    await page.goto(f"{live_server_url}/step4?project_id={PROJECT['id']}")
    await page.wait_for_selector("#workspace:not([hidden])")

    next_href = await page.locator("#next-step-link").get_attribute("href")
    assert next_href == f"/step5?project_id={PROJECT['id']}"
    await page.close()


@pytest.mark.asyncio
async def test_step5_back_link_points_to_step4(browser_instance: Browser, live_server_url: str):
    page = await browser_instance.new_page()
    await _default_routes(page)
    await page.goto(f"{live_server_url}/step5?project_id={PROJECT['id']}")
    await page.wait_for_selector("#workspace:not([hidden])")

    back_href = await page.locator("#back-link").get_attribute("href")
    assert back_href == f"/step4?project_id={PROJECT['id']}"
    await page.close()
