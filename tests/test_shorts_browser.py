"""Phase 63 (ENH-045): the "Shorts viral" card on Step 1 -- templates, the 30/45/60 s lengths, a news article source."""
import pytest
from playwright.async_api import async_playwright, expect

from tests.conftest import live_server

ARTICLE = ("A strong storm reached the coast of Vietnam on Monday. Schools in three provinces closed for two days. "
           "Officials asked people to stay inside.")


@pytest.fixture(scope="module")
def base_url(tmp_path_factory):
    with live_server(tmp_path_factory, "shorts-browser") as url:
        yield url


@pytest.fixture
async def page():
    async with async_playwright() as driver:
        browser = await driver.chromium.launch(headless=True)
        page = await browser.new_page(viewport={"width": 1440, "height": 1000})
        yield page
        await browser.close()


async def result(response):
    assert response.status == 200, await response.text()
    return (await response.json())["data"]


async def test_the_shorts_card_makes_a_vertical_news_short_from_an_article(page, base_url):
    profile = await result(await page.request.post(base_url + "/api/visuals/profiles", data={
        "name": "News Narrator", "gender": "female", "accent": "american", "appearance": "dark hair", "outfit": "blue coat",
    }))
    await page.goto(base_url + "/step1")
    await expect(page.locator("#shorts-templates")).to_be_hidden()
    await page.locator(".type-card[data-mode='shorts']").click()
    await expect(page.locator(".type-card[data-mode='shorts']")).to_have_attribute("aria-checked", "true")
    await expect(page.locator("#shorts-templates")).to_be_visible()
    await expect(page.locator("#subject-cards")).to_be_hidden()
    await expect(page.locator("#duration-presets button")).to_have_text(["30 s", "45 s", "60 s"])
    await expect(page.locator("#duration-presets button[aria-pressed='true']")).to_have_text("45 s")
    await expect(page.locator(".speaker-slot").first).to_have_text("Narrator (voice only)")
    # a blur Short has no material source; a news Short takes an article
    await page.locator("[data-template='blur']").click()
    await expect(page.locator("input[name=content_source][value=material]")).to_be_hidden()
    await page.locator("[data-template='news']").click()
    await page.locator("input[name=content_source][value=material]").check()
    await expect(page.locator("input[name=source_kind][value=article]")).to_be_checked()
    await expect(page.locator("input[name=source_kind][value=dialogue]")).to_be_hidden()
    await expect(page.locator("#link-row")).to_be_visible()
    await page.locator("#source-link").fill("http://127.0.0.1:9/private")
    await page.locator("#source-link-btn").click()
    await expect(page.locator("#source-link-status")).to_contain_text("public")
    await page.locator("#source-text").fill(ARTICLE)
    await page.locator("#name").fill("Storm news")
    await page.locator("#topic").fill("A storm reaches the coast")
    await page.locator("#duration-presets button", has_text="60 s").click()
    await page.locator("button[data-choose='0']").click()
    await page.locator(f".cs-card[data-id='{profile['id']}']").click()
    await page.locator("[data-cs='choose']").click()
    await page.locator("[data-cs='close']").click()
    await page.locator("#submit-btn").click()
    await page.wait_for_url("**/step2?**")
    projects = await result(await page.request.get(base_url + "/api/projects"))
    created = next(item for item in projects if item["name"] == "Storm news")
    stored = await result(await page.request.get(base_url + f"/api/projects/{created['id']}"))
    assert (stored["presentation_mode"], stored["explainer_style"], stored["duration_minutes"]) == ("solo_explainer", "news", 1)
    assert (stored["source_kind"], stored["source_text"]) == ("article", ARTICLE)
