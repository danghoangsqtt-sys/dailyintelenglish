"""Bounded recovery for Windows Chromium socket-buffer allocation failures in local UI tests."""

import asyncio
import logging
from typing import Any, Awaitable, Callable
from urllib.parse import urlparse

from playwright.async_api import Error as PlaywrightError

logger = logging.getLogger(__name__)


async def local_navigation(goto: Callable[..., Awaitable[Any]], page: Any, url: str, **options: Any) -> Any:
    """Retry one failed local GET navigation on ERR_NO_BUFFER_SPACE, preserving normal load checks."""
    try:
        return await goto(page, url, **options)
    except PlaywrightError as exc:
        if urlparse(url).hostname not in {"localhost", "127.0.0.1", "::1"} or "net::ERR_NO_BUFFER_SPACE" not in str(exc):
            raise
        logger.warning("local_browser_navigation_retry url=%s reason=ERR_NO_BUFFER_SPACE attempts=2", url)
        await asyncio.sleep(0.25)  # let Windows reclaim transient socket buffers; a second failure is reported
        return await goto(page, url, **options)
