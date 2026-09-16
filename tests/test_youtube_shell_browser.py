"""Browser coverage for Task 4.2e's YouTube Package shell."""

import json
import socket
import threading
import time
from typing import AsyncGenerator

import pytest
import uvicorn
from playwright.async_api import Browser, Page, async_playwright

from app.main import app

PROJECT_ID = "youtube-shell-project"
PROJECT = {
    "id": PROJECT_ID,
    "name": "YouTube Shell Test",
    "status": "video_generated",
    "topic": "Remote work culture",
    "cefr_level": "B1",
    "genre": "interview",
}
PACKAGE = {
    "id": "youtube-shell-package",
    "project_id": PROJECT_ID,
    "titles": [
        {"variant": "click_worthy", "text": "The Remote Work Secret Nobody Expects"},
        {"variant": "educational", "text": "Learn Remote Work English at B1"},
        {"variant": "seo", "text": "Remote Work English Podcast B1 Interview"},
    ],
    "description": "An English-learning podcast episode about remote work culture.",
    "chapters_text": "00:00 Introduction\n01:20 Working from home",
    "chapters_estimated": False,
    "tags": ["remote work", "english learning", "b1 podcast"],
    "created_at": "2026-09-16T00:00:00Z",
    "updated_at": "2026-09-16T00:00:00Z",
}


def _find_free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as listener:
        listener.bind(("127.0.0.1", 0))
        return listener.getsockname()[1]


@pytest.fixture(scope="module")
def live_server_url():
    port = _find_free_port()
    server = uvicorn.Server(
        uvicorn.Config(app, host="127.0.0.1", port=port, log_level="warning")
    )
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
    server.should_exit = True
    thread.join(timeout=10)


@pytest.fixture
async def browser_instance() -> AsyncGenerator[Browser, None]:
    async with async_playwright() as playwright:
        browser = await playwright.chromium.launch(headless=True)
        yield browser
        await browser.close()


def _envelope(data, error=None) -> str:
    return json.dumps(
        {"success": error is None, "data": data, "error": error, "meta": {}}
    )


async def _mock_youtube_routes(
    page: Page,
    *,
    package_response,
    video_ready: bool,
    thumbnail_ready: bool,
) -> None:
    async def handle(route) -> None:
        url = route.request.url
        method = route.request.method
        if url.endswith(f"/api/projects/{PROJECT_ID}/video/status") and method == "GET":
            if video_ready:
                await route.fulfill(
                    status=200,
                    content_type="application/json",
                    body=_envelope({"status": "complete"}),
                )
            else:
                await route.fulfill(
                    status=404,
                    content_type="application/json",
                    body=_envelope(None, "No video"),
                )
        elif url.endswith(f"/api/projects/{PROJECT_ID}/thumbnails") and method == "GET":
            thumbnails = (
                [{"id": "favorite-thumbnail", "is_selected": True}]
                if thumbnail_ready
                else []
            )
            await route.fulfill(
                status=200,
                content_type="application/json",
                body=_envelope(thumbnails),
            )
        elif url.endswith(f"/api/projects/{PROJECT_ID}/youtube/generate") and method == "POST":
            await route.fulfill(
                status=200,
                content_type="application/json",
                body=_envelope(PACKAGE),
            )
        elif url.endswith(f"/api/projects/{PROJECT_ID}/youtube") and method == "GET":
            await route.fulfill(
                status=200,
                content_type="application/json",
                body=_envelope(package_response),
            )
        elif url.endswith(f"/api/projects/{PROJECT_ID}") and method == "GET":
            await route.fulfill(
                status=200,
                content_type="application/json",
                body=_envelope(PROJECT),
            )
        else:
            await route.continue_()

    await page.route("**/api/projects/**", handle)


@pytest.mark.asyncio
async def test_youtube_shell_resizes_toggles_and_generate_populates_stage(
    browser_instance: Browser, live_server_url: str
) -> None:
    page = await browser_instance.new_page(viewport={"width": 1440, "height": 900})
    await _mock_youtube_routes(
        page,
        package_response=None,
        video_ready=False,
        thumbnail_ready=False,
    )
    await page.goto(f"{live_server_url}/step7?project_id={PROJECT_ID}")
    await page.wait_for_selector("#generate-panel:not([hidden])")

    assert await page.locator("#pane-sidebar .step-nav-workflow").count() == 1
    assert await page.locator("#pane-stage #generate-panel").count() == 1
    assert await page.locator("#pane-stage #content-wrap").count() == 1
    assert await page.locator("#pane-inspector #export-status-note").count() == 1
    assert await page.locator("#pane-inspector #export-zip-link").count() == 1
    assert await page.locator("#pane-timeline, #resizer-top").count() == 0
    assert "Generate the YouTube package" in await page.locator(
        "#export-status-note"
    ).text_content()

    sidebar_before = await page.locator("#pane-sidebar").bounding_box()
    left_handle = await page.locator("#resizer-left").bounding_box()
    assert sidebar_before and left_handle
    await page.mouse.move(left_handle["x"] + 2, left_handle["y"] + 30)
    await page.mouse.down()
    await page.mouse.move(left_handle["x"] + 102, left_handle["y"] + 30)
    await page.mouse.up()
    sidebar_after = await page.locator("#pane-sidebar").bounding_box()
    assert sidebar_after and sidebar_after["width"] > sidebar_before["width"] + 70

    inspector_before = await page.locator("#pane-inspector").bounding_box()
    right_handle = await page.locator("#resizer-right").bounding_box()
    assert inspector_before and right_handle
    await page.mouse.move(right_handle["x"] + 2, right_handle["y"] + 30)
    await page.mouse.down()
    await page.mouse.move(right_handle["x"] - 82, right_handle["y"] + 30)
    await page.mouse.up()
    inspector_after = await page.locator("#pane-inspector").bounding_box()
    assert inspector_after and inspector_after["width"] > inspector_before["width"] + 70

    await page.click("#sidebar-collapse-btn")
    assert await page.locator("#pane-sidebar").evaluate(
        "element => element.classList.contains('collapsed')"
    )
    assert await page.locator("#sidebar-collapse-btn").get_attribute("aria-expanded") == "false"

    await page.click("#sidebar-collapse-btn")
    assert not await page.locator("#pane-sidebar").evaluate(
        "element => element.classList.contains('collapsed')"
    )
    assert await page.locator("#sidebar-collapse-btn").get_attribute("aria-expanded") == "true"

    await page.click("#generate-btn")
    await page.wait_for_selector("#content-wrap:not([hidden])")
    assert await page.locator("#pane-stage #title-grid .title-card").count() == 3
    assert await page.locator("#pane-stage #description-text").count() == 1
    assert await page.locator("#pane-stage #chapters-text").count() == 1
    assert await page.locator("#pane-stage #tags-list .tag-chip").count() == 3
    assert await page.locator("#export-zip-link").get_attribute("aria-disabled") == "true"
    status = await page.locator("#export-status-note").text_content()
    assert "video" in status.lower()
    assert "thumbnail" in status.lower()
    await page.close()


@pytest.mark.asyncio
async def test_ready_export_stays_in_inspector_with_all_content_in_stage(
    browser_instance: Browser, live_server_url: str
) -> None:
    page = await browser_instance.new_page(viewport={"width": 1440, "height": 900})
    await _mock_youtube_routes(
        page,
        package_response=PACKAGE,
        video_ready=True,
        thumbnail_ready=True,
    )
    await page.goto(f"{live_server_url}/step7?project_id={PROJECT_ID}")
    await page.wait_for_selector("#content-wrap:not([hidden])")

    for selector in ("#title-grid", "#description-text", "#chapters-text", "#tags-list"):
        assert await page.locator(f"#pane-stage {selector}").count() == 1
    assert await page.locator("#pane-inspector #export-status-note").count() == 1
    assert "Ready" in await page.locator("#export-status-note").text_content()
    assert await page.locator("#export-zip-link").get_attribute("aria-disabled") == "false"
    assert await page.locator("#export-zip-link").get_attribute(
        "href"
    ) == f"/api/projects/{PROJECT_ID}/youtube/export"
    await page.close()
