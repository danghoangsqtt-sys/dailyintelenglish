"""Tasks 33.4/33.5 (D79/D84/D86): the Profiles tab -- Quick create, picture slots with prompts, drop into a slot, approve."""

from __future__ import annotations

import io
from typing import AsyncGenerator, Generator

import pytest
from playwright.async_api import Browser, async_playwright

from tests.conftest import live_server
from tests.test_character_asset_slots import _person


@pytest.fixture(scope="module")
def live_server_url(tmp_path_factory: pytest.TempPathFactory) -> Generator[str, None, None]:
    with live_server(tmp_path_factory, "profiles_browser") as url:
        yield url


@pytest.fixture
async def browser_instance() -> AsyncGenerator[Browser, None]:
    async with async_playwright() as playwright:
        browser = await playwright.chromium.launch()
        yield browser
        await browser.close()


def _png(picture) -> bytes:
    buffer = io.BytesIO()
    picture.save(buffer, "PNG")
    return buffer.getvalue()


async def _create(page, base: str, name: str, gender: str = "male") -> None:
    await page.goto(f"{base}/characters")
    await page.wait_for_selector("#profiles-panel:not([hidden])")
    await page.click("#profile-new")
    form = page.locator("#profile-create-form")
    await form.locator("[name=name]").fill(name)
    await form.locator("[name=gender]").select_option(gender)
    await form.locator("[name=accent]").select_option("british")
    await form.locator("[name=appearance]").fill("short black hair, round glasses")
    await form.locator("[name=outfit]").fill("grey hoodie and jeans")
    await form.locator("button[type=submit]").click()
    await page.wait_for_selector("#profile-detail:not([hidden]) .slot-card")


@pytest.mark.asyncio
async def test_quick_create_opens_the_29_slot_cards_with_prompts(browser_instance: Browser, live_server_url: str):
    page = await browser_instance.new_page(viewport={"width": 1024, "height": 900})
    await _create(page, live_server_url, "Kai")

    assert await page.locator(".slot-card").count() == 29
    base_card = page.locator('.slot-card[data-slot="calm__closed"]')
    assert "#00B140" in await base_card.locator(".slot-prompt").input_value()
    assert await base_card.locator(".slot-drop").get_attribute("aria-disabled") == "false"
    smile = page.locator('.slot-card[data-slot="smile__closed"]')
    assert await smile.get_attribute("data-state") == "waiting"
    assert "stands on the left" in await page.locator("#profile-summary").text_content()
    assert await page.locator('.profile-card:has-text("Kai")').count() == 1
    await page.close()


@pytest.mark.asyncio
async def test_a_dropped_file_goes_into_its_card_and_can_be_approved(browser_instance: Browser, live_server_url: str):
    page = await browser_instance.new_page(viewport={"width": 1280, "height": 900})
    await _create(page, live_server_url, "Lena", "female")
    assert "stands on the right" in await page.locator("#profile-summary").text_content()

    base_card = page.locator('.slot-card[data-slot="calm__closed"]')
    await base_card.locator("input[type=file]").set_input_files(
        {"name": "random-name.jpg", "mimeType": "image/png", "buffer": _png(_person())})
    await page.wait_for_selector('.slot-card[data-slot="calm__closed"][data-state="needs_review"]')
    assert await page.locator("#profile-approve-all").is_visible()

    await page.locator('.slot-card[data-slot="calm__closed"] .slot-approve').click()
    await page.wait_for_selector('.slot-card[data-slot="calm__closed"][data-state="approved"]')
    smile = page.locator('.slot-card[data-slot="smile__closed"]')
    await page.wait_for_selector('.slot-card[data-slot="smile__closed"][data-state="empty"]')
    assert await smile.locator('a[download]').count() == 1  # the input picture to attach in the outside AI
    await page.close()


@pytest.mark.asyncio
async def test_a_bad_picture_shows_the_reason_and_keeps_the_card_usable(browser_instance: Browser, live_server_url: str):
    page = await browser_instance.new_page(viewport={"width": 1280, "height": 900})
    await _create(page, live_server_url, "Omar")
    await page.locator('.slot-card[data-slot="calm__closed"] input[type=file]').set_input_files(
        {"name": "broken.png", "mimeType": "image/png", "buffer": b"not a picture"})
    await page.wait_for_selector("#profile-message.is-error")  # replaces the "created" notice
    assert "not a readable picture" in await page.locator("#profile-message").text_content()
    assert await page.locator('.slot-card[data-slot="calm__closed"]').get_attribute("data-state") == "empty"
    await page.close()


@pytest.mark.asyncio
async def test_the_old_local_generation_and_scenes_tabs_still_open(browser_instance: Browser, live_server_url: str):
    page = await browser_instance.new_page()
    await page.goto(f"{live_server_url}/characters")
    await page.click("#characters-tab")
    assert await page.locator("#characters-panel").is_visible()
    assert await page.locator("#profiles-panel").is_hidden()
    await page.click("#scenes-tab")
    assert await page.locator("#scenes-panel").is_visible()
    await page.click("#profiles-tab")
    assert await page.locator("#profiles-panel").is_visible()
    await page.close()
