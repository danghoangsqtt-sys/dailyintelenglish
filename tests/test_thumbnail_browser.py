"""Real-Chromium coverage for the interactive Step 6 thumbnail state machine."""

import asyncio
import json
from typing import AsyncGenerator, Generator
from urllib.parse import urlparse

import pytest
from playwright.async_api import Browser, Route, async_playwright

from tests.browser_confirm import answer_confirm
from tests.conftest import live_server

PROJECT = {
    "id": "thumbnail-ui-project",
    "name": "Thumbnail UI Episode",
    "topic": "Practical English for future careers",
    "cefr_level": "B2",
    "genre": "debate",
}

TEMPLATES = [  # Task 36.3/36.4 (D92): the two thumbnail kinds
    {"id": "composed", "display_name": "Characters + illustration", "description": "composed", "available": True,
     "preview_url": "/static/thumbnail_templates/composed.png"},
    {"id": "outside_ai", "display_name": "Your outside-AI picture", "description": "outside", "available": True,
     "preview_url": "/static/thumbnail_templates/outside_ai.png"},
]
OUTSIDE_PROMPT = {"prompt": "Create a YouTube thumbnail, landscape 16:9 ... Alex (attached picture 1)",
                  "pictures": [{"name": "Alex", "number": 1, "url": "/static/thumbnail_templates/composed.png"}]}


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
    template_name: str = "composed",
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


@pytest.fixture(scope="module")
def live_server_url(tmp_path_factory: pytest.TempPathFactory) -> Generator[str, None, None]:
    """Serve the real Step 6 page and static assets with isolated runtime storage."""
    with live_server(tmp_path_factory, "thumbnail-browser") as url:
        yield url


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
        elif path == f"/api/projects/{PROJECT['id']}/thumbnails/outside-prompt" and method == "GET":
            await fulfill_json(route, OUTSIDE_PROMPT)
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
    assert await page.locator(".template-option").count() == 2
    await page.locator('[data-template-id="outside_ai"]').click()
    await page.select_option("#variant-count", "3")
    await page.evaluate(
        "const button = document.getElementById('generate-btn'); button.click(); button.click();"
    )

    await page.locator(".variant-card").first.wait_for()
    assert generate_calls == 1
    assert await page.locator(".variant-card").count() == 3
    assert await page.locator('[data-template-id="outside_ai"]').get_attribute(
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


@pytest.mark.asyncio
async def test_the_outside_ai_panel_gives_the_prompt_and_the_card_waits_for_the_picture(
    browser_instance: Browser, live_server_url: str,
) -> None:
    """Task 36.4 (D90): the prompt and the character pictures to attach; the outside-AI card is locked until an upload."""
    page = await browser_instance.new_page()
    TEMPLATES[1]["available"] = False
    try:
        await install_base_routes(page, [])
        await page.goto(f"{live_server_url}/step6?project_id={PROJECT['id']}")
        await page.locator("#workspace").wait_for()
        card = page.locator('[data-template-id="outside_ai"]')
        assert await card.get_attribute("aria-disabled") == "true"
        assert await card.is_disabled() and await card.get_attribute("aria-pressed") == "false"
        assert await page.locator('[data-template-id="composed"]').get_attribute("aria-pressed") == "true"
        await page.locator("#outside-panel summary").click()
        await page.wait_for_function("document.getElementById('outside-prompt').value.includes('16:9')")
        assert "Picture 1: Alex" in await page.locator("#outside-pictures").text_content()
    finally:
        TEMPLATES[1]["available"] = True
        await page.close()


@pytest.mark.asyncio
async def test_regenerate_asks_in_the_page_and_works_where_native_dialogs_are_blocked(
    browser_instance: Browser,
    live_server_url: str,
) -> None:
    """Walkthrough 2026-10-14: "Regenerate thumbnails" did nothing in a host that blocks window.confirm(). The page now
    asks with its own dialog: Cancel keeps the variants, Continue regenerates, and no native dialog is ever used."""
    page = await browser_instance.new_page()
    native_dialogs: list[str] = []
    page.on("dialog", lambda dialog: (native_dialogs.append(dialog.message), asyncio.ensure_future(dialog.dismiss())))
    thumbnails: list[dict] = [variant(index) for index in range(3)]
    generate_calls = 0

    async def mutations(route: Route, path: str, method: str) -> bool:
        nonlocal generate_calls
        if path.endswith("/thumbnails/generate") and method == "POST":
            generate_calls += 1
            thumbnails[:] = [variant(index, headline=f"New {index + 1}") for index in range(3)]
            await fulfill_json(route, thumbnails)
            return True
        return False

    await install_base_routes(page, thumbnails, mutations)
    await page.goto(f"{live_server_url}/step6?project_id={PROJECT['id']}")
    await page.locator(".variant-card").first.wait_for()

    await page.click("#generate-btn")
    assert "replaces all current thumbnail variants" in await answer_confirm(page, accept=False)
    assert generate_calls == 0

    await page.evaluate("const button = document.getElementById('generate-btn'); button.click(); button.click();")
    await answer_confirm(page, accept=True)
    await page.get_by_text("New 1").first.wait_for()
    assert generate_calls == 1  # the double click did not queue a second regeneration
    assert await page.locator(".confirm-dialog").count() == 0
    assert native_dialogs == []
    await page.close()


@pytest.mark.asyncio
async def test_drawing_ai_scenes_shows_them_and_selects_the_ai_scene_kind(
    browser_instance: Browser,
    live_server_url: str,
) -> None:
    """Phase 43 (D122): "Draw AI scenes" runs the local Qwen draw, lists the pictures (a crowded one flagged with "Draw
    again") and makes the "AI scene (local Qwen)" kind available and selected."""
    page = await browser_instance.new_page()
    scene_kind = {"id": "qwen_scene", "display_name": "AI scene (local Qwen)", "description": "scene", "available": False,
                  "preview_url": "/static/thumbnail_templates/qwen_scene.png"}
    templates = [*TEMPLATES, scene_kind]
    picture = "/static/thumbnail_templates/qwen_scene.png"
    scenes = [{"index": 0, "crowded": False, "faces": 2, "side": "left", "free_share": 0.39, "preview_url": picture},
              {"index": 1, "crowded": True, "faces": 2, "side": "left", "free_share": 0.2, "preview_url": picture}]
    calls: list[tuple[str, str]] = []

    async def handle(route: Route) -> None:
        path = urlparse(route.request.url).path
        method = route.request.method
        if path == "/api/thumbnails/templates":
            return await fulfill_json(route, templates)
        if path.endswith("/thumbnails/ai-scenes") and method == "GET":
            return await fulfill_json(route, [])
        if path.endswith("/thumbnails/ai-scenes") and method == "POST":
            calls.append((path, route.request.post_data))
            await asyncio.sleep(0.2)
            scene_kind["available"] = True
            return await fulfill_json(route, scenes)
        if path.endswith("/thumbnails/ai-scenes/1/redraw"):
            calls.append((path, ""))
            return await fulfill_json(route, [scenes[0], {**scenes[1], "crowded": False}])
        if path == f"/api/projects/{PROJECT['id']}" and method == "GET":
            return await fulfill_json(route, PROJECT)
        if path == f"/api/projects/{PROJECT['id']}/thumbnails" and method == "GET":
            return await fulfill_json(route, [])
        if path.endswith("/thumbnails/outside-prompt"):
            return await fulfill_json(route, OUTSIDE_PROMPT)
        await route.continue_()

    await page.route("**/api/**", handle)
    await page.goto(f"{live_server_url}/step6?project_id={PROJECT['id']}")
    await page.locator("#workspace").wait_for()
    assert await page.locator('[data-template-id="qwen_scene"]').get_attribute("aria-disabled") == "true"

    await page.select_option("#ai-scene-count", "2")
    await page.click("#ai-scene-btn")
    await page.locator("#ai-scene-progress .generation-status-stage").wait_for()
    await page.locator('.ai-scene-item[data-scene="1"]').wait_for()
    assert json.loads(calls[0][1]) == {"count": 2}
    assert "Crowded" in await page.locator('.ai-scene-item[data-scene="1"]').text_content()
    assert await page.locator('[data-template-id="qwen_scene"]').get_attribute("aria-pressed") == "true"
    assert "crowded" in (await page.locator("#ai-scene-status").text_content()).lower()

    await page.locator('.ai-scene-item[data-scene="1"] button').click()
    await page.get_by_text('"AI scene (local Qwen)" is selected').wait_for()
    assert calls[-1][0].endswith("/ai-scenes/1/redraw")
    assert await page.locator(".ai-scene-item.is-crowded").count() == 0
    await page.close()
