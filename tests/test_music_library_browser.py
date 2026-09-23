"""Playwright E2E coverage for the Music Library UI."""

import asyncio
import json
from typing import AsyncGenerator, Generator

import pytest
from playwright.async_api import Browser, Dialog, async_playwright

from app.core.config import settings
from tests.conftest import live_server

VALID_MP3 = b"ID3\x04\x00\x00\x00\x00\x00\x00browser-music"


@pytest.fixture(scope="module")
def live_server_url(tmp_path_factory: pytest.TempPathFactory) -> Generator[str, None, None]:
    with live_server(tmp_path_factory, "music-browser") as url:
        yield url


@pytest.fixture(autouse=True)
def empty_music_library(live_server_url: str) -> None:
    """Reset browser-test storage without changing the configured directory."""
    music_dir = settings.DATA_DIR / "music_library"
    music_dir.mkdir(parents=True, exist_ok=True)
    for path in music_dir.iterdir():
        if path.is_file():
            path.unlink()


@pytest.fixture
async def browser_instance() -> AsyncGenerator[Browser, None]:
    async with async_playwright() as playwright:
        browser = await playwright.chromium.launch(headless=True)
        yield browser
        await browser.close()


def _file_payload(content: bytes = VALID_MP3) -> dict:
    return {"name": "calm theme.mp3", "mimeType": "audio/mpeg", "buffer": content}


@pytest.mark.asyncio
async def test_upload_preview_and_reload_persistence(
    browser_instance: Browser, live_server_url: str
):
    page = await browser_instance.new_page()
    await page.goto(f"{live_server_url}/music")
    await page.locator("#music-file-input").set_input_files(_file_payload())

    card = page.locator("[data-filename='calm theme.mp3']")
    await card.wait_for()
    assert "calm theme.mp3" in await card.locator(".track-name").text_content()
    assert "/api/music/calm%20theme.mp3" in await card.locator("audio").get_attribute("src")

    await page.reload()
    await page.locator("[data-filename='calm theme.mp3']").wait_for()
    assert await page.locator(".track-card").count() == 1
    await page.close()


@pytest.mark.asyncio
async def test_delete_requires_confirmation_and_removes_track(
    browser_instance: Browser, live_server_url: str
):
    music_dir = settings.DATA_DIR / "music_library"
    (music_dir / "delete-me.mp3").write_bytes(VALID_MP3)
    page = await browser_instance.new_page()
    await page.goto(f"{live_server_url}/music")
    card = page.locator("[data-filename='delete-me.mp3']")
    await card.wait_for()

    async def dismiss_dialog(dialog: Dialog) -> None:
        await dialog.dismiss()

    page.on("dialog", dismiss_dialog)
    await card.locator("[data-action='delete']").click()
    assert await card.count() == 1
    assert (music_dir / "delete-me.mp3").exists()

    page.remove_listener("dialog", dismiss_dialog)
    page.once("dialog", lambda dialog: dialog.accept())
    await card.locator("[data-action='delete']").click()
    await card.wait_for(state="detached")
    assert not (music_dir / "delete-me.mp3").exists()
    await page.close()


@pytest.mark.asyncio
async def test_invalid_magic_bytes_show_friendly_error_only(
    browser_instance: Browser, live_server_url: str
):
    page = await browser_instance.new_page()
    await page.goto(f"{live_server_url}/music")
    await page.locator("#music-file-input").set_input_files(_file_payload(b"not-an-mp3"))

    error = page.locator("#error-message")
    await error.wait_for(state="visible")
    assert await error.text_content() == (
        "We couldn't upload that music file. Check the format and try again."
    )
    assert "header bytes" not in await page.locator("body").text_content()
    await page.close()


@pytest.mark.asyncio
async def test_rapid_repeated_upload_is_coalesced_to_one_request(
    browser_instance: Browser, live_server_url: str
):
    page = await browser_instance.new_page()
    upload_requests = 0

    async def delay_upload(route):
        nonlocal upload_requests
        if route.request.method == "POST":
            upload_requests += 1
            await asyncio.sleep(0.15)
            await route.fulfill(
                status=200,
                content_type="application/json",
                body=json.dumps(
                    {
                        "success": True,
                        "data": {
                            "filename": "calm theme.mp3",
                            "size_bytes": len(VALID_MP3),
                            "content_url": "/api/music/calm%20theme.mp3",
                        },
                        "error": None,
                        "meta": {},
                    }
                ),
            )
        else:
            await route.continue_()

    await page.route("**/api/music", delay_upload)
    await page.goto(f"{live_server_url}/music")
    input_element = page.locator("#music-file-input")
    await input_element.set_input_files(_file_payload())
    await page.evaluate(
        "document.getElementById('music-file-input').dispatchEvent(new Event('change'))"
    )
    await page.locator("#status-message").wait_for(state="visible")

    assert upload_requests == 1
    await page.close()
