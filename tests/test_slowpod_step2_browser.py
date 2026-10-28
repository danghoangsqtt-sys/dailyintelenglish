"""Phase 81: Step 2 shows a slow-podcast line's Vietnamese translation and saves an edit of it."""

from typing import AsyncGenerator, Generator

import pytest
from playwright.async_api import Browser, async_playwright

from tests.conftest import live_server


@pytest.fixture(scope="module")
def live_server_url(tmp_path_factory: pytest.TempPathFactory) -> Generator[str, None, None]:
    with live_server(tmp_path_factory, "slowpod-step2-browser") as url:
        yield url


@pytest.fixture
async def browser_instance() -> AsyncGenerator[Browser, None]:
    async with async_playwright() as playwright:
        browser = await playwright.chromium.launch(headless=True)
        yield browser
        await browser.close()


async def test_the_translation_is_shown_edited_and_saved(browser_instance: Browser, live_server_url: str):
    page = await browser_instance.new_page()
    response = await page.request.post(f"{live_server_url}/api/projects", data={
        "name": "Slow podcast", "topic": "My morning", "cefr_level": "A2", "duration_minutes": 0.75, "num_speakers": 1,
        "genre": "informational", "accent": "american", "presentation_mode": "solo_explainer", "explainer_style": "slowpod",
        "speakers": [{"name": "Lina", "gender": "female", "accent": "american"}]})
    project = (await response.json())["data"]
    speaker = project["speakers"][0]["id"]
    await page.request.put(f"{live_server_url}/api/projects/{project['id']}/script", data={"lines": [
        {"speaker_id": speaker, "text": "Every morning, I wake up at six.", "language_notes": {"translation_vi": "Mỗi sáng tôi dậy lúc sáu giờ."}}]})
    await page.goto(f"{live_server_url}/step2?project_id={project['id']}")
    field = page.locator("#script-list [data-action='translation']")
    await field.wait_for()
    assert await field.input_value() == "Mỗi sáng tôi dậy lúc sáu giờ."
    await field.fill("Sáng nào tôi cũng dậy lúc sáu giờ.")
    await field.dispatch_event("change")
    for _ in range(50):
        lines = (await (await page.request.get(f"{live_server_url}/api/projects/{project['id']}/script")).json())["data"]
        if lines[0]["language_notes"].get("translation_vi") == "Sáng nào tôi cũng dậy lúc sáu giờ.":
            break
        await page.wait_for_timeout(200)
    assert lines[0]["language_notes"]["translation_vi"] == "Sáng nào tôi cũng dậy lúc sáu giờ."
    await page.close()
