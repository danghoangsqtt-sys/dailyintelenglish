"""Phase 57 (ENH-039): Step 1 -- video type cards, AI topic ideas, and a video made from the owner's material."""
import json

import pytest
from playwright.async_api import async_playwright, expect

from tests.conftest import live_server


@pytest.fixture(scope="module")
def base_url(tmp_path_factory):
    with live_server(tmp_path_factory, "step1-sources") as url:
        yield url


@pytest.fixture
async def page():
    async with async_playwright() as playwright:
        browser = await playwright.chromium.launch(headless=True)
        page = await browser.new_page(viewport={"width": 1280, "height": 900})
        yield page
        await browser.close()


async def result(response):
    assert response.status == 200, await response.text()
    return (await response.json())["data"]


def envelope(data):
    return {"status": 200, "content_type": "application/json",
            "body": json.dumps({"success": True, "data": data, "error": None, "meta": {}})}


async def test_type_cards_and_ai_ideas_fill_the_form(page, base_url):
    asked = []

    async def ideas(route):
        asked.append(json.loads(route.request.post_data))
        await route.fulfill(**envelope({"ideas": [
            {"name": "How Espresso Machines Work", "topic": "What happens inside an espresso machine", "description": "d1"},
            {"name": "Choosing a Bank Account", "topic": "How to compare bank accounts", "description": "d2"}]}))

    await page.route("**/api/projects/topic-ideas", ideas)
    await page.goto(base_url + "/step1")
    classic = page.locator(".type-card[data-mode='classic']")
    solo = page.locator(".type-card[data-mode='solo_explainer']")
    await expect(classic).to_have_attribute("aria-checked", "true")
    await solo.click()
    await expect(solo).to_have_attribute("aria-checked", "true")
    await expect(page.locator("#presentation-mode")).to_have_value("solo_explainer")
    await expect(page.locator("#explainer-structure-row")).to_be_visible()
    await expect(page.locator("#ideas-panel")).to_be_hidden()
    await page.get_by_label("✨ AI topic ideas").check()
    await page.locator("#ideas-hint").fill("coffee machines")
    await page.locator("#ideas-btn").click()
    await page.locator(".idea-card").first.wait_for()
    assert asked == [{"presentation_mode": "solo_explainer", "cefr_level": "B1", "hint": "coffee machines", "explainer_subject": "topic"}]
    await page.locator(".idea-card").nth(1).click()
    await expect(page.locator("#name")).to_have_value("Choosing a Bank Account")
    await expect(page.locator("#topic")).to_have_value("How to compare bank accounts")


async def test_material_panel_reads_a_photo_and_offers_word_for_word_only_for_a_conversation(page, base_url):
    async def read(route):
        assert b'name="kind"' in route.request.post_data_buffer
        await route.fulfill(**envelope({"text": "A: Hello!\nB: Hi, how are you?"}))

    await page.route("**/api/projects/read-image", read)
    await page.goto(base_url + "/step1")
    await page.get_by_label("📄 From your material").check()
    await expect(page.locator("#material-panel")).to_be_visible()
    await expect(page.locator("#source-use-row")).to_be_visible()
    await page.locator("#source-image").set_input_files({"name": "page.png", "mimeType": "image/png", "buffer": b"png"})
    await expect(page.locator("#source-text")).to_have_value("A: Hello!\nB: Hi, how are you?")
    await expect(page.locator("#source-image-status")).to_contain_text("check the text")
    await page.get_by_label("Use it word for word").check()
    await expect(page.locator("#source-hint")).to_contain_text("first label is Character 1")
    await page.get_by_label("A vocabulary list").check()
    await expect(page.locator("#source-use-row")).to_be_hidden()  # a word list is always written by the AI
    await page.get_by_label("A dialogue").check()
    await page.locator(".type-card[data-mode='solo_explainer']").click()
    await expect(page.locator("#source-use-row")).to_be_hidden()  # a Solo talk is always written by the AI
    await expect(page.locator("#source-hint")).to_contain_text("talk by your presenter")


async def test_a_solo_video_from_a_vocabulary_list_is_created_with_its_material(page, base_url):
    profile = await result(await page.request.post(base_url + "/api/visuals/profiles", data={
        "name": "List Presenter", "gender": "female", "accent": "american", "appearance": "dark hair", "outfit": "red shirt",
    }))
    await page.goto(base_url + "/step1")
    await page.locator(".type-card[data-mode='solo_explainer']").click()
    await page.get_by_label("📄 From your material").check()
    await page.get_by_label("A vocabulary list").check()
    await page.locator("#source-text").fill("invoice - hoá đơn\naudit\ncash flow")
    await page.locator("button[data-choose='0']").click()
    await page.locator(f".cs-card[data-id='{profile['id']}']").click()
    await page.locator("[data-cs='choose']").click()
    await page.locator("[data-cs='close']").click()
    await page.locator("#submit-btn").click()  # no topic typed: the list proposes one
    await page.wait_for_url("**/step2?**")
    projects = await result(await page.request.get(base_url + "/api/projects"))
    created = next(item for item in projects if item["name"].startswith("Using these words"))
    stored = await result(await page.request.get(base_url + f"/api/projects/{created['id']}"))
    assert (stored["source_kind"], stored["source_use"]) == ("vocabulary", "rewrite")
    assert stored["source_text"] == "invoice - hoá đơn\naudit\ncash flow"
    assert stored["topic"] == "Using these words: invoice, audit, cash flow"
    await page.goto(base_url + f"/step1?project_id={created['id']}")
    await expect(page.locator("#source-text")).to_have_value("invoice - hoá đơn\naudit\ncash flow")
    await expect(page.locator("#source-text")).to_be_disabled()
