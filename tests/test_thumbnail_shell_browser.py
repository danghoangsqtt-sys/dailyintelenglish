"""Browser coverage for Task 4.2d's Thumbnail Generator shell."""

import json
from typing import AsyncGenerator
from urllib.parse import urlparse

import pytest
from playwright.async_api import Browser, Page, Route, async_playwright

from tests.conftest import live_server

PROJECT_ID = "thumbnail-shell-project"
PROJECT = {
    "id": PROJECT_ID,
    "name": "Thumbnail Shell Test",
    "status": "video_generated",
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
    )
]


@pytest.fixture(scope="module")
def live_server_url(tmp_path_factory: pytest.TempPathFactory):
    with live_server(tmp_path_factory, "thumbnail-shell") as url:
        yield url


@pytest.fixture
async def browser_instance() -> AsyncGenerator[Browser, None]:
    async with async_playwright() as playwright:
        browser = await playwright.chromium.launch(headless=True)
        yield browser
        await browser.close()


def _envelope(data, error=None) -> str:
    return json.dumps(
        {"success": error is None, "data": data, "error": error, "meta": {}}
    )


def _variant(
    index: int,
    *,
    selected: bool = False,
    revision: str | None = None,
    headline: str | None = None,
    palette: dict | None = None,
) -> dict:
    thumbnail_id = f"thumbnail-shell-{index}"
    revision = revision or f"shell-revision-{index}"
    image_name = ("minimal_clean", "gradient_bold", "modern_split")[index % 3]
    image_url = f"/static/thumbnail_templates/{image_name}.png?revision={revision}"
    return {
        "id": thumbnail_id,
        "project_id": PROJECT_ID,
        "template_name": "minimal_clean",
        "variant_index": index,
        "is_selected": selected,
        "created_at": "2026-09-16T00:00:00Z",
        "revision": revision,
        "suggestion": {
            "headline": headline or f"Future English {index + 1}",
            "supporting_text": "Practical English for tomorrow",
            "topic_keywords": ["English", f"future-{index + 1}"],
            "palette": palette
            or {
                "primary": "#111827",
                "secondary": "#60A5FA",
                "accent": "#F59E0B",
                "text": "#FFFFFF",
            },
        },
        "assets": {
            aspect: {image_format: image_url for image_format in ("png", "jpg")}
            for aspect in ("16x9", "9x16")
        },
    }


async def _mock_thumbnail_routes(
    page: Page,
    thumbnails: list[dict],
    *,
    patch_payloads: list[dict] | None = None,
) -> None:
    async def handle(route: Route) -> None:
        path = urlparse(route.request.url).path
        method = route.request.method
        if path == f"/api/projects/{PROJECT_ID}" and method == "GET":
            await route.fulfill(
                status=200,
                content_type="application/json",
                body=_envelope(PROJECT),
            )
        elif path == "/api/thumbnails/templates" and method == "GET":
            await route.fulfill(
                status=200,
                content_type="application/json",
                body=_envelope(TEMPLATES),
            )
        elif path == f"/api/projects/{PROJECT_ID}/thumbnails" and method == "GET":
            await route.fulfill(
                status=200,
                content_type="application/json",
                body=_envelope(thumbnails),
            )
        elif path.endswith("/thumbnails/generate") and method == "POST":
            payload = route.request.post_data_json
            thumbnails[:] = [_variant(index) for index in range(payload["variant_count"])]
            await route.fulfill(
                status=200,
                content_type="application/json",
                body=_envelope(thumbnails),
            )
        elif path.endswith("/favorite") and method == "PUT":
            thumbnail_id = path.split("/")[-2]
            for thumbnail in thumbnails:
                thumbnail["is_selected"] = thumbnail["id"] == thumbnail_id
            selected = next(
                thumbnail for thumbnail in thumbnails if thumbnail["is_selected"]
            )
            await route.fulfill(
                status=200,
                content_type="application/json",
                body=_envelope(selected),
            )
        elif "/thumbnails/" in path and method == "PATCH":
            payload = route.request.post_data_json
            if patch_payloads is not None:
                patch_payloads.append(payload)
            thumbnail_id = path.split("/")[-1]
            selected_index = next(
                index
                for index, thumbnail in enumerate(thumbnails)
                if thumbnail["id"] == thumbnail_id
            )
            updated = _variant(
                selected_index,
                selected=True,
                revision="shell-revision-updated",
                headline=payload["headline"],
                palette=payload["palette"],
            )
            thumbnails[selected_index] = updated
            await route.fulfill(
                status=200,
                content_type="application/json",
                body=_envelope(updated),
            )
        else:
            await route.continue_()

    await page.route("**/api/**", handle)


@pytest.mark.asyncio
async def test_thumbnail_shell_structure_resizes_and_sidebar_toggles(
    browser_instance: Browser, live_server_url: str
) -> None:
    page = await browser_instance.new_page(viewport={"width": 1440, "height": 900})
    thumbnails = [_variant(0, selected=True), _variant(1), _variant(2)]
    await _mock_thumbnail_routes(page, thumbnails)
    await page.goto(f"{live_server_url}/step6?project_id={PROJECT_ID}")
    await page.wait_for_selector("#workspace:not([hidden])")

    assert await page.locator("#pane-sidebar .step-nav-workflow").count() == 1
    assert await page.locator("#pane-stage #generator-section").count() == 1
    assert await page.locator("#pane-stage #variants-section").count() == 1
    assert await page.locator("#pane-inspector #editor-section").count() == 1
    assert await page.locator("#pane-timeline, #resizer-top").count() == 0

    sidebar_before = await page.locator("#pane-sidebar").bounding_box()
    left_handle = await page.locator("#resizer-left").bounding_box()
    assert sidebar_before and left_handle
    await page.mouse.move(left_handle["x"] + 2, left_handle["y"] + 30)
    await page.mouse.down()
    await page.mouse.move(left_handle["x"] + 102, left_handle["y"] + 30)
    await page.mouse.up()
    sidebar_after = await page.locator("#pane-sidebar").bounding_box()
    assert sidebar_after and sidebar_after["width"] > sidebar_before["width"] + 70

    inspector_before = await page.locator("#pane-inspector").bounding_box()
    right_handle = await page.locator("#resizer-right").bounding_box()
    assert inspector_before and right_handle
    await page.mouse.move(right_handle["x"] + 2, right_handle["y"] + 30)
    await page.mouse.down()
    await page.mouse.move(right_handle["x"] - 82, right_handle["y"] + 30)
    await page.mouse.up()
    inspector_after = await page.locator("#pane-inspector").bounding_box()
    assert inspector_after and inspector_after["width"] > inspector_before["width"] + 70

    await page.click("#sidebar-collapse-btn")
    assert await page.locator("#pane-sidebar").evaluate(
        "element => element.classList.contains('collapsed')"
    )
    assert await page.locator("#sidebar-collapse-btn").get_attribute("aria-expanded") == "false"

    await page.click("#sidebar-collapse-btn")
    assert not await page.locator("#pane-sidebar").evaluate(
        "element => element.classList.contains('collapsed')"
    )
    assert await page.locator("#sidebar-collapse-btn").get_attribute("aria-expanded") == "true"
    await page.close()


@pytest.mark.asyncio
async def test_generated_favorite_editor_autosaves_once_inside_inspector(
    browser_instance: Browser, live_server_url: str
) -> None:
    page = await browser_instance.new_page(viewport={"width": 1440, "height": 900})
    thumbnails: list[dict] = []
    patch_payloads: list[dict] = []
    await _mock_thumbnail_routes(page, thumbnails, patch_payloads=patch_payloads)
    await page.goto(f"{live_server_url}/step6?project_id={PROJECT_ID}")
    await page.wait_for_selector("#workspace:not([hidden])")

    await page.click("#generate-btn")
    await page.wait_for_selector(".variant-card")
    assert await page.locator(".variant-card").count() == 3

    await page.click("[data-thumbnail-id='thumbnail-shell-1']")
    await page.wait_for_selector("#pane-inspector #editor-layout:not([hidden])")
    assert await page.locator(".variant-card.selected").get_attribute(
        "data-thumbnail-id"
    ) == "thumbnail-shell-1"

    await page.locator("#headline-input").fill("One debounced inspector edit")
    await page.locator("#color-accent").fill("#12abef")
    await page.wait_for_timeout(900)

    assert len(patch_payloads) == 1
    assert patch_payloads[0]["headline"] == "One debounced inspector edit"
    assert patch_payloads[0]["palette"]["accent"] == "#12ABEF"
    assert "revision=shell-revision-updated" in await page.locator(
        "#preview-image"
    ).get_attribute("src")
    await page.close()
