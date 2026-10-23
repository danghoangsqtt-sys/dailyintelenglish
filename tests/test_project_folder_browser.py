from __future__ import annotations

from typing import AsyncGenerator

import pytest
from playwright.async_api import Browser, Page, async_playwright

from tests.conftest import live_server


@pytest.fixture(scope="module")
def live_server_url(tmp_path_factory: pytest.TempPathFactory):
    with live_server(tmp_path_factory, "project-folder") as url:
        yield url


@pytest.fixture
async def browser_instance() -> AsyncGenerator[Browser, None]:
    async with async_playwright() as playwright:
        browser = await playwright.chromium.launch(headless=True)
        yield browser
        await browser.close()


async def _create_project(page: Page, base_url: str) -> str:
    response = await page.request.post(f"{base_url}/api/projects", data={
        "name": "Folder Browser Video",
        "topic": "Browser Folder Topic",
        "cefr_level": "B1",
        "duration_minutes": 2,
        "num_speakers": 2,
        "genre": "small_talk",
        "accent": "american",
        "speakers": [
            {"name": "Mia", "gender": "female", "accent": "american"},
            {"name": "Tom", "gender": "male", "accent": "american"},
        ],
    })
    assert response.status == 200
    return (await response.json())["data"]["id"]


@pytest.mark.asyncio
async def test_step1_new_project_panel_defaults_to_topic_hierarchy(browser_instance: Browser, live_server_url: str):
    page = await browser_instance.new_page()
    await page.goto(f"{live_server_url}/step1")
    layout = page.locator("#pf-layout")
    await layout.wait_for()

    assert await layout.input_value() == "topic_hierarchy"
    await page.locator(".pf-hint").wait_for()
    assert "Topic folder" in await page.locator(".pf-hint").text_content()
    await page.locator("[data-pf='path']").fill("D:\\Videos\\Daily Beyond English")
    assert "Topic / Series / video" in await page.locator("[data-pf='preview']").text_content()
    await page.close()


@pytest.mark.asyncio
async def test_step7_previews_and_saves_hierarchical_or_legacy_destination(
    browser_instance: Browser, live_server_url: str, tmp_path
):
    page = await browser_instance.new_page()
    project_id = await _create_project(page, live_server_url)
    await page.goto(f"{live_server_url}/step7?project_id={project_id}")
    await page.locator("#pf-layout").wait_for()
    assert await page.locator("#pf-layout").input_value() == "topic_hierarchy"

    root = tmp_path / "Topic Parent"
    await page.locator("[data-pf='path']").fill(str(root))
    preview = page.locator("[data-pf='preview']")
    await preview.wait_for()
    await page.wait_for_function(
        "() => document.querySelector('[data-pf=preview]').textContent.includes('Browser Folder Topic')"
    )
    assert str(root / "Browser Folder Topic" / "Folder Browser Video") in await preview.text_content()

    async with page.expect_response(
        lambda response: response.url.endswith(f"/api/projects/{project_id}/export")
        and response.request.method == "PUT"
    ) as response_info:
        await page.locator("[data-pf='save']").click()
    saved = await response_info.value
    settings = (await saved.json())["data"]["settings"]
    assert settings["layout_mode"] == "topic_hierarchy"
    assert settings["relative_dir"] == "Browser Folder Topic\\Folder Browser Video"

    await page.locator("#pf-layout").select_option("legacy")
    await page.wait_for_function(
        "() => document.querySelector('[data-pf=preview]').textContent.includes('Topic Parent')"
    )
    async with page.expect_response(
        lambda response: response.url.endswith(f"/api/projects/{project_id}/export")
        and response.request.method == "PUT"
    ) as response_info:
        await page.locator("[data-pf='save']").click()
    saved = await response_info.value
    settings = (await saved.json())["data"]["settings"]
    assert settings["layout_mode"] == "legacy"
    assert (await saved.json())["data"]["folder"] == str(root)
    await page.close()
