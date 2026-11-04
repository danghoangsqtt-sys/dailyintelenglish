"""Phase 93 (Task 93.9): the new pages -- Home, Create video, Videos, Library -- on a phone, in both themes, by keyboard."""

from typing import AsyncGenerator

import pytest
from playwright.async_api import Browser, async_playwright

from backend.tests.conftest import live_server

PAGES = ["/", "/create", "/videos", "/library", "/channel", "/automation", "/characters", "/activities", "/music", "/shorts-batch", "/settings"]


@pytest.fixture(scope="module")
def live_server_url(tmp_path_factory: pytest.TempPathFactory):
    with live_server(tmp_path_factory, "studio-pages") as url:
        yield url


@pytest.fixture
async def browser_instance() -> AsyncGenerator[Browser, None]:
    async with async_playwright() as playwright:
        browser = await playwright.chromium.launch(headless=True)
        yield browser
        await browser.close()


@pytest.mark.asyncio
@pytest.mark.parametrize("path", PAGES)
async def test_no_sideways_scroll_on_a_phone(browser_instance, live_server_url, path):
    page = await browser_instance.new_page(viewport={"width": 375, "height": 812})
    response = await page.goto(f"{live_server_url}{path}")
    assert response.ok
    await page.wait_for_load_state("networkidle")
    assert await page.evaluate("document.documentElement.scrollWidth <= window.innerWidth + 1"), path
    await page.close()


@pytest.mark.asyncio
async def test_both_themes_paint_the_page_from_the_tokens(browser_instance, live_server_url):
    page = await browser_instance.new_page()
    await page.goto(f"{live_server_url}/")
    light = await page.evaluate("getComputedStyle(document.body).backgroundColor")
    await page.evaluate("document.documentElement.setAttribute('data-theme', 'dark')")
    dark = await page.evaluate("getComputedStyle(document.body).backgroundColor")
    assert light == "rgb(246, 247, 242)" and dark == "rgb(17, 22, 19)"
    assert "Baloo 2" in await page.evaluate("getComputedStyle(document.querySelector('h1')).fontFamily")
    await page.close()


@pytest.mark.asyncio
async def test_home_without_an_assistant_character_still_works(browser_instance, live_server_url):
    page = await browser_instance.new_page()
    await page.goto(f"{live_server_url}/")
    await page.locator("#waiting-list .e-empty, #waiting-list .e-row").first.wait_for()
    await page.wait_for_function("document.querySelector('.e-lina').hasAttribute('hidden')")  # no Lina in an empty library
    form = page.locator("#home-topic")
    await page.locator("#home-topic-input").fill("the second conditional")
    await form.locator("button[type=submit]").click()
    await page.wait_for_url("**/create?topic=the+second+conditional")
    link = page.locator('.e-tpl[data-kind="grammar"]')
    assert (await link.get_attribute("href")).endswith("mode=shorts&template=grammar&topic=the%20second%20conditional")
    await page.close()


@pytest.mark.asyncio
async def test_create_opens_step1_with_the_template_chosen(browser_instance, live_server_url):
    page = await browser_instance.new_page()
    await page.goto(f"{live_server_url}/create")
    await page.locator('.e-tpl[data-kind="roots"]').click()
    await page.wait_for_url("**/step1?mode=shorts&template=roots")
    await page.wait_for_function("document.querySelector('#shorts-templates [data-template=\"roots\"]')?.getAttribute('aria-checked') === 'true'")
    await page.close()


@pytest.mark.asyncio
async def test_keyboard_focus_is_visible_on_the_rail(browser_instance, live_server_url):
    page = await browser_instance.new_page()
    await page.goto(f"{live_server_url}/videos")
    await page.locator(".side-today").focus()
    outline = await page.evaluate("getComputedStyle(document.activeElement).outlineStyle")
    assert outline not in ("none", "")
    await page.close()


@pytest.mark.asyncio
async def test_area_tabs_join_the_pages_of_an_area(browser_instance, live_server_url):
    page = await browser_instance.new_page()
    await page.goto(f"{live_server_url}/automation")
    tabs = page.locator("nav.area-tabs a")
    assert await tabs.all_text_contents() == ["Publishing plan", "Automation"]
    assert await page.locator('nav.area-tabs a[aria-current="page"]').text_content() == "Automation"
    await page.goto(f"{live_server_url}/music")
    assert "Voices and brand" in await page.locator("nav.area-tabs").text_content()
    await page.close()
