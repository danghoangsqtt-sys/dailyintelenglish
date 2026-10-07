"""Task 27.4: steps 1 to 7 share one studio frame: the app sidebar, the steps panel on the left, the stage in the middle
and an inspector panel on the right (steps 2, 4 and 5 also carry the timeline below)."""

from typing import AsyncGenerator, Generator

import pytest
from playwright.async_api import Browser, async_playwright

from tests.conftest import live_server
from tests.test_visuals_project_api import PROJECT

STEPS = [(1, "step1"), (2, "step2"), (3, "step3"), (4, "step4"), (5, "step5"), (6, "step6"), (7, "step7")]


@pytest.fixture(scope="module")
def live_server_url(tmp_path_factory: pytest.TempPathFactory) -> Generator[str, None, None]:
    with live_server(tmp_path_factory, "studio-frame-browser") as url:
        yield url


@pytest.fixture
async def browser_instance() -> AsyncGenerator[Browser, None]:
    async with async_playwright() as playwright:
        browser = await playwright.chromium.launch(headless=True)
        yield browser
        await browser.close()


@pytest.mark.asyncio
@pytest.mark.parametrize("number,path", STEPS)
async def test_every_step_has_the_same_three_panels_and_the_step_list(browser_instance: Browser, live_server_url: str, number, path):
    page = await browser_instance.new_page(viewport={"width": 1440, "height": 900})
    created = await page.request.post(f"{live_server_url}/api/projects", data=PROJECT)
    project_id = (await created.json())["data"]["id"]
    await page.goto(f"{live_server_url}/{path}?project_id={project_id}")
    await page.wait_for_selector("#step-nav .step-nav-pill")
    assert await page.locator("#app-sidebar").count() == 1  # the app navigation
    panels = page.locator(".shell-row > aside, .shell-row > main")
    ids = [await panels.nth(index).get_attribute("id") for index in range(await panels.count())]
    assert ids == ["pane-sidebar", "pane-main", "pane-inspector"]  # steps panel, stage, inspector: left to right
    assert await page.locator("#pane-sidebar #step-nav").count() == 1
    pills = page.locator("#step-nav .step-nav-pill")
    assert await pills.count() == 7
    assert await page.locator("#step-nav .step-nav-pill.active").count() == 1
    assert (await page.locator("#step-nav .step-nav-pill.active").text_content()).strip().endswith(
        ["Config", "Script", "Learning", "Audio", "Video", "Thumbnail", "YouTube"][number - 1])
    left, stage, inspector = [await page.locator(f"#{pane}").bounding_box() for pane in ("pane-sidebar", "pane-main", "pane-inspector")]
    assert left["x"] < stage["x"] < inspector["x"] and left["width"] >= 150 and inspector["width"] >= 200
    assert await page.evaluate("document.documentElement.scrollWidth <= window.innerWidth + 1")  # no sideways scroll
    await page.close()
