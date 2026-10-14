"""Phase 32.6b browser contract for owner review of activity cutaways."""

from __future__ import annotations

from contextlib import nullcontext
from io import BytesIO
from typing import AsyncGenerator, Generator

import pytest
from PIL import Image
from playwright.async_api import Browser, async_playwright

from backend.api import visuals as visuals_api
from backend.core.config import settings
from backend.library import activity_library_service as activities
from tests.conftest import live_server
from tests.browser_confirm import answer_confirm


@pytest.fixture(scope="module")
def activity_live_server_url(tmp_path_factory: pytest.TempPathFactory) -> Generator[str, None, None]:
    pretend_image_python = tmp_path_factory.mktemp("activity-library-venv") / "python.exe"
    pretend_image_python.touch()
    with pytest.MonkeyPatch.context() as patch:
        patch.setattr(settings, "IMAGE_ENGINE", "fake")
        patch.setattr(settings, "AI_VISUALS_ENABLED", True)
        patch.setattr(visuals_api, "IMAGE_PYTHON", pretend_image_python)
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
async def test_activity_pictures_require_separate_owner_names_without_using_the_inbox(
    activity_browser: Browser, activity_live_server_url: str,
):
    east = BytesIO()
    west = BytesIO()
    Image.new("RGB", (1280, 720), (80, 35, 120)).save(east, format="PNG")
    Image.new("RGB", (1280, 720), (120, 35, 80)).save(west, format="PNG")
    page = await activity_browser.new_page()
    await page.goto(f"{activity_live_server_url}/shots")
    await page.get_by_role("button", name="Add activity pictures").click()
    assert await page.get_by_role("radio", name="Generic").get_attribute("aria-checked") == "true"
    assert await page.locator(".activity-upload-name").count() == 1
    await page.locator(".activity-upload-name").fill("go east")
    await page.locator(".activity-upload-context").fill("city, waterfront")
    east_file = {"name": "east.png", "mimeType": "image/png", "buffer": east.getvalue()}
    west_file = {"name": "west.png", "mimeType": "image/png", "buffer": west.getvalue()}
    await page.locator("#activity-upload-file").set_input_files([east_file, west_file])
    assert await page.locator("#activity-upload-filmstrip button").count() == 2
    assert await page.locator("#activity-upload-preview-count").text_content() == "Picture 1 of 2"
    await page.get_by_role("button", name="Next", exact=True).click()
    assert await page.locator("#activity-upload-preview-count").text_content() == "Picture 2 of 2"
    assert await page.locator("#activity-upload-preview-filename").text_content() == "west.png"
    assert await page.locator("#activity-upload-preview").get_attribute("src") == await page.locator("#activity-upload-filmstrip img").nth(1).get_attribute("src")
    assert await page.locator(".activity-upload-item:visible").count() == 1
    await page.get_by_role("button", name="Show picture 1 of 2").click()
    assert await page.locator("#activity-upload-preview-count").text_content() == "Picture 1 of 2"
    names = page.locator(".activity-upload-name")
    assert await names.count() == 2
    assert await names.nth(0).input_value() == "go east"
    assert await page.locator(".activity-upload-context").nth(0).input_value() == "city, waterfront"
    assert await page.locator("#activity-upload-submit").is_disabled()
    await page.get_by_role("button", name="Next picture").click()
    await names.nth(1).fill("go west")
    await page.locator(".activity-upload-aliases").nth(1).fill("head west")
    await page.get_by_role("button", name="Previous picture").click()
    await page.locator(".activity-upload-aliases").nth(0).fill("head east")
    await page.locator("#activity-upload-file").set_input_files([west_file, east_file])
    assert await names.nth(0).input_value() == "go west"
    assert await names.nth(1).input_value() == "go east"
    assert await page.locator(".activity-upload-context").nth(1).input_value() == "city, waterfront"
    await page.locator("#activity-upload-file").set_input_files([east_file, west_file])
    assert await names.nth(0).input_value() == "go east"
    assert await names.nth(1).input_value() == "go west"
    assert await page.locator("#activity-upload-submit").is_enabled()
    batch_upload = "**/api/visuals/library/activities/upload-batch"
    await page.route(batch_upload, lambda route: route.fulfill(status=503, json={"success": False, "error": "Temporary upload failure"}))
    await page.get_by_role("button", name="Add pictures").click()
    await page.locator("#activity-upload-message").get_by_text("Temporary upload failure").wait_for()
    assert await page.locator("#activity-upload-dialog").evaluate("dialog => dialog.open")
    await page.unroute(batch_upload)
    await page.route(batch_upload, lambda route: route.fulfill(status=404, json={"detail": "Not Found"}))
    await page.get_by_role("button", name="Add pictures").click()
    await page.wait_for_function("!document.getElementById('activity-upload-dialog').open")
    await page.locator("#activity-message").get_by_text("2 pictures added.").wait_for()
    await page.unroute(batch_upload)

    east_card = page.locator("#activity-grid .shot-card", has_text="go east")
    west_card = page.locator("#activity-grid .shot-card", has_text="go west")
    await east_card.wait_for()
    await west_card.wait_for()
    assert await east_card.count() == 1
    assert await west_card.count() == 1
    assert "city" in await east_card.locator(".shot-meta").text_content()
    assert "needs review" in await east_card.text_content()
    approve_all = page.locator("#activity-approve-all-btn")
    await page.wait_for_function("!document.getElementById('activity-approve-all-btn').disabled")
    assert await approve_all.is_enabled()
    await approve_all.click()
    await answer_confirm(page, accept=False)
    assert "needs review" in await east_card.text_content()
    batch_route = "**/api/visuals/library/activities/approve-batch"
    await page.route(batch_route, lambda route: route.fulfill(status=404, json={"detail": "Not Found"}))
    review_calls = []

    async def interrupt_second_review(route):
        review_calls.append(route.request.url)
        if len(review_calls) == 2:
            await route.fulfill(status=503, json={"success": False, "error": "Temporary failure"})
        else:
            await route.continue_()

    review_route = "**/api/visuals/library/activities/*/review"
    await page.route(review_route, interrupt_second_review)
    await approve_all.click()
    await answer_confirm(page, accept=True)
    await page.locator("#activity-message").get_by_text("Approved 1 of 2 pictures.", exact=False).wait_for()
    assert await page.locator("#activity-grid .shot-card.is-pending").count() == 1
    await page.unroute(review_route)
    await approve_all.click()
    await answer_confirm(page, accept=True)
    await page.locator("#activity-message").get_by_text("1 activity picture approved.").wait_for()
    assert await page.locator("#activity-grid .shot-card.is-approved").count() >= 2
    assert await approve_all.is_disabled()
    await page.unroute(batch_route)
    delete_east = east_card.get_by_role("button", name="Delete")
    await delete_east.click()
    await answer_confirm(page, accept=False)
    assert await east_card.count() == 1
    await delete_east.click()
    await answer_confirm(page, accept=True)
    await east_card.wait_for(state="detached")
    assert await page.locator("#activity-message").text_content() == "Activity picture deleted."
    assert await west_card.count() == 1
    await page.close()


@pytest.mark.asyncio
async def test_select_arbitrary_activity_pictures_for_review_and_delete(
    activity_browser: Browser, activity_live_server_url: str,
):
    with nullcontext(activity_live_server_url) as url:
        page = await activity_browser.new_page()
        await page.goto(f"{url}/shots")
        await page.get_by_role("button", name="Add activity pictures").click()
        pictures = []
        for index in range(4):
            content = BytesIO()
            Image.new("RGB", (1280, 720), (35 + index * 25, 70, 105)).save(content, format="PNG")
            pictures.append({"name": f"multi-{index}.png", "mimeType": "image/png", "buffer": content.getvalue()})
        await page.locator("#activity-upload-file").set_input_files(pictures)
        assert await page.locator("#activity-upload-filmstrip button").count() == 4
        await page.get_by_role("button", name="Show picture 4 of 4").click()
        assert await page.locator("#activity-upload-preview-count").text_content() == "Picture 4 of 4"
        assert await page.locator("#activity-upload-preview-filename").text_content() == "multi-3.png"
        assert await page.locator("#activity-upload-items .activity-upload-item.is-previewed").count() == 1
        for index, name in enumerate(("multi alpha", "multi beta", "multi gamma", "multi delta")):
            await page.get_by_role("button", name=f"Show picture {index + 1} of 4").click()
            await page.locator(".activity-upload-item:visible .activity-upload-name").fill(name)
        assert await page.locator("#activity-upload-progress").text_content() == "Editing picture 4 of 4 · 4 named"
        await page.get_by_role("button", name="Add pictures").click()
        await page.wait_for_function("!document.getElementById('activity-upload-dialog').open")

        alpha = page.locator("#activity-grid .shot-card", has_text="multi alpha")
        beta = page.locator("#activity-grid .shot-card", has_text="multi beta")
        gamma = page.locator("#activity-grid .shot-card", has_text="multi gamma")
        delta = page.locator("#activity-grid .shot-card", has_text="multi delta")
        await alpha.locator(".activity-select-checkbox").check()
        await gamma.locator(".activity-select-checkbox").check()
        assert await page.locator("#activity-selected-count").text_content() == "2 selected"
        assert not await beta.locator(".activity-select-checkbox").is_checked()
        approve = page.get_by_role("button", name="Approve selected")
        await approve.click()
        await answer_confirm(page, accept=False)
        assert "needs review" in await alpha.text_content()

        review_calls = []

        async def interrupt_second_review(route):
            review_calls.append(route.request.url)
            if len(review_calls) == 2:
                await route.fulfill(status=503, json={"success": False, "error": "Temporary failure"})
            else:
                await route.continue_()

        review_route = "**/api/visuals/library/activities/*/review"
        await page.route(review_route, interrupt_second_review)
        await approve.click()
        await answer_confirm(page, accept=True)
        await page.locator("#activity-message").get_by_text("1 of 2 pictures approved.", exact=False).wait_for()
        assert await page.locator("#activity-selected-count").text_content() == "1 selected"
        await page.unroute(review_route)
        await approve.click()
        await answer_confirm(page, accept=True)
        await page.locator("#activity-message").get_by_text("1 activity picture approved.").wait_for()
        assert "approved" in await alpha.text_content()
        assert "approved" in await gamma.text_content()
        assert "needs review" in await beta.text_content()

        await beta.locator(".activity-select-checkbox").check()
        await gamma.locator(".activity-select-checkbox").check()
        await page.get_by_role("button", name="Reject selected").click()
        await answer_confirm(page, accept=True)
        await page.locator("#activity-message").get_by_text("2 activity pictures rejected.").wait_for()
        assert "rejected" in await beta.text_content()
        assert "rejected" in await gamma.text_content()
        assert "approved" in await alpha.text_content()

        await page.select_option("#activity-filter-state", "pending")
        await delta.wait_for()
        pending_count = await page.locator("#activity-grid .shot-card").count()
        await page.locator("#activity-select-all").check()
        assert await page.locator("#activity-selected-count").text_content() == f"{pending_count} selected"
        await page.select_option("#activity-filter-state", "")
        await alpha.wait_for()
        assert await page.locator("#activity-selected-count").text_content() == "0 selected"
        await alpha.locator(".activity-select-checkbox").check()
        await gamma.locator(".activity-select-checkbox").check()
        delete = page.get_by_role("button", name="Delete selected")
        await delete.click()
        await answer_confirm(page, accept=False)
        assert await alpha.count() == 1
        delete_route = "**/api/visuals/library/activities/*"

        async def unavailable_delete(route):
            if route.request.method == "DELETE":
                await route.fulfill(status=405, json={"detail": "Method Not Allowed"})
            else:
                await route.continue_()

        await page.route(delete_route, unavailable_delete)
        await delete.click()
        await answer_confirm(page, accept=True)
        await page.locator("#activity-message").get_by_text("Restart the app to enable image deletion.", exact=False).wait_for()
        assert await page.locator("#activity-selected-count").text_content() == "2 selected"
        await page.unroute(delete_route)
        await delete.click()
        await answer_confirm(page, accept=True)
        await page.locator("#activity-message").get_by_text("2 activity pictures deleted.").wait_for()
        assert await alpha.count() == 0
        assert await gamma.count() == 0
        assert await beta.count() == 1
        assert await delta.count() == 1
        assert await page.locator("#activity-selected-count").text_content() == "0 selected"
        await page.close()
