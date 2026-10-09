"""Phase 32.6b browser contract for owner review of activity cutaways."""

from __future__ import annotations

from io import BytesIO
from typing import AsyncGenerator, Generator

import pytest
from PIL import Image
from playwright.async_api import Browser, async_playwright

from app.api import visuals as visuals_api
from app.core.config import settings
from app.services.visuals import activity_analysis_service as activity_analysis
from app.services.visuals import activity_library_service as activities
from tests.conftest import live_server


async def fake_activity_analysis(images: list[tuple[bytes, str]]) -> list[dict]:
    assert all(content and filename for content, filename in images)
    return [{
        "activity": "folding clothes",
        "context_tags": ["laundry room", "clothing care"],
        "aliases": ["fold laundry", "fold clothes"],
        "confidence": 0.96,
        "source": "local_ai",
    } for _image in images]


@pytest.fixture(scope="module")
def activity_live_server_url(tmp_path_factory: pytest.TempPathFactory) -> Generator[str, None, None]:
    pretend_image_python = tmp_path_factory.mktemp("activity-library-venv") / "python.exe"
    pretend_image_python.touch()
    with pytest.MonkeyPatch.context() as patch:
        patch.setattr(settings, "IMAGE_ENGINE", "fake")
        patch.setattr(settings, "AI_VISUALS_ENABLED", True)
        patch.setattr(visuals_api, "IMAGE_PYTHON", pretend_image_python)
        patch.setattr(activity_analysis, "analyze_activity_images", fake_activity_analysis)
        with live_server(tmp_path_factory, "activity-library-browser") as url:
            yield url


@pytest.fixture
async def activity_browser() -> AsyncGenerator[Browser, None]:
    async with async_playwright() as playwright:
        browser = await playwright.chromium.launch(headless=True)
        yield browser
        await browser.close()


@pytest.mark.asyncio
async def test_activity_picture_import_edit_and_review_from_shot_library(
    activity_browser: Browser, activity_live_server_url: str,
):
    inbox = activities.inbox_dir()
    inbox.mkdir(parents=True, exist_ok=True)
    Image.new("RGB", (1280, 720), (12, 80, 52)).save(inbox / "generic__cooking__kitchen__01.png")
    page = await activity_browser.new_page()
    await page.goto(f"{activity_live_server_url}/shots")
    await page.locator("#activity-import-card summary").click()
    await page.locator("#activity-import-btn").click()
    card = page.locator("#activity-grid .shot-card")
    await card.wait_for()
    assert "cooking · Generic" in await card.first.locator(".shot-title").text_content()
    await card.first.get_by_role("button", name="Preview / edit").click()
    await page.locator("#activity-dialog[open]").wait_for()
    await page.locator("#activity-name").fill("preparing dinner")
    await page.locator("#activity-context").fill("evening, kitchen")
    await page.locator("#activity-save-btn").click()
    await page.wait_for_function("!document.getElementById('activity-dialog').open")
    assert "preparing dinner" in await card.first.locator(".shot-title").text_content()
    await card.first.get_by_role("button", name="Approve").click()
    await page.locator("#activity-grid .shot-card.is-approved").wait_for()
    await page.select_option("#activity-filter-state", "approved")
    assert await page.locator("#activity-grid .shot-card").count() == 1
    await page.close()


@pytest.mark.asyncio
async def test_activity_picture_can_be_uploaded_without_using_the_inbox(
    activity_browser: Browser, activity_live_server_url: str,
):
    content = BytesIO()
    Image.new("RGB", (1280, 720), (80, 35, 120)).save(content, format="PNG")
    page = await activity_browser.new_page()
    await page.goto(f"{activity_live_server_url}/shots")
    await page.get_by_role("button", name="Add activity pictures").click()
    assert await page.locator("#activity-upload-name").count() == 0
    assert await page.get_by_role("radio", name="Generic").get_attribute("aria-checked") == "true"
    await page.locator("#activity-upload-file").set_input_files({
        "name": "any-name.png", "mimeType": "image/png", "buffer": content.getvalue(),
    })
    await page.get_by_role("button", name="Analyze and add").click()
    await page.wait_for_function("!document.getElementById('activity-upload-dialog').open")

    card = page.locator("#activity-grid .shot-card", has_text="folding clothes · Generic")
    await card.wait_for()
    assert "needs review" in await card.text_content()
    await page.close()
