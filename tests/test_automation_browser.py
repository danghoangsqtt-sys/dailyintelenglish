"""Phase 62 (ENH-044): the Automation page -- settings saved, the queue shown, Run now asked, the report drawn."""
from datetime import date

import pytest
from playwright.async_api import async_playwright, expect

from tests.conftest import live_server


@pytest.fixture(scope="module")
def base_url(tmp_path_factory):
    with live_server(tmp_path_factory, "automation-browser") as url:
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


async def test_the_page_saves_the_schedule_and_lists_the_due_episodes(page, base_url):
    topic = await result(await page.request.post(base_url + "/api/channel/topics", data={"name": "Daily Life"}))
    series = await result(await page.request.post(base_url + f"/api/channel/topics/{topic['id']}/series",
                                                  data={"name": "Mornings", "genre": "small_talk"}))
    episode = await result(await page.request.post(base_url + f"/api/channel/series/{series['id']}/episodes", data={"title": "Coffee"}))
    await result(await page.request.patch(base_url + f"/api/channel/episodes/{episode['id']}",
                                          data={"publish_date": date.today().isoformat()}))
    await page.goto(base_url + "/automation")
    await page.locator("#open-settings").click()  # Phase 67 A: the settings live in the slide-over
    await expect(page.locator("#auto-queue li")).to_have_count(1)
    await expect(page.locator("#auto-queue li")).to_contain_text("Mornings · Ep. 1: Coffee")
    await expect(page.locator("#auto-state-text")).to_have_text("Off")
    await expect(page.locator("#auto-startup")).to_be_disabled()  # the dev app cannot open itself with Windows
    await page.locator("#auto-enabled").check()
    await page.locator("#auto-start").fill("22:00")
    await page.locator("#auto-max").fill("3")
    await page.locator("#auto-form button[type=submit]").click()
    await expect(page.locator("#auto-notice")).to_have_text("Saved.")
    await expect(page.locator("#auto-state-text")).to_contain_text("On · 22:00")
    stored = (await result(await page.request.get(base_url + "/api/automation")))["settings"]
    assert (stored["enabled"], stored["window_start"], stored["max_per_night"]) == (True, "22:00", 3)
    await page.locator("#auto-enabled").uncheck()
    await page.locator("#auto-form button[type=submit]").click()
    await expect(page.locator("#auto-state-text")).to_have_text("Off")
    await expect(page.locator("a.side-link[href='/automation']")).to_have_attribute("aria-current", "page")


async def test_the_review_studio_shows_the_schedule_and_reviews_a_made_video(page, base_url):
    from datetime import timedelta

    topic = await result(await page.request.post(base_url + "/api/channel/topics", data={"name": "Studio"}))
    series = await result(await page.request.post(base_url + f"/api/channel/topics/{topic['id']}/series", data={"name": "Week"}))
    soon = await result(await page.request.post(base_url + f"/api/channel/series/{series['id']}/episodes", data={"title": "Tea time"}))
    later = await result(await page.request.post(base_url + f"/api/channel/series/{series['id']}/episodes", data={"title": "Bus stop"}))
    await result(await page.request.patch(base_url + f"/api/channel/episodes/{soon['id']}", data={"publish_date": date.today().isoformat()}))
    await result(await page.request.patch(base_url + f"/api/channel/episodes/{later['id']}",
                                          data={"publish_date": (date.today() + timedelta(days=3)).isoformat()}))
    board = await result(await page.request.get(base_url + "/api/automation/board"))
    today_items = {item["title"]: item for item in board["days"][0]["items"]}
    assert len(board["days"]) == 14 and "Tea time" in today_items and "Bus stop" not in today_items
    assert [item["title"] for item in board["days"][3]["items"]] == ["Bus stop"]
    assert today_items["Tea time"]["state"] == "planned" and board["videos"] == []  # no project yet
    await page.goto(base_url + "/automation")
    await expect(page.locator("#studio-kpis .kpi")).to_have_count(5)
    await expect(page.locator(".kpi[data-kpi='due'] b")).not_to_have_text("0")
    await expect(page.locator("#settings-drawer")).not_to_have_class("settings-drawer open")
    await page.locator("#open-settings").click()
    await expect(page.locator("#settings-drawer")).to_have_class("settings-drawer open")
    await page.keyboard.press("Escape")
    await expect(page.locator("#settings-backdrop")).to_be_hidden()
    await expect(page.locator(".strip-day").first).to_contain_text("Tea time")
    await expect(page.locator(".strip-day").nth(3)).to_contain_text("Bus stop")
    await page.locator(".strip-chip", has_text="Tea time").click()
    await expect(page.locator("#review-title")).to_have_text("Tea time")
    await expect(page.locator("#review-body")).to_contain_text("Not made yet")
    await page.locator("[data-review-tab='details']").click()
    await expect(page.locator("#review-body")).to_contain_text("Publishing date")
    # an episode marked approved (as the Approve button does) shows as approved on the board
    await result(await page.request.patch(base_url + f"/api/channel/episodes/{soon['id']}", data={"review_status": "approved"}))
    board = await result(await page.request.get(base_url + "/api/automation/board"))
    assert {item["title"]: item["state"] for item in board["days"][0]["items"]}["Tea time"] == "approved"
    bad = await page.request.patch(base_url + f"/api/channel/episodes/{soon['id']}", data={"review_status": "maybe"})
    assert bad.status == 422
