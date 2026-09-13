"""Playwright E2E coverage for the Step 7 YouTube Package UI (Task 1.9, Sub-task 1.9a)."""

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
    "id": "yt-proj-e2e",
    "name": "YouTube E2E Test Episode",
    "status": "script_generated",
    "topic": "Remote work culture",
    "cefr_level": "B1",
    "genre": "interview",
}

PACKAGE = {
    "id": "pkg-1",
    "project_id": PROJECT["id"],
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


async def _mock_project_and_package(page, package_response, *, video_ready=False, thumbnail_ready=False) -> None:
    async def handle_routes(route):
        url = route.request.url
        method = route.request.method
        if url.endswith(f"/api/projects/{PROJECT['id']}/video/status") and method == "GET":
            if video_ready:
                await route.fulfill(
                    status=200,
                    content_type="application/json",
                    body=json.dumps({"success": True, "data": {"status": "complete"}, "error": None, "meta": {}}),
                )
            else:
                await route.fulfill(
                    status=404,
                    content_type="application/json",
                    body=json.dumps({"success": False, "data": None, "error": "no video", "meta": {}}),
                )
        elif url.endswith(f"/api/projects/{PROJECT['id']}/thumbnails") and method == "GET":
            thumbnails = [{"id": "t1", "is_selected": thumbnail_ready}] if thumbnail_ready else []
            await route.fulfill(
                status=200,
                content_type="application/json",
                body=json.dumps({"success": True, "data": thumbnails, "error": None, "meta": {}}),
            )
        elif url.endswith(f"/api/projects/{PROJECT['id']}/youtube/generate") and method == "POST":
            await route.fulfill(
                status=200,
                content_type="application/json",
                body=json.dumps({"success": True, "data": PACKAGE, "error": None, "meta": {}}),
            )
        elif url.endswith(f"/api/projects/{PROJECT['id']}/youtube") and method == "GET":
            await route.fulfill(
                status=200,
                content_type="application/json",
                body=json.dumps({"success": True, "data": package_response, "error": None, "meta": {}}),
            )
        elif url.endswith(f"/api/projects/{PROJECT['id']}") and method == "GET":
            await route.fulfill(
                status=200,
                content_type="application/json",
                body=json.dumps({"success": True, "data": PROJECT, "error": None, "meta": {}}),
            )
        else:
            await route.continue_()

    await page.route("**/api/projects/**", handle_routes)


@pytest.mark.asyncio
async def test_generate_panel_shown_before_any_package_exists(browser_instance: Browser, live_server_url: str):
    page = await browser_instance.new_page()
    await _mock_project_and_package(page, None)

    await page.goto(f"{live_server_url}/step7?project_id={PROJECT['id']}")

    await page.wait_for_selector("#generate-panel:not([hidden])")
    assert await page.locator("#content-wrap").is_hidden()
    await page.close()


@pytest.mark.asyncio
async def test_generate_renders_titles_description_tags_and_estimated_chapters(
    browser_instance: Browser, live_server_url: str
):
    page = await browser_instance.new_page()
    await _mock_project_and_package(page, None)
    await page.goto(f"{live_server_url}/step7?project_id={PROJECT['id']}")
    await page.wait_for_selector("#generate-panel:not([hidden])")

    await page.click("#generate-btn")

    await page.wait_for_selector("#content-wrap:not([hidden])")
    assert await page.locator("#title-text-click_worthy").text_content() == PACKAGE["titles"][0]["text"]
    assert await page.locator("#title-text-educational").text_content() == PACKAGE["titles"][1]["text"]
    assert await page.locator("#title-text-seo").text_content() == PACKAGE["titles"][2]["text"]
    assert await page.locator("#description-text").text_content() == PACKAGE["description"]
    assert "Estimated from script length" in await page.locator("#chapters-estimate-note").text_content()
    chapters_text = await page.locator("#chapters-text").text_content()
    assert "00:00 Introduction" in chapters_text
    tag_chips = page.locator(".tag-chip")
    assert await tag_chips.count() == len(PACKAGE["tags"])
    await page.close()


@pytest.mark.asyncio
async def test_existing_package_loads_directly_without_generate_click(
    browser_instance: Browser, live_server_url: str
):
    page = await browser_instance.new_page()
    await _mock_project_and_package(page, PACKAGE)

    await page.goto(f"{live_server_url}/step7?project_id={PROJECT['id']}")

    await page.wait_for_selector("#content-wrap:not([hidden])")
    assert await page.locator("#generate-panel").is_hidden()
    assert await page.locator("#description-text").text_content() == PACKAGE["description"]
    await page.close()


@pytest.mark.asyncio
async def test_regenerate_requires_confirmation_and_can_be_cancelled(
    browser_instance: Browser, live_server_url: str
):
    page = await browser_instance.new_page()
    await _mock_project_and_package(page, PACKAGE)
    generate_calls = 0

    async def count_generate(route):
        nonlocal generate_calls
        generate_calls += 1
        await route.continue_()

    await page.route(f"**/api/projects/{PROJECT['id']}/youtube/generate", count_generate)
    await page.goto(f"{live_server_url}/step7?project_id={PROJECT['id']}")
    await page.wait_for_selector("#content-wrap:not([hidden])")

    page.once("dialog", lambda dialog: dialog.dismiss())
    await page.click("#regenerate-btn")
    await page.wait_for_timeout(200)
    assert generate_calls == 0

    page.once("dialog", lambda dialog: dialog.accept())
    await page.click("#regenerate-btn")
    await page.wait_for_function(
        "document.getElementById('description-text').textContent.length > 0"
    )
    assert generate_calls == 1
    await page.close()


@pytest.mark.asyncio
async def test_copy_button_copies_description_to_clipboard(browser_instance: Browser, live_server_url: str):
    page = await browser_instance.new_page()
    context = page.context
    await context.grant_permissions(["clipboard-read", "clipboard-write"])
    await _mock_project_and_package(page, PACKAGE)
    await page.goto(f"{live_server_url}/step7?project_id={PROJECT['id']}")
    await page.wait_for_selector("#content-wrap:not([hidden])")

    await page.click("button[data-copy-target='description-text']")

    clipboard_text = await page.evaluate("navigator.clipboard.readText()")
    assert clipboard_text == PACKAGE["description"]
    await page.close()


@pytest.mark.asyncio
async def test_generate_failure_shows_friendly_error_only(browser_instance: Browser, live_server_url: str):
    page = await browser_instance.new_page()

    async def handle_routes(route):
        url = route.request.url
        method = route.request.method
        if url.endswith(f"/api/projects/{PROJECT['id']}/youtube/generate") and method == "POST":
            await route.fulfill(
                status=502,
                content_type="application/json",
                body=json.dumps(
                    {"success": False, "data": None, "error": "Gemini API returned HTTP 429 after 4 attempt(s)", "meta": {}}
                ),
            )
        elif url.endswith(f"/api/projects/{PROJECT['id']}/youtube") and method == "GET":
            await route.fulfill(
                status=200,
                content_type="application/json",
                body=json.dumps({"success": True, "data": None, "error": None, "meta": {}}),
            )
        elif url.endswith(f"/api/projects/{PROJECT['id']}") and method == "GET":
            await route.fulfill(
                status=200,
                content_type="application/json",
                body=json.dumps({"success": True, "data": PROJECT, "error": None, "meta": {}}),
            )
        else:
            await route.continue_()

    await page.route("**/api/projects/**", handle_routes)
    await page.goto(f"{live_server_url}/step7?project_id={PROJECT['id']}")
    await page.wait_for_selector("#generate-panel:not([hidden])")

    await page.click("#generate-btn")

    await page.wait_for_selector("#error-banner:not([hidden])")
    banner_text = await page.locator("#error-banner").text_content()
    assert "couldn't generate" in banner_text.lower()
    assert "429" not in banner_text
    await page.close()


@pytest.mark.asyncio
async def test_export_link_disabled_when_video_and_thumbnail_not_ready(browser_instance: Browser, live_server_url: str):
    page = await browser_instance.new_page()
    await _mock_project_and_package(page, PACKAGE, video_ready=False, thumbnail_ready=False)

    await page.goto(f"{live_server_url}/step7?project_id={PROJECT['id']}")
    await page.wait_for_selector("#content-wrap:not([hidden])")

    assert await page.locator("#export-zip-link").get_attribute("aria-disabled") == "true"
    status_text = await page.locator("#export-status-note").text_content()
    assert "video" in status_text.lower()
    assert "thumbnail" in status_text.lower()
    await page.close()


@pytest.mark.asyncio
async def test_export_link_enabled_and_chapters_marked_measured_when_ready(
    browser_instance: Browser, live_server_url: str
):
    page = await browser_instance.new_page()
    measured_package = {**PACKAGE, "chapters_estimated": False}
    await _mock_project_and_package(page, measured_package, video_ready=True, thumbnail_ready=True)

    await page.goto(f"{live_server_url}/step7?project_id={PROJECT['id']}")
    await page.wait_for_selector("#content-wrap:not([hidden])")

    assert await page.locator("#export-zip-link").get_attribute("aria-disabled") == "false"
    href = await page.locator("#export-zip-link").get_attribute("href")
    assert href.endswith(f"/api/projects/{PROJECT['id']}/youtube/export")
    note_text = await page.locator("#chapters-estimate-note").text_content()
    assert "Measured" in note_text
    await page.close()
