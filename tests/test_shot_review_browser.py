"""Task 28.5: Step 5 marks a shot that still failed its checks after the retries, so the user can regenerate it."""

import sqlite3
import time
from typing import AsyncGenerator, Generator

import pytest
from playwright.async_api import Browser, async_playwright

from app.api import visuals as visuals_api
from app.core.config import settings
from tests.conftest import live_server
from tests.test_visuals_project_api import PROJECT, locked_character

NOTE = "Minh's top may not be black; 3 faces found for 2 people"


@pytest.fixture(scope="module")
def live_server_url(tmp_path_factory: pytest.TempPathFactory) -> Generator[str, None, None]:
    pretend_image_python = tmp_path_factory.mktemp("shot-review-venv") / "python.exe"
    pretend_image_python.touch()
    with pytest.MonkeyPatch.context() as patch:
        patch.setattr(settings, "IMAGE_ENGINE", "fake")
        patch.setattr(settings, "AI_VISUALS_ENABLED", True)
        patch.setattr(settings, "VISUALS_COLOUR_RETRIES", 0)
        patch.setattr(visuals_api, "IMAGE_PYTHON", pretend_image_python)
        with live_server(tmp_path_factory, "shot-review-browser") as url:
            yield url


@pytest.fixture
async def browser_instance() -> AsyncGenerator[Browser, None]:
    async with async_playwright() as playwright:
        browser = await playwright.chromium.launch(headless=True)
        yield browser
        await browser.close()


async def _project_with_shots(page, base: str) -> str:
    created = await page.request.post(f"{base}/api/projects", data=PROJECT)
    project_id = (await created.json())["data"]["id"]
    ids = [locked_character("Nova", "yellow"), locked_character("Mira", "green")]
    scene = (await (await page.request.get(f"{base}/api/visuals/scenes")).json())["data"][0]["id"]
    visuals = f"{base}/api/projects/{project_id}/visuals"
    await page.request.put(f"{visuals}/cast", data=[{"speaker_index": i, "character_id": c} for i, c in enumerate(ids)])
    await page.request.put(f"{visuals}/scenes", data=[scene])
    job = (await (await page.request.post(f"{visuals}/shots")).json())["data"]
    for _ in range(600):
        status = (await (await page.request.get(f"{base}/api/visuals/jobs/{job['id']}")).json())["data"]["status"]
        if status in ("complete", "error", "cancelled"):
            assert status == "complete"
            break
        time.sleep(0.05)
    return project_id


@pytest.mark.asyncio
async def test_step5_marks_only_the_shot_that_needs_checking(browser_instance: Browser, live_server_url: str):
    page = await browser_instance.new_page()
    project_id = await _project_with_shots(page, live_server_url)
    with sqlite3.connect(settings.db_path) as connection:
        connection.execute(
            "UPDATE project_shots SET review_note = ? WHERE id = (SELECT id FROM project_shots "
            "WHERE project_id = ? ORDER BY created_at, rowid LIMIT 1)", (NOTE, project_id))
    await page.route(
        f"**/api/projects/{project_id}/audio/status",
        lambda route: route.fulfill(json={"success": True, "data": {"status": "complete", "timestamps": []}}),
    )
    await page.goto(f"{live_server_url}/step5?project_id={project_id}")
    await page.locator("#visual-shot-grid .visual-shot-card").first.wait_for()
    cards = page.locator("#visual-shot-grid .visual-shot-card")
    total = await cards.count()
    assert total > 1
    flagged = page.locator("#visual-shot-grid .visual-shot-card.needs-review")
    assert await flagged.count() == 1
    review = flagged.locator(".visual-review")
    text = await review.text_content()
    assert "Check this shot" in text and NOTE in text and "Regenerate" in text
    assert await review.get_attribute("role") == "status"
    assert "btn-primary" in await flagged.get_by_role("button", name="Regenerate").get_attribute("class")
    assert await page.locator("#visual-shot-grid .visual-review").count() == 1
    other = cards.nth(1)
    assert "btn-primary" not in await other.get_by_role("button", name="Regenerate").get_attribute("class")
    await page.close()
