"""Browser coverage for Task 4.2a's Learning workspace shell and item inspector.

First browser coverage this page has ever had — previously only API/service-level tests
existed (`test_learning_api.py`, `test_learning_service.py`).
"""

import json
import socket
import threading
import time
from typing import AsyncGenerator

import pytest
import uvicorn
from playwright.async_api import Browser, Page, async_playwright

from app.main import app

PROJECT_ID = "learning-shell-project"
PROJECT = {
    "id": PROJECT_ID,
    "name": "Learning Shell Test",
    "status": "script_generated",
    "topic": "Testing the new workspace",
    "cefr_level": "B1",
    "genre": "interview",
    "speakers": [{"id": "speaker-a", "name": "Alex", "gender": "male", "accent": "american"}],
}
PACK = {
    "vocabulary": [
        {
            "word": "thorough",
            "part_of_speech": "adjective",
            "ipa": "/ˈθʌrə/",
            "definition_en": "careful and complete",
            "definition_vi": "kỹ lưỡng",
            "example_sentence": "She did a thorough review.",
        },
        {
            "word": "deliberate",
            "part_of_speech": "adjective",
            "ipa": "/dɪˈlɪbərət/",
            "definition_en": "done on purpose",
            "definition_vi": "có chủ ý",
            "example_sentence": "It was a deliberate choice.",
        },
    ],
    "idioms": [
        {
            "phrase": "pick up the slack",
            "meaning_en": "do extra work to cover for someone",
            "meaning_vi": "gánh vác thêm việc",
            "example_sentence": "I had to pick up the slack.",
        }
    ],
    "grammar": [
        {
            "point": "Present perfect",
            "structure": "have/has + past participle",
            "explanation_en": "Links a past action to now.",
            "explanation_vi": "Liên kết hành động quá khứ với hiện tại.",
            "examples": ["It has made our planning easier."],
        }
    ],
    "questions": [
        {
            "question": "What did the team change?",
            "options": ["Planning", "Location"],
            "correct_answer": "Planning",
            "explanation": "The transcript explicitly mentions planning.",
        }
    ],
}


def _find_free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as listener:
        listener.bind(("127.0.0.1", 0))
        return listener.getsockname()[1]


@pytest.fixture(scope="module")
def live_server_url():
    port = _find_free_port()
    server = uvicorn.Server(uvicorn.Config(app, host="127.0.0.1", port=port, log_level="warning"))
    thread = threading.Thread(target=server.run, daemon=True)
    thread.start()
    started_at = time.time()
    while time.time() - started_at < 10.0:
        try:
            with socket.create_connection(("127.0.0.1", port), timeout=0.5):
                break
        except OSError:
            time.sleep(0.1)
    else:
        raise RuntimeError("Live test server failed to start within 10 seconds")
    yield f"http://127.0.0.1:{port}"


@pytest.fixture
async def browser_instance() -> AsyncGenerator[Browser, None]:
    async with async_playwright() as playwright:
        browser = await playwright.chromium.launch(headless=True)
        yield browser
        await browser.close()


def _envelope(data, error=None) -> str:
    return json.dumps({"success": error is None, "data": data, "error": error, "meta": {}})


async def _mock_learning_routes(page: Page, save_calls: list[str] | None = None) -> None:
    async def handle(route):
        url, method = route.request.url, route.request.method
        if url.endswith(f"/api/projects/{PROJECT_ID}") and method == "GET":
            await route.fulfill(status=200, content_type="application/json", body=_envelope(PROJECT))
        elif url.endswith(f"/api/projects/{PROJECT_ID}/learning") and method == "GET":
            await route.fulfill(status=200, content_type="application/json", body=_envelope(PACK))
        elif url.endswith(f"/api/projects/{PROJECT_ID}/learning") and method == "PUT":
            if save_calls is not None:
                save_calls.append(route.request.post_data or "")
            await route.fulfill(status=200, content_type="application/json", body=_envelope(PACK))
        else:
            await route.continue_()

    await page.route("**/api/**", handle)


@pytest.mark.asyncio
async def test_learning_shell_resizes_collapses_and_keeps_tabs_working(
    browser_instance: Browser, live_server_url: str
):
    page = await browser_instance.new_page(viewport={"width": 1440, "height": 900})
    await _mock_learning_routes(page)
    await page.goto(f"{live_server_url}/step3?project_id={PROJECT_ID}")
    await page.wait_for_selector("#content-wrap:not([hidden])")

    before = await page.locator("#pane-sidebar").bounding_box()
    handle = await page.locator("#resizer-left").bounding_box()
    assert before and handle
    await page.mouse.move(handle["x"] + 2, handle["y"] + 30)
    await page.mouse.down()
    await page.mouse.move(handle["x"] + 122, handle["y"] + 30)
    await page.mouse.up()
    after = await page.locator("#pane-sidebar").bounding_box()
    assert after and after["width"] > before["width"] + 80

    inspector_before = await page.locator("#pane-inspector").bounding_box()
    right_handle = await page.locator("#resizer-right").bounding_box()
    assert inspector_before and right_handle
    await page.mouse.move(right_handle["x"] + 2, right_handle["y"] + 30)
    await page.mouse.down()
    await page.mouse.move(right_handle["x"] - 82, right_handle["y"] + 30)
    await page.mouse.up()
    inspector_after = await page.locator("#pane-inspector").bounding_box()
    assert inspector_after and inspector_after["width"] > inspector_before["width"] + 70

    await page.click("#sidebar-collapse-btn")
    assert await page.locator("#pane-sidebar").evaluate("element => element.classList.contains('collapsed')")

    # Tabs still work inside the new shell.
    await page.click("[data-tab='idioms']")
    assert await page.locator("#idioms-panel").is_hidden() is False
    assert await page.locator("#vocabulary-panel").is_hidden() is True
    await page.close()


@pytest.mark.asyncio
async def test_learning_item_selection_shows_detail_and_clears_on_tab_switch(
    browser_instance: Browser, live_server_url: str
):
    page = await browser_instance.new_page()
    await _mock_learning_routes(page)
    await page.goto(f"{live_server_url}/step3?project_id={PROJECT_ID}")
    await page.wait_for_selector("#content-wrap:not([hidden])")

    assert "Select an item" in await page.locator("#learning-inspector").text_content()

    await page.click(".item-card[data-section='vocabulary'][data-index='1']")
    inspector_text = await page.locator("#learning-inspector").text_content()
    assert "deliberate" in inspector_text
    assert "done on purpose" in inspector_text
    assert await page.locator(".item-card[data-section='vocabulary'][data-index='1']").evaluate(
        "element => element.classList.contains('selected')"
    )

    # Switching tabs clears a selection that belongs to a different section.
    await page.click("[data-tab='grammar']")
    assert "Select an item" in await page.locator("#learning-inspector").text_content()

    # Quiz inspector always shows the answer, independent of the main list's toggle.
    await page.click("[data-tab='quiz']")
    await page.click(".item-card[data-section='questions'][data-index='0']")
    quiz_inspector_text = await page.locator("#learning-inspector").text_content()
    assert "Planning" in quiz_inspector_text
    assert "explicitly mentions planning" in quiz_inspector_text
    # The main list's own answer stays hidden (untouched by inspecting it).
    assert await page.locator(".quiz-answer").is_hidden()
    await page.close()


@pytest.mark.asyncio
async def test_learning_inline_edit_and_autosave_still_works(browser_instance: Browser, live_server_url: str):
    page = await browser_instance.new_page()
    save_calls: list[str] = []
    await _mock_learning_routes(page, save_calls=save_calls)
    await page.goto(f"{live_server_url}/step3?project_id={PROJECT_ID}")
    await page.wait_for_selector("#content-wrap:not([hidden])")

    field = page.locator(".item-card[data-section='vocabulary'][data-index='0'] .item-title")
    await field.click()
    await field.press("Control+A")
    await field.type("meticulous")
    await field.evaluate("element => element.blur()")

    started_at = time.time()
    while not save_calls and time.time() - started_at < 5.0:
        await page.wait_for_timeout(50)
    assert len(save_calls) >= 1
    payload = json.loads(save_calls[-1])
    assert payload["vocabulary"][0]["word"] == "meticulous"

    # The click-to-edit also selects the card (bubbles to the tab-panel click handler),
    # so the inspector should reflect the edited value too, not the stale pre-edit text.
    assert "meticulous" in await page.locator("#learning-inspector").text_content()
    await page.close()
