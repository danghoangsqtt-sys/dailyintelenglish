"""Browser coverage for Task 2.4's resizable Script workspace and inspector actions."""

import json
import socket
import threading
import time
from typing import AsyncGenerator

import pytest
import uvicorn
from playwright.async_api import Browser, Page, async_playwright

from app.main import app

PROJECT_ID = "script-shell-project"
PROJECT = {
    "id": PROJECT_ID,
    "name": "Shell Test",
    "status": "script_generated",
    "topic": "Testing the new workspace",
    "cefr_level": "B1",
    "genre": "interview",
    "speakers": [
        {"id": "speaker-a", "name": "Alex", "gender": "male", "accent": "american"},
        {"id": "speaker-b", "name": "Sam", "gender": "female", "accent": "american"},
    ],
}
LINES = [
    {
        "id": "line-1",
        "speaker_id": "speaker-a",
        "text": "How has remote work changed your team this year?",
        "language_notes": {"collocations": ["remote work"], "idioms": [], "grammar_point": "Present perfect"},
    },
    {
        "id": "line-2",
        "speaker_id": "speaker-b",
        "text": "It has made our planning much more deliberate.",
        "language_notes": {"collocations": ["made planning"], "idioms": ["pick up the slack"], "grammar_point": "Present perfect"},
    },
]


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


def _envelope(data, error=None) -> str:
    return json.dumps({"success": error is None, "data": data, "error": error, "meta": {}})


async def _mock_script_routes(page: Page, preview_status: int = 200, preview_calls: list[str] | None = None) -> None:
    async def handle(route):
        url, method = route.request.url, route.request.method
        if url.endswith(f"/api/projects/{PROJECT_ID}") and method == "GET":
            await route.fulfill(status=200, content_type="application/json", body=_envelope(PROJECT))
        elif url.endswith(f"/api/projects/{PROJECT_ID}/script") and method == "GET":
            await route.fulfill(status=200, content_type="application/json", body=_envelope(LINES))
        elif url.endswith("/tts/preview") and method == "POST":
            if preview_calls is not None:
                preview_calls.append(route.request.post_data or "")
            if preview_status == 200:
                await route.fulfill(status=200, content_type="application/json", body=_envelope({"engine_used": "edge_tts"}))
            else:
                await route.fulfill(status=500, content_type="application/json", body=_envelope(None, "Provider secret detail"))
        elif "/tts/cache/" in url and method == "GET":
            await route.fulfill(status=200, content_type="audio/mpeg", body=b"")
        else:
            await route.continue_()

    await page.route("**/api/**", handle)


@pytest.mark.asyncio
async def test_script_shell_resizes_collapses_selects_and_keeps_inline_edit(
    browser_instance: Browser, live_server_url: str
):
    page = await browser_instance.new_page(viewport={"width": 1440, "height": 900})
    await _mock_script_routes(page)
    await page.goto(f"{live_server_url}/step2?project_id={PROJECT_ID}")
    await page.wait_for_selector("[data-line-id='line-1']")

    assert await page.locator("#script-inspector").text_content() is not None
    assert "Line 1" in await page.locator("#script-inspector").text_content()
    before = await page.locator("#pane-sidebar").bounding_box()
    handle = await page.locator("#resizer-left").bounding_box()
    assert before and handle
    await page.mouse.move(handle["x"] + 2, handle["y"] + 30)
    await page.mouse.down()
    await page.mouse.move(handle["x"] + 122, handle["y"] + 30)
    await page.mouse.up()
    after = await page.locator("#pane-sidebar").bounding_box()
    assert after and after["width"] > before["width"] + 80

    inspector_before = await page.locator("#pane-inspector").bounding_box()
    right_handle = await page.locator("#resizer-right").bounding_box()
    assert inspector_before and right_handle
    await page.mouse.move(right_handle["x"] + 2, right_handle["y"] + 30)
    await page.mouse.down()
    await page.mouse.move(right_handle["x"] - 82, right_handle["y"] + 30)
    await page.mouse.up()
    inspector_after = await page.locator("#pane-inspector").bounding_box()
    assert inspector_after and inspector_after["width"] > inspector_before["width"] + 70

    timeline_before = await page.locator("#pane-timeline").bounding_box()
    top_handle = await page.locator("#resizer-top").bounding_box()
    assert timeline_before and top_handle
    await page.mouse.move(top_handle["x"] + 200, top_handle["y"] + 2)
    await page.mouse.down()
    await page.mouse.move(top_handle["x"] + 200, top_handle["y"] - 72)
    await page.mouse.up()
    timeline_after = await page.locator("#pane-timeline").bounding_box()
    assert timeline_after and timeline_after["height"] > timeline_before["height"] + 60

    await page.click("#sidebar-collapse-btn")
    assert await page.locator("#pane-sidebar").evaluate("element => element.classList.contains('collapsed')")
    assert await page.locator("#sidebar-collapse-btn").get_attribute("aria-expanded") == "false"
    await page.click("#sidebar-collapse-btn")
    await page.locator("#resizer-left").focus()
    await page.keyboard.press("ArrowRight")

    await page.click("[data-line-id='line-2']")
    assert "Line 2" in await page.locator("#script-inspector").text_content()
    assert await page.locator("#script-timeline [data-line-id='line-2']").evaluate(
        "element => element.classList.contains('active')"
    )
    await page.locator("[data-line-id='line-2'] .line-text").click()
    assert await page.locator("[data-line-id='line-2'] textarea").count() == 1
    await page.close()


@pytest.mark.asyncio
async def test_script_inspector_listen_calls_existing_preview_endpoint_and_exposes_audio(
    browser_instance: Browser, live_server_url: str
):
    page = await browser_instance.new_page()
    preview_calls: list[str] = []
    await _mock_script_routes(page, preview_calls=preview_calls)
    await page.goto(f"{live_server_url}/step2?project_id={PROJECT_ID}")
    await page.wait_for_selector("[data-inspector-action='listen']")
    await page.click("[data-inspector-action='listen']")
    await page.wait_for_function("document.querySelector('#inspector-audio')?.src.includes('/tts/cache/line-1.mp3')")

    assert len(preview_calls) == 1
    assert json.loads(preview_calls[0]) == {"line_id": "line-1"}
    assert await page.locator("#inspector-audio").is_hidden() is False
    await page.close()


@pytest.mark.asyncio
async def test_script_inspector_listen_failure_shows_friendly_error(browser_instance: Browser, live_server_url: str):
    page = await browser_instance.new_page()
    await _mock_script_routes(page, preview_status=500)
    await page.goto(f"{live_server_url}/step2?project_id={PROJECT_ID}")
    await page.wait_for_selector("[data-inspector-action='listen']")
    await page.click("[data-inspector-action='listen']")
    await page.wait_for_selector("#error-banner:not([hidden])")

    banner = await page.locator("#error-banner").text_content()
    assert "couldn't synthesize" in banner.lower()
    assert "Provider secret detail" not in banner
    assert "Listen" in await page.locator("[data-inspector-action='listen']").text_content()
    await page.close()
