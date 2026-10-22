"""Phase 71 (ENH-053): the Full and Lite editions and the local AI picture features."""

from __future__ import annotations

import json
import sys

import pytest
from fastapi.testclient import TestClient

from backend.core import edition
from backend.core.config import settings
from backend.main import app

STRONG = {"gpu_total_mb": 12288, "gpu_ok": True, "image_env": True}
SMALL = {"gpu_total_mb": 4096, "gpu_ok": False, "image_env": False}
NONE = {"gpu_total_mb": None, "gpu_ok": False, "image_env": False}


@pytest.mark.parametrize("name, choice, found, shown, reason", [
    ("full", "auto", STRONG, True, "can draw"),
    ("full", "auto", SMALL, False, "4 GB (8 GB needed)"),
    ("full", "auto", NONE, False, "no NVIDIA GPU"),
    ("full", "auto", {**STRONG, "image_env": False}, False, ".venv-image"),
    ("lite", "auto", STRONG, False, "Lite edition"),
    ("lite", "on", SMALL, True, "setting"),
    ("full", "off", STRONG, False, "setting"),
])
def test_the_decision(name, choice, found, shown, reason):
    result = edition.decide(name, choice, found)
    assert result[0] is shown and reason in result[1]


def test_a_packaged_app_reads_its_edition_from_build_info(tmp_path, monkeypatch):
    (tmp_path / "build-info.json").write_text(json.dumps({"version": "1.6.0", "edition": "lite"}), encoding="utf-8")
    monkeypatch.setattr(sys, "frozen", True, raising=False)
    monkeypatch.setattr(sys, "executable", str(tmp_path / "DailyIntelEnglishStudio.exe"))
    assert edition.edition() == "lite"
    (tmp_path / "build-info.json").write_text(json.dumps({"version": "1.5.0"}), encoding="utf-8")
    monkeypatch.setattr(settings, "EDITION", "full")
    assert edition.edition() == "full"  # an older build without the field is Full


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "DATA_DIR", tmp_path)
    monkeypatch.setattr(settings, "EDITION", "lite")

    async def small():
        return dict(SMALL)

    monkeypatch.setattr(edition, "detect", small)
    with TestClient(app) as test_client:
        yield test_client


def test_the_api_reports_and_saves_the_switch(client):
    data = client.get("/api/system/capabilities").json()["data"]
    assert data == {"edition": "lite", "local_image_ai": False, "choice": "auto", "reason": "the Lite edition hides them", **SMALL}
    data = client.put("/api/system/capabilities", json={"local_image_ai": "on"}).json()["data"]
    assert data["local_image_ai"] is True and data["choice"] == "on"
    assert client.get("/api/system/capabilities").json()["data"]["choice"] == "on"
    assert client.put("/api/system/capabilities", json={"local_image_ai": "maybe"}).status_code == 422


# ---------------------------------------------------------------- browser: the Lite edition hides the four features

@pytest.fixture(scope="module")
def lite_server_url(tmp_path_factory):
    from tests.conftest import live_server

    original = settings.EDITION
    settings.EDITION = "lite"
    try:
        with live_server(tmp_path_factory, "lite_edition_browser") as url:
            yield url
    finally:
        settings.EDITION = original


@pytest.mark.asyncio
async def test_lite_hides_the_local_picture_features_and_the_switch_brings_them_back(lite_server_url):
    from playwright.async_api import async_playwright

    async with async_playwright() as playwright:
        browser = await playwright.chromium.launch()
        page = await browser.new_page()
        await page.goto(f"{lite_server_url}/settings")
        await page.wait_for_function("document.documentElement.dataset.localImageAi === 'off'")
        assert "Lite edition" in await page.locator("#local-image-ai-status").text_content()
        assert await page.locator("input[name=local-image-ai][value=auto]").is_checked()
        await page.goto(f"{lite_server_url}/step6?project_id=none")
        await page.wait_for_function("document.documentElement.dataset.localImageAi === 'off'")
        assert not await page.locator("#topic-picture-row").is_visible() and not await page.locator("#ai-scene-panel").is_visible()
        await page.goto(f"{lite_server_url}/step5?project_id=none")
        await page.wait_for_function("document.documentElement.dataset.localImageAi === 'off'")
        assert await page.locator("#draw-illustrations-btn").count() == 1
        assert not await page.locator("#draw-illustrations-btn").is_visible()
        # the switch: Show
        await page.goto(f"{lite_server_url}/settings")
        await page.locator("label", has=page.locator("input[name=local-image-ai][value=on]")).click()
        await page.wait_for_function("document.documentElement.dataset.localImageAi === 'on'")
        assert "Shown" in await page.locator("#local-image-ai-status").text_content()
        await page.goto(f"{lite_server_url}/step6?project_id=none")
        await page.wait_for_function("document.documentElement.dataset.localImageAi === 'on'")
        assert await page.locator("#topic-picture-row").count() == 1
        await browser.close()
