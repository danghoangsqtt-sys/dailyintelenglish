"""Task 29.7: the Shot Library page (review once), and Step 5's "Add to library", "from library" and coverage line."""

from typing import AsyncGenerator, Generator

import pytest
from playwright.async_api import Browser, async_playwright

from app.api import visuals as visuals_api
from app.core.config import settings
from tests.conftest import live_server
from tests.test_shot_review_browser import _project_with_shots


@pytest.fixture(scope="module")
def live_server_url(tmp_path_factory: pytest.TempPathFactory) -> Generator[str, None, None]:
    pretend_image_python = tmp_path_factory.mktemp("shot-library-venv") / "python.exe"
    pretend_image_python.touch()
    with pytest.MonkeyPatch.context() as patch:
        patch.setattr(settings, "IMAGE_ENGINE", "fake")
        patch.setattr(settings, "AI_VISUALS_ENABLED", True)
        patch.setattr(settings, "VISUALS_COLOUR_RETRIES", 0)
        patch.setattr(visuals_api, "IMAGE_PYTHON", pretend_image_python)
        with live_server(tmp_path_factory, "shot-library-browser") as url:
            yield url


@pytest.fixture
async def browser_instance() -> AsyncGenerator[Browser, None]:
    async with async_playwright() as playwright:
        browser = await playwright.chromium.launch(headless=True)
        yield browser
        await browser.close()


async def _step5(page, base: str, project_id: str) -> None:
    await page.route(
        f"**/api/projects/{project_id}/audio/status",
        lambda route: route.fulfill(json={"success": True, "data": {"status": "complete", "timestamps": []}}),
    )
    await page.goto(f"{base}/step5?project_id={project_id}")
    await page.locator("#visual-shot-grid .visual-shot-card").first.wait_for()


@pytest.mark.asyncio
async def test_add_to_library_review_it_once_and_the_next_run_is_served_from_the_library(
    browser_instance: Browser, live_server_url: str,
):
    page = await browser_instance.new_page()
    project_id = await _project_with_shots(page, live_server_url)
    await _step5(page, live_server_url, project_id)
    cards = page.locator("#visual-shot-grid .visual-shot-card")
    total = await cards.count()
    assert total >= 2
    assert await page.locator("#library-coverage").is_hidden()  # nothing approved yet: no line
    for index in range(total):  # keep every finished picture
        await cards.nth(index).locator("[data-action='add-to-library']").click()
        await cards.nth(index).get_by_text("In the library").wait_for()

    await page.goto(f"{live_server_url}/shots")
    grid = page.locator("#shot-grid .shot-card")
    await grid.first.wait_for()
    assert await grid.count() == total
    assert "needs review" in await page.locator("#shot-count").text_content() or "waiting for review" in await page.locator("#shot-count").text_content()
    assert await page.locator("#shot-grid .shot-card.is-pending").count() == total
    await grid.first.locator("[data-action='reject']").click()
    await page.locator("#shot-grid .shot-card.is-rejected").wait_for()
    page.once("dialog", lambda dialog: dialog.accept())
    await page.locator("#approve-all-btn").click()
    await page.locator("#shot-message.message-success").wait_for()
    assert await page.locator("#shot-grid .shot-card.is-approved").count() == total - 1
    assert await page.locator("#shot-grid .shot-card.is-rejected").count() == 1
    await page.select_option("#filter-state", "approved")
    await page.wait_for_function(f"document.querySelectorAll('#shot-grid .shot-card').length === {total - 1}")

    await _step5(page, live_server_url, project_id)  # coverage: the approved ones will be reused
    await page.locator("#library-coverage:not([hidden])").wait_for()
    text = await page.locator("#library-coverage").text_content()
    assert f"{total - 1} of {total}" in text and "will be drawn" in text
    await page.get_by_role("button", name="Generate shots").click()
    await page.locator("#visual-shot-grid .visual-badge").first.wait_for()
    assert await page.locator("#visual-shot-grid .visual-badge").count() == total - 1  # "from library"
    assert await page.locator("#visual-shot-grid [data-action='add-to-library']").count() == 1  # the redrawn one only
    await page.close()


@pytest.mark.asyncio
async def test_the_empty_library_says_what_to_do_and_the_sidebar_links_to_it(browser_instance: Browser, live_server_url: str):
    page = await browser_instance.new_page()
    await page.goto(f"{live_server_url}/shots")
    await page.wait_for_selector("#shot-count, #shot-empty")
    assert "Add to library" in await page.locator("#shot-empty").text_content()  # the hint exists (shown when empty)
    link = page.locator("#app-sidebar a[href='/shots']")
    assert await link.get_attribute("aria-current") == "page"
    await page.goto(f"{live_server_url}/music")
    link = page.locator("#app-sidebar a[href='/shots']")
    assert await link.count() == 1 and await link.get_attribute("aria-current") is None
    await link.click()
    await page.wait_for_url("**/shots")
    await page.close()


@pytest.mark.asyncio
async def test_pictures_dropped_in_the_inbox_folder_are_imported_from_the_page(browser_instance: Browser, live_server_url: str):
    import sqlite3

    from PIL import Image

    from app.services.visuals import shot_library_service as lib
    from tests.test_visuals_project_api import locked_character

    lina, alex = locked_character("Lina", "white"), locked_character("Alex", "navy")
    with sqlite3.connect(settings.db_path) as connection:
        connection.execute("UPDATE characters SET gender = 'male' WHERE id = ?", (alex,))
        connection.execute("UPDATE characters SET created_at = '2026-01-01' WHERE id = ?", (lina,))
    lib.inbox_dir().mkdir(parents=True, exist_ok=True)
    Image.new("RGB", (1344, 768), (10, 120, 10)).save(lib.inbox_dir() / "park__duo-wide-lina-alex.png")
    Image.new("RGB", (1344, 768), (10, 10, 120)).save(lib.inbox_dir() / "nowhere__duo-wide.png")
    page = await browser_instance.new_page()
    await page.goto(f"{live_server_url}/shots")
    await page.locator("#import-card summary").click()
    await page.wait_for_function("document.getElementById('inbox-count').textContent.includes('2 pictures')")
    assert (await page.locator("#inbox-folder").text_content()).endswith("shots_inbox")
    before = await page.locator("#shot-grid .shot-card").count()
    await page.click("#import-btn")
    await page.locator("#import-result li.is-error").wait_for()
    results = await page.locator("#import-result li").all_text_contents()
    assert results[0].startswith("1 imported, 1 left") and "unknown scene" in results[1]
    await page.wait_for_function(f"document.querySelectorAll('#shot-grid .shot-card').length === {before + 1}")
    assert "1 picture waiting" in await page.locator("#inbox-count").text_content()
    await page.close()


@pytest.mark.asyncio
async def test_step5_requires_explicit_profile_assignment_even_when_names_match(browser_instance: Browser, live_server_url: str):
    import sqlite3

    from tests.test_visuals_project_api import PROJECT, locked_character

    lina_id = locked_character("Olga", "white")
    alex_id = locked_character("Ivan", "navy")
    with sqlite3.connect(settings.db_path) as connection:
        connection.execute("UPDATE characters SET gender = 'male' WHERE id = ?", (alex_id,))
    page = await browser_instance.new_page()
    body = {**PROJECT, "speakers": [{"name": "Ivan", "gender": "male", "accent": "american"},
                                    {"name": "Olga", "gender": "female", "accent": "american"}]}
    created = await page.request.post(f"{live_server_url}/api/projects", data=body)
    project_id = (await created.json())["data"]["id"]
    await page.route(
        f"**/api/projects/{project_id}/audio/status",
        lambda route: route.fulfill(json={"success": True, "data": {"status": "complete", "timestamps": []}}),
    )
    await page.add_init_script("localStorage.setItem('die-visual-mode', 'podcast_black')")
    await page.goto(f"{live_server_url}/step5?project_id={project_id}")
    await page.locator(f'[data-character-id="{alex_id}"]').wait_for()
    visuals_response = await page.request.get(f"{live_server_url}/api/projects/{project_id}/visuals")
    assert (await visuals_response.json())["data"]["cast"] == []

    await page.locator(f'[data-character-id="{alex_id}"]').click()
    await page.locator('[data-action="choose-profile"]').click()
    await page.locator('[data-cast-speaker-index="1"]').click()
    await page.locator(f'[data-character-id="{lina_id}"]').click()
    await page.locator('[data-action="choose-profile"]').click()

    cast_response = await page.request.get(f"{live_server_url}/api/projects/{project_id}/visuals")
    cast = (await cast_response.json())["data"]["cast"]
    assert [member["character_id"] for member in cast] == [alex_id, lina_id]
    await page.close()


@pytest.mark.asyncio
async def test_a_new_project_starts_with_alex_and_lina_as_speakers(browser_instance: Browser, live_server_url: str):
    page = await browser_instance.new_page()
    await page.goto(f"{live_server_url}/step1")
    await page.wait_for_selector("#speaker-name-0")
    assert await page.locator("#speaker-name-0").input_value() == "Alex"
    assert await page.locator("#speaker-gender-0").input_value() == "male"
    assert await page.locator("#speaker-name-1").input_value() == "Lina"
    assert await page.locator("#speaker-gender-1").input_value() == "female"
    await page.close()


@pytest.mark.asyncio
async def test_sprite_pictures_in_the_inbox_become_a_set_from_the_page(browser_instance: Browser, live_server_url: str):
    """Phase 32 (Task 32.1): the Talking sprites card lists the sets, imports the inbox and shows what was refused."""
    import sqlite3

    from app.services.visuals import sprite_service
    from tests.test_sprite_service import _figure
    from tests.test_visuals_project_api import locked_character

    with sqlite3.connect(settings.db_path) as connection:
        known = {row[0].lower() for row in connection.execute("SELECT name FROM characters")}
    if "lina" not in known:
        locked_character("Lina", "white")
    for name in ("calm__closed", "calm__open", "smile__open"):
        _figure(sprite_service.inbox_dir() / f"lina__{name}.png")
    _figure(sprite_service.inbox_dir() / "lina__laugh__open.png", torso_dx=40)
    with pytest.MonkeyPatch.context() as patch:
        patch.setattr(sprite_service, "detected_face_ellipse", lambda _path: None)  # no face model in a test
        page = await browser_instance.new_page()
        await page.goto(f"{live_server_url}/shots")
        await page.locator("#import-card summary").click()
        await page.wait_for_function("document.getElementById('sprite-count').textContent.includes('4 sprite pictures')")
        assert (await page.locator("#sprite-folder").text_content()).endswith("sprites_inbox")
        assert "no sprites yet" in await page.locator("#sprite-sets li[data-character='Lina']").text_content()
        await page.click("#sprite-import-btn")
        await page.locator("#sprite-result li.is-error").wait_for()
        results = await page.locator("#sprite-result li").all_text_contents()
        assert results[0].startswith("1 sprite set imported: Lina (3 pictures)") and "torso moved" in results[1]
        await page.wait_for_function(
            "document.querySelector(\"#sprite-sets li[data-character='Lina']\").textContent.includes('3 of 15 faces')")
        await page.close()
