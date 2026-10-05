"""Playwright coverage for Report-UX-1 (elapsed counter + ETA + Step 4/5 progress parity).

One test per Step page (2/3/4/5), each asserting the shared `GenerationStatus` component's
elapsed counter genuinely advances against real wall-clock time. Same `page.route()` /
`_envelope()` mocking convention as `tests/test_script_jobs_browser.py`,
`tests/test_learning_jobs_browser.py`, `tests/test_tts_audio_browser.py`,
`tests/test_video_studio_browser.py` -- no real Gemini/OpenRouter/Ollama/Edge-TTS/ffmpeg call.

Step 2/3 rely on `AiJob`'s real 2000ms poll interval to provide the wall-clock gap (no
artificial delay needed in the mock). Step 4/5 have no poll loop (a single awaited request
each) -- their mocked route handler holds the response with a real `asyncio.sleep(2.5)` so
the counter has time to advance before the operation "completes" (DRUX-d).
"""

import asyncio
import json
import re
from datetime import datetime, timezone
from typing import AsyncGenerator

import pytest
from playwright.async_api import Browser, Page, async_playwright

from tests.conftest import live_server


def _envelope(data, error=None) -> str:
    return json.dumps({"success": error is None, "data": data, "error": error, "meta": {}})


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


@pytest.fixture
async def browser_instance() -> AsyncGenerator[Browser, None]:
    async with async_playwright() as playwright:
        browser = await playwright.chromium.launch(headless=True)
        yield browser
        await browser.close()


# ---------------------------------------------------------------------------
# Step 2 -- Script
# ---------------------------------------------------------------------------

SCRIPT_PROJECT_ID = "genstatus-script-proj"
SCRIPT_PROJECT = {
    "id": SCRIPT_PROJECT_ID,
    "name": "Generation Status Script Test",
    "status": "draft",
    "topic": "Testing the elapsed counter",
    "cefr_level": "B1",
    "genre": "small_talk",
    "accent": "american",
    "speakers": [{"id": "sp1", "name": "Alex", "gender": "male", "accent": "american"}],
}


def _ai_health() -> dict:
    return {
        "mode": "local", "ollama_reachable": True, "model": "qwen3.5:9b",
        "model_present": True, "model_digest": "abc123", "cloud_enabled": False,
    }


def _script_job(**overrides) -> dict:
    base = {
        "id": "job-1", "project_id": SCRIPT_PROJECT_ID, "operation": "script", "status": "running",
        "stage": "section_1", "progress": 40, "requested_provider": "hybrid", "actual_provider": "ollama",
        "model": "qwen3.5:9b", "fallback_used": False, "fallback_reason": None,
        "cancel_requested": False, "attempt": 1, "repair_count": 0, "fallback_count": 0,
        "recovery_count": 0, "error_code": None, "error_message": None,
        "created_at": _now_iso(), "started_at": _now_iso(),
        "updated_at": _now_iso(), "finished_at": None,
    }
    base.update(overrides)
    return base


@pytest.fixture
def script_live_server_url(tmp_path_factory: pytest.TempPathFactory):
    with live_server(tmp_path_factory, "genstatus-script") as url:
        yield url


async def _mock_script_routes(page: Page, *, job: dict) -> None:
    jobs_by_id = {"job-1": job}

    async def handle(route):
        url, method = route.request.url, route.request.method
        if url.endswith("/api/ai/health") and method == "GET":
            await route.fulfill(status=200, content_type="application/json", body=_envelope(_ai_health()))
        elif url.endswith(f"/api/projects/{SCRIPT_PROJECT_ID}") and method == "GET":
            await route.fulfill(status=200, content_type="application/json", body=_envelope(SCRIPT_PROJECT))
        elif url.endswith(f"/api/projects/{SCRIPT_PROJECT_ID}/script") and method == "GET":
            await route.fulfill(status=200, content_type="application/json", body=_envelope([]))
        elif "/ai-jobs/active" in url and method == "GET":
            await route.fulfill(status=200, content_type="application/json", body=_envelope(None))
        elif url.endswith(f"/api/projects/{SCRIPT_PROJECT_ID}/ai-jobs") and method == "POST":
            await route.fulfill(status=202, content_type="application/json", body=_envelope(jobs_by_id["job-1"]))
        elif url.endswith("/ai-jobs/job-1") and method == "GET":
            await route.fulfill(status=200, content_type="application/json", body=_envelope(jobs_by_id["job-1"]))
        else:
            await route.continue_()

    await page.route("**/api/**", handle)


@pytest.mark.asyncio
async def test_step2_elapsed_counter_advances_against_real_wall_clock(
    browser_instance: Browser, script_live_server_url: str
):
    page = await browser_instance.new_page()
    await _mock_script_routes(page, job=_script_job())
    await page.goto(f"{script_live_server_url}/step2?project_id={SCRIPT_PROJECT_ID}")
    await page.wait_for_selector("#generate-panel:not([hidden])")

    await page.click("#generate-btn")
    await page.wait_for_selector("#ai-job-status:not([hidden])")

    # AiJob's real 2000ms poll interval provides the wall-clock gap -- no mocked delay needed.
    await page.wait_for_timeout(2500)

    elapsed_text = await page.locator(".generation-status-elapsed").text_content()
    assert elapsed_text is not None and re.search(r"0:0[2-9]", elapsed_text), elapsed_text
    await page.close()


# ---------------------------------------------------------------------------
# Step 3 -- Learning
# ---------------------------------------------------------------------------

LEARNING_PROJECT_ID = "genstatus-learning-proj"
LEARNING_PROJECT = {
    "id": LEARNING_PROJECT_ID,
    "name": "Generation Status Learning Test",
    "status": "script_generated",
    "topic": "Testing the elapsed counter",
    "cefr_level": "B1",
    "genre": "small_talk",
    "accent": "american",
    "speakers": [{"id": "sp1", "name": "Alex", "gender": "male", "accent": "american"}],
}


def _learning_job(**overrides) -> dict:
    base = {
        "id": "job-1", "project_id": LEARNING_PROJECT_ID, "operation": "learning", "status": "running",
        "stage": "generating", "progress": 40, "requested_provider": "hybrid", "actual_provider": "ollama",
        "model": "qwen3.5:9b", "fallback_used": False, "fallback_reason": None,
        "cancel_requested": False, "attempt": 1, "repair_count": 0, "fallback_count": 0,
        "recovery_count": 0, "error_code": None, "error_message": None,
        "created_at": _now_iso(), "started_at": _now_iso(),
        "updated_at": _now_iso(), "finished_at": None,
    }
    base.update(overrides)
    return base


@pytest.fixture
def learning_live_server_url(tmp_path_factory: pytest.TempPathFactory):
    with live_server(tmp_path_factory, "genstatus-learning") as url:
        yield url


async def _mock_learning_routes(page: Page, *, job: dict) -> None:
    jobs_by_id = {"job-1": job}

    async def handle(route):
        url, method = route.request.url, route.request.method
        if url.endswith("/api/ai/health") and method == "GET":
            await route.fulfill(status=200, content_type="application/json", body=_envelope(_ai_health()))
        elif url.endswith(f"/api/projects/{LEARNING_PROJECT_ID}") and method == "GET":
            await route.fulfill(status=200, content_type="application/json", body=_envelope(LEARNING_PROJECT))
        elif url.endswith(f"/api/projects/{LEARNING_PROJECT_ID}/learning") and method == "GET":
            await route.fulfill(status=200, content_type="application/json", body=_envelope(None))
        elif "/ai-jobs/active" in url and method == "GET":
            await route.fulfill(status=200, content_type="application/json", body=_envelope(None))
        elif url.endswith(f"/api/projects/{LEARNING_PROJECT_ID}/ai-jobs") and method == "POST":
            await route.fulfill(status=202, content_type="application/json", body=_envelope(jobs_by_id["job-1"]))
        elif url.endswith("/ai-jobs/job-1") and method == "GET":
            await route.fulfill(status=200, content_type="application/json", body=_envelope(jobs_by_id["job-1"]))
        else:
            await route.continue_()

    await page.route("**/api/**", handle)


@pytest.mark.asyncio
async def test_step3_elapsed_counter_advances_against_real_wall_clock(
    browser_instance: Browser, learning_live_server_url: str
):
    page = await browser_instance.new_page()
    await _mock_learning_routes(page, job=_learning_job())
    await page.goto(f"{learning_live_server_url}/step3?project_id={LEARNING_PROJECT_ID}")
    await page.wait_for_selector("#generate-panel:not([hidden])")

    await page.click("#generate-btn")
    await page.wait_for_selector("#ai-job-status:not([hidden])")

    await page.wait_for_timeout(2500)

    elapsed_text = await page.locator(".generation-status-elapsed").text_content()
    assert elapsed_text is not None and re.search(r"0:0[2-9]", elapsed_text), elapsed_text
    await page.close()


# ---------------------------------------------------------------------------
# Step 4 -- TTS Audio Studio
# ---------------------------------------------------------------------------

TTS_PROJECT = {
    "id": "genstatus-tts-proj",
    "name": "Generation Status TTS Test",
    "status": "script_generated",
    "topic": "Testing the elapsed counter",
    "cefr_level": "B1",
    "genre": "small_talk",
    "speakers": [
        {
            "id": "sp1", "speaker_index": 0, "name": "Alex", "gender": "male", "accent": "american",
            "tts_engine": "edge_tts", "voice_id": None, "voice_description": "", "speed": 1.0,
            "pitch": 0.0, "volume": 1.0, "avatar_image_path": None,
        },
    ],
}
TTS_LINES = [
    {"id": "line-1", "line_index": 0, "speaker_id": "sp1", "text": "Hello there.", "language_notes": None, "duration_seconds": None},
]
TTS_MUSIC_TRACKS: list = []
TTS_AUDIO_JOB = {
    "project_id": TTS_PROJECT["id"],
    "status": "complete",
    "mp3_path": "data/audio/genstatus-tts-proj/mix.mp3",
    "wav_path": "data/audio/genstatus-tts-proj/mix.wav",
    "timestamps": [{"start_sec": 0.0, "end_sec": 1.0, "label": "Alex", "speaker_id": "sp1"}],
    "background_music": None,
    "duration_seconds": 1.0,
    "loudness_lufs": -16.0,
    "error_message": None,
    "started_at": _now_iso(),
    "completed_at": None,
}


@pytest.fixture
def tts_live_server_url(tmp_path_factory: pytest.TempPathFactory):
    with live_server(tmp_path_factory, "genstatus-tts") as url:
        yield url


async def _mock_tts_routes(page: Page) -> None:
    async def handle(route):
        url, method = route.request.url, route.request.method
        if url.endswith(f"/api/projects/{TTS_PROJECT['id']}") and method == "GET":
            await route.fulfill(status=200, content_type="application/json", body=_envelope(TTS_PROJECT))
        elif url.endswith(f"/api/projects/{TTS_PROJECT['id']}/script") and method == "GET":
            await route.fulfill(status=200, content_type="application/json", body=_envelope(TTS_LINES))
        elif url.endswith("/api/music") and method == "GET":
            await route.fulfill(status=200, content_type="application/json", body=_envelope(TTS_MUSIC_TRACKS))
        elif url.endswith("/audio/status") and method == "GET":
            await route.fulfill(status=404, content_type="application/json", body=_envelope(None, "no audio"))
        elif "/tts/preview" in url and method == "POST":
            # DRUX-d: hold the response open for real wall-clock time so the elapsed
            # counter has something to measure before this "line" finishes synthesizing.
            await asyncio.sleep(2.5)
            await route.fulfill(
                status=200, content_type="application/json",
                body=_envelope({"audio_path": "cached.mp3", "engine_used": "edge_tts"}),
            )
        elif url.endswith("/audio/generate") and method == "POST":
            await route.fulfill(status=200, content_type="application/json", body=_envelope(TTS_AUDIO_JOB))
        else:
            await route.continue_()

    await page.route("**/api/**", handle)


@pytest.mark.asyncio
async def test_step4_elapsed_counter_advances_against_real_wall_clock(
    browser_instance: Browser, tts_live_server_url: str
):
    page = await browser_instance.new_page()
    await _mock_tts_routes(page)
    await page.goto(f"{tts_live_server_url}/step4?project_id={TTS_PROJECT['id']}")
    await page.wait_for_selector("#generate-btn:not([disabled])")

    await page.click("#generate-btn")
    # Real wall-clock wait while the mocked /tts/preview call is held open (see
    # _mock_tts_routes) -- must exceed the mock's asyncio.sleep(2.5) minus a small margin.
    await page.wait_for_timeout(2200)

    progress_text = await page.locator("#generate-progress").text_content()
    assert progress_text is not None and re.search(r"0:0[1-9]", progress_text), progress_text
    assert "Synthesizing line 1/1" in progress_text
    await page.close()


# ---------------------------------------------------------------------------
# Step 5 -- Video Studio
# ---------------------------------------------------------------------------

VIDEO_PROJECT = {"id": "genstatus-video-proj", "name": "Generation Status Video Test", "status": "audio_generated", "cefr_level": "B1", "genre": "small_talk"}
VIDEO_TEMPLATES = [
    {"id": "midnight", "display_name": "Midnight", "preview_url": "/static/video_backgrounds/midnight.png"},
]
VIDEO_JOB = {
    "project_id": VIDEO_PROJECT["id"],
    "status": "complete",
    "mode": "background",
    "mp4_path": "data/video/genstatus-video-proj/video.mp4",
    "srt_path": "data/video/genstatus-video-proj/subtitles.srt",
    "background_image": "midnight",
    "error_message": None,
    "started_at": _now_iso(),
    "completed_at": None,
}


@pytest.fixture
def video_live_server_url(tmp_path_factory: pytest.TempPathFactory):
    with live_server(tmp_path_factory, "genstatus-video") as url:
        yield url


async def _mock_video_routes(page: Page) -> None:
    async def handle(route):
        url, method = route.request.url, route.request.method
        if url.endswith(f"/api/projects/{VIDEO_PROJECT['id']}") and method == "GET":
            await route.fulfill(status=200, content_type="application/json", body=_envelope(VIDEO_PROJECT))
        elif url.endswith("/audio/status") and method == "GET":
            await route.fulfill(status=200, content_type="application/json", body=_envelope({"status": "complete"}))
        elif url.endswith("/api/video/templates") and method == "GET":
            await route.fulfill(status=200, content_type="application/json", body=_envelope(VIDEO_TEMPLATES))
        elif url.endswith("/video/status") and method == "GET":
            await route.fulfill(status=404, content_type="application/json", body=_envelope(None, "no video"))
        elif url.endswith("/video/generate") and method == "POST":
            # DRUX-d: hold the response open for real wall-clock time.
            await asyncio.sleep(2.5)
            await route.fulfill(status=200, content_type="application/json", body=_envelope(VIDEO_JOB))
        else:
            await route.continue_()

    await page.route("**/api/**", handle)


@pytest.mark.asyncio
async def test_step5_elapsed_counter_advances_against_real_wall_clock(
    browser_instance: Browser, video_live_server_url: str
):
    page = await browser_instance.new_page()
    await _mock_video_routes(page)
    # Task 19.9 made Enhanced the default wherever Remotion is installed; this test is about the
    # Standard flow, so it stores the owner's Standard choice (machine-independent).
    await page.add_init_script("try { localStorage.setItem('die-video-renderer', 'ffmpeg'); } catch (e) {}")
    await page.goto(f"{video_live_server_url}/step5?project_id={VIDEO_PROJECT['id']}")
    await page.wait_for_selector("#workspace:not([hidden])")

    await page.click("#generate-btn")
    await page.wait_for_timeout(2200)

    progress_text = await page.locator("#generate-progress").text_content()
    assert progress_text is not None and re.search(r"0:0[1-9]", progress_text), progress_text
    assert "Rendering with ffmpeg" in progress_text
    await page.close()
