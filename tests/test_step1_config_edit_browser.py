"""Browser coverage for Step 1 create, edit, locked, and load-error modes."""

import asyncio
import json
import socket
import threading
import time
from copy import deepcopy
from typing import AsyncGenerator

import pytest
import uvicorn
from playwright.async_api import Browser, async_playwright

from app.main import app

PROJECT_ID = "step1-edit-project"
LANGUAGE_FEATURES = {
    "collocation": False,
    "idiom": True,
    "slang": True,
    "local_expressions": False,
    "phrasal_verbs": True,
    "business_register": True,
}
DRAFT_PROJECT = {
    "id": PROJECT_ID,
    "name": "Existing Draft",
    "status": "draft",
    "topic": "A draft topic",
    "cefr_level": "C1",
    "duration_minutes": 12.5,
    "num_speakers": 2,
    "genre": "interview",
    "accent": "british",
    "language_features": LANGUAGE_FEATURES,
    "speakers": [
        {
            "id": "speaker-alex",
            "name": "Alex",
            "gender": "male",
            "accent": "british",
            "tts_engine": "edge_tts",
            "voice_description": "Warm and measured",
            "speed": 1.25,
            "pitch": 0.1,
            "volume": 0.8,
        },
        {
            "id": "speaker-sam",
            "name": "Sam",
            "gender": "female",
            "accent": "american",
            "tts_engine": "omnivoice",
            "voice_description": "Bright",
            "speed": 0.9,
            "pitch": -0.2,
            "volume": 1.1,
        },
    ],
}


def _find_free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


@pytest.fixture(scope="module")
def live_server_url():
    port = _find_free_port()
    config = uvicorn.Config(app, host="127.0.0.1", port=port, log_level="warning")
    server = uvicorn.Server(config)
    thread = threading.Thread(target=server.run, daemon=True)
    thread.start()

    start_time = time.time()
    while time.time() - start_time < 10.0:
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


async def _fulfill_project(route, project: dict) -> None:
    await route.fulfill(
        status=200,
        content_type="application/json",
        body=json.dumps({"success": True, "data": project}),
    )


@pytest.mark.asyncio
async def test_draft_project_is_fetched_and_prefilled(browser_instance: Browser, live_server_url: str):
    page = await browser_instance.new_page()
    get_count = 0

    async def handle_project(route):
        nonlocal get_count
        if route.request.method == "GET":
            get_count += 1
            await _fulfill_project(route, DRAFT_PROJECT)
        else:
            await route.continue_()

    await page.route(f"**/api/projects/{PROJECT_ID}", handle_project)
    await page.goto(f"{live_server_url}/step1?project_id={PROJECT_ID}")
    await page.wait_for_selector("#config-form:not([hidden])")

    assert get_count == 1
    assert await page.input_value("#name") == "Existing Draft"
    assert await page.input_value("#topic") == "A draft topic"
    assert await page.input_value("#cefr") == "C1"
    assert await page.locator("#duration-custom").is_visible()
    assert await page.input_value("#duration-custom") == "12.5"
    assert await page.locator("#genre-grid [data-value='interview']").get_attribute("aria-pressed") == "true"
    assert await page.locator("#accent-grid [data-value='british']").get_attribute("aria-pressed") == "true"
    assert await page.input_value("#num-speakers") == "2"
    assert await page.input_value("#speaker-name-0") == "Alex"
    assert await page.input_value("#speaker-gender-1") == "female"
    assert await page.input_value("#speaker-accent-1") == "american"
    assert not await page.locator("#feature-collocation").is_checked()
    assert await page.locator("#feature-slang").is_checked()
    assert await page.locator("#feature-business_register").is_checked()
    assert await page.locator("#submit-btn").text_content() == "Save Changes"
    await page.close()


@pytest.mark.asyncio
async def test_draft_save_uses_one_put_preserves_id_and_refetches_update(
    browser_instance: Browser, live_server_url: str
):
    page = await browser_instance.new_page()
    current_project = deepcopy(DRAFT_PROJECT)
    put_payloads = []
    post_count = 0

    async def handle_project(route):
        if route.request.method == "GET":
            await _fulfill_project(route, current_project)
        elif route.request.method == "PUT":
            payload = json.loads(route.request.post_data)
            put_payloads.append(payload)
            await asyncio.sleep(0.1)
            current_project.update(payload)
            current_project["id"] = PROJECT_ID
            current_project["status"] = "draft"
            await _fulfill_project(route, current_project)
        else:
            await route.continue_()

    async def count_posts(route):
        nonlocal post_count
        if route.request.method == "POST":
            post_count += 1
        await route.continue_()

    await page.route(f"**/api/projects/{PROJECT_ID}", handle_project)
    await page.route("**/api/projects", count_posts)
    await page.goto(f"{live_server_url}/step1?project_id={PROJECT_ID}")
    await page.wait_for_selector("#submit-btn:not([hidden])")

    await page.fill("#name", "Updated Draft")
    await page.fill("#speaker-name-0", "Alex Updated")
    await page.evaluate(
        """
        const form = document.getElementById("config-form");
        form.requestSubmit();
        form.requestSubmit();
        """
    )
    await page.wait_for_url(f"**/step2?project_id={PROJECT_ID}*")

    assert len(put_payloads) == 1
    assert post_count == 0
    payload = put_payloads[0]
    assert payload["name"] == "Updated Draft"
    assert payload["speakers"][0] == {
        "name": "Alex Updated",
        "gender": "male",
        "accent": "british",
        "tts_engine": "edge_tts",
        "voice_description": "Warm and measured",
        "speed": 1.25,
        "pitch": 0.1,
        "volume": 0.8,
    }

    await page.goto(f"{live_server_url}/step1?project_id={PROJECT_ID}")
    await page.wait_for_selector("#submit-btn:not([hidden])")
    assert await page.input_value("#name") == "Updated Draft"
    assert PROJECT_ID in page.url
    await page.close()


@pytest.mark.parametrize("status", ["script_generated", "audio_generated", "video_generated", "complete"])
@pytest.mark.asyncio
async def test_progressed_project_is_read_only(
    browser_instance: Browser, live_server_url: str, status: str
):
    page = await browser_instance.new_page()
    project = {**deepcopy(DRAFT_PROJECT), "status": status}

    async def handle_project(route):
        await _fulfill_project(route, project)

    await page.route(f"**/api/projects/{PROJECT_ID}", handle_project)
    await page.goto(f"{live_server_url}/step1?project_id={PROJECT_ID}")
    await page.wait_for_selector("#status-banner:not([hidden])")

    assert "read-only" in (await page.text_content("#status-banner")).lower()
    assert await page.input_value("#name") == "Existing Draft"
    assert await page.locator("#submit-btn").is_hidden()
    assert await page.locator("#config-form input:not([disabled])").count() == 0
    assert await page.locator("#config-form select:not([disabled])").count() == 0
    assert await page.locator("#config-form button:not([disabled])").count() == 0
    await page.close()


@pytest.mark.asyncio
async def test_project_load_failure_never_falls_back_to_create_form(
    browser_instance: Browser, live_server_url: str
):
    page = await browser_instance.new_page()

    async def handle_project(route):
        await route.fulfill(
            status=404,
            content_type="application/json",
            body=json.dumps({"success": False, "data": None, "error": "Internal project lookup detail"}),
        )

    await page.route(f"**/api/projects/{PROJECT_ID}", handle_project)
    await page.goto(f"{live_server_url}/step1?project_id={PROJECT_ID}")
    await page.wait_for_selector("#error-banner:not([hidden])")

    banner_text = await page.text_content("#error-banner")
    assert "couldn't load this project" in banner_text.lower()
    assert "Internal project lookup detail" not in banner_text
    assert await page.locator("#config-form").is_hidden()
    assert await page.locator("#submit-btn").is_hidden()
    await page.close()


@pytest.mark.asyncio
async def test_no_project_id_keeps_create_flow(browser_instance: Browser, live_server_url: str):
    page = await browser_instance.new_page()
    post_payloads = []

    async def handle_projects(route):
        if route.request.method == "POST":
            payload = json.loads(route.request.post_data)
            post_payloads.append(payload)
            await route.fulfill(
                status=201,
                content_type="application/json",
                body=json.dumps(
                    {
                        "success": True,
                        "data": {**payload, "id": "new-project-id", "status": "draft"},
                    }
                ),
            )
        else:
            await route.continue_()

    await page.route("**/api/projects", handle_projects)
    await page.goto(f"{live_server_url}/step1")
    await page.wait_for_selector("#submit-btn:not([hidden])")

    assert await page.locator("#submit-btn").text_content() == "Create Project"
    await page.fill("#name", "New Project")
    await page.fill("#topic", "A new topic")
    await page.fill("#speaker-name-0", "Taylor")
    await page.fill("#speaker-name-1", "Morgan")
    await page.click("#submit-btn")
    await page.wait_for_url("**/step2?project_id=new-project-id*")

    assert len(post_payloads) == 1
    assert post_payloads[0]["name"] == "New Project"
    assert [speaker["name"] for speaker in post_payloads[0]["speakers"]] == ["Taylor", "Morgan"]
    await page.close()
