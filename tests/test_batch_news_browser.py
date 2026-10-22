"""Phase 66 (ENH-048): the Shorts batch page -- ideas from a topic become a dated series; the news tab lists stories."""
import json

import pytest
from playwright.async_api import async_playwright, expect

from tests.conftest import live_server


@pytest.fixture(scope="module")
def base_url(tmp_path_factory):
    with live_server(tmp_path_factory, "batch-browser") as url:
        yield url


@pytest.fixture
async def page():
    async with async_playwright() as driver:
        browser = await driver.chromium.launch(headless=True)
        page = await browser.new_page(viewport={"width": 1400, "height": 1000})
        yield page
        await browser.close()


async def result(response):
    assert response.status == 200, await response.text()
    return (await response.json())["data"]


async def test_ideas_from_a_topic_become_a_dated_series(page, base_url):
    profile = await result(await page.request.post(base_url + "/api/visuals/profiles", data={
        "name": "Batch Narrator", "gender": "female", "accent": "american", "appearance": "dark hair", "outfit": "green coat"}))
    ideas = [{"title": f"Mistake {n}", "brief": f"Point {n}"} for n in range(1, 6)]

    async def fake_ideas(route):
        body = json.loads(route.request.post_data)
        assert (body["template"], body["count"], body["topic"]) == ("mistakes", 5, "Confusing words")
        await route.fulfill(json={"success": True, "data": {"ideas": ideas}, "error": None, "meta": {}})

    await page.route("**/api/shorts-batch/ideas", fake_ideas)
    await page.goto(base_url + "/shorts-batch")
    await expect(page.locator("a.side-link[href='/shorts-batch']")).to_have_attribute("aria-current", "page")
    await page.locator("#batch-topic").fill("Confusing words")
    await page.locator("#batch-count").fill("5")
    await page.locator("#ideas-form button[type=submit]").click()
    await expect(page.locator("#batch-items li")).to_have_count(5)
    await page.locator("#batch-items li").nth(4).get_by_role("button", name="Remove").click()
    await expect(page.locator("#batch-items li")).to_have_count(4)
    await page.locator("#batch-items li").first.locator("input").first.fill("Bored or boring")
    await expect(page.locator("#batch-series")).to_have_value("Confusing words")
    await page.locator("#batch-cast-0").select_option(profile["id"])
    await page.locator("#batch-start").fill("2026-11-01")
    await page.locator("#create-form button[type=submit]").click()
    await expect(page.locator("#batch-notice")).to_contain_text("Created: 4 Shorts dated 2026-11-01 → 2026-11-04")
    tree = await result(await page.request.get(base_url + "/api/channel"))
    series = next(s for topic in tree["topics"] for s in topic["series"] if s["name"] == "Confusing words")
    assert series["explainer_style"] == "mistakes"
    assert [e["title"] for e in series["episodes"]][:2] == ["Bored or boring", "Mistake 2"]


async def test_the_news_tab_lists_stories_and_reads_the_chosen_articles(page, base_url):
    stories = [{"title": "Storm hits the coast", "link": "https://news.example/storm", "summary": "Schools closed.", "source": "World",
                "published": "2026-10-22T08:00:00+00:00"}]
    await page.route("**/api/news/today", lambda route: route.fulfill(json={"success": True, "data": {"stories": stories, "problems": []},
                                                                            "error": None, "meta": {}}))
    await page.route("**/api/news/articles", lambda route: route.fulfill(json={"success": True, "data": {"articles": [
        {"url": stories[0]["link"], "title": "Storm", "text": "A storm reached the coast on Monday.", "error": ""}]}, "error": None, "meta": {}}))
    await page.goto(base_url + "/shorts-batch")
    await page.locator("#tab-news").click()
    await expect(page.locator("#news-panel")).to_be_visible()
    await expect(page.locator("#feeds-list li")).to_have_count(2)  # the two default feeds
    errors = []
    page.on("pageerror", lambda error: errors.append(str(error)))
    await page.locator("#news-load").click()
    await page.wait_for_timeout(500)
    assert not errors, errors
    await expect(page.locator("#news-list li")).to_have_count(1)
    await page.locator("#news-list input[type=checkbox]").check()
    await page.locator("#news-use").click()
    await expect(page.locator("#batch-items li")).to_have_count(1)
    await expect(page.locator("#batch-items li")).to_contain_text("Article: 7 words")
