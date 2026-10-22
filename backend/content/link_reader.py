"""Phase 63 (ENH-045): read a news article from a public web link -- its title and main text -- so Step 1 can show it
to the owner before an English news Short is written from it (in the narrator's own words, never copied).

Only public http(s) addresses are fetched (no localhost or private network), at most 2 MB, with a short deadline and
three redirects, each checked again.
"""

from __future__ import annotations

import asyncio
import ipaddress
import re
import socket
from html.parser import HTMLParser
from urllib.parse import urljoin, urlsplit

import httpx

from backend.core.exceptions import ValidationError

MAX_BYTES = 2 * 1024 * 1024
TIMEOUT_SECONDS = 15
MAX_REDIRECTS = 3
TEXT_MAX = 12000
SKIP = {"script", "style", "noscript", "nav", "header", "footer", "aside", "form", "svg", "figure", "button"}
BLOCKS = {"p", "h1", "h2", "h3", "li", "blockquote"}


class _Extractor(HTMLParser):
    """The title and the paragraphs of a page (inside <article> when the page has one)."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.title = ""
        self.blocks: list[tuple[bool, str]] = []  # (inside an article, text)
        self._skip = 0
        self._article = 0
        self._in_title = False
        self._block: list[str] | None = None

    def handle_starttag(self, tag: str, attrs) -> None:
        if tag in SKIP:
            self._skip += 1
        elif tag == "article":
            self._article += 1
        elif tag == "title":
            self._in_title = True
        elif tag in BLOCKS and not self._skip:
            self._block = []
        elif tag == "br" and self._block is not None:
            self._block.append(" ")

    def handle_endtag(self, tag: str) -> None:
        if tag in SKIP and self._skip:
            self._skip -= 1
        elif tag == "article" and self._article:
            self._article -= 1
        elif tag == "title":
            self._in_title = False
        elif tag in BLOCKS and self._block is not None:
            text = re.sub(r"\s+", " ", "".join(self._block)).strip()
            if text:
                self.blocks.append((self._article > 0, text))
            self._block = None

    def handle_data(self, data: str) -> None:
        if self._in_title:
            self.title += data
        elif self._block is not None and not self._skip:
            self._block.append(data)


def extract(html: str) -> dict[str, str]:
    """{"title", "text"} of an HTML page: the article's paragraphs, else every paragraph with a few words."""
    parser = _Extractor()
    parser.feed(html)
    inside = [text for article, text in parser.blocks if article]
    blocks = inside or parser.blocks and [text for _article, text in parser.blocks]
    blocks = [text for text in (blocks or []) if len(text.split()) >= 4 or text.endswith((".", "?", "!"))]
    text = "\n\n".join(blocks)[:TEXT_MAX].strip()
    return {"title": re.sub(r"\s+", " ", parser.title).strip()[:300], "text": text}


def _check_host(url: str) -> None:
    parts = urlsplit(url)
    if parts.scheme not in ("http", "https") or not parts.hostname:
        raise ValidationError("Use a web link that starts with http:// or https://")
    try:
        addresses = {info[4][0] for info in socket.getaddrinfo(parts.hostname, parts.port or 443, proto=socket.IPPROTO_TCP)}
    except socket.gaierror as exc:
        raise ValidationError("That web address could not be found") from exc
    for address in addresses:
        ip = ipaddress.ip_address(address.split("%")[0])
        if ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_reserved or ip.is_multicast or ip.is_unspecified:
            raise ValidationError("Only public web pages can be read")


async def read_link(url: str, transport: httpx.AsyncBaseTransport | None = None) -> dict[str, str]:
    """Fetch a public page and return {"url", "title", "text"}; ValidationError with a plain reason otherwise."""
    url = url.strip()
    async with httpx.AsyncClient(transport=transport, timeout=TIMEOUT_SECONDS, follow_redirects=False,
                                 headers={"User-Agent": "Mozilla/5.0 (DailyBeyondEnglish link reader)"}) as client:
        for _hop in range(MAX_REDIRECTS + 1):
            if transport is None:  # the tests hand in a fake transport for a fake public page
                await asyncio.to_thread(_check_host, url)
            elif urlsplit(url).scheme not in ("http", "https"):
                raise ValidationError("Use a web link that starts with http:// or https://")
            try:
                async with client.stream("GET", url) as response:
                    if response.is_redirect and response.headers.get("location"):
                        url = urljoin(url, response.headers["location"])
                        continue
                    if response.status_code >= 400:
                        raise ValidationError(f"The page answered with an error ({response.status_code})")
                    kind = response.headers.get("content-type", "")
                    if "html" not in kind and "text" not in kind:
                        raise ValidationError("That link is not a web page with text")
                    body = b""
                    async for chunk in response.aiter_bytes():
                        body += chunk
                        if len(body) > MAX_BYTES:
                            raise ValidationError("That page is too large to read")
                    page = extract(body.decode(response.encoding or "utf-8", errors="replace"))
            except httpx.HTTPError as exc:
                raise ValidationError("The page could not be read right now; paste the article instead") from exc
            if len(page["text"].split()) < 40:
                raise ValidationError("No article text was found on that page; paste the article instead")
            return {"url": url, **page}
    raise ValidationError("That link redirects too many times")
