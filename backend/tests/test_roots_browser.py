"""Phase 87: the word-roots Short in the app -- Step 1 offers it with its 3-minute lengths, Step 2 keeps the beat cards
on save, and Step 4 shows a VieNeu speaker's Vietnamese voices."""

from typing import AsyncGenerator, Generator

import pytest
from playwright.async_api import Browser, async_playwright

from backend.tests.conftest import live_server


@pytest.fixture(scope="module")
def live_server_url(tmp_path_factory: pytest.TempPathFactory) -> Generator[str, None, None]:
    with live_server(tmp_path_factory, "roots-browser") as url:
        yield url


@pytest.fixture
async def browser_instance() -> AsyncGenerator[Browser, None]:
    async with async_playwright() as playwright:
        browser = await playwright.chromium.launch(headless=True)
        yield browser
        await browser.close()


async def _roots_project(page, url: str, engine: str = "edge_tts") -> dict:
    response = await page.request.post(f"{url}/api/projects", data={
        "name": "Gốc PRESS", "topic": "Gốc PRESS", "cefr_level": "B1", "duration_minutes": 2.0, "num_speakers": 1,
        "genre": "informational", "accent": "american", "presentation_mode": "solo_explainer", "explainer_style": "roots",
        "speakers": [{"name": "Huyền", "gender": "female", "accent": "american", "tts_engine": engine}]})
    assert response.ok, await response.text()
    return (await response.json())["data"]


async def test_step1_offers_the_roots_short_with_academic_lengths(browser_instance: Browser, live_server_url: str):
    page = await browser_instance.new_page()
    await page.goto(f"{live_server_url}/step1")
    card = page.locator("[data-template='roots']")
    await card.wait_for(state="attached")
    assert "Word roots" in await card.inner_text() or "Gốc từ" in await card.inner_text()
    await page.close()


async def test_step2_save_keeps_the_beat_cards(browser_instance: Browser, live_server_url: str):
    page = await browser_instance.new_page()
    project = await _roots_project(page, live_server_url)
    speaker = project["speakers"][0]["id"]
    card = {"beat": "whole", "word": "compress", "meaning": "nén lại",
            "parts": [{"text": "com", "role": "prefix", "meaning": "cùng nhau"}, {"text": "press", "role": "root", "meaning": "ép"}]}
    await page.request.put(f"{live_server_url}/api/projects/{project['id']}/script", data={"lines": [
        {"speaker_id": speaker, "text": "Compress, nén lại.", "language_notes": {"roots": card}},
        {"speaker_id": speaker, "text": "Comment đáp án nhé!", "language_notes": {"roots": {"beat": "follow"}}}]})
    await page.goto(f"{live_server_url}/step2?project_id={project['id']}")
    text = page.locator("#script-list [data-action='edit-text']").first
    await text.wait_for()
    assert await page.locator("#editor-review").is_hidden()  # the beats are built by the server: no editor review
    await text.click()
    editor = page.locator("#script-list textarea").first
    await editor.fill("Compress, nghĩa là nén lại.")
    await editor.press("Enter")
    for _ in range(50):
        lines = (await (await page.request.get(f"{live_server_url}/api/projects/{project['id']}/script")).json())["data"]
        if lines[0]["text"] == "Compress, nghĩa là nén lại.":
            break
        await page.wait_for_timeout(200)
    assert lines[0]["text"] == "Compress, nghĩa là nén lại."
    assert lines[0]["language_notes"]["roots"]["word"] == "compress"
    await page.close()


async def test_step4_shows_the_vieneu_voices_for_a_vietnamese_narrator(browser_instance: Browser, live_server_url: str):
    page = await browser_instance.new_page()
    project = await _roots_project(page, live_server_url, engine="vieneu")
    speaker = project["speakers"][0]["id"]
    await page.request.put(f"{live_server_url}/api/projects/{project['id']}/script", data={"lines": [
        {"speaker_id": speaker, "text": "Compress, nén lại.", "language_notes": {"roots": {"beat": "whole", "word": "compress"}}}]})
    await page.goto(f"{live_server_url}/step4?project_id={project['id']}")
    select = page.locator("select.vieneu-voice")
    await select.wait_for()
    await page.wait_for_function("document.querySelectorAll('select.vieneu-voice option').length === 25")
    assert await select.input_value() == "Ngọc Huyền"
    await select.select_option("Thiện Minh")
    await select.dispatch_event("change")
    await page.locator(".speaker-card button", has_text="Save voice").or_(
        page.locator(".speaker-card button", has_text="Lưu giọng")).first.click()
    for _ in range(50):
        current = (await (await page.request.get(f"{live_server_url}/api/projects/{project['id']}")).json())["data"]["speakers"][0]
        if current["voice_id"] == "Thiện Minh":
            break
        await page.wait_for_timeout(200)
    assert current["tts_engine"] == "vieneu" and current["voice_id"] == "Thiện Minh"
    await page.close()
