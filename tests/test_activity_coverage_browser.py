"""Task 32.6c: Step 5 explains activity matches and sprite fallbacks before render."""

from typing import AsyncGenerator, Generator

import pytest
from playwright.async_api import Browser, async_playwright

from backend.api import visuals as visuals_api
from backend.core.config import settings
from tests.conftest import live_server
from tests.test_visuals_project_api import PROJECT, locked_character


@pytest.fixture(scope="module")
def live_server_url(tmp_path_factory: pytest.TempPathFactory) -> Generator[str, None, None]:
    pretend_image_python = tmp_path_factory.mktemp("activity-coverage-venv") / "python.exe"
    pretend_image_python.touch()
    with pytest.MonkeyPatch.context() as patch:
        patch.setattr(settings, "IMAGE_ENGINE", "fake")
        patch.setattr(settings, "AI_VISUALS_ENABLED", True)
        patch.setattr(visuals_api, "IMAGE_PYTHON", pretend_image_python)
        with live_server(tmp_path_factory, "activity-coverage-browser") as url:
            yield url


@pytest.fixture
async def browser_instance() -> AsyncGenerator[Browser, None]:
    async with async_playwright() as playwright:
        browser = await playwright.chromium.launch(headless=True)
        yield browser
        await browser.close()


async def _project_with_cast(page, base: str) -> str:
    """A project with two cast characters and one scene (Phase 44: no drawn shots any more)."""
    created = await page.request.post(f"{base}/api/projects", data=PROJECT)
    project_id = (await created.json())["data"]["id"]
    ids = [locked_character("Nova", "yellow"), locked_character("Mira", "green")]
    scene = (await (await page.request.get(f"{base}/api/visuals/scenes")).json())["data"][0]["id"]
    visuals = f"{base}/api/projects/{project_id}/visuals"
    await page.request.put(f"{visuals}/cast", data=[{"speaker_index": i, "character_id": c} for i, c in enumerate(ids)])
    await page.request.put(f"{visuals}/scenes", data=[scene])
    return project_id


async def _step5(page, base: str, project_id: str) -> None:
    await page.route(
        f"**/api/projects/{project_id}/audio/status",
        lambda route: route.fulfill(json={"success": True, "data": {"status": "complete", "timestamps": []}}),
    )
    await page.goto(f"{base}/step5?project_id={project_id}")


@pytest.mark.asyncio
async def test_step5_explains_character_generic_and_missing_activity_coverage(
    browser_instance: Browser, live_server_url: str,
):
    page = await browser_instance.new_page()
    project_id = await _project_with_cast(page, live_server_url)
    await page.route(
        f"**/api/projects/{project_id}/visuals/activity-coverage",
        lambda route: route.fulfill(json={
            "success": True,
            "data": {
                "matched": 2,
                "character": 1,
                "generic": 1,
                "missing": 1,
                "sprite_fallback": 1,
                "to_draw": 0,
                "items": [
                    {"beat_id": "beat-left", "position": 0, "action": "turn left", "status": "character",
                     "fallback": None, "match": {"activity_id": "alex-left", "match_type": "character"}},
                    {"beat_id": "beat-straight", "position": 1, "action": "go straight", "status": "generic",
                     "fallback": None, "match": {"activity_id": "generic-straight", "match_type": "generic"}},
                    {"beat_id": "beat-cross", "position": 2, "action": "cross the street", "status": "missing",
                     "fallback": "sprites", "match": None, "suggestions": ["walking", "go straight"],
                     "activity": "cross the street", "place": "", "prompt": "Create a semi-realistic illustration of one adult",
                     "pending": {"id": "pending-cross", "url": "/static/img/logo.png"}},
                ],
            },
            "error": None,
            "meta": {},
        }),
    )

    await _step5(page, live_server_url, project_id)

    coverage = page.locator("#activity-coverage:not([hidden])")
    await coverage.wait_for()
    text = await coverage.text_content()
    assert "2 of 3 inserts matched (1 character, 1 generic)" in text
    assert 'No illustration for 1: "cross the street" (closest in the library: "walking", "go straight")' in text
    assert "is-warning" in (await coverage.get_attribute("class"))
    card = page.locator('.activity-missing-card[data-beat="beat-cross"]')
    await card.wait_for()
    assert await card.locator('button[data-action="approve"]').is_visible()
    assert await card.locator('button[data-action="redraw"]').is_visible()
    assert "one adult" in await card.locator("textarea").input_value()
    assert await page.locator("#draw-illustrations-btn").is_disabled()  # the only missing insert already has a picture
    await page.close()
