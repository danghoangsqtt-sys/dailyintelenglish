"""Playwright coverage for the shared seven-step progress and breadcrumb component."""

import json
import socket
import threading
import time
from typing import AsyncGenerator

import pytest
import uvicorn
from playwright.async_api import Browser, Page, async_playwright

from app.main import app

PROJECT_ID = "step-nav-project"
PROJECT = {
    "id": PROJECT_ID,
    "name": "Step Navigation Test",
    "status": "draft",
    "topic": "Navigation",
    "cefr_level": "B1",
    "genre": "small_talk",
    "speakers": [],
}
STEP_LABELS = ["Config", "Script", "Learning", "Audio", "Video", "Thumbnail", "YouTube"]


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


@pytest.fixture
async def browser_instance() -> AsyncGenerator[Browser, None]:
    async with async_playwright() as playwright:
        browser = await playwright.chromium.launch(headless=True)
        yield browser
        await browser.close()


def _envelope(data, error=None) -> str:
    return json.dumps({"success": error is None, "data": data, "error": error, "meta": {}})


async def _mock_page_apis(page: Page) -> None:
    async def handle_routes(route):
        url = route.request.url
        method = route.request.method

        if url.endswith(f"/api/projects/{PROJECT_ID}") and method == "GET":
            await route.fulfill(status=200, content_type="application/json", body=_envelope(PROJECT))
        elif url.endswith(f"/api/projects/{PROJECT_ID}/script") and method == "GET":
            await route.fulfill(status=200, content_type="application/json", body=_envelope([]))
        elif url.endswith(f"/api/projects/{PROJECT_ID}/learning") and method == "GET":
            await route.fulfill(status=200, content_type="application/json", body=_envelope(None))
        elif url.endswith(f"/api/projects/{PROJECT_ID}/thumbnails") and method == "GET":
            await route.fulfill(status=200, content_type="application/json", body=_envelope([]))
        elif url.endswith(f"/api/projects/{PROJECT_ID}/youtube") and method == "GET":
            await route.fulfill(status=200, content_type="application/json", body=_envelope(None))
        elif url.endswith("/api/thumbnails/templates") and method == "GET":
            await route.fulfill(status=200, content_type="application/json", body=_envelope([]))
        elif url.endswith("/audio/status") and method == "GET":
            await route.fulfill(status=404, content_type="application/json", body=_envelope(None, "No audio"))
        elif url.endswith("/video/status") and method == "GET":
            await route.fulfill(status=404, content_type="application/json", body=_envelope(None, "No video"))
        else:
            await route.fulfill(status=404, content_type="application/json", body=_envelope(None, "Not mocked"))

    await page.route("**/api/**", handle_routes)


@pytest.mark.asyncio
@pytest.mark.parametrize("current_step", range(1, 8))
async def test_each_page_renders_and_navigates_shared_step_nav(
    browser_instance: Browser, live_server_url: str, current_step: int
):
    page = await browser_instance.new_page()
    await _mock_page_apis(page)
    await page.goto(f"{live_server_url}/step{current_step}?project_id={PROJECT_ID}")
    await page.wait_for_selector("#step-nav .step-nav-pill")

    assert await page.locator("#step-nav .step-nav").get_attribute("aria-label") == "Project steps"
    assert await page.locator("#step-nav .step-nav > span").text_content() == f"Step {current_step} of 7"
    labels = await page.locator("#step-nav .step-nav-pill").evaluate_all(
        "links => links.map(link => link.lastChild.textContent)"
    )
    assert labels == STEP_LABELS
    assert await page.locator("#step-nav .step-nav-pill").count() == 7

    active = page.locator('#step-nav .step-nav-pill[aria-current="step"]')
    assert await active.count() == 1
    assert await active.get_attribute("data-step") == str(current_step)
    assert await active.evaluate("element => getComputedStyle(element).color") != await page.locator(
        "#step-nav .step-nav-pill:not(.active)"
    ).first.evaluate("element => getComputedStyle(element).color")

    if current_step in (2, 3, 4, 5, 6):
        # Steps 2-6 use the 3-panel shell — #step-nav lives inside #pane-sidebar,
        # not directly under the topbar.
        assert await page.locator("#pane-sidebar #step-nav .step-nav-workflow").count() == 1
        assert await page.locator("#step-nav .workflow-item .step-dot.active").text_content() == str(current_step)
    else:
        is_between_header_and_main = await page.locator("#step-nav").evaluate(
            "element => element.previousElementSibling?.matches('header.topbar') === true "
            "&& element.nextElementSibling?.matches('main.main') === true"
        )
        assert is_between_header_and_main

    target_step = 7 if current_step != 7 else 1
    target = page.locator(f'#step-nav .step-nav-pill[data-step="{target_step}"]')
    assert await target.get_attribute("href") == f"/step{target_step}?project_id={PROJECT_ID}"
    await target.click()
    await page.wait_for_url(f"**/step{target_step}?project_id={PROJECT_ID}")
    assert page.url.endswith(f"/step{target_step}?project_id={PROJECT_ID}")
    await page.close()


@pytest.mark.asyncio
@pytest.mark.parametrize("current_step", range(1, 8))
async def test_missing_project_id_never_creates_null_or_undefined_links(
    browser_instance: Browser, live_server_url: str, current_step: int
):
    page = await browser_instance.new_page()
    await page.goto(f"{live_server_url}/step{current_step}")
    await page.wait_for_selector("#step-nav .step-nav-pill")

    hrefs = await page.locator("#step-nav .step-nav-pill").evaluate_all(
        "links => links.map(link => link.getAttribute('href'))"
    )
    assert hrefs == [f"/step{step}" for step in range(1, 8)]
    assert all("null" not in href and "undefined" not in href for href in hrefs)
    await page.close()


@pytest.mark.asyncio
async def test_step_nav_rebuilds_from_url_after_reload(
    browser_instance: Browser, live_server_url: str
):
    page = await browser_instance.new_page()
    await _mock_page_apis(page)
    await page.goto(f"{live_server_url}/step6?project_id={PROJECT_ID}")
    await page.wait_for_selector('#step-nav .step-nav-pill[aria-current="step"]')

    await page.reload()
    await page.wait_for_selector('#step-nav .step-nav-pill[aria-current="step"]')

    assert await page.locator("#step-nav .step-nav > span").text_content() == "Step 6 of 7"
    assert (
        await page.locator('#step-nav .step-nav-pill[aria-current="step"]').get_attribute(
            "data-step"
        )
        == "6"
    )
    assert await page.locator(
        '#step-nav .step-nav-pill[data-step="2"]'
    ).get_attribute("href") == f"/step2?project_id={PROJECT_ID}"
    await page.close()
