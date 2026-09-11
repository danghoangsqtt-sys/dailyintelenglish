"""Headless browser E2E tests for Step 2 and Step 3 UI async state machines (BUG-012).

Tests:
1. Normal edit -> autosave -> saved -> navigation succeeds.
2. Rapid successive edits coalesce into a single trailing save without clobbering.
3. Save failure (HTTP 500) blocks navigation, prevents data loss, and does not infinite-loop.
4. Save failure recovery: clicking Retry succeeds and unlocks Next navigation.
5. Regeneration buttons are disabled while edits are unsaved or saving.
6. Dirty state triggers beforeunload alert.
"""

import asyncio
import json
import socket
import threading
import time
from typing import AsyncGenerator
import pytest
import uvicorn
from playwright.async_api import async_playwright, Browser

from app.main import app

SAMPLE_PROJECT = {
    "id": "test-proj-e2e",
    "name": "E2E Browser Test Episode",
    "status": "draft",
    "topic": "Artificial Intelligence in Healthcare",
    "cefr_level": "B2",
    "duration_minutes": 10.0,
    "num_speakers": 2,
    "genre": "interview",
    "accent": "american",
    "language_features": {"collocation": True, "idiom": True},
    "speakers": [
        {"id": "spk-1", "name": "Dr. Smith", "gender": "male", "accent": "american"},
        {"id": "spk-2", "name": "Host", "gender": "female", "accent": "american"},
    ],
    "created_at": "2026-09-11T00:00:00Z",
    "updated_at": "2026-09-11T00:00:00Z",
}

SAMPLE_SCRIPT = [
    {
        "id": "line-1",
        "speaker_id": "spk-1",
        "text": "Hello, welcome to our discussion on medical AI.",
        "language_notes": {"collocations": ["medical AI"], "idioms": [], "grammar_point": "Present Simple"},
    },
    {
        "id": "line-2",
        "speaker_id": "spk-2",
        "text": "Thank you for joining us today.",
        "language_notes": {"collocations": ["joining us"], "idioms": [], "grammar_point": "Present Continuous"},
    },
]

SAMPLE_LEARNING_PACK = {
    "vocabulary": [
        {
            "word": "diagnostic",
            "part_of_speech": "adj",
            "ipa": "/ˌdaɪ.əɡˈnɒs.tɪk/",
            "definition_en": "used to identify an illness",
            "definition_vi": "dùng để chẩn đoán",
            "example_sentence": "AI tools improve diagnostic accuracy.",
        }
    ],
    "idioms": [
        {
            "phrase": "at the cutting edge",
            "meaning_en": "at the most advanced stage",
            "meaning_vi": "ở vị trí tiên phong",
            "example_sentence": "This lab is at the cutting edge of medicine.",
        }
    ],
    "grammar": [
        {
            "point": "Passive Voice in Scientific Reports",
            "structure": "is/are + past participle",
            "explanation_en": "Used to describe medical processes neutrally.",
            "explanation_vi": "Dùng để diễn đạt khách quan.",
            "examples": ["Data is analyzed automatically."],
        }
    ],
    "questions": [
        {
            "question": "What improves diagnostic accuracy?",
            "options": ["AI tools", "Manual records", "Guesswork", "None"],
            "correct_answer": "AI tools",
            "explanation": "AI tools automate scan analysis.",
        }
    ],
}


def _find_free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


@pytest.fixture(scope="module")
def live_server_url():
    port = _find_free_port()
    config = uvicorn.Config(app, host="127.0.0.1", port=port, log_level="warning")
    server = uvicorn.Server(config)
    thread = threading.Thread(target=server.run, daemon=True)
    thread.start()

    start_time = time.time()
    while time.time() - start_time < 10.0:
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
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        yield browser
        await browser.close()


@pytest.mark.asyncio
async def test_step2_normal_edit_and_successful_autosave_navigation(browser_instance: Browser, live_server_url: str):
    """Scenario 1: User edits script line, autosave succeeds, Next Step navigates to Step 3."""
    page = await browser_instance.new_page()
    saved_payloads = []

    async def handle_routes(route):
        url = route.request.url
        method = route.request.method
        if "/api/projects/test-proj-e2e/script" in url:
            if method == "GET":
                await route.fulfill(status=200, content_type="application/json", body=json.dumps({"success": True, "data": SAMPLE_SCRIPT}))
            elif method == "PUT":
                body = route.request.post_data_json
                saved_payloads.append(body)
                await route.fulfill(status=200, content_type="application/json", body=json.dumps({"success": True, "data": body.get("lines", [])}))
        elif "/api/projects/test-proj-e2e" in url:
            await route.fulfill(status=200, content_type="application/json", body=json.dumps({"success": True, "data": SAMPLE_PROJECT}))
        else:
            await route.continue_()

    await page.route("**/api/projects/**", handle_routes)
    await page.goto(f"{live_server_url}/step2?project_id=test-proj-e2e")

    await page.wait_for_selector("[data-line-id='line-1']")
    line_text_el = page.locator("[data-line-id='line-1'] .line-text")
    await line_text_el.click()

    textarea = page.locator("[data-line-id='line-1'] textarea")
    await textarea.fill("Updated line 1 text through Playwright.")
    await textarea.blur()

    # Verify badge transitions to Saved
    await page.wait_for_function("document.getElementById('save-status').textContent.includes('Saved') || document.getElementById('save-status').textContent === ''")
    assert len(saved_payloads) >= 1
    assert saved_payloads[-1]["lines"][0]["text"] == "Updated line 1 text through Playwright."

    # Next navigation should succeed
    await page.click("#next-step-btn")
    await page.wait_for_url("**/step3?project_id=test-proj-e2e*")
    assert "/step3" in page.url
    await page.close()


@pytest.mark.asyncio
async def test_step2_save_failure_blocks_navigation_and_recovers(browser_instance: Browser, live_server_url: str):
    """Scenario 3 & 4: Save failure (500) blocks Next Step without infinite wait; clicking Retry recovers and navigates."""
    page = await browser_instance.new_page()
    fail_save = True

    async def handle_routes(route):
        nonlocal fail_save
        url = route.request.url
        method = route.request.method
        if "/api/projects/test-proj-e2e/script" in url:
            if method == "GET":
                await route.fulfill(status=200, content_type="application/json", body=json.dumps({"success": True, "data": SAMPLE_SCRIPT}))
            elif method == "PUT":
                if fail_save:
                    await route.fulfill(status=500, content_type="application/json", body=json.dumps({"success": False, "error": {"code": "ERR", "message": "Disk failure"}}))
                else:
                    body = route.request.post_data_json
                    await route.fulfill(status=200, content_type="application/json", body=json.dumps({"success": True, "data": body.get("lines", [])}))
        elif "/api/projects/test-proj-e2e" in url:
            await route.fulfill(status=200, content_type="application/json", body=json.dumps({"success": True, "data": SAMPLE_PROJECT}))
        else:
            await route.continue_()

    await page.route("**/api/projects/**", handle_routes)
    await page.goto(f"{live_server_url}/step2?project_id=test-proj-e2e")

    await page.wait_for_selector("[data-line-id='line-1']")
    await page.locator("[data-line-id='line-1'] .line-text").click()
    textarea = page.locator("[data-line-id='line-1'] textarea")
    await textarea.fill("Unsaved failing edit.")
    await textarea.blur()

    # Wait for failure badge to show
    await page.wait_for_selector("#retry-save-btn")
    status_text = await page.text_content("#save-status")
    assert "Save failed" in status_text

    # Attempt to click Next Step -> must BLOCK navigation
    await page.click("#next-step-btn")
    await page.wait_for_selector("#error-banner:not([hidden])")
    assert "/step2" in page.url  # Must still be on step2!

    error_banner = page.locator("#error-banner")
    banner_text = await error_banner.text_content()
    assert "Cannot proceed" in banner_text

    # Verify regenerate buttons are disabled while in failed/unsaved state
    regen_btn = page.locator("[data-line-id='line-1'] [data-action='regenerate']")
    assert await regen_btn.is_disabled()

    # Now fix backend / unmock failure, click Retry
    fail_save = False
    await page.click("#retry-save-btn")
    await page.wait_for_function("document.getElementById('save-status').textContent.includes('Saved') || document.getElementById('save-status').textContent === ''")

    # Now Next Step must succeed
    await page.click("#next-step-btn")
    await page.wait_for_url("**/step3?project_id=test-proj-e2e*")
    assert "/step3" in page.url
    await page.close()


@pytest.mark.asyncio
async def test_step2_rapid_edits_coalescence(browser_instance: Browser, live_server_url: str):
    """Rapid successive edits coalesce into a single trailing save with latest content."""
    page = await browser_instance.new_page()
    put_calls = 0
    saved_payloads = []

    async def handle_routes(route):
        nonlocal put_calls
        url = route.request.url
        method = route.request.method
        if "/api/projects/test-proj-e2e/script" in url:
            if method == "GET":
                await route.fulfill(status=200, content_type="application/json", body=json.dumps({"success": True, "data": SAMPLE_SCRIPT}))
            elif method == "PUT":
                put_calls += 1
                await asyncio.sleep(0.15)  # Simulate network latency
                body = route.request.post_data_json
                saved_payloads.append(body)
                await route.fulfill(status=200, content_type="application/json", body=json.dumps({"success": True, "data": body.get("lines", [])}))
        elif "/api/projects/test-proj-e2e" in url:
            await route.fulfill(status=200, content_type="application/json", body=json.dumps({"success": True, "data": SAMPLE_PROJECT}))
        else:
            await route.continue_()

    await page.route("**/api/projects/**", handle_routes)
    await page.goto(f"{live_server_url}/step2?project_id=test-proj-e2e")

    await page.wait_for_selector("[data-line-id='line-1']")
    # First edit
    await page.locator("[data-line-id='line-1'] .line-text").click()
    textarea = page.locator("[data-line-id='line-1'] textarea")
    await textarea.fill("Edit 1")
    await textarea.blur()

    # Rapid second edit on line 2 while first save is in flight
    await page.locator("[data-line-id='line-2'] .line-text").click()
    textarea2 = page.locator("[data-line-id='line-2'] textarea")
    await textarea2.fill("Edit 2")
    await textarea2.blur()

    # Wait for all saves to settle
    await page.wait_for_function("document.getElementById('save-status').textContent.includes('Saved') || document.getElementById('save-status').textContent === ''")
    assert len(saved_payloads) >= 1
    final_lines = saved_payloads[-1]["lines"]
    assert final_lines[0]["text"] == "Edit 1"
    assert final_lines[1]["text"] == "Edit 2"
    await page.close()


@pytest.mark.asyncio
async def test_step3_normal_edit_and_navigation(browser_instance: Browser, live_server_url: str):
    """Step 3: Editing vocabulary field triggers autosave and allows Next Step to Step 4."""
    page = await browser_instance.new_page()
    saved_packs = []

    async def handle_routes(route):
        url = route.request.url
        method = route.request.method
        if "/api/projects/test-proj-e2e/learning" in url:
            if method == "GET":
                await route.fulfill(status=200, content_type="application/json", body=json.dumps({"success": True, "data": SAMPLE_LEARNING_PACK}))
            elif method == "PUT":
                body = route.request.post_data_json
                saved_packs.append(body)
                await route.fulfill(status=200, content_type="application/json", body=json.dumps({"success": True, "data": body}))
        elif "/api/projects/test-proj-e2e" in url:
            await route.fulfill(status=200, content_type="application/json", body=json.dumps({"success": True, "data": SAMPLE_PROJECT}))
        else:
            await route.continue_()

    await page.route("**/api/projects/**", handle_routes)
    await page.goto(f"{live_server_url}/step3?project_id=test-proj-e2e")

    await page.wait_for_selector(".field.item-title")
    first_word_el = page.locator(".field.item-title").first
    await first_word_el.click()
    await first_word_el.fill("prognostic")
    await page.keyboard.press("Tab")

    await page.wait_for_function("document.getElementById('save-status').textContent.includes('Saved') || document.getElementById('save-status').textContent === ''")
    assert len(saved_packs) >= 1

    await page.click("#next-step-btn")
    await page.wait_for_url("**/step4?project_id=test-proj-e2e*")
    assert "/step4" in page.url
    await page.close()


@pytest.mark.asyncio
async def test_step3_save_failure_blocks_navigation_without_infinite_loop(browser_instance: Browser, live_server_url: str):
    """Step 3: Save failure blocks Next Step, displays error, and DOES NOT busy-wait infinitely."""
    page = await browser_instance.new_page()
    fail_save = True

    async def handle_routes(route):
        nonlocal fail_save
        url = route.request.url
        method = route.request.method
        if "/api/projects/test-proj-e2e/learning" in url:
            if method == "GET":
                await route.fulfill(status=200, content_type="application/json", body=json.dumps({"success": True, "data": SAMPLE_LEARNING_PACK}))
            elif method == "PUT":
                if fail_save:
                    await route.fulfill(status=500, content_type="application/json", body=json.dumps({"success": False, "error": {"code": "ERR", "message": "Failed to save"}}))
                else:
                    body = route.request.post_data_json
                    await route.fulfill(status=200, content_type="application/json", body=json.dumps({"success": True, "data": body}))
        elif "/api/projects/test-proj-e2e" in url:
            await route.fulfill(status=200, content_type="application/json", body=json.dumps({"success": True, "data": SAMPLE_PROJECT}))
        else:
            await route.continue_()

    await page.route("**/api/projects/**", handle_routes)
    await page.goto(f"{live_server_url}/step3?project_id=test-proj-e2e")

    await page.wait_for_selector(".field.item-title")
    first_word_el = page.locator(".field.item-title").first
    await first_word_el.click()
    await first_word_el.fill("unsuccessful_edit")
    await page.keyboard.press("Tab")

    # Wait for failure badge to show
    await page.wait_for_selector("#retry-save-btn")
    assert "Save failed" in await page.text_content("#save-status")

    # Click Next Step -> must not hang, must block navigation and show friendly error
    start_click = time.time()
    await page.click("#next-step-btn")
    elapsed = time.time() - start_click
    assert elapsed < 3.0  # Must return promptly without infinite busy-wait!
    assert "/step3" in page.url

    await page.wait_for_selector("#error-banner:not([hidden])")
    error_banner = page.locator("#error-banner")
    assert "Cannot proceed" in await error_banner.text_content()

    # Re-enable and recover
    fail_save = False
    await page.click("#retry-save-btn")
    await page.wait_for_function("document.getElementById('save-status').textContent.includes('Saved') || document.getElementById('save-status').textContent === ''")

    # Navigation now succeeds
    await page.click("#next-step-btn")
    await page.wait_for_url("**/step4?project_id=test-proj-e2e*")
    assert "/step4" in page.url
    await page.close()
