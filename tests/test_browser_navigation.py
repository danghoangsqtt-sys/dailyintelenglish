"""BUG-040: only the observed local Chromium infrastructure failure may be retried."""

import pytest
from playwright.async_api import Error as PlaywrightError, TimeoutError as PlaywrightTimeoutError

from tests.browser_navigation import local_navigation


async def test_one_local_socket_buffer_failure_recovers_without_changing_load_options(caplog):
    calls, marker = [], object()

    async def goto(page, url, **options):
        calls.append((page, url, options))
        if len(calls) == 1:
            raise PlaywrightError("Page.goto: net::ERR_NO_BUFFER_SPACE")
        return marker

    assert await local_navigation(goto, marker, "http://127.0.0.1:8000/step3", wait_until="load", timeout=30000) is marker
    assert len(calls) == 2 and calls[0] == calls[1]
    assert "ERR_NO_BUFFER_SPACE" in caplog.text


@pytest.mark.parametrize("url,error", [
    ("https://example.com", PlaywrightError("net::ERR_NO_BUFFER_SPACE")),
    ("http://localhost:8000/", PlaywrightTimeoutError("Page.goto: timeout waiting for load")),
    ("http://localhost:8000/", PlaywrightError("net::ERR_CONNECTION_REFUSED")),
    ("http://localhost:8000/", AssertionError("application assertion")),
])
async def test_other_errors_are_not_retried(url, error):
    calls = []

    async def goto(*args, **kwargs):
        calls.append(args)
        raise error

    with pytest.raises(type(error)):
        await local_navigation(goto, None, url)
    assert len(calls) == 1


async def test_persistent_socket_buffer_failure_is_reported_after_two_attempts():
    calls = []

    async def goto(*args, **kwargs):
        calls.append(args)
        raise PlaywrightError("net::ERR_NO_BUFFER_SPACE")

    with pytest.raises(PlaywrightError, match="ERR_NO_BUFFER_SPACE"):
        await local_navigation(goto, None, "http://localhost:8000/")
    assert len(calls) == 2
