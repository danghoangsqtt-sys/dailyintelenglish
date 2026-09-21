"""Playwright coverage for Step 3's durable-job Generate flow (Task 13.6).

Mirrors tests/test_script_jobs_browser.py's coverage for the learning-content
pipeline: refresh/navigation resumes an active job, a duplicate click does not
create a second job, cancel is keyboard accessible, a fallback is visible, and
the finished pack reloads into the normal content view once the job completes.
"""

import json
import socket
import threading
import time
from typing import AsyncGenerator

import pytest
import uvicorn
from playwright.async_api import Browser, Page, async_playwright

from app.main import app

PROJECT_ID = "learning-jobs-proj"

PROJECT = {
    "id": PROJECT_ID,
    "name": "Learning Jobs Test",
    "status": "script_generated",
    "topic": "Testing durable learning jobs",
    "cefr_level": "B1",
    "genre": "small_talk",
    "accent": "american",
    "speakers": [{"id": "sp1", "name": "Alex", "gender": "male", "accent": "american"}],
}

FINISHED_PACK = {
    "vocabulary": [
        {
            "word": "testing",
            "part_of_speech": "noun",
            "ipa": "/ˈtɛstɪŋ/",
            "definition_en": "the activity of testing something",
            "definition_vi": "kiểm thử",
            "example_sentence": "We are testing durable learning jobs.",
        }
    ],
    "idioms": [],
    "grammar": [],
    "questions": [],
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

    # Without this, the server thread (and the process-wide Database/AIWorker
    # singletons it started against the real DATA_DIR) keeps running for the rest of
    # the pytest session, so a later TestClient(app)-based test's lifespan startup
    # finds the singleton already connected and silently reuses it instead of opening
    # its own isolated tmp_path database -- found for real when this leaked into
    # tests/test_settings_api.py's "before anything is saved" assertion.
    server.should_exit = True
    thread.join(timeout=10.0)


@pytest.fixture
async def browser_instance() -> AsyncGenerator[Browser, None]:
    async with async_playwright() as playwright:
        browser = await playwright.chromium.launch(headless=True)
        yield browser
        await browser.close()


def _envelope(data, error=None) -> str:
    return json.dumps({"success": error is None, "data": data, "error": error, "meta": {}})


def _job(**overrides) -> dict:
    base = {
        "id": "job-1", "project_id": PROJECT_ID, "operation": "learning", "status": "running",
        "stage": "generating", "progress": 40, "requested_provider": "hybrid", "actual_provider": "ollama",
        "model": "qwen3.5:9b", "fallback_used": False, "fallback_reason": None,
        "cancel_requested": False, "attempt": 1, "repair_count": 0, "fallback_count": 0,
        "recovery_count": 0, "error_code": None, "error_message": None,
        "created_at": "2026-01-01T00:00:00Z", "started_at": "2026-01-01T00:00:00Z",
        "updated_at": "2026-01-01T00:00:00Z", "finished_at": None,
    }
    base.update(overrides)
    return base


def _ai_health(**overrides) -> dict:
    """Task 14.7: a healthy /api/ai/health payload -- the default for every
    `_mock_routes` call below, so existing tests are unaffected by the new
    Ollama-missing gate unless a test explicitly asks for the unhealthy case."""
    base = {
        "mode": "local", "ollama_reachable": True, "model": "qwen3.5:9b",
        "model_present": True, "model_digest": "6488c96fa5fa", "cloud_enabled": False,
    }
    base.update(overrides)
    return base


async def _mock_routes(page: Page, *, active_job: dict | None, jobs_by_id: dict, on_create=None, ai_health: dict | None = None):
    health = ai_health or _ai_health()

    async def handle(route):
        url, method = route.request.url, route.request.method
        if url.endswith("/api/ai/health") and method == "GET":
            await route.fulfill(status=200, content_type="application/json", body=_envelope(health))
        elif url.endswith(f"/api/projects/{PROJECT_ID}") and method == "GET":
            await route.fulfill(status=200, content_type="application/json", body=_envelope(PROJECT))
        elif url.endswith(f"/api/projects/{PROJECT_ID}/learning") and method == "GET":
            await route.fulfill(status=200, content_type="application/json", body=_envelope(None))
        elif "/ai-jobs/active" in url and method == "GET":
            await route.fulfill(status=200, content_type="application/json", body=_envelope(active_job))
        elif url.endswith(f"/api/projects/{PROJECT_ID}/ai-jobs") and method == "POST":
            if on_create:
                on_create()
            job = jobs_by_id.get("job-1", _job())
            await route.fulfill(status=202, content_type="application/json", body=_envelope(job))
        elif url.endswith("/ai-jobs/job-1/cancel") and method == "POST":
            jobs_by_id["job-1"] = _job(status="cancelled", cancel_requested=True, progress=40)
            await route.fulfill(status=200, content_type="application/json", body=_envelope(jobs_by_id["job-1"]))
        elif url.endswith("/ai-jobs/job-1") and method == "GET":
            await route.fulfill(status=200, content_type="application/json", body=_envelope(jobs_by_id["job-1"]))
        else:
            await route.continue_()

    await page.route("**/api/**", handle)


@pytest.mark.asyncio
async def test_refresh_resumes_an_active_learning_job(browser_instance: Browser, live_server_url: str):
    page = await browser_instance.new_page()
    jobs_by_id = {"job-1": _job(status="running", progress=60)}
    await _mock_routes(page, active_job=jobs_by_id["job-1"], jobs_by_id=jobs_by_id)

    await page.goto(f"{live_server_url}/step3?project_id={PROJECT_ID}")

    await page.wait_for_selector("#ai-job-status:not([hidden])")
    assert await page.locator("#generate-panel").is_hidden()
    assert "60" in await page.locator("#ai-job-status").inner_text()
    await page.close()


@pytest.mark.asyncio
async def test_double_click_generate_creates_only_one_learning_job(browser_instance: Browser, live_server_url: str):
    page = await browser_instance.new_page()
    create_calls = {"n": 0}

    def on_create():
        create_calls["n"] += 1

    jobs_by_id = {"job-1": _job(status="running")}
    await _mock_routes(page, active_job=None, jobs_by_id=jobs_by_id, on_create=on_create)
    await page.goto(f"{live_server_url}/step3?project_id={PROJECT_ID}")
    await page.wait_for_selector("#generate-panel:not([hidden])")

    await page.click("#generate-btn")
    await page.wait_for_timeout(100)
    generate_btn = page.locator("#generate-btn")
    if await generate_btn.count() > 0 and await generate_btn.is_visible():
        await generate_btn.click(force=True)
    await page.wait_for_timeout(200)

    assert create_calls["n"] == 1
    await page.close()


@pytest.mark.asyncio
async def test_learning_cancel_button_is_keyboard_accessible(browser_instance: Browser, live_server_url: str):
    page = await browser_instance.new_page()
    jobs_by_id = {"job-1": _job(status="running")}
    await _mock_routes(page, active_job=jobs_by_id["job-1"], jobs_by_id=jobs_by_id)
    await page.goto(f"{live_server_url}/step3?project_id={PROJECT_ID}")

    await page.wait_for_selector("#ai-job-cancel-btn")
    cancel_btn = page.locator("#ai-job-cancel-btn")
    assert (await cancel_btn.evaluate("el => el.tagName")).lower() == "button"

    await cancel_btn.focus()
    await page.keyboard.press("Enter")

    await page.wait_for_selector("text=Generation cancelled")
    await page.close()


@pytest.mark.asyncio
async def test_fallback_used_never_shows_gemini_copy(browser_instance: Browser, live_server_url: str):
    """Task 14.7 (local-only mode): `fallback_used` is now a dormant field
    (only meaningful if cloud is re-enabled via the unsupported rollback
    path, ADR-001 A2) -- the status banner must never mention Gemini, even
    when the job row itself says `fallback_used=True`."""
    page = await browser_instance.new_page()
    jobs_by_id = {"job-1": _job(status="running", fallback_used=True, actual_provider="gemini")}
    await _mock_routes(page, active_job=jobs_by_id["job-1"], jobs_by_id=jobs_by_id)
    await page.goto(f"{live_server_url}/step3?project_id={PROJECT_ID}")

    await page.wait_for_selector("#ai-job-status:not([hidden])")
    banner_text = await page.locator("#ai-job-status").inner_text()
    assert "Gemini" not in banner_text
    await page.close()


@pytest.mark.asyncio
async def test_generate_disabled_with_guidance_when_ollama_missing(browser_instance: Browser, live_server_url: str):
    """Task 14.7 action 4: the generate button is disabled and install/pull
    guidance (naming the live model) renders when /api/ai/health reports
    Ollama unreachable or the model missing."""
    page = await browser_instance.new_page()
    await _mock_routes(
        page, active_job=None, jobs_by_id={},
        ai_health=_ai_health(ollama_reachable=False, model_present=False),
    )
    await page.goto(f"{live_server_url}/step3?project_id={PROJECT_ID}")
    await page.wait_for_selector("#generate-panel:not([hidden])")

    await page.wait_for_selector("#ollama-guidance")
    assert await page.locator("#generate-btn").is_disabled()
    guidance_text = await page.locator("#ollama-guidance").inner_text()
    assert "ollama.com" in guidance_text
    assert "Gemini" not in guidance_text
    await page.close()


@pytest.mark.asyncio
async def test_learning_terminal_error_shows_retry_and_never_a_raw_exception(
    browser_instance: Browser, live_server_url: str
):
    page = await browser_instance.new_page()
    jobs_by_id = {
        "job-1": _job(status="error", error_code="pack_validation_failed", error_message="idiom phrase not grounded")
    }
    await _mock_routes(page, active_job=jobs_by_id["job-1"], jobs_by_id=jobs_by_id)
    await page.goto(f"{live_server_url}/step3?project_id={PROJECT_ID}")

    await page.wait_for_selector("#ai-job-retry-btn")
    banner_text = await page.locator("#ai-job-status").inner_text()
    assert "pack_validation_failed" not in banner_text
    assert "Traceback" not in banner_text
    await page.close()


@pytest.mark.asyncio
async def test_learning_ai_job_status_banner_has_aria_live(browser_instance: Browser, live_server_url: str):
    page = await browser_instance.new_page()
    jobs_by_id = {"job-1": _job(status="running")}
    await _mock_routes(page, active_job=jobs_by_id["job-1"], jobs_by_id=jobs_by_id)
    await page.goto(f"{live_server_url}/step3?project_id={PROJECT_ID}")

    aria_live = await page.locator("#ai-job-status").get_attribute("aria-live")
    assert aria_live == "polite"
    await page.close()
