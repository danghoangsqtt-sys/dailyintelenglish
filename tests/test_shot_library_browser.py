"""Task 29.7: the Shot Library page (review once), and Step 5's "Add to library", "from library" and coverage line."""

import time
from typing import AsyncGenerator, Generator

import pytest
from playwright.async_api import Browser, async_playwright

from app.api import visuals as visuals_api
from app.core.config import settings
from tests.conftest import live_server
from tests.test_shot_review_browser import _project_with_shots


@pytest.fixture(scope="module")
def live_server_url(tmp_path_factory: pytest.TempPathFactory) -> Generator[str, None, None]:
    pretend_image_python = tmp_path_factory.mktemp("shot-library-venv") / "python.exe"
    pretend_image_python.touch()
    with pytest.MonkeyPatch.context() as patch:
        patch.setattr(settings, "IMAGE_ENGINE", "fake")
        patch.setattr(settings, "AI_VISUALS_ENABLED", True)
        patch.setattr(settings, "VISUALS_COLOUR_RETRIES", 0)
        patch.setattr(visuals_api, "IMAGE_PYTHON", pretend_image_python)
        with live_server(tmp_path_factory, "shot-library-browser") as url:
            yield url


@pytest.fixture
async def browser_instance() -> AsyncGenerator[Browser, None]:
    async with async_playwright() as playwright:
        browser = await playwright.chromium.launch(headless=True)
        yield browser
        await browser.close()


async def _step5(page, base: str, project_id: str) -> None:
    await page.route(
        f"**/api/projects/{project_id}/audio/status",
        lambda route: route.fulfill(json={"success": True, "data": {"status": "complete", "timestamps": []}}),
    )
    await page.goto(f"{base}/step5?project_id={project_id}")
    await page.locator("#visual-shot-grid .visual-shot-card").first.wait_for()


@pytest.mark.asyncio
async def test_add_to_library_review_it_once_and_the_next_run_is_served_from_the_library(
    browser_instance: Browser, live_server_url: str,
):
    page = await browser_instance.new_page()
    project_id = await _project_with_shots(page, live_server_url)
    await _step5(page, live_server_url, project_id)
    cards = page.locator("#visual-shot-grid .visual-shot-card")
    total = await cards.count()
    assert total >= 2
    assert await page.locator("#library-coverage").is_hidden()  # nothing approved yet: no line
    for index in range(total):  # keep every finished picture
        await cards.nth(index).locator("[data-action='add-to-library']").click()
        await cards.nth(index).get_by_text("In the library").wait_for()

    await page.goto(f"{live_server_url}/shots")
    grid = page.locator("#shot-grid .shot-card")
    await grid.first.wait_for()
    assert await grid.count() == total
    assert "needs review" in await page.locator("#shot-count").text_content() or "waiting for review" in await page.locator("#shot-count").text_content()
    assert await page.locator("#shot-grid .shot-card.is-pending").count() == total
    await grid.first.locator("[data-action='reject']").click()
    await page.locator("#shot-grid .shot-card.is-rejected").wait_for()
    page.once("dialog", lambda dialog: dialog.accept())
    await page.locator("#approve-all-btn").click()
    await page.locator("#shot-message.message-success").wait_for()
    assert await page.locator("#shot-grid .shot-card.is-approved").count() == total - 1
    assert await page.locator("#shot-grid .shot-card.is-rejected").count() == 1
    await page.select_option("#filter-state", "approved")
    await page.wait_for_function(f"document.querySelectorAll('#shot-grid .shot-card').length === {total - 1}")

    await _step5(page, live_server_url, project_id)  # coverage: the approved ones will be reused
    await page.locator("#library-coverage:not([hidden])").wait_for()
    text = await page.locator("#library-coverage").text_content()
    assert f"{total - 1} of {total}" in text and "will be drawn" in text
    await page.get_by_role("button", name="Generate shots").click()
    await page.locator("#visual-shot-grid .visual-badge").first.wait_for()
    assert await page.locator("#visual-shot-grid .visual-badge").count() == total - 1  # "from library"
    assert await page.locator("#visual-shot-grid [data-action='add-to-library']").count() == 1  # the redrawn one only
    await page.close()


@pytest.mark.asyncio
async def test_the_empty_library_says_what_to_do_and_the_sidebar_links_to_it(browser_instance: Browser, live_server_url: str):
    page = await browser_instance.new_page()
    await page.goto(f"{live_server_url}/shots")
    await page.wait_for_selector("#shot-count, #shot-empty")
    assert "Add to library" in await page.locator("#shot-empty").text_content()  # the hint exists (shown when empty)
    link = page.locator("#app-sidebar a[href='/shots']")
    assert await link.get_attribute("aria-current") == "page"
    await page.goto(f"{live_server_url}/music")
    link = page.locator("#app-sidebar a[href='/shots']")
    assert await link.count() == 1 and await link.get_attribute("aria-current") is None
    await link.click()
    await page.wait_for_url("**/shots")
    await page.close()
