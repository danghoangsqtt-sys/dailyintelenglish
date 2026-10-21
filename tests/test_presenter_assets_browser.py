"""Front UI actual API persistence, explicit view, parent review and asynchronous context guards."""
import asyncio

import pytest
from playwright.async_api import async_playwright, expect

from tests.conftest import live_server
from tests.test_presenter_asset_plan import figure_bytes


@pytest.fixture(scope="module")
def base_url(tmp_path_factory):
    with live_server(tmp_path_factory, "front-ui") as url:
        yield url


@pytest.fixture
async def page():
    async with async_playwright() as driver:
        browser = await driver.chromium.launch(headless=True)
        page = await browser.new_page(viewport={"width": 1280, "height": 1000})
        async def voices(route):
            await route.fulfill(json={"success": True, "data": {"voices": [
                {"engine": "edge_tts", "voice_id": "en-US-GuyNeural", "name": "Guy", "locale": "en-US", "gender": "male"},
                {"engine": "edge_tts", "voice_id": "en-US-AndrewNeural", "name": "Andrew", "locale": "en-US", "gender": "male"},
            ], "stale": False}})
        await page.route("**/api/tts/voices*", voices)
        yield page
        await browser.close()


async def profile(page, base, name):
    response = await page.request.post(base + "/api/visuals/profiles", data={"name": name, "gender": "male",
        "accent": "american", "appearance": "dark hair", "outfit": "green shirt"})
    assert response.status == 200, await response.text()
    return (await response.json())["data"]


async def open_front(page, base, character):
    await page.goto(base + "/characters")
    await page.locator(f".profile-card[data-id='{character['id']}']").click()
    await expect(page.locator(".slot-card")).to_have_count(29)
    await page.locator("#profile-view-front").click()
    await expect(page.locator(".slot-card")).to_have_count(21)


async def test_front_prompt_import_review_reload_preserves_voice_draft_and_native(page, base_url):
    character = await profile(page, base_url, "Front UI Presenter")
    await open_front(page, base_url, character)
    await expect(page.locator("#profile-pack-progress")).to_have_text("0/21 approved")
    base = page.locator(".slot-card[data-slot='calm__closed']")
    assert "eyes looking directly at the camera" in await base.locator("textarea").input_value()
    await expect(page.locator(".slot-card[data-slot='gesture-point-left']")).to_have_attribute("data-state", "waiting")
    picker = page.locator("#profile-voice-picker")
    await page.locator("#profile-tab-voice").click()  # Phase 58: the voice has its own profile tab
    await picker.locator(".voice-select").select_option("en-US-AndrewNeural")
    await page.locator("#profile-view-front").click()
    await base.locator("input[type=file]").set_input_files({"name": "Hoang-front.png", "mimeType": "image/png", "buffer": figure_bytes()})
    await expect(base).to_have_attribute("data-state", "needs_review")
    await expect(picker.locator(".voice-select")).to_have_value("en-US-AndrewNeural")
    await expect(picker.locator(".voice-save")).to_be_enabled()
    await base.locator(".slot-approve").click()
    await expect(page.locator("#profile-pack-progress")).to_have_text("1/21 approved")
    reference = page.locator(".slot-card[data-slot='calm__open'] a[download]")
    assert "view=front" in await reference.get_attribute("href")
    download = await page.request.get(base_url + await reference.get_attribute("href"))
    assert download.status == 200 and (await download.body()).startswith(b"\x89PNG")
    await page.locator("#profile-view-native").click()
    await expect(page.locator(".slot-card")).to_have_count(29)
    await expect(page.locator("#profile-pack-progress")).to_have_text("0/29 approved")
    await expect(picker.locator(".voice-select")).to_have_value("en-US-AndrewNeural")
    await page.locator("#profile-tab-voice").click()
    await picker.locator(".voice-reload").click()
    await page.reload()
    await page.locator(f".profile-card[data-id='{character['id']}']").click()
    await page.locator("#profile-view-front").click()
    await expect(page.locator("#profile-pack-progress")).to_have_text("1/21 approved")
    await base.locator("input[type=file]").set_input_files({"name": "bad.png", "mimeType": "image/png", "buffer": b"bad"})
    await expect(page.locator("#profile-message")).to_have_class("library-message is-error")
    await expect(page.locator("#profile-pack-progress")).to_have_text("1/21 approved")


async def test_front_batch_reports_each_outcome_and_approve_then_reload(page, base_url):
    character = await profile(page, base_url, "Front Batch Presenter")
    await open_front(page, base_url, character)
    await page.locator("#profile-bulk").set_input_files([
        {"name": "calm__closed.png", "mimeType": "image/png", "buffer": figure_bytes()},
        {"name": "smile__closed.png", "mimeType": "image/png", "buffer": figure_bytes()},
        {"name": "blink.png", "mimeType": "image/png", "buffer": figure_bytes()},
    ])
    await expect(page.locator("#profile-message")).to_contain_text("1 stored")
    await expect(page.locator("#profile-message")).to_contain_text("1 not named")
    await expect(page.locator("#profile-message")).to_contain_text("1 refused")
    await page.locator("#profile-approve-all").click()
    await expect(page.locator("#profile-pack-progress")).to_have_text("1/21 approved")


async def test_pending_front_upload_keeps_profile_view_context_locked(page, base_url):
    first = await profile(page, base_url, "Locked Upload A")
    second = await profile(page, base_url, "Locked Upload B")
    await open_front(page, base_url, first)
    entered, release = asyncio.Event(), asyncio.Event()
    async def delayed(route):
        entered.set()
        await release.wait()
        await route.continue_()
    await page.route(f"**/{first['id']}/slots/calm__closed/upload?view=front", delayed)
    await page.locator(".slot-card[data-slot='calm__closed'] input").set_input_files({"name": "base.png", "mimeType": "image/png", "buffer": figure_bytes()})
    await asyncio.wait_for(entered.wait(), 5)
    await expect(page.locator("#profile-view-native")).to_be_disabled()
    await expect(page.locator("#profile-new")).to_be_disabled()
    await page.locator(f".profile-card[data-id='{second['id']}']").click()
    await expect(page.locator("#profile-name")).to_have_text(first["name"])
    release.set()
    await expect(page.locator(".slot-card[data-slot='calm__closed']")).to_have_attribute("data-state", "needs_review")
    await page.locator(f".profile-card[data-id='{second['id']}']").click()
    await expect(page.locator("#profile-name")).to_have_text(second["name"])
    await expect(page.locator("#profile-pack-progress")).to_have_text("0/21 approved")


async def test_late_front_slot_response_cannot_replace_another_profile(page, base_url):
    first = await profile(page, base_url, "Late Front A")
    second = await profile(page, base_url, "Late Front B")
    await page.goto(base_url + "/characters")
    await page.locator(f".profile-card[data-id='{first['id']}']").click()
    entered, release, finished = asyncio.Event(), asyncio.Event(), asyncio.Event()
    async def delayed(route):
        response = await route.fetch()
        entered.set()
        await release.wait()
        await route.fulfill(response=response)
        finished.set()
    await page.route(f"**/{first['id']}/slots?view=front", delayed)
    await page.locator("#profile-view-front").click()
    await asyncio.wait_for(entered.wait(), 5)
    await page.locator(f".profile-card[data-id='{second['id']}']").click()
    await expect(page.locator("#profile-name")).to_have_text(second["name"])
    release.set()
    await asyncio.wait_for(finished.wait(), 5)
    await expect(page.locator("#profile-prompt-pack")).to_have_attribute("href", f"/api/visuals/profiles/{second['id']}/prompt-pack.txt?view=front")
    await expect(page.locator(".slot-card")).to_have_count(21)


async def test_create_locks_second_submit_and_other_navigation(page, base_url):
    other = await profile(page, base_url, "Before Pending Create")
    await page.goto(base_url + "/characters")
    await page.locator("#profile-new").click()
    form = page.locator("#profile-create-form")
    await form.locator("[name=name]").fill("Pending Create Once")
    await form.locator("[name=appearance]").fill("dark hair")
    await form.locator("[name=outfit]").fill("blue shirt")
    entered, release = asyncio.Event(), asyncio.Event()
    calls = []
    async def delayed(route):
        if route.request.method != "POST":
            return await route.continue_()
        calls.append(route.request.post_data)
        response = await route.fetch()
        entered.set()
        await release.wait()
        await route.fulfill(response=response)
    await page.route("**/api/visuals/profiles", delayed)
    await form.locator("button[type=submit]").click()
    await asyncio.wait_for(entered.wait(), 5)
    await expect(form.locator("button[type=submit]")).to_be_disabled()
    await form.dispatch_event("submit")
    await page.locator(f".profile-card[data-id='{other['id']}']").click()
    await expect(form).to_be_visible()
    release.set()
    await expect(page.locator("#profile-name")).to_have_text("Pending Create Once")
    assert len(calls) == 1


async def test_loading_another_profile_disables_old_editable_fields(page, base_url):
    first = await profile(page, base_url, "Loading Fields A")
    second = await profile(page, base_url, "Loading Fields B")
    await open_front(page, base_url, first)
    entered, release = asyncio.Event(), asyncio.Event()
    async def delayed(route):
        response = await route.fetch()
        entered.set()
        await release.wait()
        await route.fulfill(response=response)
    await page.route(base_url + f"/api/visuals/profiles/{second['id']}", delayed)
    await page.locator(f".profile-card[data-id='{second['id']}']").click()
    await asyncio.wait_for(entered.wait(), 5)
    await expect(page.locator("#profile-intro")).to_be_disabled()
    await expect(page.locator("#profile-voice-picker .voice-select")).to_be_disabled()
    await expect(page.locator(".slot-card")).to_have_count(0)
    release.set()
    await expect(page.locator("#profile-name")).to_have_text(second["name"])
    await expect(page.locator("#profile-intro")).to_be_enabled()
    await expect(page.locator(".slot-card")).to_have_count(21)


async def test_a_refused_upload_shows_its_reason_on_the_card(page, base_url):
    # BUG-049: the refusal was only shown at the top of the panel and the card fell back to Empty.
    character = await profile(page, base_url, "Refused Upload")
    await open_front(page, base_url, character)
    reason = "the head changed (only 60% of it is unchanged; a gesture may change the arms only)"
    async def refuse(route):
        await route.fulfill(status=422, json={"success": False, "data": None, "error": reason})
    upload = f"**/{character['id']}/slots/calm__closed/upload?view=front"
    await page.route(upload, refuse)
    card = page.locator(".slot-card[data-slot='calm__closed']")
    await card.locator("input").set_input_files({"name": "base.png", "mimeType": "image/png", "buffer": figure_bytes()})
    await expect(card.locator(".slot-refused")).to_have_text(f"Not stored: {reason}")
    await expect(card).to_have_attribute("data-state", "empty")
    await page.unroute(upload)
    await card.locator("input").set_input_files({"name": "base.png", "mimeType": "image/png", "buffer": figure_bytes()})
    await expect(card).to_have_attribute("data-state", "needs_review")
    await expect(card.locator(".slot-refused")).to_have_count(0)
