"""Task 22.8 (D51): Step 4's "✨ Auto (best match)" background music, in a real browser."""

import json
import subprocess
from typing import AsyncGenerator, Generator

import httpx
import pytest
from playwright.async_api import Browser, async_playwright

from app.core.config import settings
from app.services import music_select_service
from app.services.ai.contracts import AIMode, GenerationResult
from app.services.ai.fake_provider import FakeProvider
from app.services.ai.router import AIRouter
from tests.conftest import live_server


def _router() -> AIRouter:
    pick = {"filename": "market_walk.mp3", "reason": "Warm guitar suits a friendly market chat."}
    results = [GenerationResult(text=json.dumps(pick), provider="fake", model="fake", latency_ms=1.0, attempt=1,
                                prompt_hash="x") for _ in range(10)]
    return AIRouter(primary=None, fallback=FakeProvider("fake", results), mode=AIMode.LOCAL)


@pytest.fixture(scope="module")
def live_server_url(tmp_path_factory: pytest.TempPathFactory) -> Generator[str, None, None]:
    with pytest.MonkeyPatch.context() as patch:
        patch.setattr(music_select_service, "build_ai_router_from_settings", _router)
        with live_server(tmp_path_factory, "music-auto-browser") as url:
            yield url


@pytest.fixture
async def browser_instance() -> AsyncGenerator[Browser, None]:
    async with async_playwright() as playwright:
        browser = await playwright.chromium.launch(headless=True)
        yield browser
        await browser.close()


def setup_project(url: str, with_tracks: bool) -> str:
    music_dir = settings.DATA_DIR / "music_library"
    music_dir.mkdir(parents=True, exist_ok=True)
    for path in music_dir.iterdir():
        if path.is_file():
            path.unlink()
    with httpx.Client(base_url=url, timeout=30) as client:
        if with_tracks:
            for name, seconds, mood in (("market_walk.mp3", 150, "acoustic"), ("sleepy.mp3", 150, "calm")):
                subprocess.run([settings.FFMPEG_PATH, "-y", "-loglevel", "error", "-f", "lavfi", "-i",
                                "anullsrc=r=8000:cl=mono", "-t", str(seconds), "-b:a", "16k", str(music_dir / name)],
                               check=True)
            client.get("/api/music")
            for name, _, mood in (("market_walk.mp3", 0, "acoustic"), ("sleepy.mp3", 0, "calm")):
                assert client.patch(f"/api/music/{name}", json={"mood": mood}).status_code == 200
        project = client.post("/api/projects", json={
            "name": "Auto music", "topic": "Weekend markets", "cefr_level": "B1", "duration_minutes": 2,
            "num_speakers": 2, "genre": "interview", "accent": "american",
            "speakers": [{"name": "Lan", "gender": "female", "accent": "american"},
                         {"name": "Minh", "gender": "male", "accent": "american"}],
        }).json()["data"]
        detail = client.get(f"/api/projects/{project['id']}").json()["data"]
        ids = [speaker["id"] for speaker in sorted(detail["speakers"], key=lambda s: s["speaker_index"])]
        client.put(f"/api/projects/{project['id']}/script", json={"lines": [
            {"speaker_id": ids[number % 2], "text": f"Line {number} about the market."} for number in range(2)]})
    return project["id"]


async def stub_audio(page, sent: list) -> None:
    """No real TTS or mixing: capture what Generate sends."""

    async def handle(route):
        url, method = route.request.url, route.request.method
        if "/tts/preview" in url and method == "POST":
            await route.fulfill(status=200, content_type="application/json",
                                body=json.dumps({"success": True, "data": {"audio_path": "x.mp3"}, "error": None}))
        elif url.endswith("/audio/generate") and method == "POST":
            sent.append(json.loads(route.request.post_data or "{}"))
            await route.fulfill(status=500, content_type="application/json",
                                body=json.dumps({"success": False, "data": None, "error": "stub"}))
        else:
            await route.continue_()

    await page.route("**/api/**", handle)


@pytest.mark.asyncio
async def test_auto_is_the_default_and_generate_sends_the_pick(browser_instance: Browser, live_server_url: str):
    project_id = setup_project(live_server_url, with_tracks=True)
    page = await browser_instance.new_page()
    sent: list = []
    await stub_audio(page, sent)
    await page.goto(f"{live_server_url}/step4?project_id={project_id}")
    await page.wait_for_selector("#workspace:not([hidden])")
    assert await page.input_value("#music-select") == "__auto__"
    await page.wait_for_function("document.querySelector('#music-auto-note').textContent.startsWith('Auto pick:')")
    note = await page.locator("#music-auto-note").text_content()
    assert "Market walk (Acoustic / warm, 2:30)" in note and "Warm guitar suits a friendly market chat." in note
    assert "✨ Market walk" in await page.locator("#music-timeline").text_content()
    options = await page.locator("#music-select option").all_text_contents()
    assert options[:2] == ["✨ Auto (best match)", "None"] and "Sleepy (Calm / ambient, 2:30)" in options

    await page.click("#generate-btn")
    for _ in range(50):
        if sent:
            break
        await page.wait_for_timeout(100)
    assert sent and sent[0]["background_music"] == "market_walk.mp3"

    await page.select_option("#music-select", "")
    assert await page.locator("#music-auto-note").text_content() == ""
    assert "No music selected" in await page.locator("#music-timeline").text_content()
    await page.select_option("#music-select", "sleepy.mp3")
    assert "Sleepy" in await page.locator("#music-timeline").text_content()
    await page.close()


@pytest.mark.asyncio
async def test_empty_library_has_no_auto_option(browser_instance: Browser, live_server_url: str):
    project_id = setup_project(live_server_url, with_tracks=False)
    page = await browser_instance.new_page()
    await page.goto(f"{live_server_url}/step4?project_id={project_id}")
    await page.wait_for_selector("#workspace:not([hidden])")
    assert await page.locator("#music-select option").all_text_contents() == ["None"]
    assert "Music Library" in await page.locator("#music-auto-note").text_content()
    await page.close()
