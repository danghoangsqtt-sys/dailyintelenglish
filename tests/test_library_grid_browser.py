"""Task 27.3b: the Character and Scene libraries as large image grids with a sticky detail panel."""

import re
import time
from typing import AsyncGenerator, Generator

import pytest
from playwright.async_api import Browser, async_playwright

from app.api import visuals as visuals_api
from app.core.config import settings
from tests.conftest import live_server
from tests.test_visuals_project_api import locked_character


@pytest.fixture(scope="module")
def live_server_url(tmp_path_factory: pytest.TempPathFactory) -> Generator[str, None, None]:
    pretend_image_python = tmp_path_factory.mktemp("library-grid-venv") / "python.exe"
    pretend_image_python.touch()
    with pytest.MonkeyPatch.context() as patch:
        patch.setattr(settings, "IMAGE_ENGINE", "fake")
        patch.setattr(settings, "AI_VISUALS_ENABLED", True)
        patch.setattr(visuals_api, "IMAGE_PYTHON", pretend_image_python)
        with live_server(tmp_path_factory, "library-grid-browser") as url:
            yield url


@pytest.fixture
async def browser_instance() -> AsyncGenerator[Browser, None]:
    async with async_playwright() as playwright:
        browser = await playwright.chromium.launch(headless=True)
        yield browser
        await browser.close()


async def _box(locator) -> dict:
    return await locator.evaluate(
        "e => { const r = e.getBoundingClientRect(); return {x: r.x, y: r.y, w: r.width, h: r.height}; }")


@pytest.mark.asyncio
async def test_characters_are_portrait_tiles_with_outfit_swatches_and_a_sticky_detail_panel(
        browser_instance: Browser, live_server_url: str):
    locked_character("Lan", "yellow")
    locked_character("Minh", "green")
    page = await browser_instance.new_page(viewport={"width": 1400, "height": 900})
    await page.goto(f"{live_server_url}/characters")
    tiles = page.locator("#character-list .character-tile")
    await tiles.nth(1).wait_for()
    assert await tiles.count() == 2
    for index in range(2):
        picture = await _box(tiles.nth(index).locator("img.library-face"))
        assert picture["w"] >= 140 and picture["h"] > picture["w"], picture  # a portrait, not a 56 px avatar
        swatches = tiles.nth(index).locator(".library-swatch")
        assert await swatches.count() == 2
        titles = await swatches.evaluate_all("items => items.map(item => item.title)")
        assert titles[1] == "navy blue bottom" and titles[0].endswith(" top")
    # the detail panel is on the right of the grid and stays in view
    grid, editor = await _box(page.locator("#character-list")), await _box(page.locator(".library-editor").first)
    assert editor["x"] >= grid["x"] + grid["w"] - 2
    assert await page.locator("#characters-panel .library-editor").first.evaluate(
        "e => getComputedStyle(e).position") == "sticky"
    # selecting a tile fills the hero with its face, name and status
    assert await page.locator("#character-hero").is_hidden()
    await tiles.nth(1).click()
    assert await tiles.nth(1).get_attribute("aria-current") == "true"
    assert await tiles.nth(0).get_attribute("aria-current") == "false"
    hero = page.locator("#character-hero")
    await hero.wait_for(state="visible")
    face = await tiles.nth(1).locator("img.library-face").get_attribute("src")
    assert await hero.locator("img").get_attribute("src") == face
    names = await tiles.locator(".library-card-name").all_text_contents()
    assert names[1] in await hero.inner_text() and "locked" in await hero.inner_text()
    await page.close()


@pytest.mark.asyncio
async def test_a_narrow_screen_stacks_the_grid_above_the_detail_panel(browser_instance: Browser, live_server_url: str):
    locked_character("Narrow", "yellow")
    page = await browser_instance.new_page(viewport={"width": 700, "height": 900})
    await page.goto(f"{live_server_url}/characters")
    await page.locator("#character-list .character-tile").first.wait_for()
    grid, editor = await _box(page.locator("#character-list")), await _box(page.locator(".library-editor").first)
    assert editor["y"] >= grid["y"] + grid["h"] - 2
    assert await page.evaluate("document.documentElement.scrollWidth <= window.innerWidth")
    await page.close()


@pytest.mark.asyncio
async def test_scenes_have_a_detail_panel_that_follows_the_selected_card(
        browser_instance: Browser, live_server_url: str):
    page = await browser_instance.new_page(viewport={"width": 1400, "height": 900})
    base = live_server_url
    job = (await (await page.request.post(f"{base}/api/visuals/scenes/builtin-cafe/preview")).json())["data"]
    for _ in range(600):
        status = (await (await page.request.get(f"{base}/api/visuals/jobs/{job['id']}")).json())["data"]["status"]
        if status in ("complete", "error", "cancelled"):
            assert status == "complete"
            break
        time.sleep(0.05)
    await page.goto(f"{base}/characters")
    await page.locator("#scenes-tab").click()
    cards = page.locator("#scene-grid .library-scene")
    await cards.first.wait_for()
    detail = page.locator("#scene-detail")
    assert await detail.is_hidden()  # nothing selected yet
    card = cards.filter(has=page.locator("h3", has_text=re.compile(r"^Cafe"))).first
    await card.locator("img").wait_for()
    await card.click(position={"x": 20, "y": 20})  # on the picture, not on a button
    await detail.wait_for(state="visible")
    assert await card.get_attribute("aria-current") == "true"
    plate = page.locator("#scene-detail-plate")
    assert "/preview" in await plate.get_attribute("src")
    text = await detail.inner_text()
    assert "Cafe" in text and "a cozy street cafe" in text
    grid, panel = await _box(page.locator("#scene-grid")), await _box(page.locator("#scene-side"))
    assert panel["x"] >= grid["x"] + grid["w"] - 2
    assert await page.locator("#scene-side").evaluate("e => getComputedStyle(e).position") == "sticky"
    # Edit still fills the form
    await card.get_by_role("button", name="Edit").click()
    assert await page.locator("#scene-form [name=name]").input_value() == "Cafe"
    assert await page.locator("#scene-editor-title").text_content() == "Edit Cafe"
    # a scene without a plate shows a placeholder, not a broken picture
    other = cards.filter(has=page.locator("h3", has_text=re.compile(r"^Library"))).first
    await other.click(position={"x": 20, "y": 20})
    assert await page.locator("#scene-detail-plate").is_hidden()
    assert await page.locator("#scene-detail-empty").is_visible()
    await page.close()
