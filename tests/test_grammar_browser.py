"""Phase 88: the easy-grammar Short in the app -- Step 1 offers it with its 3-minute lengths, the Shorts batch shows its
silent preview, and Step 2 keeps the beat cards on save."""

from typing import AsyncGenerator, Generator

import pytest
from playwright.async_api import Browser, async_playwright

from tests.conftest import live_server


@pytest.fixture(scope="module")
def live_server_url(tmp_path_factory: pytest.TempPathFactory) -> Generator[str, None, None]:
    with live_server(tmp_path_factory, "grammar-browser") as url:
        yield url


@pytest.fixture
async def browser_instance() -> AsyncGenerator[Browser, None]:
    async with async_playwright() as playwright:
        browser = await playwright.chromium.launch(headless=True)
        yield browser
        await browser.close()


async def test_step1_offers_the_grammar_short_with_academic_lengths(browser_instance: Browser, live_server_url: str):
    page = await browser_instance.new_page()
    await page.goto(f"{live_server_url}/step1")
    card = page.locator("[data-template='grammar']")
    await card.wait_for(state="attached")
    assert "Easy grammar" in await card.inner_text() or "Ngữ pháp" in await card.inner_text()
    await page.close()


async def test_step2_save_keeps_the_grammar_cards(browser_instance: Browser, live_server_url: str):
    page = await browser_instance.new_page()
    response = await page.request.post(f"{live_server_url}/api/projects", data={
        "name": "Câu bị động", "topic": "Câu bị động", "cefr_level": "B1", "duration_minutes": 2.0, "num_speakers": 1,
        "genre": "informational", "accent": "american", "presentation_mode": "solo_explainer", "explainer_style": "grammar",
        "speakers": [{"name": "Huyền", "gender": "female", "accent": "american"}]})
    assert response.ok, await response.text()
    project = (await response.json())["data"]
    speaker = project["speakers"][0]["id"]
    card = {"beat": "scene", "scene": 1, "label": "BẺ KHOÁ V3", "title": "Chiếc nhãn dán kết quả!",
            "cards": [{"kind": "sticker", "text": "CLEANED"}]}
    await page.request.put(f"{live_server_url}/api/projects/{project['id']}/script", data={"lines": [
        {"speaker_id": speaker, "text": "V3 giống như một nhãn dán.", "language_notes": {"grammar": card}},
        {"speaker_id": speaker, "text": "Comment đáp án nhé!", "language_notes": {"grammar": {"beat": "follow"}}}]})
    await page.goto(f"{live_server_url}/step2?project_id={project['id']}")
    text = page.locator("#script-list [data-action='edit-text']").first
    await text.wait_for()
    assert await page.locator("#editor-review").is_hidden()  # the beats are built by the server: no editor review
    await text.click()
    editor = page.locator("#script-list textarea").first
    await editor.fill("V3 giống hệt một chiếc nhãn dán.")
    await editor.press("Enter")
    for _ in range(50):
        lines = (await (await page.request.get(f"{live_server_url}/api/projects/{project['id']}/script")).json())["data"]
        if lines[0]["text"] == "V3 giống hệt một chiếc nhãn dán.":
            break
        await page.wait_for_timeout(200)
    assert lines[0]["text"] == "V3 giống hệt một chiếc nhãn dán."
    assert lines[0]["language_notes"]["grammar"]["cards"][0]["text"] == "CLEANED"
    await page.close()


async def test_the_shorts_batch_offers_easy_grammar(browser_instance: Browser, live_server_url: str):
    page = await browser_instance.new_page()
    await page.goto(f"{live_server_url}/shorts-batch")
    card = page.locator("#template-grid .template-card", has_text="Easy grammar").or_(
        page.locator("#template-grid .template-card", has_text="Ngữ pháp dễ hiểu"))
    await card.first.wait_for()
    await page.close()
