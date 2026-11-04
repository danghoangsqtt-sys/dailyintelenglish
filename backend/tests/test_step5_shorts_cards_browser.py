"""Phase 78 (Task 78.3): the Shorts & TikTok clip cards -- a 9:16 sketch before rendering, accessible fields, a length that
follows the edited lines, and Approve that keeps edited lines. The server's video/audio/shorts answers are stubbed: this checks
the page, the API itself is covered by test_shorts.py."""

import json
from typing import AsyncGenerator, Generator

import pytest
from playwright.async_api import Browser, async_playwright

from backend.tests.conftest import live_server

TIMESTAMPS = [{"start_sec": index * 10.0, "end_sec": index * 10.0 + 9.5, "label": "Lan" if index % 2 else "Minh",
               "speaker_id": "s", "text": f"Line {index + 1} of the talk."} for index in range(12)]
CLIP = {"id": "clip-1", "line_from": 2, "line_to": 5, "hook": "How to start a chat", "reason": "Useful openers.",
        "status": "proposed", "seconds": 39.5, "video_url": None, "cover_url": None,
        "packages": {"shorts": {"title": "How to start a chat #Shorts", "description": "Learn"}, "tiktok": {"caption": "Learn"}}}


@pytest.fixture(scope="module")
def live_server_url(tmp_path_factory: pytest.TempPathFactory) -> Generator[str, None, None]:
    with live_server(tmp_path_factory, "shorts-cards-browser") as url:
        yield url


@pytest.fixture
async def browser_instance() -> AsyncGenerator[Browser, None]:
    async with async_playwright() as playwright:
        browser = await playwright.chromium.launch(headless=True)
        yield browser
        await browser.close()


async def _stub(page, url: str, explainer_style: str | None = None) -> tuple[str, list]:
    response = await page.request.post(f"{url}/api/projects", data={
        "name": "Shorts cards", "topic": "Small talk at work", "cefr_level": "B1", "duration_minutes": 2,
        "num_speakers": 2, "genre": "interview", "accent": "american",
        "speakers": [{"name": "Lan", "gender": "female", "accent": "american"},
                     {"name": "Minh", "gender": "male", "accent": "american"}],
    })
    project_id = (await response.json())["data"]["id"]
    sent: list = []
    ok = lambda data: {"success": True, "data": data, "error": None}  # noqa: E731
    await page.route(f"**/api/projects/{project_id}/audio/status",
                     lambda route: route.fulfill(json=ok({"status": "complete", "timestamps": TIMESTAMPS})))
    await page.route(f"**/api/projects/{project_id}/video/status",
                     lambda route: route.fulfill(json=ok({"status": "complete", "mp4_path": "x.mp4", "mp4_path_vertical": None})))
    await page.route(f"**/api/projects/{project_id}/storyboard/preview", lambda route: route.fulfill(json=ok({"lines": 12, "beats": [
        {"position": 0, "line_from": 0, "line_to": 11, "kind": "scene", "scene": None, "scene_is_fallback": False,
         "speaking": 0, "characters": []}]})))

    async def shorts(route):
        if route.request.method == "PATCH":
            sent.append(json.loads(route.request.post_data))
            await route.fulfill(json=ok({**CLIP, "status": "approved"}))
        else:
            await route.fulfill(json=ok([CLIP]))
    await page.route(f"**/api/projects/{project_id}/shorts**", shorts)
    if explainer_style:
        async def project(route):
            original = await route.fetch()
            body = await original.json()
            body["data"]["explainer_style"] = explainer_style
            await route.fulfill(response=original, json=body)
        await page.route(f"**/api/projects/{project_id}", project)
    return project_id, sent


async def test_clip_card_sketch_length_and_approve_keeps_edited_lines(browser_instance: Browser, live_server_url: str):
    page = await browser_instance.new_page()
    project_id, sent = await _stub(page, live_server_url)
    await page.goto(f"{live_server_url}/step5?project_id={project_id}")
    card = page.locator("#shorts-list .short-card")
    await card.wait_for()
    assert await card.locator(".bp-frame.is-vertical .bp-hook").inner_text() == "How to start a chat"
    assert "Line 3 of the talk." in await card.locator(".bp-caption").inner_text()
    assert await card.get_by_label("First line").input_value() == "3"
    assert await card.locator(".short-length").inner_text() == "39.5 s"
    reason_box = await card.locator(".short-reason").bounding_box()
    fields_box = await card.locator(".short-fields").bounding_box()
    assert reason_box["y"] >= fields_box["y"] + fields_box["height"]  # V2: the reason no longer covers the inputs

    await card.get_by_label("Last line").fill("12")
    assert "a clip lasts 30–90 s" in await card.locator(".short-length").inner_text()  # 119.5 s
    await card.get_by_label("Last line").fill("7")
    assert await card.locator(".short-length").inner_text() == "49.5 s"
    await card.get_by_role("button", name="Approve").click()
    await page.wait_for_function("document.querySelector('#shorts-progress').textContent === 'Approved.'")
    assert sent == [{"line_from": 2, "line_to": 6, "status": "approved", "hook": "How to start a chat"}]
    await page.close()


async def test_a_short_project_explains_instead_of_offering_clips(browser_instance: Browser, live_server_url: str):
    page = await browser_instance.new_page()
    project_id, _sent = await _stub(page, live_server_url, explainer_style="chat")
    await page.goto(f"{live_server_url}/step5?project_id={project_id}")
    await page.locator("#shorts-vertical-main").wait_for()
    assert await page.locator("#shorts-tools").is_hidden()
    assert await page.locator("#result-player.is-vertical").count() == 1
    await page.close()
