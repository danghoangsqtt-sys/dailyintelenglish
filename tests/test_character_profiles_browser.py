"""Browser coverage for the Phase 33 profile library and resumable wizard."""

from typing import AsyncGenerator, Generator

import pytest
from playwright.async_api import Browser, async_playwright

from tests.conftest import live_server


@pytest.fixture(scope="module")
def live_server_url(tmp_path_factory: pytest.TempPathFactory) -> Generator[str, None, None]:
    with live_server(tmp_path_factory, "character-profiles-browser") as url:
        yield url


@pytest.fixture
async def browser_instance() -> AsyncGenerator[Browser, None]:
    async with async_playwright() as playwright:
        browser = await playwright.chromium.launch(headless=True)
        yield browser
        await browser.close()


@pytest.mark.asyncio
async def test_wizard_saves_and_resumes_one_step_at_a_time(
    browser_instance: Browser, live_server_url: str,
):
    page = await browser_instance.new_page(viewport={"width": 1024, "height": 768})
    await page.goto(f"{live_server_url}/characters")
    await page.get_by_role("button", name="New character").click()
    await page.get_by_role("heading", name="How will you build the visuals?").wait_for()
    await page.get_by_role("button", name="Continue").click()

    await page.locator('[data-step="1"] [name="name"]').fill("Nova Guide")
    await page.locator('[data-step="1"] [name="role"]').fill("English teacher")
    await page.locator('[data-step="1"] [name="intro"]').fill("A patient guide for daily conversations.")
    await page.get_by_role("button", name="Continue").click()
    await page.get_by_role("heading", name="Personality and dialogue").wait_for()

    await page.locator('[data-step="2"] [name="personality"]').fill("patient, curious")
    await page.locator('[data-step="2"] [name="speaking_style"]').fill("clear and encouraging")
    await page.get_by_text("Saved.", exact=True).wait_for()
    await page.reload()

    await page.get_by_role("heading", name="Personality and dialogue").wait_for()
    assert await page.locator('[data-step="2"] [name="personality"]').input_value() == "patient, curious"
    assert await page.locator(".wizard-form").evaluate("node => getComputedStyle(node).overflowY") == "visible"
    assert float((await page.locator('.wizard-fields label').first.evaluate(
        "node => getComputedStyle(node).fontSize"
    )).removesuffix("px")) >= 16

    await page.get_by_role("button", name="Save and close").click()
    await page.get_by_role("button", name="Nova Guide, English teacher").wait_for()
    await page.get_by_role("button", name="Nova Guide, English teacher").click()
    assert await page.get_by_text("Core visuals", exact=True).count() >= 1
    assert await page.locator("#profile-missing").get_by_text("face", exact=False).count() >= 1
    await page.close()


@pytest.mark.asyncio
async def test_profile_filters_duplicate_archive_and_restore(
    browser_instance: Browser, live_server_url: str,
):
    page = await browser_instance.new_page()
    await page.goto(f"{live_server_url}/characters")
    await page.locator("#character-search").fill("Nova Guide")
    await page.get_by_role("button", name="Nova Guide, English teacher").wait_for()
    await page.get_by_role("button", name="Nova Guide, English teacher").click()
    await page.get_by_role("button", name="Duplicate").click()
    await page.get_by_text("Profile duplicated.").wait_for()
    await page.evaluate("window.confirm = () => true")
    await page.get_by_role("button", name="Archive").click()
    await page.get_by_text("Profile archived.").wait_for()
    await page.locator("#character-state").select_option("archived")
    copy = page.get_by_role("button", name="Nova Guide copy, English teacher")
    await copy.wait_for()
    await copy.click()
    await page.get_by_role("button", name="Restore").click()
    await page.get_by_text("Profile restored.").wait_for()
    await page.close()
