"""Headless browser E2E tests for the Dashboard page (Task 1.2 remaining acceptance criterion).

Tests:
1. Listing: projects render as cards with correct status badges.
2. Filtering: status filter buttons narrow the visible cards.
3. Search: search box narrows cards by name.
4. Empty state: shown when there are no projects.
5. New Project button navigates to /step1.
6. Continue button navigates to the workflow step mapped from project status.
7. Delete button (after confirming the browser dialog) removes the card without reload.
8. Pagination caps the rendered DOM, navigates, resets, and clamps after deletion.
"""

import json
from typing import AsyncGenerator

import pytest
from playwright.async_api import async_playwright, Browser

from tests.conftest import live_server

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


def _pagination_projects(count: int) -> list[dict]:
    """Build an isolated large project set without changing the shared small fixture."""
    return [
        {
            "id": f"pagination-project-{index:02d}",
            "name": f"Pagination Project {index:02d}",
            "status": "draft" if index < 30 else "complete",
            "cefr_level": "B1",
            "genre": "news",
            "created_at": "2026-09-11T00:00:00Z",
        }
        for index in range(count)
    ]


@pytest.fixture(scope="module")
def live_server_url(tmp_path_factory: pytest.TempPathFactory):
    with live_server(tmp_path_factory, "dashboard") as url:
        yield url


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


@pytest.mark.parametrize(
    ("status", "expected_step"),
    [
        ("draft", 2),
        ("script_generated", 2),
        ("audio_generated", 4),
        ("video_generated", 5),
        ("complete", 7),
    ],
)
@pytest.mark.asyncio
async def test_dashboard_continue_button_navigates_to_status_step(
    browser_instance: Browser, live_server_url: str, status: str, expected_step: int
):
    project_id = f"proj-{status}"
    projects = [
        {
            "id": project_id,
            "name": f"Project {status}",
            "status": status,
            "cefr_level": "B1",
            "genre": "news",
            "created_at": "2026-09-11T00:00:00Z",
        }
    ]
    page = await browser_instance.new_page()
    await _mock_list_projects(page, projects)
    await page.goto(f"{live_server_url}/")

    await page.wait_for_selector(f"[data-id='{project_id}']")
    await page.click(f"[data-id='{project_id}'] [data-action='continue']")
    await page.wait_for_url(f"**/step{expected_step}?project_id={project_id}*")
    assert f"/step{expected_step}" in page.url
    assert f"project_id={project_id}" in page.url
    await page.close()


@pytest.mark.asyncio
async def test_dashboard_continue_unknown_status_is_noop(browser_instance: Browser, live_server_url: str):
    projects = [
        {
            "id": "proj-unknown",
            "name": "Unknown Status Project",
            "status": "future_status",
            "cefr_level": "B1",
            "genre": "news",
            "created_at": "2026-09-11T00:00:00Z",
        }
    ]
    page = await browser_instance.new_page()
    await _mock_list_projects(page, projects)
    await page.goto(f"{live_server_url}/")

    await page.wait_for_selector("[data-id='proj-unknown']")
    original_url = page.url
    await page.click("[data-id='proj-unknown'] [data-action='continue']")
    await page.wait_for_timeout(100)
    assert page.url == original_url
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


@pytest.mark.asyncio
async def test_dashboard_load_failure_shows_error_banner_not_misleading_empty_state(
    browser_instance: Browser, live_server_url: str
):
    """A failed load must never look identical to a genuinely empty account (Task 2.3c)."""
    page = await browser_instance.new_page()

    async def handle_routes(route):
        if route.request.url.endswith("/api/projects") and route.request.method == "GET":
            await route.fulfill(
                status=500,
                content_type="application/json",
                body=json.dumps({"success": False, "data": None, "error": "Database connection lost"}),
            )
        else:
            await route.continue_()

    await page.route("**/api/projects", handle_routes)
    await page.goto(f"{live_server_url}/")

    await page.wait_for_selector("#error-banner:not([hidden])")
    banner_text = await page.text_content("#error-banner")
    assert "couldn't load" in banner_text.lower()
    assert "Database connection lost" not in banner_text
    assert await page.locator("#empty-state:not([hidden])").count() == 0
    assert await page.locator(".project-card").count() == 0
    await page.close()


@pytest.mark.asyncio
async def test_dashboard_delete_failure_shows_error_banner_not_native_alert(
    browser_instance: Browser, live_server_url: str
):
    """The delete failure path must use the friendly banner, never a raw alert() (Task 2.3c)."""
    page = await browser_instance.new_page()
    await _mock_list_projects(page, MOCK_PROJECTS)

    async def handle_delete(route):
        if route.request.method == "DELETE":
            await route.fulfill(
                status=500,
                content_type="application/json",
                body=json.dumps({"success": False, "data": None, "error": "Disk write failed"}),
            )
        else:
            await route.continue_()

    await page.route("**/api/projects/proj-complete-1", handle_delete)
    dialog_messages = []

    def handle_dialog(dialog):
        dialog_messages.append(dialog.message)
        return dialog.accept()

    page.on("dialog", handle_dialog)

    await page.goto(f"{live_server_url}/")
    await page.wait_for_selector("[data-id='proj-complete-1']")
    await page.click("[data-id='proj-complete-1'] [data-action='delete']")

    await page.wait_for_selector("#error-banner:not([hidden])")
    banner_text = await page.text_content("#error-banner")
    assert "couldn't delete" in banner_text.lower()
    assert "Disk write failed" not in banner_text
    # Only the confirm() dialog should have fired — never a second alert() with raw error text.
    assert dialog_messages == ["Delete this project? This cannot be undone."]
    assert await page.locator("[data-id='proj-complete-1']").count() == 1
    await page.close()


@pytest.mark.asyncio
async def test_dashboard_pagination_caps_dom_navigates_and_resets_on_reload(
    browser_instance: Browser, live_server_url: str
):
    projects = _pagination_projects(50)
    page = await browser_instance.new_page()
    await _mock_list_projects(page, projects)
    await page.goto(f"{live_server_url}/")

    await page.wait_for_selector("#project-pagination:not([hidden])")
    cards = page.locator(".project-card")
    assert await cards.count() == 24
    assert await cards.first.get_attribute("data-id") == "pagination-project-00"
    assert await cards.last.get_attribute("data-id") == "pagination-project-23"
    assert await page.locator("#page-indicator").text_content() == "Page 1 of 3"
    assert await page.locator("#previous-page-btn").is_disabled()
    assert not await page.locator("#next-page-btn").is_disabled()

    await page.click("#next-page-btn")
    assert await cards.count() == 24
    assert await cards.first.get_attribute("data-id") == "pagination-project-24"
    assert await cards.last.get_attribute("data-id") == "pagination-project-47"
    assert await page.locator("#page-indicator").text_content() == "Page 2 of 3"
    assert not await page.locator("#previous-page-btn").is_disabled()
    assert not await page.locator("#next-page-btn").is_disabled()

    await page.click("#next-page-btn")
    assert await cards.count() == 2
    assert await cards.first.get_attribute("data-id") == "pagination-project-48"
    assert await cards.last.get_attribute("data-id") == "pagination-project-49"
    assert await page.locator("#page-indicator").text_content() == "Page 3 of 3"
    assert await page.locator("#next-page-btn").is_disabled()

    await page.reload()
    await page.wait_for_selector("[data-id='pagination-project-00']")
    assert await page.locator(".project-card").count() == 24
    assert await page.locator("#page-indicator").text_content() == "Page 1 of 3"
    await page.close()


@pytest.mark.asyncio
async def test_dashboard_pagination_is_hidden_for_a_single_page(
    browser_instance: Browser, live_server_url: str
):
    page = await browser_instance.new_page()
    await _mock_list_projects(page, _pagination_projects(3))
    await page.goto(f"{live_server_url}/")

    await page.wait_for_selector(".project-card")
    assert await page.locator(".project-card").count() == 3
    assert await page.locator("#project-pagination").is_hidden()
    await page.close()


@pytest.mark.asyncio
async def test_dashboard_filter_and_search_reset_pagination_to_first_page(
    browser_instance: Browser, live_server_url: str
):
    projects = _pagination_projects(50)
    page = await browser_instance.new_page()
    await _mock_list_projects(page, projects)
    await page.goto(f"{live_server_url}/")

    await page.wait_for_selector("#project-pagination:not([hidden])")
    await page.click("#next-page-btn")
    assert await page.locator("#page-indicator").text_content() == "Page 2 of 3"

    await page.click("[data-filter='draft']")
    assert await page.locator("#page-indicator").text_content() == "Page 1 of 2"
    assert await page.locator(".project-card").count() == 24
    assert await page.locator(".project-card").first.get_attribute("data-id") == "pagination-project-00"

    await page.click("#next-page-btn")
    assert await page.locator("#page-indicator").text_content() == "Page 2 of 2"
    await page.fill("#search-input", "pagination")
    assert await page.locator("#page-indicator").text_content() == "Page 1 of 2"
    assert await page.locator(".project-card").first.get_attribute("data-id") == "pagination-project-00"
    await page.close()


@pytest.mark.asyncio
async def test_dashboard_delete_last_card_on_last_page_clamps_to_valid_page(
    browser_instance: Browser, live_server_url: str
):
    projects = _pagination_projects(25)
    page = await browser_instance.new_page()
    await _mock_list_projects(page, projects)
    delete_requests = []

    async def handle_delete(route):
        if route.request.method == "DELETE":
            delete_requests.append(route.request.url)
            await route.fulfill(
                status=200,
                content_type="application/json",
                body=json.dumps({"success": True, "data": None}),
            )
        else:
            await route.continue_()

    await page.route("**/api/projects/pagination-project-24", handle_delete)
    page.on("dialog", lambda dialog: dialog.accept())
    await page.goto(f"{live_server_url}/")

    await page.wait_for_selector("#project-pagination:not([hidden])")
    await page.click("#next-page-btn")
    assert await page.locator(".project-card").count() == 1
    assert await page.locator(".project-card").first.get_attribute("data-id") == "pagination-project-24"

    await page.click("[data-id='pagination-project-24'] [data-action='delete']")
    await page.wait_for_selector("[data-id='pagination-project-00']")
    assert delete_requests == [f"{live_server_url}/api/projects/pagination-project-24"]
    assert await page.locator(".project-card").count() == 24
    assert await page.locator("#project-pagination").is_hidden()
    assert await page.locator("#empty-state").is_hidden()
    await page.close()
