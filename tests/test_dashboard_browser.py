"""Headless browser E2E tests for the Dashboard page (Task 1.2 remaining acceptance criterion).

Tests:
1. Listing: projects render as cards with correct status badges.
2. Filtering: status filter buttons narrow the visible cards.
3. Search: search box narrows cards by name.
4. Empty state: shown when there are no projects.
5. New Project button navigates to /step1.
6. Continue button navigates to /step2?project_id=... for a draft project.
7. Delete button (after confirming the browser dialog) removes the card without reload.
"""

import json
import socket
import threading
import time
from typing import AsyncGenerator

import pytest
import uvicorn
from playwright.async_api import async_playwright, Browser

from app.main import app

MOCK_PROJECTS = [
    {
        "id": "proj-draft-1",
        "name": "Healthcare AI Draft",
        "status": "draft",
        "cefr_level": "B2",
        "genre": "interview",
        "created_at": "2026-09-11T00:00:00Z",
    },
    {
        "id": "proj-script-1",
        "name": "Climate Change Update",
        "status": "script_generated",
        "cefr_level": "C1",
        "genre": "news",
        "created_at": "2026-09-10T00:00:00Z",
    },
    {
        "id": "proj-complete-1",
        "name": "Space Exploration Recap",
        "status": "complete",
        "cefr_level": "B1",
        "genre": "documentary",
        "created_at": "2026-09-09T00:00:00Z",
    },
]


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


async def _mock_list_projects(page, projects: list[dict]) -> None:
    async def handle_routes(route):
        url = route.request.url
        method = route.request.method
        if url.endswith("/api/projects") and method == "GET":
            await route.fulfill(
                status=200,
                content_type="application/json",
                body=json.dumps({"success": True, "data": projects}),
            )
        else:
            await route.continue_()

    await page.route("**/api/projects", handle_routes)


@pytest.mark.asyncio
async def test_dashboard_lists_projects_with_status_badges(browser_instance: Browser, live_server_url: str):
    page = await browser_instance.new_page()
    await _mock_list_projects(page, MOCK_PROJECTS)
    await page.goto(f"{live_server_url}/")

    await page.wait_for_selector(".project-card")
    cards = page.locator(".project-card")
    assert await cards.count() == 3

    draft_card = page.locator("[data-id='proj-draft-1']")
    assert "Draft" in await draft_card.locator(".badge-status-draft").text_content()

    script_card = page.locator("[data-id='proj-script-1']")
    assert "Script Ready" in await script_card.locator(".badge-status-script_generated").text_content()

    assert await page.locator("#empty-state").is_hidden()
    await page.close()


@pytest.mark.asyncio
async def test_dashboard_filter_narrows_visible_cards(browser_instance: Browser, live_server_url: str):
    page = await browser_instance.new_page()
    await _mock_list_projects(page, MOCK_PROJECTS)
    await page.goto(f"{live_server_url}/")

    await page.wait_for_selector(".project-card")
    await page.click("[data-filter='draft']")

    cards = page.locator(".project-card")
    assert await cards.count() == 1
    assert await cards.first.get_attribute("data-id") == "proj-draft-1"
    assert await page.locator("#empty-state").is_hidden()
    await page.close()


@pytest.mark.asyncio
async def test_dashboard_search_narrows_visible_cards(browser_instance: Browser, live_server_url: str):
    page = await browser_instance.new_page()
    await _mock_list_projects(page, MOCK_PROJECTS)
    await page.goto(f"{live_server_url}/")

    await page.wait_for_selector(".project-card")
    await page.fill("#search-input", "climate")

    cards = page.locator(".project-card")
    assert await cards.count() == 1
    assert await cards.first.get_attribute("data-id") == "proj-script-1"
    await page.close()


@pytest.mark.asyncio
async def test_dashboard_empty_state_shown_when_no_projects(browser_instance: Browser, live_server_url: str):
    page = await browser_instance.new_page()
    await _mock_list_projects(page, [])
    await page.goto(f"{live_server_url}/")

    await page.wait_for_selector("#empty-state:not([hidden])")
    assert await page.locator(".project-card").count() == 0
    empty_text = await page.text_content("#empty-state")
    assert "No projects yet" in empty_text
    await page.close()


@pytest.mark.asyncio
async def test_dashboard_new_project_button_navigates_to_step1(browser_instance: Browser, live_server_url: str):
    page = await browser_instance.new_page()
    await _mock_list_projects(page, MOCK_PROJECTS)
    await page.goto(f"{live_server_url}/")

    await page.wait_for_selector(".project-card")
    await page.click("#new-project-btn")
    await page.wait_for_url("**/step1")
    assert "/step1" in page.url
    await page.close()


@pytest.mark.asyncio
async def test_dashboard_continue_button_navigates_to_step2_for_draft(browser_instance: Browser, live_server_url: str):
    page = await browser_instance.new_page()
    await _mock_list_projects(page, MOCK_PROJECTS)
    await page.goto(f"{live_server_url}/")

    await page.wait_for_selector("[data-id='proj-draft-1']")
    await page.click("[data-id='proj-draft-1'] [data-action='continue']")
    await page.wait_for_url("**/step2?project_id=proj-draft-1*")
    assert "/step2" in page.url
    assert "project_id=proj-draft-1" in page.url
    await page.close()


@pytest.mark.asyncio
async def test_dashboard_delete_removes_card_after_confirm(browser_instance: Browser, live_server_url: str):
    page = await browser_instance.new_page()
    await _mock_list_projects(page, MOCK_PROJECTS)

    async def handle_delete(route):
        if route.request.method == "DELETE":
            await route.fulfill(status=200, content_type="application/json", body=json.dumps({"success": True, "data": None}))
        else:
            await route.continue_()

    await page.route("**/api/projects/proj-complete-1", handle_delete)
    page.on("dialog", lambda dialog: dialog.accept())

    await page.goto(f"{live_server_url}/")
    await page.wait_for_selector("[data-id='proj-complete-1']")
    await page.click("[data-id='proj-complete-1'] [data-action='delete']")

    await page.wait_for_selector("[data-id='proj-complete-1']", state="detached")
    assert await page.locator(".project-card").count() == 2
    await page.close()
