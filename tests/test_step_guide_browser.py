"""Phase 56 (ENH-038): the next-step bar of the step pages says whether the step is done and links to the next one."""

from typing import AsyncGenerator, Generator

import pytest
from playwright.async_api import Browser, async_playwright

from tests.conftest import live_server
from tests.test_visuals_project_api import PROJECT


@pytest.fixture(scope="module")
def live_server_url(tmp_path_factory: pytest.TempPathFactory) -> Generator[str, None, None]:
    with live_server(tmp_path_factory, "step-guide-browser") as url:
        yield url


@pytest.fixture
async def browser_instance() -> AsyncGenerator[Browser, None]:
    async with async_playwright() as playwright:
        browser = await playwright.chromium.launch(headless=True)
        yield browser
        await browser.close()


@pytest.mark.asyncio
async def test_the_bar_follows_the_projects_progress(browser_instance: Browser, live_server_url: str):
    page = await browser_instance.new_page(viewport={"width": 1440, "height": 900})
    created = await page.request.post(f"{live_server_url}/api/projects", data=PROJECT)
    project = (await created.json())["data"]
    project_id = project["id"]

    await page.goto(f"{live_server_url}/step2?project_id={project_id}")
    bar = page.locator(".pane-stage #step-guide")
    await bar.wait_for()
    assert await bar.get_attribute("data-done") == "false"
    assert "To finish this step: generate or write the script." in await bar.text_content()
    next_link = bar.locator(".step-guide-next")
    assert await next_link.text_content() == "Next: Step 3 — Learning →"
    assert await next_link.get_attribute("href") == f"/step3?project_id={project_id}"

    speaker = project["speakers"][0]["id"]
    saved = await page.request.put(f"{live_server_url}/api/projects/{project_id}/script",
                                   data={"lines": [{"speaker_id": speaker, "text": "Hello there."}]})
    assert saved.ok, await saved.text()
    await page.evaluate("StepGuide.refresh()")
    await page.wait_for_function("document.getElementById('step-guide').dataset.done === 'true'")
    assert "✓ Step 2 — Script is done" in await bar.text_content()

    await page.goto(f"{live_server_url}/step4?project_id={project_id}")
    bar = page.locator("#step-guide")
    await bar.wait_for()
    assert "Step 3 — Learning is not done yet" in await bar.locator(".step-guide-earlier").text_content()
    await page.wait_for_function("document.querySelector('#step-nav [data-step=\"3\"] .step-dot').textContent === '3'")
    assert await page.locator('#step-nav [data-step="2"] .step-dot').text_content() == "✓"
    await page.goto(f"{live_server_url}/step7?project_id={project_id}")
    await page.locator("#step-guide").wait_for()
    assert await page.locator("#step-guide .step-guide-next").get_attribute("href") == "/"
    await page.close()


@pytest.mark.asyncio
async def test_no_bar_without_a_project(browser_instance: Browser, live_server_url: str):
    page = await browser_instance.new_page()
    await page.goto(f"{live_server_url}/step1")
    await page.locator("#page-title").wait_for()
    await page.goto(f"{live_server_url}/step2?project_id=missing")
    await page.wait_for_load_state("networkidle")
    assert await page.locator("#step-guide").count() == 0
    await page.close()
