"""Task 27.2 (Phase 27); Phase 93 (D138/D140): one rail on every page -- Create video, the five areas, Settings;
it collapses to icons, and on phones it is a tab bar at the bottom."""

import json
from typing import AsyncGenerator

import pytest
from playwright.async_api import Browser, Page, async_playwright

from backend.tests.conftest import live_server

PAGES = {  # page -> the rail item it lights (its area)
    "/": "Today", "/videos": "Videos", "/create": "Create video", "/shorts-batch": "Create video", "/library": "Library",
    "/characters": "Library", "/music": "Library", "/activities": "Library", "/channel": "Channel", "/automation": "Channel",
    "/settings": "Settings", "/step1": "Videos", "/step2": "Videos", "/step3": "Videos", "/step4": "Videos",
    "/step5": "Videos", "/step6": "Videos", "/step7": "Videos",
}
LINKS = ["Create video", "Today", "Channel", "Videos", "Library", "Settings"]


@pytest.fixture(scope="module")
def live_server_url(tmp_path_factory: pytest.TempPathFactory):
    with live_server(tmp_path_factory, "app-sidebar") as url:
        yield url


@pytest.fixture
async def browser_instance() -> AsyncGenerator[Browser, None]:
    async with async_playwright() as playwright:
        browser = await playwright.chromium.launch(headless=True)
        yield browser
        await browser.close()


async def _open(browser: Browser, url: str, width: int = 1400, height: int = 900) -> Page:
    page = await browser.new_page(viewport={"width": width, "height": height})

    async def not_mocked(route):
        await route.fulfill(status=404, content_type="application/json",
                            body=json.dumps({"success": False, "data": None, "error": "n/a", "meta": {}}))

    if "/step" in url:  # the step pages need a project; the sidebar is static markup
        await page.route("**/api/**", not_mocked)
    await page.goto(url)
    return page


async def _sidebar_width(page: Page) -> float:
    return await page.locator("#app-sidebar").evaluate("element => element.getBoundingClientRect().width")


@pytest.mark.asyncio
@pytest.mark.parametrize("path", list(PAGES))
async def test_every_page_has_one_sidebar_with_one_link_of_each_name(browser_instance, live_server_url, path):
    page = await _open(browser_instance, f"{live_server_url}{path}?project_id=none")
    assert await page.locator("aside#app-sidebar").count() == 1
    assert await page.locator("nav.app-nav, header.topbar a.brand").count() == 0  # the top bar lost them
    assert await page.locator("a.brand").count() == 1
    for name in LINKS:
        assert await page.get_by_role("link", name=name, exact=True).count() == 1, name
    current = await page.locator('#app-sidebar a[aria-current="page"]').get_attribute("aria-label")
    assert current == PAGES[path]
    await page.close()


@pytest.mark.asyncio
async def test_toggle_collapses_to_a_rail_and_the_choice_is_remembered(browser_instance, live_server_url):
    page = await _open(browser_instance, f"{live_server_url}/")
    toggle = page.locator("#sidebar-toggle")
    assert await toggle.get_attribute("aria-expanded") == "true"
    expanded = await _sidebar_width(page)
    assert 240 <= expanded <= 256
    await toggle.click()
    assert await page.evaluate("document.body.classList.contains('sidebar-collapsed')")
    assert await toggle.get_attribute("aria-expanded") == "false"
    await page.wait_for_function("document.getElementById('app-sidebar').getBoundingClientRect().width <= 80")
    # the links keep their names when only the icons show (title and aria-label stay)
    assert await page.get_by_role("link", name="Library", exact=True).count() == 1
    assert await page.evaluate("localStorage.getItem('dbe.sidebar')") == "collapsed"
    await page.reload()
    assert await page.evaluate("document.body.classList.contains('sidebar-collapsed')")
    await page.locator("#sidebar-toggle").click()
    await page.wait_for_function(
        "document.getElementById('app-sidebar').getBoundingClientRect().width === " + str(expanded))
    assert await _sidebar_width(page) == expanded
    assert await page.evaluate("localStorage.getItem('dbe.sidebar')") == "expanded"
    await page.close()


@pytest.mark.asyncio
async def test_studio_pages_start_as_a_rail_and_the_dashboard_stays_open(browser_instance, live_server_url):
    studio = await _open(browser_instance, f"{live_server_url}/step2?project_id=none")
    assert await _sidebar_width(studio) <= 80
    assert await studio.locator("#pane-sidebar").count() == 1  # the studio keeps its own panel
    await studio.close()
    home = await _open(browser_instance, f"{live_server_url}/")
    assert await _sidebar_width(home) >= 240
    await home.close()


@pytest.mark.asyncio
async def test_phones_get_a_tab_bar_at_the_bottom(browser_instance, live_server_url):
    page = await _open(browser_instance, f"{live_server_url}/", width=375, height=812)
    sidebar = page.locator("#app-sidebar")
    assert await sidebar.is_visible()
    box = await sidebar.bounding_box()
    assert box["y"] + box["height"] >= 812 - 1 and box["width"] >= 370  # along the bottom edge, full width
    assert await page.evaluate("document.documentElement.scrollWidth <= window.innerWidth")
    for name in ["Today", "Channel", "Videos", "Library", "Settings"]:
        assert await page.get_by_role("link", name=name, exact=True).is_visible(), name
    assert not await page.locator("#sidebar-toggle").is_visible()
    await page.close()


@pytest.mark.asyncio
async def test_step1_keeps_the_step_nav_in_the_steps_panel_right_below_the_top_bar(browser_instance, live_server_url):
    # Task 27.4: Step 1 now has the studio frame; its step list sits in the left panel, which follows the top bar.
    page = await _open(browser_instance, f"{live_server_url}/step1?project_id=none")
    assert await page.locator("#pane-sidebar #step-nav").count() == 1
    assert await page.locator(".shell-flex").evaluate(
        "element => element.previousElementSibling?.matches('header.topbar') === true"
    )
    top = await page.locator("header.topbar").bounding_box()
    nav = await page.locator("#step-nav").bounding_box()
    assert nav["y"] >= top["y"] + top["height"] - 1  # not hidden behind the top bar
    await page.close()
