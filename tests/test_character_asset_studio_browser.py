"""Visual Asset Studio mapping, upload, preview, and review flow."""

import io
from typing import AsyncGenerator, Generator

import pytest
from PIL import Image
from playwright.async_api import Browser, async_playwright

from tests.conftest import live_server


@pytest.fixture(scope="module")
def live_server_url(tmp_path_factory: pytest.TempPathFactory) -> Generator[str, None, None]:
    with live_server(tmp_path_factory, "character-asset-studio") as url:
        yield url


@pytest.fixture
async def browser_instance() -> AsyncGenerator[Browser, None]:
    async with async_playwright() as playwright:
        browser = await playwright.chromium.launch(headless=True)
        yield browser
        await browser.close()


def picture(image_format: str = "PNG", colour=(80, 150, 110)) -> bytes:
    output = io.BytesIO()
    Image.new("RGB", (640, 640), colour).save(output, format=image_format)
    return output.getvalue()


@pytest.mark.asyncio
async def test_single_and_bulk_upload_keep_numbered_previews_and_explicit_slots(
    browser_instance: Browser, live_server_url: str,
):
    page = await browser_instance.new_page(viewport={"width": 1180, "height": 820})
    response = await page.request.post(
        f"{live_server_url}/api/visuals/characters",
        data={"name": "Studio Hero", "wizard_step": 5},
    )
    profile = (await response.json())["data"]
    await page.goto(f"{live_server_url}/characters")
    await page.evaluate("id => localStorage.setItem('characterWizardId', id)", profile["id"])
    await page.reload()
    await page.get_by_role("button", name="Open Visual Asset Studio").click()

    face = page.locator(".asset-slot-card").filter(has_text="Reference portrait")
    await face.locator('input[type="file"]').set_input_files({
        "name": "my-own-name.jpg", "mimeType": "image/jpeg", "buffer": picture("JPEG"),
    })
    await page.get_by_text("Reference portrait uploaded. Review it before use.").wait_for()
    await face.get_by_role("button", name="Approve").click()
    await face.get_by_text("Ready").wait_for()

    await page.locator("#asset-bulk-input").set_input_files([
        {"name": "first.webp", "mimeType": "image/webp", "buffer": picture("WEBP", (120, 90, 170))},
        {"name": "second.png", "mimeType": "image/png", "buffer": picture("PNG", (170, 130, 70))},
    ])
    items = page.locator(".bulk-map-item")
    assert await items.count() == 2
    assert await items.nth(0).get_by_text("1. first.webp").is_visible()
    assert await items.nth(1).get_by_text("2. second.png").is_visible()
    await items.nth(0).locator("select").select_option("portrait_calm")
    await items.nth(1).locator("select").select_option("portrait_smile")
    await page.get_by_role("button", name="Upload mapped pictures").click()
    await page.get_by_text("2 pictures uploaded. Review them below.").wait_for()
    assert await page.locator(".asset-slot-card .asset-slot-preview img").count() >= 3
    await page.get_by_role("button", name="Back to setup").click()
    await page.get_by_role("heading", name="Identity references").wait_for()
    await page.close()
