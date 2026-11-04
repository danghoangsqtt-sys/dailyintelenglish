"""Phase 90: the "Edit on the video" editor of a grammar Short in Step 5 -- an edit shows on the preview, is saved for
the whole scene and can be undone."""

from typing import AsyncGenerator, Generator

import pytest
from playwright.async_api import Browser, async_playwright

from backend.content.grammar_lesson import GrammarLesson, build_beats
from backend.tests.conftest import live_server
from backend.tests.test_grammar_script import PASSIVE


@pytest.fixture(scope="module")
def live_server_url(tmp_path_factory: pytest.TempPathFactory) -> Generator[str, None, None]:
    with live_server(tmp_path_factory, "beat-editor-browser") as url:
        yield url


@pytest.fixture
async def browser_instance() -> AsyncGenerator[Browser, None]:
    async with async_playwright() as playwright:
        browser = await playwright.chromium.launch(headless=True)
        yield browser
        await browser.close()


async def _project(page, url: str) -> dict:
    response = await page.request.post(f"{url}/api/projects", data={
        "name": "Câu bị động", "topic": "Câu bị động", "cefr_level": "B1", "duration_minutes": 2.0, "num_speakers": 1,
        "genre": "informational", "accent": "american", "presentation_mode": "solo_explainer", "explainer_style": "grammar",
        "speakers": [{"name": "Huyền", "gender": "female", "accent": "american"}]})
    project = (await response.json())["data"]
    speaker = project["speakers"][0]["id"]
    beats = build_beats(GrammarLesson.model_validate(PASSIVE), "vi")[:6]
    await page.request.put(f"{url}/api/projects/{project['id']}/script", data={"lines": [
        {"speaker_id": speaker, "text": text, "language_notes": {"grammar": card}} for text, card in beats]})
    return project


async def _titles(page, url: str, project_id: str) -> list[str]:
    view = (await (await page.request.get(f"{url}/api/projects/{project_id}/beats")).json())["data"]
    return [line["card"]["title"] for line in view["lines"]]


async def test_an_edit_shows_on_the_video_is_saved_for_the_scene_and_undone(browser_instance: Browser, live_server_url: str):
    page = await browser_instance.new_page(viewport={"width": 1500, "height": 1000})
    project = await _project(page, live_server_url)
    await page.goto(f"{live_server_url}/step5?project_id={project['id']}")
    editor = page.locator(".beat-editor")
    await editor.wait_for()
    await page.locator(".beat-item").nth(5).wait_for()
    assert await page.locator(".beat-item").count() == 6
    assert await page.locator(".beat-player-box [data-short-style='grammar']").count() == 1  # the 9:16 player
    await page.locator(".beat-item").nth(3).click()  # scene 1, first line
    title = page.locator(".beat-form [data-f='title']")
    await title.fill("Câu bị động là trạng thái")
    await page.wait_for_function("document.querySelector('[data-grammar-pill]') && "
                                 "document.body.innerText.includes('Câu bị động là trạng thái')")
    for _ in range(40):
        titles = await _titles(page, live_server_url, project["id"])
        if titles[3:6] == ["Câu bị động là trạng thái"] * 3:
            break
        await page.wait_for_timeout(150)
    assert titles[3:6] == ["Câu bị động là trạng thái"] * 3  # the scene's three lines
    assert titles[2] != "Câu bị động là trạng thái"  # the hook is another scene
    await page.locator("[data-act='undo']").click()
    for _ in range(40):
        titles = await _titles(page, live_server_url, project["id"])
        if titles[3] != "Câu bị động là trạng thái":
            break
        await page.wait_for_timeout(150)
    assert titles[3] == titles[4] == titles[5] != "Câu bị động là trạng thái"
    await page.close()


async def test_a_spoken_line_edit_marks_only_that_lines_voice(browser_instance: Browser, live_server_url: str):
    page = await browser_instance.new_page(viewport={"width": 1500, "height": 1000})
    project = await _project(page, live_server_url)
    await page.goto(f"{live_server_url}/step5?project_id={project['id']}")
    await page.locator(".beat-item").nth(5).wait_for()
    await page.locator(".beat-item").nth(2).click()
    await page.locator(".beat-form [data-act='text']").fill("Hiểu bản chất trong một phút!")
    await page.locator("[data-act='text-save']").click()
    await page.wait_for_function("document.querySelectorAll('.beat-item')[2].innerText.includes('Hiểu bản chất trong một phút')")
    lines = (await (await page.request.get(f"{live_server_url}/api/projects/{project['id']}/script")).json())["data"]
    assert lines[2]["text"] == "Hiểu bản chất trong một phút!" and lines[2]["language_notes"]["grammar"]["beat"] == "hook"
    await page.close()


async def test_a_slow_podcast_translation_shows_on_the_video(browser_instance: Browser, live_server_url: str):
    """Phase 91.2: the editor opens for every Short drawn from its lines, with that kind's fields."""
    page = await browser_instance.new_page(viewport={"width": 1500, "height": 1000})
    response = await page.request.post(f"{live_server_url}/api/projects", data={
        "name": "Morning", "topic": "Morning", "cefr_level": "B1", "duration_minutes": 0.75, "num_speakers": 1,
        "genre": "informational", "accent": "american", "presentation_mode": "solo_explainer", "explainer_style": "slowpod",
        "speakers": [{"name": "Huyền", "gender": "female", "accent": "american"}]})
    project = (await response.json())["data"]
    await page.request.put(f"{live_server_url}/api/projects/{project['id']}/script", data={"lines": [
        {"speaker_id": project["speakers"][0]["id"], "text": "I wake up early.", "language_notes": {"translation_vi": "Tôi dậy sớm."}}]})
    await page.goto(f"{live_server_url}/step5?project_id={project['id']}")
    await page.locator(".beat-item").first.wait_for()
    await page.locator(".beat-item").first.click()
    await page.locator(".beat-form [data-f='translation_vi']").fill("Tôi thức dậy sớm.")
    await page.wait_for_function("document.querySelector('[data-slowpod-translation]')?.innerText.includes('Tôi thức dậy sớm.')")
    await page.close()


async def test_a_news_short_has_its_spoken_lines_under_its_editor(browser_instance: Browser, live_server_url: str):
    """Phase 91.3: a solo explainer keeps its visual editor and gains the spoken lines; one saved line keeps the others."""
    page = await browser_instance.new_page(viewport={"width": 1500, "height": 1000})
    response = await page.request.post(f"{live_server_url}/api/projects", data={
        "name": "News", "topic": "Trees", "cefr_level": "B1", "duration_minutes": 0.9, "num_speakers": 1,
        "genre": "informational", "accent": "american", "presentation_mode": "solo_explainer", "explainer_style": "news",
        "speakers": [{"name": "Huyền", "gender": "female", "accent": "american"}]})
    project = (await response.json())["data"]
    await page.request.put(f"{live_server_url}/api/projects/{project['id']}/script", data={"lines": [
        {"speaker_id": project["speakers"][0]["id"], "text": text} for text in ("Cities plant trees.", "It is cooler.")]})
    await page.goto(f"{live_server_url}/step5?project_id={project['id']}")
    panel = page.locator(".line-panel")
    await panel.wait_for()
    await panel.locator("textarea").nth(1).fill("The streets are cooler.")
    await panel.locator("[data-act='save'][data-at='1']").click()
    for _ in range(40):
        lines = (await (await page.request.get(f"{live_server_url}/api/projects/{project['id']}/script")).json())["data"]
        if lines[1]["text"] == "The streets are cooler.":
            break
        await page.wait_for_timeout(150)
    assert [line["text"] for line in lines] == ["Cities plant trees.", "The streets are cooler."]
    await page.close()
