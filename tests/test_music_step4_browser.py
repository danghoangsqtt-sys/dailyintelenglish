"""Task 22.3: Playwright coverage for the Step 4 "AI background music" card (fake engine, fake AI)."""

import json
from typing import AsyncGenerator, Generator

import httpx
import pytest
from playwright.async_api import Browser, async_playwright

from app.core.config import settings
from app.services.ai.contracts import AIMode, GenerationResult
from app.services.ai.fake_provider import FakeProvider
from app.services.ai.router import AIRouter
from app.services.music import brief_service
from tests.conftest import live_server

BRIEF = {"style": "acoustic", "brief": "warm and curious, calm tempo, soft guitar"}


def _router() -> AIRouter:
    answer = GenerationResult(text=json.dumps(BRIEF), provider="fake", model="fake", latency_ms=1.0, attempt=1,
                              prompt_hash="abc")
    return AIRouter(primary=None, fallback=FakeProvider("fake", [answer]), mode=AIMode.LOCAL)


@pytest.fixture(scope="module")
def live_server_url(tmp_path_factory: pytest.TempPathFactory) -> Generator[str, None, None]:
    with pytest.MonkeyPatch.context() as patch:
        patch.setattr(settings, "MUSIC_ENGINE", "fake")
        patch.setattr(settings, "AI_MUSIC_ENABLED", True)
        patch.setattr(settings, "MUSIC_LENGTH_STRATEGY", "full")
        patch.setattr(brief_service, "build_ai_router_from_settings", _router)
        with live_server(tmp_path_factory, "music-step4-browser") as url:
            yield url


@pytest.fixture
async def browser_instance() -> AsyncGenerator[Browser, None]:
    async with async_playwright() as playwright:
        browser = await playwright.chromium.launch(headless=True)
        yield browser
        await browser.close()


def make_project(url: str) -> str:
    with httpx.Client(base_url=url, timeout=30) as client:
        project = client.post("/api/projects", json={
            "name": "Music step 4", "topic": "Weekend markets", "cefr_level": "B1", "duration_minutes": 2,
            "num_speakers": 2, "genre": "interview", "accent": "american",
            "speakers": [{"name": "Lan", "gender": "female", "accent": "american"},
                         {"name": "Minh", "gender": "male", "accent": "american"}],
        }).json()["data"]
        detail = client.get(f"/api/projects/{project['id']}").json()["data"]
        ids = [speaker["id"] for speaker in sorted(detail["speakers"], key=lambda s: s["speaker_index"])]
        response = client.put(f"/api/projects/{project['id']}/script", json={"lines": [
            {"speaker_id": ids[number % 2], "text": f"Line {number} about the market."} for number in range(4)
        ]})
        assert response.status_code == 200, response.text
    return project["id"]


@pytest.mark.asyncio
async def test_suggest_preview_use_and_attach(browser_instance: Browser, live_server_url: str):
    project_id = make_project(live_server_url)
    page = await browser_instance.new_page()
    await page.goto(f"{live_server_url}/step4?project_id={project_id}")
    await page.wait_for_selector("#workspace:not([hidden])")
    status = page.locator("#music-ai-status")
    await page.wait_for_function(
        "document.querySelector('#music-ai-status').textContent.includes('Suggest a brief')")
    assert await page.input_value("#music-ai-minutes") == "2"
    assert await page.input_value("#music-ai-seconds") == "15"

    await page.click("#music-ai-suggest")
    await page.wait_for_function("document.querySelector('#music-ai-status').textContent.includes('Suggested by the AI')")
    assert await page.input_value("#music-ai-style") == "acoustic"
    assert await page.input_value("#music-ai-brief") == BRIEF["brief"]

    await page.fill("#music-ai-minutes", "1")
    await page.fill("#music-ai-seconds", "30")
    await page.click("#music-ai-make-previews")
    previews = page.locator("#music-ai-previews .music-ai-preview")
    await previews.nth(2).wait_for(timeout=30000)
    assert await previews.count() == 3
    assert "Listen to the previews" in await status.text_content()

    await previews.nth(1).locator("[data-action='use']").click()
    await page.wait_for_function(
        "document.querySelector('#music-ai-status').textContent.includes('selected as this episode')",
        timeout=30000)
    seed = await previews.nth(1).get_attribute("data-seed")
    filename = f"acoustic-warm-and-curious-calm-tempo-soft-guitar-{seed}.mp3"
    assert await page.input_value("#music-select") == filename
    assert filename in await page.locator("#music-timeline").text_content()
    assert "1:30" in await status.text_content()
    assert await page.locator("#music-ai-previews .is-picked").count() == 1

    # Reload: the brief, previews and the attached track are remembered and preselected.
    await page.reload()
    await page.wait_for_selector("#workspace:not([hidden])")
    await page.wait_for_function(f"document.querySelector('#music-select').value === {json.dumps(filename)}")
    assert await page.input_value("#music-ai-brief") == BRIEF["brief"]
    assert await page.locator("#music-ai-previews .music-ai-preview").count() == 3
    assert "Attached:" in await status.text_content()
    await page.close()


@pytest.mark.asyncio
async def test_unavailable_generation_keeps_the_dropdown_usable(
    browser_instance: Browser, live_server_url: str, monkeypatch: pytest.MonkeyPatch,
):
    project_id = make_project(live_server_url)
    monkeypatch.setattr(settings, "AI_MUSIC_ENABLED", False)
    page = await browser_instance.new_page()
    await page.goto(f"{live_server_url}/step4?project_id={project_id}")
    await page.wait_for_selector("#workspace:not([hidden])")
    note = page.locator("#music-ai-unavailable")
    await note.wait_for()
    assert "disabled" in await note.text_content()
    assert await page.locator("#music-ai-make-previews").is_disabled()
    assert await page.locator("#music-select").is_enabled()
    await page.close()
