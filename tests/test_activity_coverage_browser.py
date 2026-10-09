"""Task 32.6c: Step 5 explains activity matches and sprite fallbacks before render."""

import pytest
from playwright.async_api import Browser

from tests.test_shot_library_browser import (  # noqa: F401
    _step5,
    browser_instance,
    live_server_url,
)
from tests.test_shot_review_browser import _project_with_shots


@pytest.mark.asyncio
async def test_step5_explains_character_generic_and_missing_activity_coverage(
    browser_instance: Browser, live_server_url: str,  # noqa: F811
):
    page = await browser_instance.new_page()
    project_id = await _project_with_shots(page, live_server_url)
    await page.route(
        f"**/api/projects/{project_id}/visuals/activity-coverage",
        lambda route: route.fulfill(json={
            "success": True,
            "data": {
                "matched": 2,
                "character": 1,
                "generic": 1,
                "missing": 1,
                "sprite_fallback": 1,
                "items": [
                    {"beat_id": "beat-left", "position": 0, "action": "turn left", "status": "character",
                     "fallback": None, "match": {"activity_id": "alex-left", "match_type": "character"}},
                    {"beat_id": "beat-straight", "position": 1, "action": "go straight", "status": "generic",
                     "fallback": None, "match": {"activity_id": "generic-straight", "match_type": "generic"}},
                    {"beat_id": "beat-cross", "position": 2, "action": "cross the street", "status": "missing",
                     "fallback": "sprites", "match": None},
                ],
            },
            "error": None,
            "meta": {},
        }),
    )

    await _step5(page, live_server_url, project_id)

    coverage = page.locator("#activity-coverage:not([hidden])")
    await coverage.wait_for()
    text = await coverage.text_content()
    assert "2 matched (1 character, 1 generic)" in text
    assert "Missing → sprite fallback (1): cross the street" in text
    await page.close()
