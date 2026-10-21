"""Real voice persistence with a labeled20-entry UI fixture; no provider synthesis calls."""

import asyncio
import json

import pytest
from playwright.async_api import async_playwright, expect

from backend.core.config import settings
from tests.conftest import live_server
from tests.test_character_voice_selection import config
from tests.test_visuals_project_api import locked_character

GUY, ANDREW, RYAN = "en-US-GuyNeural", "en-US-AndrewNeural", "en-GB-RyanNeural"
VOICES = [
    {"engine": "edge_tts", "voice_id": GUY, "name": "Guy", "locale": "en-US", "gender": "male"},
    {"engine": "edge_tts", "voice_id": ANDREW, "name": "Andrew", "locale": "en-US", "gender": "male"},
    {"engine": "edge_tts", "voice_id": RYAN, "name": "Ryan", "locale": "en-GB", "gender": "male"},
    {"engine": "edge_tts", "voice_id": "en-US-JennyNeural", "name": "Jenny", "locale": "en-US", "gender": "female"},
    *[{"engine": "edge_tts", "voice_id": f"en-GB-Fixture{i:02}Neural", "name": f"UI Fixture {i:02}",
       "locale": "en-GB", "gender": "female"} for i in range(16)],
]


@pytest.fixture(scope="module")
def base_url(tmp_path_factory):
    with live_server(tmp_path_factory, "voice-picker") as url:
        yield url


@pytest.fixture
async def page():
    async with async_playwright() as playwright:
        browser = await playwright.chromium.launch(headless=True)
        page = await browser.new_page(viewport={"width": 1280, "height": 900})

        async def catalog(route):
            await route.fulfill(json={"success": True, "data": {"voices": VOICES, "stale": False,
                                "fetched_at": "2026-10-16T00:00:00Z"}})

        await page.route("**/api/tts/voices", catalog)
        await page.route("**/api/tts/voices?*", catalog)
        yield page
        await browser.close()


async def result(response):
    assert response.status == 200, await response.text()
    return (await response.json())["data"]


async def create_profile(page, base, name="Voice Presenter"):
    profile = await result(await page.request.post(base + "/api/visuals/profiles", data={
        "name": name, "gender": "male", "accent": "american", "appearance": "short black hair", "outfit": "green shirt",
    }))
    await page.goto(base + "/characters")
    await page.locator(f".profile-card[data-id='{profile['id']}']").click()
    await page.locator("#profile-tab-voice").click()  # Phase 58: the voice has its own profile tab
    picker = page.locator("#profile-voice-picker")
    await expect(picker.locator(".voice-count")).to_have_text("20 of 20 English voices")
    return profile, picker


async def test_twenty_choices_filter_search_save_reload_and_explicit_preview(page, base_url, tmp_path):
    profile, picker = await create_profile(page, base_url)
    assert await picker.locator(".voice-select option").count() == 21
    await picker.locator(".voice-locale").select_option("en-GB")
    await picker.locator(".voice-gender").select_option("male")
    await expect(picker.locator(".voice-count")).to_have_text("1 of 20 English voices")
    await picker.locator(".voice-select").select_option(RYAN)
    await picker.locator(".voice-locale").select_option("")
    await picker.locator(".voice-gender").select_option("")
    await picker.locator(".voice-search").fill("Andrew")
    await expect(picker.locator(".voice-count")).to_have_text("1 of 20 English voices")
    await picker.locator(".voice-select").select_option(ANDREW)
    await picker.locator(".voice-save").click()
    await expect(picker.locator(".voice-status")).to_contain_text("Profile voice saved")
    stored = await result(await page.request.get(base_url + f"/api/visuals/profiles/{profile['id']}"))
    assert stored["voice"]["voice_id"] == ANDREW
    await page.reload()
    await page.locator(f".profile-card[data-id='{profile['id']}']").click()
    await expect(picker.locator(".voice-select")).to_have_value(ANDREW)
    await expect(picker.locator(".voice-current")).to_contain_text(ANDREW)
    await page.screenshot(path=str(tmp_path / "profile-voice-picker.png"), full_page=False)


async def test_conflict_keeps_draft_until_explicit_reload(page, base_url):
    profile, picker = await create_profile(page, base_url, "Conflict Presenter")
    initial = await picker.locator(".voice-select").input_value()
    url = base_url + f"/api/visuals/profiles/{profile['id']}"

    async def conflict(route):
        if route.request.method == "PATCH":
            await route.fulfill(status=409, json={"success": False, "error": "Changed elsewhere"})
        else:
            await route.continue_()

    await page.route(url, conflict)
    await picker.locator(".voice-select").select_option(ANDREW)
    await picker.locator(".voice-save").click()
    await expect(picker.locator(".voice-status")).to_contain_text("Your selection is kept")
    await expect(picker.locator(".voice-select")).to_have_value(ANDREW)
    await expect(picker.locator(".voice-current")).to_contain_text(initial)
    await picker.locator(".voice-reload").click()
    await expect(picker.locator(".voice-select")).to_have_value(initial)
    await expect(picker.locator(".voice-save")).to_be_disabled()
    await page.unroute(url, conflict)
    await picker.locator(".voice-select").select_option(ANDREW)
    await picker.locator(".voice-save").click()
    await expect(picker.locator(".voice-status")).to_contain_text("Profile voice saved")


async def test_preview_token_rejects_late_response_even_when_abort_is_ignored(page, base_url):
    # Native cancellation is advisory; independently exercise the request-token guard.
    await page.add_init_script("""const original = window.fetch; window.fetch = (input, init = {}) => original(input,
      String(input).includes('/api/tts/voices/preview') ? {...init, signal: undefined} : init);""")
    _, picker = await create_profile(page, base_url, "Audition Presenter")
    started, release, completed = asyncio.Event(), asyncio.Event(), asyncio.Event()
    payloads = []

    async def preview(route):
        payload = json.loads(route.request.post_data)
        payloads.append(payload)
        if payload["voice_id"] == GUY:
            started.set()
            await release.wait()
        key = "a" if payload["voice_id"] == GUY else "b"
        await route.fulfill(json={"success": True, "data": {
            "voice": {"voice_id": payload["voice_id"]}, "audio_url": f"/fixture-{key}.mp3",
        }})
        if key == "a":
            completed.set()

    await page.route("**/api/tts/voices/preview", preview)
    await page.route("**/fixture-*.mp3", lambda route: route.fulfill(status=200, content_type="audio/mpeg", body=b""))
    await picker.locator(".voice-select").select_option(GUY)
    await picker.locator(".voice-sample").fill("Wait, really? Let me explain this idea.")
    await picker.locator(".voice-preview").click()
    await asyncio.wait_for(started.wait(), 3)
    await picker.locator(".voice-select").select_option(ANDREW)
    await picker.locator(".voice-preview").click()
    await expect(picker.locator(".voice-status")).to_have_text("Preview: " + ANDREW)
    release.set()
    await asyncio.wait_for(completed.wait(), 3)
    await page.evaluate("new Promise(resolve => requestAnimationFrame(() => requestAnimationFrame(resolve)))")
    await expect(picker.locator(".voice-status")).to_have_text("Preview: " + ANDREW)
    assert (await picker.locator("audio").get_attribute("src")) == "/fixture-b.mp3"
    assert [payload["voice_id"] for payload in payloads] == [GUY, ANDREW]
    assert len({payload["text"] for payload in payloads}) == 1
    assert all("project_id" not in payload and "line_id" not in payload for payload in payloads)
    assert not list((settings.DATA_DIR / "tts_cache").rglob("*.mp3"))


async def test_profile_edit_keeps_project_voice_apply_is_explicit_and_reload_persists(page, base_url, tmp_path):
    character = locked_character("Voice Alex", "green")
    await result(await page.request.patch(base_url + f"/api/visuals/profiles/{character}", data={
        "default_voice_id": GUY, "accent": "american", "gender": "male",
    }))
    project = await result(await page.request.post(base_url + "/api/projects", data=config()))
    pid = project["id"]
    await result(await page.request.put(base_url + f"/api/projects/{pid}/visuals/cast", data=[{"speaker_index": 0, "character_id": character}]))
    lines = [{"speaker_id": speaker["id"], "text": "A clear explanation."} for speaker in project["speakers"]]
    await result(await page.request.put(base_url + f"/api/projects/{pid}/script", data={"lines": lines}))
    before = (await result(await page.request.get(base_url + f"/api/projects/{pid}")))["speakers"][0]
    await result(await page.request.patch(base_url + f"/api/visuals/profiles/{character}", data={"default_voice_id": ANDREW}))
    await page.goto(base_url + f"/step4?project_id={pid}")
    card = page.locator(f".speaker-card[data-speaker-id='{before['id']}']")
    await expect(card.locator(".speaker-actual-voice")).to_contain_text(GUY)
    await card.locator(".voice-choice summary").click()
    await expect(card.locator(".voice-count")).to_have_text("20 of 20 English voices")
    await card.locator(".apply-profile-voice").click()
    await expect(card.locator(".speaker-actual-voice")).to_contain_text(ANDREW)
    await expect(card.locator(".voice-status")).to_contain_text("Project speed, pitch and volume are kept")
    current = (await result(await page.request.get(base_url + f"/api/projects/{pid}")))["speakers"][0]
    assert [current[key] for key in ("speed", "pitch", "volume")] == [before[key] for key in ("speed", "pitch", "volume")]
    await expect(page.locator("#voice-duplicate-warning")).to_be_visible()
    await page.get_by_role("button", name="Keep shared voices").click()
    await expect(page.locator("#voice-duplicate-warning")).to_be_hidden()
    await card.locator(".voice-select").select_option(RYAN)
    await expect(page.locator("#generate-btn")).to_be_disabled()
    await card.locator(".voice-save").click()
    await expect(card.locator(".voice-status")).to_contain_text("Project voice saved")
    await expect(page.locator("#generate-btn")).to_be_enabled()
    await page.reload()
    await expect(card.locator(".speaker-actual-voice")).to_contain_text(RYAN)
    await card.locator(".voice-choice summary").click()
    await expect(card.locator(".voice-count")).to_have_text("20 of 20 English voices")
    await page.screenshot(path=str(tmp_path / "project-voice-picker.png"), full_page=False)


async def test_failed_catalog_can_refresh_without_losing_saved_identity(page, base_url):
    profile, picker = await create_profile(page, base_url, "Offline Presenter")
    saved = await picker.locator(".voice-select").input_value()

    async def unavailable(route):
        await route.fulfill(status=502, json={"success": False, "error": "Voice list unavailable"})

    await page.route("**/api/tts/voices?refresh=true", unavailable)
    await picker.locator(".voice-refresh").click()
    await expect(picker.locator(".voice-status")).to_contain_text("Voice list unavailable")
    await expect(picker.locator(".voice-current")).to_contain_text(saved)
    await page.unroute("**/api/tts/voices?refresh=true", unavailable)
    await picker.locator(".voice-refresh").click()
    await expect(picker.locator(".voice-count")).to_have_text("20 of 20 English voices")
    assert (await result(await page.request.get(base_url + f"/api/visuals/profiles/{profile['id']}")))["voice"]["voice_id"] == saved


async def test_profile_switch_confirms_discard_and_saves_details_to_the_original_profile(page, base_url):
    second = await result(await page.request.post(base_url + "/api/visuals/profiles", data={
        "name": "Second Presenter", "gender": "male", "accent": "american", "appearance": "short hair", "outfit": "blue shirt",
    }))
    first, picker = await create_profile(page, base_url, "First Presenter")
    await page.locator("#profile-tab-details").click()
    await page.locator("#profile-intro").fill("An introduction belonging only to the first presenter.")
    await page.locator("#profile-tab-voice").click()
    await picker.locator(".voice-select").select_option(ANDREW)
    destination = page.locator(f".profile-card[data-id='{second['id']}']")
    await destination.click()
    await expect(page.get_by_role("alertdialog")).to_be_visible()
    await page.keyboard.press("Escape")
    await expect(page.locator("#profile-name")).to_have_text(first["name"])
    await expect(picker.locator(".voice-select")).to_have_value(ANDREW)
    await destination.click()
    await expect(page.get_by_role("alertdialog")).to_be_visible()
    await page.keyboard.press("Enter")
    await expect(page.locator("#profile-name")).to_have_text(second["name"])
    first_saved = await result(await page.request.get(base_url + f"/api/visuals/profiles/{first['id']}"))
    second_saved = await result(await page.request.get(base_url + f"/api/visuals/profiles/{second['id']}"))
    assert first_saved["intro"] == "An introduction belonging only to the first presenter."
    assert first_saved["voice"]["voice_id"] == GUY
    assert not second_saved["intro"]


async def test_late_profile_load_cannot_replace_newer_profile_selection(page, base_url):
    second = await result(await page.request.post(base_url + "/api/visuals/profiles", data={
        "name": "Fast Presenter", "gender": "male", "accent": "american", "appearance": "short hair", "outfit": "blue shirt",
    }))
    await result(await page.request.patch(base_url + f"/api/visuals/profiles/{second['id']}", data={"default_voice_id": ANDREW}))
    first, _ = await create_profile(page, base_url, "Slow Presenter")
    started, release, completed = asyncio.Event(), asyncio.Event(), asyncio.Event()

    async def slow(route):
        response = await route.fetch()
        started.set()
        await release.wait()
        await route.fulfill(response=response)
        completed.set()

    await page.route(base_url + f"/api/visuals/profiles/{first['id']}", slow)
    await page.locator(f".profile-card[data-id='{first['id']}']").click()
    await asyncio.wait_for(started.wait(), 3)
    await page.locator(f".profile-card[data-id='{second['id']}']").click()
    await expect(page.locator("#profile-name")).to_have_text(second["name"])
    release.set()
    await asyncio.wait_for(completed.wait(), 3)
    await page.evaluate("new Promise(resolve => requestAnimationFrame(() => requestAnimationFrame(resolve)))")
    await expect(page.locator("#profile-name")).to_have_text(second["name"])
    await expect(page.locator("#profile-voice-picker .voice-current")).to_contain_text(ANDREW)


async def test_parameter_autosave_finishes_before_voice_save(page, base_url):
    project = await result(await page.request.post(base_url + "/api/projects", data=config()))
    pid = project["id"]
    await result(await page.request.put(base_url + f"/api/projects/{pid}/script", data={"lines": [
        {"speaker_id": speaker["id"], "text": "A clear explanation."} for speaker in project["speakers"]
    ]}))
    await page.goto(base_url + f"/step4?project_id={pid}")
    speaker = project["speakers"][0]
    card = page.locator(f".speaker-card[data-speaker-id='{speaker['id']}']")
    await card.locator(".voice-choice summary").click()
    await expect(card.locator(".voice-count")).to_have_text("20 of 20 English voices")
    started, release = asyncio.Event(), asyncio.Event()

    async def slow_patch(route):
        if "speed" in json.loads(route.request.post_data):
            started.set()
            await release.wait()
        await route.continue_()

    await page.route(base_url + f"/api/projects/{pid}/speakers/{speaker['id']}", slow_patch)
    slider = card.locator("input[data-field='speed']")
    await slider.fill("1.1")
    await slider.dispatch_event("input")
    await asyncio.wait_for(started.wait(), 3)
    await expect(card.locator(".voice-select")).to_be_disabled()
    await expect(page.locator("#generate-btn")).to_be_disabled()
    release.set()
    await expect(card.locator(".voice-select")).to_be_enabled()
    await card.locator(".voice-select").select_option(RYAN)
    await card.locator(".voice-save").click()
    await expect(card.locator(".voice-status")).to_contain_text("Project voice saved")
    current = (await result(await page.request.get(base_url + f"/api/projects/{pid}")))["speakers"][0]
    assert current["speed"] == 1.1 and current["voice_id"] == RYAN


async def test_pending_voice_save_blocks_profile_switch_and_normal_draft_can_reload(page, base_url):
    second = await result(await page.request.post(base_url + "/api/visuals/profiles", data={
        "name": "Next Presenter", "gender": "male", "accent": "american", "appearance": "short hair", "outfit": "blue shirt",
    }))
    first, picker = await create_profile(page, base_url, "Saving Presenter")
    await picker.locator(".voice-select").select_option(ANDREW)
    await expect(picker.locator(".voice-reload")).to_be_visible()
    await picker.locator(".voice-reload").click()
    await expect(picker.locator(".voice-select")).to_have_value(GUY)
    await expect(picker.locator(".voice-save")).to_be_disabled()
    started, release = asyncio.Event(), asyncio.Event()

    async def slow_patch(route):
        if route.request.method == "PATCH":
            started.set()
            await release.wait()
        await route.continue_()

    await page.route(base_url + f"/api/visuals/profiles/{first['id']}", slow_patch)
    await picker.locator(".voice-select").select_option(ANDREW)
    await picker.locator(".voice-save").click()
    await asyncio.wait_for(started.wait(), 3)
    await page.locator(f".profile-card[data-id='{second['id']}']").click()
    await expect(page.locator("#profile-name")).to_have_text(first["name"])
    await expect(page.locator("#profile-message")).to_contain_text("Wait until the voice finishes saving")
    await expect(page.get_by_role("alertdialog")).to_have_count(0)
    release.set()
    await expect(picker.locator(".voice-status")).to_contain_text("Profile voice saved")
    await page.locator(f".profile-card[data-id='{second['id']}']").click()
    await expect(page.locator("#profile-name")).to_have_text(second["name"])
