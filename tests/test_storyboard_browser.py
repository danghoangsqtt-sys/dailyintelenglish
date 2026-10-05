"""Task 24.4: Step 5 storyboard review -- propose (fake AI), edit, merge, save, reload, approve."""

import json
from typing import AsyncGenerator, Generator

import pytest
from playwright.async_api import Browser, async_playwright

from app.api import visuals as visuals_api
from app.core.config import settings
from app.services.ai.contracts import AIMode, GenerationResult
from app.services.ai.fake_provider import FakeProvider
from app.services.ai.router import AIRouter
from app.services.visuals import storyboard_service
from tests.conftest import live_server
from tests.test_visuals_project_api import locked_character

PROPOSAL = {"beats": [
    {"line_from": 0, "line_to": 2, "kind": "scene", "scene_id": "builtin-cafe", "new_place": None,
     "speakers": [0, 1], "action": "drinking coffee", "expression": "smile"},
    {"line_from": 3, "line_to": 3, "kind": "insert", "scene_id": None, "new_place": "crowded subway at rush hour",
     "speakers": [], "action": "", "expression": "worried"},
    {"line_from": 4, "line_to": 5, "kind": "scene", "scene_id": "builtin-park", "new_place": None,
     "speakers": [0, 1], "action": "walking along the path", "expression": "calm"},
]}


@pytest.fixture(scope="module")
def live_server_url(tmp_path_factory: pytest.TempPathFactory) -> Generator[str, None, None]:
    pretend_image_python = tmp_path_factory.mktemp("storyboard-browser-venv") / "python.exe"
    pretend_image_python.touch()

    def fake_router() -> AIRouter:
        result = GenerationResult(text=json.dumps(PROPOSAL), provider="fake", model="fake", latency_ms=1.0,
                                  attempt=1, prompt_hash="abc")
        return AIRouter(primary=None, fallback=FakeProvider("fake", [result]), mode=AIMode.LOCAL)

    with pytest.MonkeyPatch.context() as patch:
        patch.setattr(settings, "IMAGE_ENGINE", "fake")
        patch.setattr(settings, "AI_VISUALS_ENABLED", True)
        patch.setattr(visuals_api, "IMAGE_PYTHON", pretend_image_python)
        patch.setattr(storyboard_service, "build_ai_router_from_settings", fake_router)
        with live_server(tmp_path_factory, "storyboard-browser") as url:
            yield url


@pytest.fixture
async def browser_instance() -> AsyncGenerator[Browser, None]:
    async with async_playwright() as playwright:
        browser = await playwright.chromium.launch(headless=True)
        yield browser
        await browser.close()


async def _project(page, url: str) -> str:
    response = await page.request.post(f"{url}/api/projects", data={
        "name": "Storyboard UI", "topic": "Remote work and city life", "cefr_level": "B1", "duration_minutes": 2,
        "num_speakers": 2, "genre": "interview", "accent": "american",
        "speakers": [{"name": "Lan", "gender": "female", "accent": "american"},
                     {"name": "Minh", "gender": "male", "accent": "american"}],
    })
    project_id = (await response.json())["data"]["id"]
    project = (await (await page.request.get(f"{url}/api/projects/{project_id}")).json())["data"]
    ids = {speaker["speaker_index"]: speaker["id"] for speaker in project["speakers"]}
    await page.request.put(f"{url}/api/projects/{project_id}/script", data={"lines": [
        {"speaker_id": ids[number % 2], "text": f"Line {number} about the city."} for number in range(6)]})
    await page.request.put(f"{url}/api/projects/{project_id}/visuals/cast", data=[
        {"speaker_index": 0, "character_id": locked_character("Lan", "yellow")},
        {"speaker_index": 1, "character_id": locked_character("Minh", "green")}])
    await page.route(f"**/api/projects/{project_id}/audio/status",
                     lambda route: route.fulfill(json={"success": True, "data": {"status": "complete", "timestamps": []}}))
    return project_id


async def test_propose_edit_merge_save_reload_approve(browser_instance: Browser, live_server_url: str):
    page = await browser_instance.new_page()
    project_id = await _project(page, live_server_url)
    await page.goto(f"{live_server_url}/step5?project_id={project_id}")
    summary = page.locator("#storyboard-summary")
    await page.wait_for_function("document.querySelector('#storyboard-summary').textContent.includes('No storyboard')")

    await page.locator("#storyboard-propose").click()
    beats = page.locator("#storyboard-beats .storyboard-beat")
    await page.wait_for_function("document.querySelectorAll('#storyboard-beats .storyboard-beat').length === 3")
    text = await summary.inner_text()
    assert "3 beats" in text and "9/12 images" in text and "proposal: ai" in text
    assert "Cafe" in await beats.nth(0).locator("h4").inner_text()
    assert "insert: crowded subway at rush hour" in await beats.nth(1).locator("h4").inner_text()

    await page.locator("#beat-2-action").fill("sitting on a park bench")
    await page.locator("#beat-2-expression").select_option("laugh")
    assert "unsaved changes" in await summary.inner_text()
    await beats.nth(0).get_by_role("button", name="Merge with next").click()
    await page.wait_for_function("document.querySelectorAll('#storyboard-beats .storyboard-beat').length === 2")
    assert "lines 1–4" in await beats.nth(0).locator("h4").inner_text()
    assert "8/12 images" in await summary.inner_text()

    await page.locator("#storyboard-save").click()
    await page.wait_for_function("!document.querySelector('#storyboard-summary').textContent.includes('unsaved')")
    await page.reload()
    await page.wait_for_function("document.querySelectorAll('#storyboard-beats .storyboard-beat').length === 2")
    assert await page.locator("#beat-1-action").input_value() == "sitting on a park bench"
    assert await page.locator("#beat-1-expression").input_value() == "laugh"
    assert "draft (owner)" in await summary.inner_text()

    await page.locator("#beat-1-place").select_option("__new__")
    await page.locator("#beat-1-new-place").fill("a park!!!")
    await page.locator("#storyboard-save").click()
    await page.wait_for_function("document.querySelector('#storyboard-error').textContent.includes('new_place')")

    await page.locator("#beat-1-new-place").fill("a quiet riverside park")
    await page.locator("#storyboard-approve").click()
    await page.wait_for_function("document.querySelector('#storyboard-summary').textContent.includes('approved')")
    assert await page.locator("#storyboard-error").inner_text() == ""
