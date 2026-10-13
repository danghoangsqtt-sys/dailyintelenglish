"""Task 36.5 (D103-D105): the /channel page -- the AI map (proposed, edited, applied), the tree and the calendar."""

from __future__ import annotations

import json
from typing import AsyncGenerator, Generator

import pytest
from playwright.async_api import Browser, async_playwright

from tests.conftest import live_server
from tests.test_channel_api import PLAN


@pytest.fixture(scope="module")
def live_server_url(tmp_path_factory: pytest.TempPathFactory) -> Generator[str, None, None]:
    with live_server(tmp_path_factory, "channel_browser") as url:
        yield url


@pytest.fixture
async def browser_instance() -> AsyncGenerator[Browser, None]:
    async with async_playwright() as playwright:
        browser = await playwright.chromium.launch()
        yield browser
        await browser.close()


@pytest.mark.asyncio
async def test_a_proposed_map_is_edited_applied_and_dated(browser_instance: Browser, live_server_url: str):
    page = await browser_instance.new_page()
    sent = []

    async def fake_propose(route):  # the AI call is mocked; apply, the tree and the calendar are real
        sent.append(json.loads(route.request.post_data))
        await route.fulfill(status=200, content_type="application/json",
                            body=json.dumps({"success": True, "data": PLAN, "error": None, "meta": {}}))

    await page.route("**/api/channel/plan/propose", fake_propose)
    await page.goto(f"{live_server_url}/channel")
    await page.locator("#plan-form textarea[name=focus]").fill("travel and work")
    await page.locator("#plan-propose").click()
    await page.locator("#plan-proposal:not([hidden])").wait_for()
    assert sent[0]["focus"] == "travel and work" and sent[0]["cefr_levels"] == ["A2", "B1"]
    first_title = page.locator("#proposal-tree input[aria-label='Episode title']").first
    await first_title.fill("Choosing the Destination")
    await page.locator(".proposal-topic").nth(1).get_by_role("button", name="Remove topic").click()
    await page.locator("#plan-apply").click()
    await page.locator(".topic-card").first.wait_for()
    assert await page.locator(".topic-card").count() == 1
    titles = await page.locator(".episode-table input[aria-label^='Title of episode']").evaluate_all(
        "inputs => inputs.map(input => input.value)")
    assert titles == ["Choosing the Destination", "Booking a Cabin", "Packing Day"]
    create = page.locator("[data-action='create-projects']")
    assert await create.is_disabled()  # no cast chosen yet
    assert "3 planned" in await page.locator("#channel-counts").text_content()
    await page.locator("#calendar-form input[name=start_date]").fill("2026-10-19")
    await page.locator("#calendar-form button[type=submit]").click()
    await page.wait_for_function("document.querySelectorAll('#calendar-list li').length === 3")
    first_day = await page.locator("#calendar-list li").first.text_content()
    assert "Mon 2026-10-19" in first_day and "Choosing the Destination" in first_day
    await page.close()
