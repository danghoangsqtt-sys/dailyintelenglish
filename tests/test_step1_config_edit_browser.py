"""Browser coverage for Step 1 create, edit, locked, and load-error modes."""

import asyncio
import json
from copy import deepcopy
from typing import AsyncGenerator

import pytest
from playwright.async_api import Browser, async_playwright

from tests.conftest import live_server

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


def _profile(profile_id: str, name: str, gender: str, accent: str, voice=(1.0, 0.0, 1.0)) -> dict:
    ready = {"ready": True, "missing": []}
    return {
        "id": profile_id, "name": name, "gender": gender, "accent": accent, "archived": False, "intro": "",
        "personality": [], "pictures": {"portrait": None, "base": None},
        "voice": {"voice_id": "en-GB-RyanNeural", "speed": voice[0], "pitch": voice[1], "volume": voice[2]},
        "readiness": {"profile": ready, "voice": ready, "core_visuals": ready, "video_ready": True, "talking_ready": True},
    }


PROFILES = [
    _profile("p-alex", "Alex", "male", "british", (1.25, 0.1, 0.8)),
    _profile("p-sam", "Sam", "female", "american", (0.9, -0.2, 1.1)),
    _profile("p-ben", "Ben", "male", "british", (1.0, 0.0, 1.0)),
    _profile("p-lina", "Lina", "female", "american"),
]


async def _character_routes(page, cast: list[dict], saved_casts: list) -> None:
    """Phase 33 (D80): Step 1 reads the profiles and the existing cast, and saves the chosen cast after the project."""

    async def profiles(route):
        await route.fulfill(status=200, content_type="application/json",
                            body=json.dumps({"success": True, "data": PROFILES}))

    async def visuals(route):
        await route.fulfill(status=200, content_type="application/json",
                            body=json.dumps({"success": True, "data": {"cast": cast, "scenes": [], "shots": []}}))

    async def save_cast(route):
        saved_casts.append(json.loads(route.request.post_data))
        await route.fulfill(status=200, content_type="application/json",
                            body=json.dumps({"success": True, "data": {"cast": [], "scenes": [], "shots": []}}))

    await page.route("**/api/visuals/profiles*", profiles)
    await page.route("**/api/projects/*/visuals", visuals)
    await page.route("**/api/projects/*/visuals/cast", save_cast)


async def _choose(page, speaker_index: int, name: str) -> None:
    await page.click(f'[data-choose="{speaker_index}"]')
    await page.locator(".cs-card", has_text=name).click()
    await page.locator('[data-cs="choose"]').click()
    await page.wait_for_selector(f'.cs-slot[data-slot="{speaker_index}"]:has-text("{name}")')
    await page.locator('[data-cs="close"]').click()


@pytest.fixture(scope="module")
def live_server_url(tmp_path_factory: pytest.TempPathFactory):
    with live_server(tmp_path_factory, "step1-config-edit") as url:
        yield url


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

    saved_casts: list = []
    await page.route(f"**/api/projects/{PROJECT_ID}", handle_project)
    await page.route("**/api/projects", count_posts)
    await _character_routes(page, [{"speaker_index": 0, "character_id": "p-alex"},
                                   {"speaker_index": 1, "character_id": "p-sam"}], saved_casts)
    await page.goto(f"{live_server_url}/step1?project_id={PROJECT_ID}")
    await page.wait_for_selector("#submit-btn:not([hidden])")

    await page.fill("#name", "Updated Draft")
    page.once("dialog", lambda dialog: asyncio.ensure_future(dialog.dismiss()))  # keep this project's own voice settings
    await _choose(page, 0, "Ben")
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
    assert saved_casts == [[{"speaker_index": 0, "character_id": "p-ben"}, {"speaker_index": 1, "character_id": "p-sam"}]]
    assert payload["speakers"][0] == {
        "name": "Ben",
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

    saved_casts: list = []
    await page.route("**/api/projects", handle_projects)
    await _character_routes(page, [], saved_casts)
    await page.goto(f"{live_server_url}/step1")
    await page.wait_for_selector("#submit-btn:not([hidden])")

    assert await page.locator("#submit-btn").text_content() == "Create Project"
    assert await page.input_value("#speaker-name-0") == "Alex"  # the old defaults, now real characters
    assert await page.input_value("#speaker-name-1") == "Lina"
    assert await page.locator("#speaker-name-0").get_attribute("readonly") is not None
    await page.fill("#name", "New Project")
    await page.fill("#topic", "A new topic")
    await _choose(page, 1, "Sam")
    await page.click("#submit-btn")
    await page.wait_for_url("**/step2?project_id=new-project-id*")

    assert len(post_payloads) == 1
    assert post_payloads[0]["name"] == "New Project"
    assert [speaker["name"] for speaker in post_payloads[0]["speakers"]] == ["Alex", "Sam"]
    assert saved_casts == [[{"speaker_index": 0, "character_id": "p-alex"}, {"speaker_index": 1, "character_id": "p-sam"}]]
    await page.close()
