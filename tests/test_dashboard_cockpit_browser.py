"""Task 36.7 (D106-D108): the dashboard's channel cockpit renders the stats, today's actions, the roadmap and the board."""

from __future__ import annotations

from typing import AsyncGenerator, Generator

import pytest
from playwright.async_api import Browser, async_playwright

from tests.conftest import live_server
from tests.test_channel_api import PLAN


@pytest.fixture(scope="module")
def live_server_url(tmp_path_factory: pytest.TempPathFactory) -> Generator[str, None, None]:
    with live_server(tmp_path_factory, "cockpit_browser") as url:
        yield url


@pytest.fixture
async def browser_instance() -> AsyncGenerator[Browser, None]:
    async with async_playwright() as playwright:
        browser = await playwright.chromium.launch()
        yield browser
        await browser.close()


@pytest.mark.asyncio
async def test_the_cockpit_shows_the_plan_and_the_roadmap_stage(browser_instance: Browser, live_server_url: str):
    page = await browser_instance.new_page()
    applied = await page.request.post(f"{live_server_url}/api/channel/plan/apply", data={"plan": PLAN})
    assert applied.ok, await applied.text()
    await page.goto(f"{live_server_url}/")
    await page.locator("#cockpit-stats .cockpit-stat").first.wait_for()
    stats = await page.locator("#cockpit-stats").text_content()
    assert "2topics" in stats.replace(" ", "") and "5planned" in stats.replace(" ", "")
    assert "Choose the characters of 2 series" in await page.locator("#cockpit-actions").text_content()
    assert await page.locator("#roadmap-steps button").count() == 5
    current = page.locator("#roadmap-steps button[data-state='current']")
    assert await current.get_attribute("aria-pressed") == "true"
    await page.locator("#roadmap-steps button[data-stage='grow']").click()
    assert "Shorts and TikTok" in await page.locator("#roadmap-detail").text_content()
    assert await page.locator("#production-board .board-column").count() == 7
    assert "Nothing dated yet" in await page.locator("#cockpit-next").text_content()
    assert await page.locator("#new-project-btn").is_visible() and await page.locator("#project-grid").count() == 1
    await page.close()
