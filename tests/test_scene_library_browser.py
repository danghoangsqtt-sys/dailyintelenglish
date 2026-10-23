"""Phase 73: Activity Library scene lifecycle and controlled image-job UI checks."""

from __future__ import annotations

import asyncio
from io import BytesIO
from pathlib import Path
from typing import AsyncGenerator, Generator

import pytest
from PIL import Image
from playwright.async_api import Browser, Page, async_playwright, expect

from backend.api import visuals as visuals_api
from backend.ai.image.recipes import SCENE_COMPOSITION, qwen_scene_prompt
from backend.core.config import settings
from tests.browser_confirm import answer_confirm
from tests.conftest import live_server


@pytest.fixture(scope="module")
def scene_server(tmp_path_factory: pytest.TempPathFactory) -> Generator[str, None, None]:
    image_python = tmp_path_factory.mktemp("scene-library-venv") / "python.exe"
    image_python.touch()
    with pytest.MonkeyPatch.context() as patch:
        patch.setattr(settings, "IMAGE_ENGINE", "fake")
        patch.setattr(settings, "AI_VISUALS_ENABLED", True)
        patch.setattr(visuals_api, "IMAGE_PYTHON", image_python)
        with live_server(tmp_path_factory, "scene-library-browser") as url:
            yield url


@pytest.fixture
async def scene_browser() -> AsyncGenerator[Browser, None]:
    async with async_playwright() as playwright:
        browser = await playwright.chromium.launch(headless=True)
        yield browser
        await browser.close()


async def open_scenes(page: Page, url: str, local_ai: bool = True) -> None:
    await page.route("**/api/system/capabilities", lambda route: route.fulfill(json={
        "success": True, "data": {"local_image_ai": local_ai},
    }))
    await page.goto(f"{url}/activities?tab=scenes")
    await expect(page.locator("#save-scene")).to_be_enabled()


async def add_scene(page: Page, name: str) -> str:
    await page.locator("#new-scene").click()
    await expect(page.locator("#scene-source-request")).to_be_focused()
    form = page.locator("#scene-form")
    await form.locator("[name=name]").fill(name)
    await form.locator("[name=place]").fill("a sunny garden classroom")
    await form.locator("[name=category]").select_option("school")
    await page.locator("#save-scene").click()
    await expect(page.locator("#library-message")).to_have_text("Scene added.")
    return await page.locator("#scene-grid .library-scene", has=page.get_by_role("heading", name=name, exact=True)).get_attribute("data-scene-id")


async def test_scene_lifecycle_filters_and_desktop_screenshot(
    scene_browser: Browser, scene_server: str, tmp_path: Path,
):
    page = await scene_browser.new_page(viewport={"width": 1440, "height": 1000})
    errors = []
    page.on("pageerror", lambda error: errors.append(str(error)))
    await open_scenes(page, scene_server)
    builtin = page.locator('#scene-grid [data-scene-id="builtin-cafe"]')
    assert await builtin.get_by_role("button", name="Archive", exact=True).count() == 0
    assert await builtin.get_by_role("button", name="Delete", exact=True).count() == 0
    scene_id = await add_scene(page, "Garden classroom")
    card = page.locator(f'#scene-grid [data-scene-id="{scene_id}"]')
    await page.locator("#scene-search").fill("garden classroom")
    await expect(card).to_be_visible()
    await page.locator('#scene-filters [data-category="school"]').click()
    await page.locator("#scene-plate-filter").select_option("ready")
    await expect(page.locator("#scene-empty")).to_be_visible()
    await page.locator("#scene-plate-filter").select_option("missing")
    await card.get_by_role("button", name="Make plate", exact=True).click()
    await expect(page.locator("#library-message")).to_have_text("Images are ready for review.", timeout=15000)
    await expect(card).to_have_count(0)  # the new plate no longer matches "Without plate"
    await page.locator("#scene-plate-filter").select_option("ready")
    await expect(card.locator("img")).to_be_visible()
    await card.focus()
    await card.press("Enter")
    await expect(page.locator("#scene-detail-name")).to_have_text("Garden classroom")
    await card.get_by_role("button", name="Edit", exact=True).click()
    await page.locator('#scene-form [name=staging]').select_option("seated")
    await page.locator("#save-scene").click()
    await expect(page.locator("#library-message")).to_have_text("Scene saved.")
    await expect(card.locator(".scene-meta")).to_contain_text("seated")
    await expect(card.locator("img")).to_be_visible()
    await card.get_by_role("button", name="Edit", exact=True).click()
    await page.locator('#scene-form [name=place]').fill("a quiet garden classroom")
    await expect(page.locator("#scene-stale-warning")).to_be_visible()
    await page.locator("#cancel-scene-edit").click()
    await page.locator("#scene-search").fill("")
    await page.locator('#scene-filters [data-category="all"]').click()
    await page.locator("#scene-plate-filter").select_option("all")
    await page.evaluate("window.scrollTo(0, 0)")
    screenshot = tmp_path / "scene-library-desktop.png"
    await page.screenshot(path=str(screenshot), full_page=False)
    print(f"\nSCENES_SCREENSHOT={screenshot}")
    await page.locator("#scene-search").fill("garden classroom")
    await card.get_by_role("button", name="Duplicate", exact=True).click()
    await expect(page.locator("#scene-grid .library-scene", has_text="Garden classroom copy")).to_be_visible()
    await card.get_by_role("button", name="Archive", exact=True).click()
    assert "Existing videos and storyboard choices are kept" in await answer_confirm(page, accept=False)
    await expect(card).to_be_visible()
    await card.get_by_role("button", name="Archive", exact=True).click()
    await answer_confirm(page)
    await expect(card).to_have_count(0)
    active = await page.evaluate("Api.listScenes()")
    assert scene_id not in {scene["id"] for scene in active}
    await page.locator("#scene-archive-filter").select_option("archived")
    await expect(card).to_have_class("card library-scene is-archived")
    assert await card.locator("img").get_attribute("src")
    await expect(card.get_by_role("button", name="↻ Plate")).to_be_disabled()
    await card.get_by_role("button", name="Restore", exact=True).click()
    await expect(card).to_have_count(0)
    await page.locator("#scene-archive-filter").select_option("all")
    await expect(card).to_be_visible()
    await page.locator("#scene-archive-filter").select_option("active")
    await expect(card).to_be_visible()
    assert not errors
    await page.close()


@pytest.mark.parametrize("terminal", ["complete", "error", "cancelled"])
async def test_scene_job_progress_terminal_states_and_cancel(
    scene_browser: Browser, scene_server: str, terminal: str,
):
    page = await scene_browser.new_page()
    await open_scenes(page, scene_server)
    polls = 0
    cancellations = []
    job = {"id": "controlled-scene-job", "status": "queued", "stage": "Queued", "progress": 0}

    async def poll(route):
        nonlocal polls
        polls += 1
        status = terminal if (cancellations or (terminal != "cancelled" and polls > 1)) else "running"
        await route.fulfill(json={"success": True, "data": {
            **job, "status": status, "stage": "Drawing scene", "progress": 40,
            "error": "Controlled generation failure" if status == "error" else None,
        }})

    async def cancel(route):
        cancellations.append(route.request.method)
        await route.fulfill(json={"success": True, "data": {**job, "status": "cancelled"}})

    await page.route("**/api/visuals/scenes/*/preview", lambda route: route.fulfill(json={"success": True, "data": job}))
    await page.route("**/api/visuals/jobs/controlled-scene-job", poll)
    await page.route("**/api/visuals/jobs/controlled-scene-job/cancel", cancel)
    card = page.locator('#scene-grid [data-scene-id="builtin-cafe"]')
    await card.get_by_role("button", name="Make plate").click()
    await expect(page.locator("#cancel-library-job")).to_be_visible()
    await expect(card.get_by_role("button", name="Duplicate")).to_be_disabled()
    await expect(page.locator("#save-scene")).to_be_disabled()
    await expect(page.locator("#library-progress")).to_contain_text("Queued")
    if terminal == "cancelled":
        await page.locator("#cancel-library-job").click()
    expected = {
        "complete": "Images are ready for review.", "error": "Controlled generation failure",
        "cancelled": "Generation cancelled. Finished images were kept.",
    }
    await expect(page.locator("#library-message")).to_have_text(expected[terminal])
    await expect(page.locator("#cancel-library-job")).to_be_hidden()
    await expect(page.locator("#save-scene")).to_be_enabled()
    await expect(page.locator("#library-progress")).to_be_empty()
    assert cancellations == (["POST"] if terminal == "cancelled" else [])
    if terminal == "error":
        await expect(page.locator("#library-message")).to_have_attribute("role", "alert")
    await page.close()


async def test_scene_form_keeps_failed_edits_and_capabilities_hide_generation(
    scene_browser: Browser, scene_server: str,
):
    page = await scene_browser.new_page()
    await open_scenes(page, scene_server)
    await page.route("**/api/visuals/scenes", lambda route: route.fulfill(
        status=409, json={"success": False, "error": "Scene name already exists"},
    ) if route.request.method == "POST" else route.continue_())
    form = page.locator("#scene-form")
    await form.locator("[name=name]").fill("Keep my draft")
    await form.locator("[name=place]").fill("a sunny garden classroom")
    await form.locator("[name=source_request]").fill("Giữ yêu cầu của tôi")
    await form.locator("[name=image_prompt]").fill("Keep my detailed draft prompt")
    await page.locator("#save-scene").click()
    await expect(page.locator("#library-message")).to_have_text("Scene name already exists")
    await expect(form.locator("[name=name]")).to_have_value("Keep my draft")
    await expect(form.locator("[name=source_request]")).to_have_value("Giữ yêu cầu của tôi")
    await expect(form.locator("[name=image_prompt]")).to_have_value("Keep my detailed draft prompt")
    await page.evaluate("""() => {
      document.documentElement.dataset.localImageAi = 'off';
      window.dispatchEvent(new CustomEvent('dbe:capabilities', {detail: {local_image_ai: false}}));
    }""")
    await expect(page.locator('#scene-grid [data-scene-id="builtin-cafe"] .needs-local-gpu')).to_be_hidden()
    await expect(page.locator("#save-scene")).to_be_enabled()
    await page.close()


async def test_legacy_entry_profiles_theme_and_scene_query_contract(
    scene_browser: Browser, scene_server: str,
):
    page = await scene_browser.new_page()
    errors = []
    page.on("pageerror", lambda error: errors.append(str(error)))
    requests = []
    page.on("request", lambda request: requests.append(request.url))
    await page.goto(f"{scene_server}/characters")
    await expect(page.locator("#profile-new")).to_be_visible()
    await page.locator("#profile-new").click()
    await expect(page.locator("#profile-create")).to_be_visible()
    before = await page.locator("html").get_attribute("data-theme")
    await page.locator("#theme-toggle").click()
    assert await page.locator("html").get_attribute("data-theme") != before
    assert not any("/api/visuals/scenes" in url for url in requests)
    await page.locator("#scenes-tab").click()
    await expect(page.locator("#scene-form")).to_be_visible()
    assert page.url.endswith("?tab=scenes#scenes")
    await expect(page.locator("#save-scene")).to_be_enabled()
    assert len([url for url in requests if "/api/visuals/scenes?include_archived=true" in url]) == 1
    before = await page.locator("html").get_attribute("data-theme")
    await page.locator("#theme-toggle").click()
    assert await page.locator("html").get_attribute("data-theme") != before
    calls = []

    async def capture(route):
        calls.append(route.request.url)
        await route.fulfill(json={"success": True, "data": []})

    await page.route("**/api/visuals/scenes?*", capture)
    await page.evaluate("Api.listScenes({include_archived: false, project_id: 'project & 73'})")
    assert "include_archived=false" in calls[0]
    assert "project_id=project+%26+73" in calls[0]
    await page.locator("#tab-activities").click()
    await page.reload()
    await expect(page.locator("#activity-panel")).to_be_visible()
    await page.goto(f"{scene_server}/characters#scenes")
    await expect(page.locator("#scene-form")).to_be_visible()
    assert not errors
    await page.close()


async def test_scene_and_step5_vietnamese_strings(scene_browser: Browser, scene_server: str):
    page = await scene_browser.new_page()
    await page.add_init_script("localStorage.setItem('dbe.lang', 'vi')")
    await page.goto(f"{scene_server}/activities?tab=scenes")
    await expect(page.get_by_label("Tìm cảnh", exact=True)).to_be_visible()
    phrases = [
        "Choose each speaker's character. Choose a scene for each beat in the storyboard below.",
        "Choose places from your library for each beat.", "Manage scenes", "Search scenes", "(archived)",
        "Garden (archived)",
    ]
    translations = await page.evaluate("phrases => phrases.map(text => I18n.translate(text))", phrases)
    assert all(translations)
    assert translations[2:] == ["Quản lý cảnh", "Tìm cảnh", "(đã lưu trữ)", "Garden (đã lưu trữ)"]
    await page.close()


def prompt_draft(brief: str, name: str = "Prepared garden") -> dict:
    return {
        "name": name, "place": "a sunny garden classroom", "staging": "standing", "category": "school",
        "time_of_day": "day", "source_request": brief,
        "image_prompt": qwen_scene_prompt({"image_prompt": (
            "A sunlit garden classroom with timber benches and soft leafy shadows. "
            "Warm natural colors and a clear foreground create a calm learning environment."
        )}),
    }


@pytest.mark.parametrize("language,copy_mode", [("vi", "clipboard"), ("en", "fallback")])
async def test_brief_to_prompt_copy_save_and_reload_without_gpu(
    scene_browser: Browser, scene_server: str, tmp_path: Path, language: str, copy_mode: str,
):
    page = await scene_browser.new_page(viewport={"width": 1440, "height": 1200})
    await open_scenes(page, scene_server, local_ai=False)
    brief = "Lớp học trong vườn yên tĩnh, nắng dịu" if language == "vi" else "A calm garden classroom with gentle sunshine"
    draft = prompt_draft(brief, f"Prepared garden {language}")
    calls = []

    async def prepare(route):
        calls.append(route.request.post_data_json)
        await route.fulfill(json={"success": True, "data": draft})

    await page.route("**/api/visuals/scenes/prompt", prepare)
    await page.locator("#scene-source-request").fill(brief)
    await page.locator("#prepare-scene-prompt").click()
    await expect(page.locator("#scene-image-prompt")).to_have_value(draft["image_prompt"])
    assert calls == [{"brief": brief}]
    await expect(page.locator('#scene-form [name=name]')).to_have_value(draft["name"])
    await expect(page.locator('#scene-grid [data-scene-id="builtin-cafe"] .needs-local-gpu')).to_be_hidden()
    await page.locator("#scene-source-request").fill(brief + " updated")
    await expect(page.locator("#scene-request-stale")).to_be_visible()
    await expect(page.locator("#scene-image-prompt")).to_have_value(draft["image_prompt"])
    await page.locator("#scene-source-request").fill(brief)
    await expect(page.locator("#scene-request-stale")).to_be_hidden()
    if language == "vi":
        await page.evaluate("window.scrollTo(0, 0); document.getElementById('scene-side').scrollTop = 0")
        screenshot = tmp_path / "scene-prompt-desktop.png"
        await page.screenshot(path=str(screenshot), full_page=False)
        print(f"\nSCENE_PROMPT_SCREENSHOT={screenshot}")
    await page.evaluate("""mode => {
      Object.defineProperty(navigator, 'clipboard', {configurable: true, value: {
        writeText: async text => { if (mode === 'fallback') throw new Error('Clipboard denied'); window.copiedPrompt = text; }
      }});
      document.execCommand = command => { window.copiedPrompt = document.activeElement.value; return command === 'copy'; };
    }""", copy_mode)
    await page.locator("#scene-image-prompt").fill("A revised garden with stone benches and warm afternoon light.")
    await page.locator("#copy-scene-prompt").click()
    await expect(page.locator("#library-message")).to_have_text("Image prompt copied.")
    copied = await page.evaluate("window.copiedPrompt")
    # The front-end suffix must match the actual local Qwen builder, byte for byte.
    assert copied == qwen_scene_prompt({"image_prompt": "A revised garden with stone benches and warm afternoon light."})
    assert copied.endswith(SCENE_COMPOSITION)
    await page.locator("#save-scene").click()
    await expect(page.locator("#library-message")).to_have_text("Scene added.")
    await page.reload()
    card = page.locator("#scene-grid .library-scene", has=page.get_by_role("heading", name=draft["name"], exact=True))
    await card.get_by_role("button", name="Edit", exact=True).click()
    await expect(page.locator("#scene-source-request")).to_have_value(brief)
    await expect(page.locator("#scene-image-prompt")).to_have_value(copied)
    scene_id = await card.get_attribute("data-scene-id")
    response = await page.request.get(f"{scene_server}/api/visuals/scenes/{scene_id}/prompt")
    assert (await response.json())["data"]["prompt"] == copied
    await page.close()


async def test_prepare_errors_and_late_results_preserve_dirty_draft(scene_browser: Browser, scene_server: str):
    page = await scene_browser.new_page()
    await open_scenes(page, scene_server, local_ai=False)
    await page.locator("#scene-source-request").fill("A quiet garden")
    await page.locator("#scene-image-prompt").fill("My existing custom prompt")
    await page.locator('#scene-form [name=name]').fill("My unsaved scene")
    await page.route("**/api/visuals/scenes/prompt", lambda route: route.fulfill(
        status=503, json={"success": False, "error": "No text AI provider is configured"},
    ))
    await page.locator("#prepare-scene-prompt").click()
    await expect(page.locator("#library-message")).to_have_text("No text AI provider is configured")
    await expect(page.locator("#scene-image-prompt")).to_have_value("My existing custom prompt")
    await expect(page.locator('#scene-form [name=name]')).to_have_value("My unsaved scene")
    await page.unroute("**/api/visuals/scenes/prompt")
    started, release = asyncio.Event(), asyncio.Event()
    calls = []

    async def delayed_prepare(route):
        calls.append(route.request.post_data_json)
        started.set()
        await release.wait()
        await route.fulfill(json={"success": True, "data": prompt_draft("A quiet garden")})

    await page.route("**/api/visuals/scenes/prompt", delayed_prepare)
    await page.locator("#prepare-scene-prompt").click()
    await asyncio.wait_for(started.wait(), timeout=5)
    await expect(page.locator("#prepare-scene-prompt")).to_be_disabled()
    await expect(page.locator("#save-scene")).to_be_disabled()
    await page.locator("#prepare-scene-prompt").dispatch_event("click")
    await page.locator("#scene-source-request").fill("My newer Vietnamese or English request")
    await page.locator("#scene-image-prompt").fill("My newer detailed prompt")
    release.set()
    await expect(page.locator("#library-message")).to_contain_text("Your draft changed while preparing")
    assert len(calls) == 1
    await expect(page.locator("#scene-source-request")).to_have_value("My newer Vietnamese or English request")
    await expect(page.locator("#scene-image-prompt")).to_have_value("My newer detailed prompt")
    await expect(page.locator('#scene-form [name=name]')).to_have_value("My unsaved scene")
    await page.close()


async def test_saved_prompt_copy_does_not_overwrite_new_edits(scene_browser: Browser, scene_server: str):
    page = await scene_browser.new_page()
    await open_scenes(page, scene_server)
    await page.locator('#scene-grid [data-scene-id="builtin-cafe"]').get_by_role("button", name="Edit", exact=True).click()
    started, release = asyncio.Event(), asyncio.Event()

    async def delayed_prompt(route):
        started.set()
        await release.wait()
        await route.fulfill(json={"success": True, "data": {"prompt": "The stale saved prompt"}})

    await page.route("**/api/visuals/scenes/builtin-cafe/prompt", delayed_prompt)
    await page.evaluate("Object.defineProperty(navigator, 'clipboard', {value: {writeText: async text => {window.copiedPrompt = text;}}})")
    await page.locator("#copy-scene-prompt").click()
    await asyncio.wait_for(started.wait(), timeout=5)
    await page.locator("#scene-image-prompt").fill("The latest unsaved prompt")
    release.set()
    await expect(page.locator("#library-message")).to_contain_text("Your draft changed while copying")
    assert await page.evaluate("window.copiedPrompt ?? null") is None
    await expect(page.locator("#scene-image-prompt")).to_have_value("The latest unsaved prompt")
    await page.locator("#copy-scene-prompt").click()
    await expect(page.locator("#library-message")).to_have_text("Image prompt copied.")
    assert await page.evaluate("window.copiedPrompt") == qwen_scene_prompt({"image_prompt": "The latest unsaved prompt"})
    await page.evaluate("() => { navigator.clipboard.writeText = () => new Promise(resolve => {window.releaseClipboard = resolve;}); }")
    await page.locator("#copy-scene-prompt").click()
    await page.wait_for_function("typeof window.releaseClipboard === 'function'")
    await page.locator("#scene-image-prompt").fill("My edit while clipboard permission was pending")
    await page.evaluate("window.releaseClipboard()")
    await expect(page.locator("#library-message")).to_contain_text("Your draft changed while copying")
    await expect(page.locator("#scene-image-prompt")).to_have_value("My edit while clipboard permission was pending")
    await page.close()


async def test_uploaded_external_background_and_saved_prompt_local_queue(
    scene_browser: Browser, scene_server: str,
):
    page = await scene_browser.new_page()
    await open_scenes(page, scene_server, local_ai=False)
    scene_id = await add_scene(page, "External garden")
    # Save the request/prompt through the real PATCH contract as well as the create flow above.
    card = page.locator(f'#scene-grid [data-scene-id="{scene_id}"]')
    await card.get_by_role("button", name="Edit", exact=True).click()
    await page.locator("#scene-source-request").fill("A garden with benches")
    await page.locator("#scene-image-prompt").fill("A peaceful garden with wooden benches and leafy shadows.")
    await page.locator("#save-scene").click()
    await expect(page.locator("#library-message")).to_have_text("Scene saved.")
    image = BytesIO()
    Image.new("RGB", (1280, 720), (35, 100, 60)).save(image, format="JPEG")
    await card.locator(".scene-background-file").set_input_files({
        "name": "outside-garden.jpg", "mimeType": "image/jpeg", "buffer": image.getvalue(),
    })
    await expect(page.locator("#library-message")).to_have_text("Scene background uploaded.")
    await expect(card.locator("img")).to_be_visible()
    preview = await card.locator("img").get_attribute("src")
    await card.locator(".scene-background-file").set_input_files({
        "name": "broken.png", "mimeType": "image/png", "buffer": b"not an image",
    })
    await expect(page.locator("#library-message")).to_have_attribute("role", "alert")
    assert await card.locator("img").get_attribute("src") == preview
    await page.reload()
    await card.get_by_role("button", name="Edit", exact=True).click()
    saved_prompt = await page.locator("#scene-image-prompt").input_value()
    assert saved_prompt == qwen_scene_prompt({"image_prompt": "A peaceful garden with wooden benches and leafy shadows."})
    await expect(page.locator("#scene-source-request")).to_have_value("A garden with benches")
    await page.evaluate("""() => {
      document.documentElement.dataset.localImageAi = 'on';
      window.dispatchEvent(new CustomEvent('dbe:capabilities', {detail: {local_image_ai: true}}));
    }""")
    jobs = []
    job = {"id": "saved-prompt-job", "status": "queued", "stage": "Queued", "progress": 0}

    async def enqueue(route):
        jobs.append(route.request.url)
        await route.fulfill(json={"success": True, "data": job})

    await page.route(f"**/api/visuals/scenes/{scene_id}/preview", enqueue)
    await page.route("**/api/visuals/jobs/saved-prompt-job", lambda route: route.fulfill(json={
        "success": True, "data": {**job, "status": "complete", "progress": 100},
    }))
    await page.locator("#scene-source-request").fill("An unsaved new request")
    await card.get_by_role("button", name="↻ Plate").click()
    await expect(page.locator("#library-message")).to_contain_text("Save your scene changes")
    assert not jobs
    await page.locator("#scene-source-request").fill("A garden with benches")
    await card.get_by_role("button", name="↻ Plate").click()
    await expect(page.locator("#library-message")).to_have_text("Images are ready for review.")
    assert len(jobs) == 1
    response = await page.request.get(f"{scene_server}/api/visuals/scenes/{scene_id}/prompt")
    assert (await response.json())["data"]["prompt"] == saved_prompt
    await page.close()


async def test_prompt_limit_and_unavailable_clipboard_keep_draft(scene_browser: Browser, scene_server: str):
    page = await scene_browser.new_page()
    await open_scenes(page, scene_server, local_ai=False)
    await page.locator("#scene-image-prompt").fill("x" * 6000)
    await page.locator("#copy-scene-prompt").click()
    await expect(page.locator("#library-message")).to_contain_text("6000 characters including background constraints")
    await expect(page.locator("#scene-image-prompt")).to_have_value("x" * 6000)
    await page.evaluate("""() => {
      Object.defineProperty(navigator, 'clipboard', {value: {writeText: async () => {throw new Error('Denied');}}});
      document.execCommand = () => false;
    }""")
    await page.locator("#scene-image-prompt").fill("A garden prompt to copy manually")
    await page.locator("#copy-scene-prompt").click()
    await expect(page.locator("#library-message")).to_contain_text("please select and copy the text manually")
    await expect(page.locator("#scene-image-prompt")).to_have_value(qwen_scene_prompt({"image_prompt": "A garden prompt to copy manually"}))
    await page.close()
