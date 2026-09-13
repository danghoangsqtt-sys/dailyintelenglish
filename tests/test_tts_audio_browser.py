"""Playwright E2E coverage for the Step 4 TTS Audio Studio UI (Task 1.6, Sub-task 1.6c).

Same network-mocking approach as tests/test_youtube_browser.py: `page.route()`
intercepts fetches before they reach the real server, so this exercises only the
frontend JS state machine — no real TTS/ffmpeg calls needed.
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

PROJECT = {
    "id": "audio-proj-e2e",
    "name": "Audio Studio E2E Test Episode",
    "status": "script_generated",
    "topic": "Testing the audio studio",
    "cefr_level": "B1",
    "genre": "small_talk",
    "speakers": [
        {
            "id": "sp1",
            "speaker_index": 0,
            "name": "Alex",
            "gender": "male",
            "accent": "american",
            "tts_engine": "omnivoice",
            "voice_id": None,
            "voice_description": "",
            "speed": 1.0,
            "pitch": 0.0,
            "volume": 1.0,
            "avatar_image_path": None,
        },
        {
            "id": "sp2",
            "speaker_index": 1,
            "name": "Sam",
            "gender": "female",
            "accent": "american",
            "tts_engine": "edge_tts",
            "voice_id": None,
            "voice_description": "",
            "speed": 1.0,
            "pitch": 0.0,
            "volume": 1.0,
            "avatar_image_path": None,
        },
    ],
}

LINES = [
    {"id": "line-1", "line_index": 0, "speaker_id": "sp1", "text": "Welcome to the show!", "language_notes": None, "duration_seconds": None},
    {"id": "line-2", "line_index": 1, "speaker_id": "sp2", "text": "Thanks for having me.", "language_notes": None, "duration_seconds": None},
]

MUSIC_TRACKS = [{"filename": "bg-track.mp3", "size_bytes": 4096, "content_url": "/api/music/bg-track.mp3"}]

AUDIO_JOB = {
    "project_id": PROJECT["id"],
    "status": "complete",
    "mp3_path": "data/audio/audio-proj-e2e/mix.mp3",
    "wav_path": "data/audio/audio-proj-e2e/mix.wav",
    "timestamps": [
        {"start_sec": 0.0, "end_sec": 1.0, "label": "Alex", "speaker_id": "sp1"},
        {"start_sec": 1.5, "end_sec": 2.5, "label": "Sam", "speaker_id": "sp2"},
    ],
    "background_music": None,
    "duration_seconds": 2.5,
    "loudness_lufs": -16.0,
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


async def _default_routes(
    page,
    *,
    lines=None,
    project=None,
    audio_job_status=404,
    audio_job=None,
    generate_status=200,
    generate_body=None,
):
    project = project if project is not None else PROJECT
    lines = LINES if lines is None else lines
    generate_body = generate_body if generate_body is not None else AUDIO_JOB
    state = {"project": json.loads(json.dumps(project))}

    async def handle_routes(route):
        url = route.request.url
        method = route.request.method

        if url.endswith(f"/api/projects/{PROJECT['id']}") and method == "GET":
            await route.fulfill(status=200, content_type="application/json", body=_envelope(state["project"]))
        elif "/speakers/" in url and method == "PATCH":
            speaker_id = url.rsplit("/speakers/", 1)[1]
            patch = json.loads(route.request.post_data or "{}")
            for speaker in state["project"]["speakers"]:
                if speaker["id"] == speaker_id:
                    speaker.update(patch)
            await route.fulfill(status=200, content_type="application/json", body=_envelope(state["project"]))
        elif url.endswith(f"/api/projects/{PROJECT['id']}/script") and method == "GET":
            await route.fulfill(status=200, content_type="application/json", body=_envelope(lines))
        elif url.endswith("/api/music") and method == "GET":
            await route.fulfill(status=200, content_type="application/json", body=_envelope(MUSIC_TRACKS))
        elif url.endswith("/audio/status") and method == "GET":
            if audio_job_status == 200:
                await route.fulfill(status=200, content_type="application/json", body=_envelope(audio_job))
            else:
                await route.fulfill(
                    status=404, content_type="application/json", body=_envelope(None, "No audio job")
                )
        elif "/tts/preview" in url and method == "POST":
            await route.fulfill(
                status=200,
                content_type="application/json",
                body=_envelope({"audio_path": "cached.mp3", "engine_used": "edge_tts"}),
            )
        elif "/tts/cache/" in url and method == "GET":
            await route.fulfill(status=200, content_type="audio/mpeg", body=b"")
        elif url.endswith("/audio/generate") and method == "POST":
            await route.fulfill(
                status=generate_status,
                content_type="application/json",
                body=_envelope(None, "boom") if generate_status != 200 else _envelope(generate_body),
            )
        else:
            await route.continue_()

    await page.route("**/api/**", handle_routes)


@pytest.mark.asyncio
async def test_workspace_loads_speakers_and_lines(browser_instance: Browser, live_server_url: str):
    page = await browser_instance.new_page()
    await _default_routes(page)

    await page.goto(f"{live_server_url}/step4?project_id={PROJECT['id']}")
    await page.wait_for_selector("#workspace:not([hidden])")

    assert await page.locator(".speaker-card").count() == 2
    assert await page.locator(".line-card").count() == 2
    music_options = await page.locator("#music-select option").all_text_contents()
    assert "bg-track.mp3" in music_options
    await page.close()


@pytest.mark.asyncio
async def test_empty_script_shows_empty_state_not_workspace(browser_instance: Browser, live_server_url: str):
    page = await browser_instance.new_page()
    await _default_routes(page, lines=[])

    await page.goto(f"{live_server_url}/step4?project_id={PROJECT['id']}")

    await page.wait_for_selector("#empty-state:not([hidden])")
    assert await page.locator("#workspace").is_hidden()
    await page.close()


@pytest.mark.asyncio
async def test_speaker_engine_change_autosaves(browser_instance: Browser, live_server_url: str):
    page = await browser_instance.new_page()
    patch_bodies = []

    async def capture_patch(route):
        patch_bodies.append(json.loads(route.request.post_data or "{}"))
        await route.fulfill(status=200, content_type="application/json", body=_envelope(PROJECT))

    await _default_routes(page)
    await page.route(f"**/api/projects/{PROJECT['id']}/speakers/sp1", capture_patch)
    await page.goto(f"{live_server_url}/step4?project_id={PROJECT['id']}")
    await page.wait_for_selector("#workspace:not([hidden])")

    first_engine_select = page.locator(".speaker-card select").first
    await first_engine_select.select_option("edge_tts")
    await page.wait_for_timeout(600)  # past the 400ms debounce
    assert len(patch_bodies) == 1
    assert patch_bodies[0]["tts_engine"] == "edge_tts"
    await page.close()


@pytest.mark.asyncio
async def test_preview_line_reveals_audio_player(browser_instance: Browser, live_server_url: str):
    page = await browser_instance.new_page()
    await _default_routes(page)
    await page.goto(f"{live_server_url}/step4?project_id={PROJECT['id']}")
    await page.wait_for_selector("#workspace:not([hidden])")

    await page.locator(".preview-btn").first.click()

    await page.wait_for_selector(".line-audio:not([hidden])")
    await page.close()


@pytest.mark.asyncio
async def test_generate_all_happy_path_shows_player_and_downloads(browser_instance: Browser, live_server_url: str):
    page = await browser_instance.new_page()
    await _default_routes(page)
    await page.goto(f"{live_server_url}/step4?project_id={PROJECT['id']}")
    await page.wait_for_selector("#workspace:not([hidden])")

    await page.click("#generate-btn")

    await page.wait_for_selector("#result-card:not([hidden])", timeout=5000)
    mp3_href = await page.locator("#download-mp3").get_attribute("href")
    wav_href = await page.locator("#download-wav").get_attribute("href")
    assert "format=mp3" in mp3_href
    assert "format=wav" in wav_href
    progress_text = await page.locator("#generate-progress").text_content()
    assert "Done" in progress_text
    await page.close()


@pytest.mark.asyncio
async def test_generate_failure_shows_friendly_error_only(browser_instance: Browser, live_server_url: str):
    page = await browser_instance.new_page()
    await _default_routes(page, generate_status=502)
    await page.goto(f"{live_server_url}/step4?project_id={PROJECT['id']}")
    await page.wait_for_selector("#workspace:not([hidden])")

    await page.click("#generate-btn")

    await page.wait_for_selector("#error-banner:not([hidden])", timeout=5000)
    banner_text = await page.locator("#error-banner").text_content()
    assert "couldn't generate" in banner_text.lower()
    assert "boom" not in banner_text
    await page.close()


@pytest.mark.asyncio
async def test_existing_completed_job_shown_on_load(browser_instance: Browser, live_server_url: str):
    page = await browser_instance.new_page()
    await _default_routes(page, audio_job_status=200, audio_job=AUDIO_JOB)
    await page.goto(f"{live_server_url}/step4?project_id={PROJECT['id']}")

    await page.wait_for_selector("#result-card:not([hidden])")
    await page.close()
