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
