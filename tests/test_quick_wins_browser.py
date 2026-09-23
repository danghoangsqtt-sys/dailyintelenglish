"""Browser coverage for Task 6.1's theme and missing-project quick wins."""

import re
from typing import AsyncGenerator

import pytest
from playwright.async_api import Browser, Page, async_playwright

from tests.conftest import live_server

THEME_ROUTES = ("/", "/step1", "/step2", "/step3", "/step4", "/step5", "/step6", "/step7", "/music")
RAW_THEME_ROUTES = ("/step1", "/step6", "/step7", "/music")
WORKFLOW_ROUTES = ("/step2", "/step3", "/step4", "/step5", "/step6", "/step7")


@pytest.fixture(scope="module")
def live_server_url(tmp_path_factory: pytest.TempPathFactory):
    with live_server(tmp_path_factory, "quick-wins") as url:
        yield url


@pytest.fixture
async def browser_instance() -> AsyncGenerator[Browser, None]:
    async with async_playwright() as playwright:
        browser = await playwright.chromium.launch(headless=True)
        yield browser
        await browser.close()


async def _mock_empty_api(page: Page) -> None:
    async def handle(route):
        await route.fulfill(
            status=200,
            content_type="application/json",
            body='{"success":true,"data":[],"error":null,"meta":{}}',
        )

    await page.route("**/api/**", handle)


@pytest.mark.asyncio
async def test_pages_do_not_ship_a_hardcoded_theme(
    browser_instance: Browser, live_server_url: str
):
    page = await browser_instance.new_page()
    for route in RAW_THEME_ROUTES:
        response = await page.request.get(f"{live_server_url}{route}")
        assert response.ok
        markup = await response.text()
        opening_html = re.search(r"<html\b[^>]*>", markup, re.IGNORECASE)
        assert opening_html is not None
        assert "data-theme" not in opening_html.group(0)
    await page.close()


@pytest.mark.asyncio
@pytest.mark.parametrize("stored_theme", [None, "dark"])
async def test_theme_script_applies_default_or_stored_theme_on_every_page(
    browser_instance: Browser, live_server_url: str, stored_theme: str | None
):
    page = await browser_instance.new_page()
    await _mock_empty_api(page)
    if stored_theme is None:
        await page.add_init_script("localStorage.removeItem('die-theme')")
        expected_theme = "light"
    else:
        await page.add_init_script("localStorage.setItem('die-theme', 'dark')")
        expected_theme = stored_theme

    for route in THEME_ROUTES:
        await page.goto(f"{live_server_url}{route}", wait_until="domcontentloaded")
        assert await page.locator("html").get_attribute("data-theme") == expected_theme
    await page.close()


@pytest.mark.asyncio
@pytest.mark.parametrize("route", WORKFLOW_ROUTES)
async def test_missing_project_error_has_a_real_dashboard_link(
    browser_instance: Browser, live_server_url: str, route: str
):
    page = await browser_instance.new_page()
    await page.goto(f"{live_server_url}{route}")

    banner = page.locator("#error-banner")
    await banner.wait_for(state="visible")
    assert "Missing project" in (await banner.text_content())
    link = banner.get_by_role("link", name="Go to Dashboard")
    assert await link.get_attribute("href") == "/"
    await page.close()


@pytest.mark.asyncio
async def test_missing_project_dashboard_link_navigates_home(
    browser_instance: Browser, live_server_url: str
):
    page = await browser_instance.new_page()
    await page.goto(f"{live_server_url}/step2")
    await page.locator("#error-banner").get_by_role(
        "link", name="Go to Dashboard"
    ).click()
    await page.wait_for_url(f"{live_server_url}/")
    await page.close()


@pytest.mark.asyncio
@pytest.mark.parametrize("route", ["/music", "/step6", "/step7"])
async def test_disabled_and_aria_disabled_buttons_share_the_same_opacity(
    browser_instance: Browser, live_server_url: str, route: str
):
    """Task 8.1 (ENH-005): a real `disabled` button and an `aria-disabled="true"`
    link-styled-as-button must render identically, on every page that has one —
    previously each page invented its own, inconsistent local override.
    """
    page = await browser_instance.new_page()
    await _mock_empty_api(page)
    await page.goto(f"{live_server_url}{route}", wait_until="domcontentloaded")

    opacities = await page.evaluate(
        """() => {
            const btn = document.createElement('button');
            btn.className = 'btn';
            btn.disabled = true;
            document.body.appendChild(btn);
            const btnOpacity = getComputedStyle(btn).opacity;
            btn.remove();

            const link = document.createElement('a');
            link.className = 'btn';
            link.setAttribute('aria-disabled', 'true');
            document.body.appendChild(link);
            const linkOpacity = getComputedStyle(link).opacity;
            link.remove();

            return [btnOpacity, linkOpacity];
        }"""
    )
    button_opacity, link_opacity = opacities
    assert button_opacity == link_opacity
    await page.close()


@pytest.mark.asyncio
async def test_thumbnail_btn_sm_padding_matches_the_shared_rule(
    browser_instance: Browser, live_server_url: str
):
    """Task 8.1 (ENH-005): step6_thumbnail.html no longer overrides `.btn-sm`'s
    padding locally — it must now match the shared stylesheet's value, the same as
    any other page.
    """
    page = await browser_instance.new_page()
    await _mock_empty_api(page)

    async def probe_padding(route: str) -> str:
        await page.goto(f"{live_server_url}{route}", wait_until="domcontentloaded")
        return await page.evaluate(
            """() => {
                const el = document.createElement('button');
                el.className = 'btn btn-sm';
                document.body.appendChild(el);
                const padding = getComputedStyle(el).padding;
                el.remove();
                return padding;
            }"""
        )

    thumbnail_padding = await probe_padding("/step6")
    reference_padding = await probe_padding("/step7")
    assert thumbnail_padding == reference_padding
    await page.close()


@pytest.mark.asyncio
async def test_regular_error_remains_plain_text_without_a_link(
    browser_instance: Browser, live_server_url: str
):
    page = await browser_instance.new_page()

    async def fail_project_load(route):
        await route.fulfill(
            status=500,
            content_type="application/json",
            body='{"success":false,"data":null,"error":"failure","meta":{}}',
        )

    await page.route("**/api/projects/project-with-error", fail_project_load)
    await page.goto(f"{live_server_url}/step2?project_id=project-with-error")

    banner = page.locator("#error-banner")
    await banner.wait_for(state="visible")
    assert "couldn't load this project" in (await banner.text_content())
    assert await banner.locator("a").count() == 0
    await page.close()
