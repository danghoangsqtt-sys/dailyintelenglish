"""Headless browser E2E tests for the Settings page (Task 18.3).

Mirrors tests/test_dashboard_browser.py's `browser_instance`/`live_server_url`
fixture pattern. Every `/api/settings*` call is mocked via Playwright's own
`page.route(...)` (same approach the dashboard test uses for `/api/projects`)
-- this file verifies the *frontend's* rendering/interaction, not the backend,
which tests/test_settings_api.py and tests/test_settings_service.py already
cover directly.
"""

import json
from typing import AsyncGenerator

import pytest
from playwright.async_api import Browser, async_playwright

from tests.conftest import live_server


@pytest.fixture(scope="module")
def live_server_url(tmp_path_factory: pytest.TempPathFactory):
    with live_server(tmp_path_factory, "settings") as url:
        yield url


@pytest.fixture
async def browser_instance() -> AsyncGenerator[Browser, None]:
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        yield browser
        await browser.close()


DEFAULT_STATUS = {
    "cloud_configured": True,
    "cloud_last4": "9999",
    "cloud_source": "env",
    "cloud_base_url": "https://openrouter.ai/api/v1",
    "cloud_model": "nvidia/nemotron-3-super-120b-a12b:free",
    "ai_mode": "local",
    "ai_mode_source": "env",
    "allow_cloud": True,
    "effective_mode": "local",
    "effective_reason": None,
}


async def _mock_settings(page, get_status: dict, *, on_put_ai_mode=None, on_put_cloud=None, on_test_connection=None) -> None:
    async def handle(route):
        url = route.request.url
        method = route.request.method
        if url.endswith("/api/settings") and method == "GET":
            await route.fulfill(status=200, content_type="application/json", body=json.dumps({"success": True, "data": get_status}))
        elif url.endswith("/api/settings/ai-mode") and method == "PUT":
            body = json.loads(route.request.post_data or "{}")
            data = on_put_ai_mode(body) if on_put_ai_mode else {**get_status, "ai_mode": body.get("ai_mode")}
            await route.fulfill(status=200, content_type="application/json", body=json.dumps({"success": True, "data": data}))
        elif url.endswith("/api/settings/cloud") and method == "PUT":
            body = json.loads(route.request.post_data or "{}")
            data = on_put_cloud(body) if on_put_cloud else get_status
            await route.fulfill(status=200, content_type="application/json", body=json.dumps({"success": True, "data": data}))
        elif url.endswith("/api/settings/cloud/api-key") and method == "DELETE":
            data = {**get_status, "cloud_configured": False, "cloud_last4": None, "cloud_source": "none"}
            await route.fulfill(status=200, content_type="application/json", body=json.dumps({"success": True, "data": data}))
        elif url.endswith("/api/settings/cloud/test-connection") and method == "POST":
            data = on_test_connection() if on_test_connection else {"ok": True}
            await route.fulfill(status=200, content_type="application/json", body=json.dumps({"success": True, "data": data}))
        else:
            await route.continue_()

    # A single trailing "*" only matches within one path segment (no "/"), so
    # "**/api/settings*" silently misses nested paths like
    # ".../cloud/test-connection" -- caught by a debug run that showed the
    # mock never intercepting that endpoint and a REAL call reaching
    # OpenRouter. "**" at the end matches across "/" boundaries too.
    await page.route("**/api/settings**", handle)


@pytest.mark.asyncio
async def test_settings_page_loads_and_shows_current_status(browser_instance: Browser, live_server_url: str):
    page = await browser_instance.new_page()
    await _mock_settings(page, DEFAULT_STATUS)
    await page.goto(f"{live_server_url}/settings")

    await page.wait_for_selector("#effective-mode-status")
    assert await page.locator("#ai-mode-local").is_checked()
    assert "9999" in (await page.locator("#cloud-key-status").text_content())
    assert await page.locator("#cloud-base-url").input_value() == "https://openrouter.ai/api/v1"
    await page.close()


@pytest.mark.asyncio
async def test_settings_save_round_trips_and_shows_masked_key(browser_instance: Browser, live_server_url: str):
    page = await browser_instance.new_page()
    saved_status = {**DEFAULT_STATUS, "cloud_base_url": "https://custom.example.com/v1", "cloud_model": "m/x", "cloud_last4": "abcd", "cloud_source": "database"}

    def on_put_cloud(_body):
        return saved_status

    await _mock_settings(page, DEFAULT_STATUS, on_put_cloud=on_put_cloud)
    await page.goto(f"{live_server_url}/settings")
    await page.wait_for_selector("#effective-mode-status")

    await page.fill("#cloud-base-url", "https://custom.example.com/v1")
    await page.fill("#cloud-model", "m/x")
    await page.fill("#cloud-api-key", "a-new-real-key")
    await _mock_settings(page, saved_status, on_put_cloud=on_put_cloud)  # GET refresh after save returns the saved status
    await page.click("#save-cloud-settings-btn")

    await page.wait_for_function("document.getElementById('save-status').textContent.includes('Saved')")
    assert "abcd" in (await page.locator("#cloud-key-status").text_content())
    # The key input is cleared after a successful save -- it's write-only, never redisplayed.
    assert await page.locator("#cloud-api-key").input_value() == ""
    await page.close()


@pytest.mark.asyncio
async def test_settings_clear_key_reverts_status_to_none(browser_instance: Browser, live_server_url: str):
    page = await browser_instance.new_page()
    configured_status = {**DEFAULT_STATUS, "cloud_configured": True, "cloud_last4": "9999", "cloud_source": "database"}
    cleared_status = {**DEFAULT_STATUS, "cloud_configured": False, "cloud_last4": None, "cloud_source": "none"}

    await _mock_settings(page, configured_status)
    await page.goto(f"{live_server_url}/settings")
    await page.wait_for_selector("#effective-mode-status")

    await _mock_settings(page, cleared_status)  # GET refresh after clearing returns "none"
    await page.click("#clear-cloud-key-btn")

    await page.wait_for_function("document.getElementById('cloud-key-status').textContent.includes('No key')")
    await page.close()


@pytest.mark.asyncio
async def test_settings_cloud_first_disabled_and_noted_when_allow_cloud_false(browser_instance: Browser, live_server_url: str):
    page = await browser_instance.new_page()
    status = {**DEFAULT_STATUS, "allow_cloud": False}
    await _mock_settings(page, status)
    await page.goto(f"{live_server_url}/settings")

    await page.wait_for_selector("#effective-mode-status")
    assert await page.locator("#ai-mode-cloud-first").is_disabled()
    assert not await page.locator("#ai-mode-disabled-note").is_hidden()
    assert "DIE_AI_ALLOW_CLOUD" in (await page.locator("#ai-mode-disabled-note").text_content())
    await page.close()


@pytest.mark.asyncio
async def test_settings_test_connection_shows_ok_on_success(browser_instance: Browser, live_server_url: str):
    page = await browser_instance.new_page()
    await _mock_settings(page, DEFAULT_STATUS, on_test_connection=lambda: {"ok": True})
    await page.goto(f"{live_server_url}/settings")
    await page.wait_for_selector("#effective-mode-status")

    await page.click("#test-connection-btn")
    await page.wait_for_function("document.getElementById('test-connection-result').textContent.trim() === 'OK'")
    await page.close()


@pytest.mark.asyncio
async def test_settings_test_connection_shows_error_class_and_status(browser_instance: Browser, live_server_url: str):
    page = await browser_instance.new_page()
    await _mock_settings(
        page, DEFAULT_STATUS, on_test_connection=lambda: {"ok": False, "error": "ProviderAuthError", "status": 401}
    )
    await page.goto(f"{live_server_url}/settings")
    await page.wait_for_selector("#effective-mode-status")

    await page.click("#test-connection-btn")
    await page.wait_for_function(
        "document.getElementById('test-connection-result').textContent.includes('ProviderAuthError')"
    )
    assert "401" in (await page.locator("#test-connection-result").text_content())
    await page.close()


@pytest.mark.asyncio
async def test_settings_selecting_cloud_first_with_no_key_shows_effective_local_with_reason(
    browser_instance: Browser, live_server_url: str
):
    """PM review C3's required scenario: select cloud_first with no key -> the
    page shows effective Local with the "no API key" reason."""
    page = await browser_instance.new_page()
    initial_status = {**DEFAULT_STATUS, "ai_mode": "local", "cloud_configured": False, "cloud_last4": None, "cloud_source": "none"}
    after_select_status = {
        **initial_status,
        "ai_mode": "cloud_first",
        "ai_mode_source": "database",
        "effective_mode": "local",
        "effective_reason": "no API key configured",
    }

    def on_put_ai_mode(_body):
        return after_select_status

    await _mock_settings(page, initial_status, on_put_ai_mode=on_put_ai_mode)
    await page.goto(f"{live_server_url}/settings")
    await page.wait_for_selector("#effective-mode-status")

    await _mock_settings(page, after_select_status, on_put_ai_mode=on_put_ai_mode)  # GET refresh after the PUT
    await page.check("#ai-mode-cloud-first")

    await page.wait_for_function(
        "document.getElementById('effective-mode-status').textContent.includes('no API key configured')"
    )
    status_text = await page.locator("#effective-mode-status").text_content()
    assert "Local" in status_text
    await page.close()
