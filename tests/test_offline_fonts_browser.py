"""BUG-040: local pages must reach load without a remote font stylesheet."""

import asyncio
from urllib.parse import urlparse

import pytest
from playwright.async_api import async_playwright

from tests.conftest import live_server


@pytest.fixture(scope="module")
def live_server_url(tmp_path_factory):
    with live_server(tmp_path_factory, "offline-fonts") as url:
        yield url


@pytest.mark.asyncio
async def test_pages_load_with_remote_stylesheets_unavailable(live_server_url):
    """A stalled CDN must not block load or make the chosen body font unavailable."""
    async with async_playwright() as playwright:
        browser = await playwright.chromium.launch(headless=True)
        try:
            context = await browser.new_context()
            external = []
            release = asyncio.Event()

            async def local_only(route):
                if urlparse(route.request.url).hostname in {"127.0.0.1", "localhost"}:
                    await route.continue_()
                else:
                    external.append(route.request.url)
                    # Model a reachable but stalled font CDN, rather than a fast DNS error.
                    await release.wait()
                    await route.abort()

            await context.route("**/*", local_only)
            page = await context.new_page()
            try:
                for path in ["/", "/music", "/settings", "/shots", "/characters", "/channel",
                             *[f"/step{number}" for number in range(1, 8)]]:
                    response = await page.goto(f"{live_server_url}{path}", wait_until="load", timeout=5000)
                    assert response.status == 200
                    assert await page.evaluate("""async () => {
                        const loaded = await document.fonts.load('400 16px Inter');
                        return loaded.length === 1 && loaded[0].status === 'loaded';
                    }""")
                assert external == [], external
            finally:
                release.set()
                await context.close()
        finally:
            await browser.close()
