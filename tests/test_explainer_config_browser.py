"""Step1 explicit Solo mode, one-presenter lock and persisted draft/read-only behavior."""
import pytest
from playwright.async_api import async_playwright, expect

from tests.conftest import live_server


@pytest.fixture(scope="module")
def base_url(tmp_path_factory):
    with live_server(tmp_path_factory, "solo-config") as url:
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


async def test_solo_create_without_front_images_then_draft_reload_and_script_lock(page, base_url):
    profile = await result(await page.request.post(base_url + "/api/visuals/profiles", data={
        "name": "Front Presenter", "gender": "male", "accent": "american", "appearance": "dark hair", "outfit": "green shirt",
    }))
    await page.goto(base_url + "/step1")
    await page.locator("#presentation-mode").select_option("solo_explainer")
    await expect(page.locator("#num-speakers")).to_have_value("1")
    await expect(page.locator("#num-speakers")).to_be_disabled()
    await expect(page.locator(".speaker-card")).to_have_count(1)
    await page.locator("#explainer-structure").select_option("how")
    await page.locator("#name").fill("How habits work")
    await page.locator("#topic").fill("Explain a simple everyday habit")
    await page.locator("button[data-choose='0']").click()
    await page.locator(f".cs-card[data-id='{profile['id']}']").click()
    await expect(page.locator("[data-cs='choose']")).to_be_enabled()
    await page.locator("[data-cs='choose']").click()
    await expect(page.locator("[data-cs='choose']")).to_have_text("Chosen for Character 1")
    await page.locator("[data-cs='close']").click()
    await page.locator("#submit-btn").click()
    await page.wait_for_url("**/step2?**")
    projects = await result(await page.request.get(base_url + "/api/projects"))
    project = next(item for item in projects if item["name"] == "How habits work")
    pid = project["id"]
    stored = await result(await page.request.get(base_url + f"/api/projects/{pid}"))
    assert stored["presentation_mode"] == "solo_explainer" and stored["explainer_structure"] == "how"
    assert len(stored["speakers"]) == 1 and stored["speakers"][0]["character_id"] == profile["id"]
    await page.goto(base_url + f"/step1?project_id={pid}")
    await expect(page.locator("#presentation-mode")).to_have_value("solo_explainer")
    await expect(page.locator("#explainer-structure")).to_have_value("how")
    await expect(page.locator("#num-speakers")).to_be_disabled()
    await page.locator("#explainer-structure").select_option("list")
    await page.locator("#submit-btn").click()
    await page.wait_for_url("**/step2?**")
    stored = await result(await page.request.get(base_url + f"/api/projects/{pid}"))
    assert stored["explainer_structure"] == "list"
    await result(await page.request.put(base_url + f"/api/projects/{pid}/script", data={"lines": [
        {"speaker_id": stored["speakers"][0]["id"], "text": "Let's explain this idea."},
    ]}))
    await page.goto(base_url + f"/step1?project_id={pid}")
    await expect(page.locator("#presentation-mode")).to_be_disabled()
    await expect(page.locator("#explainer-structure")).to_be_disabled()


async def test_classic_count_controls_and_readiness_remain_available(page, base_url):
    profile = await result(await page.request.post(base_url + "/api/visuals/profiles", data={
        "name": "Classic Not Ready", "gender": "female", "accent": "american", "appearance": "dark hair", "outfit": "blue shirt",
    }))
    await page.goto(base_url + "/step1")
    await expect(page.locator("#presentation-mode")).to_have_value("classic")
    await expect(page.locator("#num-speakers")).to_be_enabled()
    await page.locator("#num-speakers").fill("3")
    await expect(page.locator(".speaker-card")).to_have_count(3)
    await page.locator("button[data-choose='0']").click()
    await page.locator(f".cs-card[data-id='{profile['id']}']").click()
    await expect(page.locator("[data-cs='choose']")).to_be_disabled()
    await page.locator("[data-cs='close']").click()
    await page.locator("#presentation-mode").select_option("solo_explainer")
    await expect(page.locator("#num-speakers")).to_have_value("1")
    await page.locator("#presentation-mode").select_option("classic")
    await expect(page.locator("#num-speakers")).to_be_enabled()
    await page.locator("#num-speakers").fill("2")
    await expect(page.locator(".speaker-card")).to_have_count(2)
