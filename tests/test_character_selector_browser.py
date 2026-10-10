"""Browser coverage for explicit profile preview and project cast assignment."""

import json
from typing import AsyncGenerator

import pytest
from playwright.async_api import Browser, async_playwright

from tests.conftest import live_server


PROJECT_ID = "character-selector-e2e"
SPEAKERS = [
    {"id": "speaker-0", "speaker_index": 0, "name": "Host", "gender": "female", "accent": "american",
     "tts_engine": "edge_tts", "voice_id": None, "voice_description": "custom host voice",
     "speed": 1.05, "pitch": 0.0, "volume": 1.0, "avatar_image_path": None},
    {"id": "speaker-1", "speaker_index": 1, "name": "Guest", "gender": "male", "accent": "american",
     "tts_engine": "edge_tts", "voice_id": None, "voice_description": "",
     "speed": 1.0, "pitch": 0.0, "volume": 1.0, "avatar_image_path": None},
]
PROJECT = {
    "id": PROJECT_ID, "name": "Selector test", "status": "audio_generated", "cefr_level": "B1",
    "genre": "small_talk", "speakers": SPEAKERS,
}


def profile(profile_id: str, name: str) -> dict:
    ready = {"state": "ready", "missing": []}
    return {
        "id": profile_id, "name": name, "role": "English teacher", "personality": ["friendly"],
        "status": "locked", "profile_version": 2, "identity_version": 2, "face_url": None,
        "body_url": None, "default_accent": "british", "default_tts_engine": "edge_tts",
        "default_voice_id": f"voice-{profile_id}", "default_voice_description": "warm and clear",
        "default_speed": 0.95, "default_pitch": 0.0, "default_volume": 1.0,
        "readiness": {"profile": ready, "visual": ready, "talking_starter": ready},
    }


PROFILES = [profile("profile-nova", "Nova"), profile("profile-mira", "Mira")]


def envelope(data=None, error=None):
    return json.dumps({"success": error is None, "data": data, "error": error, "meta": {}})


@pytest.fixture(scope="module")
def live_server_url(tmp_path_factory: pytest.TempPathFactory):
    with live_server(tmp_path_factory, "character-selector") as url:
        yield url


@pytest.fixture
async def browser_instance() -> AsyncGenerator[Browser, None]:
    async with async_playwright() as playwright:
        browser = await playwright.chromium.launch(headless=True)
        yield browser
        await browser.close()


@pytest.mark.asyncio
async def test_roster_preview_is_read_only_and_choose_is_explicit(browser_instance: Browser, live_server_url: str):
    page = await browser_instance.new_page(viewport={"width": 1280, "height": 900})
    cast = []
    saved_bodies = []

    async def routes(route):
        nonlocal cast
        url, method = route.request.url, route.request.method
        if url.endswith(f"/api/projects/{PROJECT_ID}") and method == "GET":
            body, status = envelope(PROJECT), 200
        elif url.endswith("/audio/status"):
            body, status = envelope({"status": "complete", "timestamps": [], "background_music": ""}), 200
        elif url.endswith(f"/api/projects/{PROJECT_ID}/script"):
            body, status = envelope([]), 200
        elif url.endswith("/api/video/templates"):
            body, status = envelope([{"id": "midnight", "display_name": "Midnight", "preview_url": "/static/video_backgrounds/midnight.png"}]), 200
        elif url.endswith("/api/video/health"):
            body, status = envelope({"remotion_configured": True}), 200
        elif url.endswith("/video/status"):
            body, status = envelope(None, "No video"), 404
        elif url.endswith(f"/api/projects/{PROJECT_ID}/visuals") and method == "GET":
            body, status = envelope({"cast": cast, "scenes": [], "shots": [], "warnings": [], "active_job": None}), 200
        elif url.endswith(f"/api/projects/{PROJECT_ID}/visuals/cast") and method == "PUT":
            payload = json.loads(route.request.post_data or "[]")
            saved_bodies.append(payload)
            cast = [{
                "speaker_index": item["speaker_index"], "character_id": item["character_id"],
                "profile_version": 2, "name": next(p["name"] for p in PROFILES if p["id"] == item["character_id"]),
                "top_color": "blue", "status": "locked", "face_url": None,
            } for item in payload]
            body, status = envelope({"cast": cast, "scenes": [], "shots": [], "warnings": [], "active_job": None}), 200
        elif url.endswith("/api/visuals/characters"):
            body, status = envelope(PROFILES), 200
        elif url.endswith("/api/visuals/scenes"):
            body, status = envelope([]), 200
        elif url.endswith("/api/visuals/health"):
            body, status = envelope({"enabled": False, "venv_image_present": False}), 200
        elif "/coverage" in url:
            body, status = envelope({"total": 0, "covered": 0, "items": [], "matched": 0, "character": 0, "generic": 0}), 200
        else:
            await route.continue_()
            return
        await route.fulfill(status=status, content_type="application/json", body=body)

    await page.route("**/api/**", routes)
    await page.goto(f"{live_server_url}/step5?project_id={PROJECT_ID}")
    await page.wait_for_selector(".cast-roster-card")

    await page.locator('[data-character-id="profile-mira"]').click()
    assert saved_bodies == []
    assert await page.locator(".cast-profile-heading h4").text_content() == "Mira"

    await page.locator('[data-action="choose-profile"]').click()
    await page.wait_for_function("() => document.querySelectorAll('.cast-speaker-slot span')[0].textContent.includes('Mira')")
    assert saved_bodies[0] == [{
        "speaker_index": 0, "character_id": "profile-mira", "copy_profile_defaults": True,
    }]

    await page.locator('[data-cast-speaker-index="1"]').click()
    assert await page.locator('[data-action="choose-profile"]').is_disabled()
    assert "already assigned" in (await page.locator(".cast-compatibility").text_content()).lower()

    await page.locator('[data-character-id="profile-nova"]').click()
    await page.locator("#cast-copy-profile-defaults").uncheck()
    await page.locator('[data-action="choose-profile"]').click()
    await page.wait_for_function("() => document.querySelectorAll('.cast-speaker-slot span')[1].textContent.includes('Nova')")
    assert saved_bodies[1][-1] == {
        "speaker_index": 1, "character_id": "profile-nova", "copy_profile_defaults": False,
    }
    assert not await page.locator("#cast-copy-profile-defaults").is_checked()
    await page.close()
