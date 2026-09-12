"""Real-Chromium coverage for the interactive Step 6 thumbnail state machine."""

import asyncio
import json
import socket
import threading
import time
from pathlib import Path
from typing import AsyncGenerator, Generator
from urllib.parse import urlparse

import pytest
import uvicorn
from playwright.async_api import Browser, Route, async_playwright

from app.core.config import settings
from app.main import app

PROJECT = {
    "id": "thumbnail-ui-project",
    "name": "Thumbnail UI Episode",
    "topic": "Practical English for future careers",
    "cefr_level": "B2",
    "genre": "debate",
}

TEMPLATES = [
    {
        "id": template_id,
        "display_name": display_name,
        "description": f"{display_name} thumbnail layout",
        "preview_url": f"/static/thumbnail_templates/{template_id}.png",
    }
    for template_id, display_name in (
        ("minimal_clean", "Minimal Clean"),
        ("gradient_bold", "Gradient Bold"),
        ("modern_split", "Modern Split"),
        ("dynamic_wave", "Dynamic Wave"),
        ("podcast_classic", "Podcast Classic"),
    )
]


def envelope(data: object = None, *, error: str | None = None) -> str:
    """Build the application's standard JSON response envelope."""
    return json.dumps(
        {
            "success": error is None,
            "data": data,
            "error": error,
            "meta": {},
        }
    )


def variant(
    index: int,
    *,
    selected: bool = False,
    revision: str | None = None,
    headline: str | None = None,
    template_name: str = "minimal_clean",
) -> dict:
    """Build one public thumbnail record consumed by the browser UI."""
    thumbnail_id = f"00000000-0000-0000-0000-00000000010{index}"
    revision = revision or thumbnail_id
    base = f"/api/projects/{PROJECT['id']}/thumbnails/{thumbnail_id}"
    return {
        "id": thumbnail_id,
        "project_id": PROJECT["id"],
        "template_name": template_name,
        "variant_index": index,
        "is_selected": selected,
        "created_at": "2026-09-12T00:00:00Z",
        "revision": revision,
        "suggestion": {
            "headline": headline or f"Future English {index + 1}",
            "supporting_text": "Practical English for tomorrow",
            "topic_keywords": ["English", f"future-{index + 1}"],
            "palette": {
                "primary": "#111827",
                "secondary": "#60A5FA",
                "accent": "#F59E0B",
                "text": "#FFFFFF",
            },
        },
        "assets": {
            aspect: {
                image_format: f"{base}/{aspect}.{image_format}?revision={revision}"
                for image_format in ("png", "jpg")
            }
            for aspect in ("16x9", "9x16")
        },
    }


def _find_free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as listener:
        listener.bind(("127.0.0.1", 0))
        return listener.getsockname()[1]


@pytest.fixture(scope="module")
def live_server_url(tmp_path_factory: pytest.TempPathFactory) -> Generator[str, None, None]:
    """Serve the real Step 6 page and static assets with isolated runtime storage."""
    original_data_dir = settings.DATA_DIR
    settings.DATA_DIR = Path(tmp_path_factory.mktemp("thumbnail-browser-data"))
    port = _find_free_port()
    server = uvicorn.Server(
        uvicorn.Config(app, host="127.0.0.1", port=port, log_level="warning")
    )
    thread = threading.Thread(target=server.run, daemon=True)
    thread.start()
    started_at = time.time()
    while time.time() - started_at < 10:
        try:
            with socket.create_connection(("127.0.0.1", port), timeout=0.5):
                break
        except OSError:
            time.sleep(0.1)
    else:
        raise RuntimeError("Live test server failed to start within 10 seconds")

    yield f"http://127.0.0.1:{port}"
    server.should_exit = True
    thread.join(timeout=10)
    settings.DATA_DIR = original_data_dir


@pytest.fixture
async def browser_instance() -> AsyncGenerator[Browser, None]:
    """Launch a real headless Chromium instance for one UI scenario."""
    async with async_playwright() as playwright:
        browser = await playwright.chromium.launch(headless=True)
        yield browser
        await browser.close()


async def fulfill_json(route: Route, data: object = None, *, status: int = 200, error=None):
    """Fulfill one intercepted API request with the standard response envelope."""
    await route.fulfill(
        status=status,
        content_type="application/json",
        body=envelope(data, error=error),
    )


async def install_base_routes(page, thumbnails: list[dict], extra_handler=None) -> None:
    """Install stateful project/template/list mocks and delegate mutation requests."""

    async def handle(route: Route) -> None:
        path = urlparse(route.request.url).path
        method = route.request.method
        if path == f"/api/projects/{PROJECT['id']}" and method == "GET":
            await fulfill_json(route, PROJECT)
        elif path == "/api/thumbnails/templates" and method == "GET":
            await fulfill_json(route, TEMPLATES)
        elif path == f"/api/projects/{PROJECT['id']}/thumbnails" and method == "GET":
            await fulfill_json(route, thumbnails)
        elif extra_handler and await extra_handler(route, path, method):
            return
        else:
            await route.continue_()

    await page.route("**/api/**", handle)


@pytest.mark.asyncio
async def test_template_generation_double_submit_lock(
    browser_instance: Browser,
    live_server_url: str,
) -> None:
    page = await browser_instance.new_page()
    thumbnails: list[dict] = []
    generate_calls = 0

    async def mutations(route: Route, path: str, method: str) -> bool:
        nonlocal generate_calls
        if path.endswith("/thumbnails/generate") and method == "POST":
            generate_calls += 1
            await asyncio.sleep(0.15)
            request = route.request.post_data_json
            thumbnails.extend(
                variant(index, template_name=request["template_name"])
                for index in range(request["variant_count"])
            )
            await fulfill_json(route, thumbnails)
            return True
        return False

    await install_base_routes(page, thumbnails, mutations)
    await page.goto(f"{live_server_url}/step6?project_id={PROJECT['id']}")
    await page.locator("#workspace").wait_for()
    assert await page.locator(".template-option").count() == 5
    await page.locator('[data-template-id="gradient_bold"]').click()
    await page.select_option("#variant-count", "3")
    await page.evaluate(
        "const button = document.getElementById('generate-btn'); button.click(); button.click();"
    )

    await page.locator(".variant-card").first.wait_for()
    assert generate_calls == 1
    assert await page.locator(".variant-card").count() == 3
    assert await page.locator('[data-template-id="gradient_bold"]').get_attribute(
        "aria-pressed"
    ) == "true"
    await page.close()


@pytest.mark.asyncio
async def test_favorite_preview_downloads_and_reload_persistence(
    browser_instance: Browser,
    live_server_url: str,
) -> None:
    page = await browser_instance.new_page()
    thumbnails = [variant(index) for index in range(3)]

    async def mutations(route: Route, path: str, method: str) -> bool:
        if path.endswith("/favorite") and method == "PUT":
            thumbnail_id = path.split("/")[-2]
            for item in thumbnails:
                item["is_selected"] = item["id"] == thumbnail_id
            await fulfill_json(route, next(item for item in thumbnails if item["is_selected"]))
            return True
        return False

    await install_base_routes(page, thumbnails, mutations)
    await page.goto(f"{live_server_url}/step6?project_id={PROJECT['id']}")
    await page.locator('[data-thumbnail-id="00000000-0000-0000-0000-000000000101"]').click()
    await page.locator("#editor-layout").wait_for()
    assert await page.locator(".variant-card.selected").get_attribute("data-thumbnail-id") == (
        "00000000-0000-0000-0000-000000000101"
    )

    await page.locator('[data-aspect="9x16"]').click()
    assert "/9x16.png?revision=" in await page.locator("#preview-image").get_attribute("src")
    for aspect in ("16x9", "9x16"):
        for image_format in ("png", "jpg"):
            link = page.locator(f"#download-{aspect}-{image_format}")
            assert f"/{aspect}.{image_format}?revision=" in await link.get_attribute("href")
            assert await link.get_attribute("download") == f"thumbnail-2-{aspect}.{image_format}"

    await page.reload()
    await page.locator("#editor-layout").wait_for()
    assert await page.locator(".variant-card.selected").get_attribute("data-thumbnail-id") == (
        "00000000-0000-0000-0000-000000000101"
    )
    assert await page.locator("#headline-input").input_value() == "Future English 2"
    await page.close()


@pytest.mark.asyncio
async def test_edit_re_render_serializes_one_trailing_save_with_latest_draft(
    browser_instance: Browser,
    live_server_url: str,
) -> None:
    page = await browser_instance.new_page()
    thumbnails = [variant(0, selected=True), variant(1), variant(2)]
    payloads: list[dict] = []
    first_started = asyncio.Event()
    second_finished = asyncio.Event()

    async def mutations(route: Route, path: str, method: str) -> bool:
        if method == "PATCH":
            payload = route.request.post_data_json
            payloads.append(payload)
            if len(payloads) == 1:
                first_started.set()
                await asyncio.sleep(0.2)
            revision = f"00000000-0000-0000-0000-00000000020{len(payloads)}"
            updated = variant(
                0,
                selected=True,
                revision=revision,
                headline=payload["headline"],
            )
            updated["suggestion"]["palette"] = payload["palette"]
            thumbnails[0] = updated
            await fulfill_json(route, updated)
            if len(payloads) == 2:
                second_finished.set()
            return True
        return False

    await install_base_routes(page, thumbnails, mutations)
    await page.goto(f"{live_server_url}/step6?project_id={PROJECT['id']}")
    await page.locator("#editor-layout").wait_for()
    await page.locator("#headline-input").fill("First headline edit")
    await asyncio.wait_for(first_started.wait(), timeout=3)
    await page.locator("#headline-input").fill("Latest coalesced headline")
    await page.locator("#color-accent").fill("#12abef")
    await asyncio.wait_for(second_finished.wait(), timeout=3)
    await page.wait_for_function("document.getElementById('save-status').textContent !== 'Saving and re-rendering…'")

    assert len(payloads) == 2
    assert payloads[0]["headline"] == "First headline edit"
    assert payloads[1]["headline"] == "Latest coalesced headline"
    assert payloads[1]["palette"]["accent"] == "#12ABEF"
    assert payloads[1]["revision"] == "00000000-0000-0000-0000-000000000201"
    assert "revision=00000000-0000-0000-0000-000000000202" in await page.locator(
        "#preview-image"
    ).get_attribute("src")
    await page.close()


@pytest.mark.asyncio
async def test_failed_save_is_friendly_and_retry_recovers(
    browser_instance: Browser,
    live_server_url: str,
) -> None:
    page = await browser_instance.new_page()
    thumbnails = [variant(0, selected=True), variant(1), variant(2)]
    patch_calls = 0

    async def mutations(route: Route, path: str, method: str) -> bool:
        nonlocal patch_calls
        if method == "PATCH":
            patch_calls += 1
            payload = route.request.post_data_json
            if patch_calls == 1:
                await fulfill_json(
                    route,
                    status=500,
                    error="sqlite raw internal path C:\\private\\thumbnails",
                )
            else:
                updated = variant(
                    0,
                    selected=True,
                    revision="00000000-0000-0000-0000-000000000299",
                    headline=payload["headline"],
                )
                thumbnails[0] = updated
                await fulfill_json(route, updated)
            return True
        return False

    await install_base_routes(page, thumbnails, mutations)
    await page.goto(f"{live_server_url}/step6?project_id={PROJECT['id']}")
    await page.locator("#headline-input").fill("Recoverable edit")
    await page.locator("#retry-save-btn").wait_for()
    await page.locator("#error-banner").wait_for()
    body_text = await page.locator("body").text_content()
    assert "sqlite raw internal path" not in body_text
    assert await page.locator("#error-banner").text_content() == (
        "We couldn't save and re-render this thumbnail. Please click Retry."
    )

    await page.locator("#retry-save-btn").click()
    await page.wait_for_function(
        "document.getElementById('save-status').textContent === 'Saved' || document.getElementById('save-status').textContent === ''"
    )
    assert patch_calls == 2
    assert "revision=00000000-0000-0000-0000-000000000299" in await page.locator(
        "#preview-image"
    ).get_attribute("src")
    await page.close()


@pytest.mark.asyncio
async def test_stale_revision_error_shows_reload_guidance_without_raw_detail(
    browser_instance: Browser,
    live_server_url: str,
) -> None:
    page = await browser_instance.new_page()
    thumbnails = [variant(0, selected=True), variant(1), variant(2)]

    async def mutations(route: Route, path: str, method: str) -> bool:
        if method == "PATCH":
            await fulfill_json(
                route,
                status=409,
                error="CAS mismatch at D:\\private\\revision-directory",
            )
            return True
        return False

    await install_base_routes(page, thumbnails, mutations)
    await page.goto(f"{live_server_url}/step6?project_id={PROJECT['id']}")
    await page.locator("#headline-input").fill("Conflicting edit")
    await page.locator("#error-banner").wait_for()

    body_text = await page.locator("body").text_content()
    assert "CAS mismatch" not in body_text
    assert await page.locator("#error-banner").text_content() == (
        "This thumbnail changed in another request. Refresh the page before trying again."
    )
    assert "changed elsewhere" in await page.locator("#save-status").text_content()
    assert await page.locator("#retry-save-btn").text_content() == "Reload latest"
    assert await page.locator("#headline-input").is_disabled()
    assert await page.locator("#download-16x9-png").get_attribute("aria-disabled") == "true"
    await page.close()


@pytest.mark.asyncio
async def test_dirty_editor_registers_beforeunload_guard(
    browser_instance: Browser,
    live_server_url: str,
) -> None:
    page = await browser_instance.new_page()
    thumbnails = [variant(0, selected=True), variant(1), variant(2)]
    await install_base_routes(page, thumbnails)
    await page.goto(f"{live_server_url}/step6?project_id={PROJECT['id']}")
    await page.locator("#headline-input").fill("Unsaved navigation guard")

    prevented = await page.evaluate(
        """() => {
          const event = new Event('beforeunload', { cancelable: true });
          window.dispatchEvent(event);
          return event.defaultPrevented;
        }"""
    )

    assert prevented is True
    await page.close()
