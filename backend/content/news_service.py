"""Phase 66 (ENH-048): today's news for news Shorts -- the owner's public RSS/Atom feeds read by the app (public
addresses only, size and time limits, a 30-minute cache), and the AI's picks with a hook for each story.

No AI provider of the app can browse the web reliably, so the app reads the feeds itself; the AI only chooses among the
real headlines and never adds facts. Without AI the headlines are still listed.
"""

from __future__ import annotations

import asyncio
import html
import re
import time
import uuid
import xml.etree.ElementTree as ElementTree
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime
from typing import Any

import aiosqlite
import httpx
from jinja2 import Environment, FileSystemLoader, StrictUndefined
from pydantic import BaseModel, Field, TypeAdapter

from backend.ai.llm.contracts import GenerationRequest
from backend.ai.llm.router import AIRouter, build_ai_router_from_settings
from backend.ai.llm.validation import parse_and_validate
from backend.content.link_reader import _check_host
from backend.core import paths
from backend.core.config import settings
from backend.core.exceptions import ProviderError, SchemaValidationError, ValidationError

MAX_BYTES = 2 * 1024 * 1024
TIMEOUT_SECONDS = 15
CACHE_SECONDS = 30 * 60
MAX_AGE_HOURS = 36
_cache: dict[str, tuple[float, list[dict]]] = {}
_env = Environment(loader=FileSystemLoader(str(paths.PROMPTS_DIR / "shorts")), undefined=StrictUndefined,
                   trim_blocks=True, lstrip_blocks=True)


def _text(element: ElementTree.Element | None) -> str:
    if element is None:
        return ""
    raw = "".join(element.itertext())
    return " ".join(html.unescape(re.sub(r"<[^>]+>", " ", raw)).split())


def _local(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def _date(value: str) -> datetime | None:
    value = value.strip()
    if not value:
        return None
    try:
        moment = parsedate_to_datetime(value)
    except (TypeError, ValueError):
        try:
            moment = datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError:
            return None
    return moment if moment.tzinfo else moment.replace(tzinfo=timezone.utc)


def parse_feed(content: bytes, source: str) -> list[dict[str, Any]]:
    """RSS 2.0 items or Atom entries: title, link, summary, published (ISO, UTC) and the feed's name. A document type
    declaration is refused (no entity expansion from the internet)."""
    head = content[:4096].lower()
    if b"<!doctype" in head or b"<!entity" in content.lower():
        raise ValidationError("That feed declares a document type; it is not read")
    try:
        root = ElementTree.fromstring(content)
    except ElementTree.ParseError as exc:
        raise ValidationError("That address is not an RSS or Atom feed") from exc
    items = []
    for node in root.iter():
        kind = _local(node.tag)
        if kind not in ("item", "entry"):
            continue
        fields = {_local(child.tag): child for child in node}
        link = ""
        if "link" in fields:
            link = fields["link"].get("href") or _text(fields["link"])
        for child in node:
            if _local(child.tag) == "link" and child.get("rel") in (None, "alternate") and child.get("href"):
                link = child.get("href")
                break
        # an XML element without children is falsy: pick the first present field explicitly
        first = lambda *names: next((fields[name] for name in names if fields.get(name) is not None), None)  # noqa: E731
        published = _date(_text(first("pubDate", "published", "updated", "date")))
        title = _text(fields.get("title"))
        if not title or not link.startswith(("http://", "https://")):
            continue
        summary = _text(first("description", "summary", "content"))
        items.append({"title": title[:300], "link": link[:2000], "summary": summary[:400], "source": source,
                      "published": published.astimezone(timezone.utc).isoformat() if published else None})
    return items


async def _fetch(url: str, transport: httpx.AsyncBaseTransport | None) -> bytes:
    if transport is None:
        await asyncio.to_thread(_check_host, url)
    async with httpx.AsyncClient(transport=transport, timeout=TIMEOUT_SECONDS, follow_redirects=True,
                                 headers={"User-Agent": "Mozilla/5.0 (DailyBeyondEnglish news reader)"}) as client:
        async with client.stream("GET", url) as response:
            if response.status_code >= 400:
                raise ValidationError(f"The feed answered with an error ({response.status_code})")
            if transport is None:
                await asyncio.to_thread(_check_host, str(response.url))  # where the redirects ended
            body = b""
            async for chunk in response.aiter_bytes():
                body += chunk
                if len(body) > MAX_BYTES:
                    raise ValidationError("That feed is too large")
            return body


async def today(feeds: list[dict], now: datetime | None = None, transport: httpx.AsyncBaseTransport | None = None) -> dict:
    """The stories of the enabled feeds from the last 36 hours, newest first, without repeats; feed problems are listed
    beside them instead of failing the whole list."""
    now = now or datetime.now(timezone.utc)
    stories, problems = [], []
    for feed in [item for item in feeds if item["enabled"]]:
        cached = _cache.get(feed["url"])
        try:
            if cached and time.monotonic() - cached[0] < CACHE_SECONDS and transport is None:
                items = cached[1]
            else:
                items = parse_feed(await _fetch(feed["url"], transport), feed["name"])
                _cache[feed["url"]] = (time.monotonic(), items)
            stories += items
        except (ValidationError, httpx.HTTPError) as exc:
            problems.append({"feed": feed["name"], "error": str(exc) or type(exc).__name__})
    cutoff = now - timedelta(hours=MAX_AGE_HOURS)
    fresh, seen = [], set()
    for story in stories:
        moment = datetime.fromisoformat(story["published"]) if story["published"] else None
        key = re.sub(r"\W+", " ", story["title"].lower()).strip()
        if (moment and moment < cutoff) or key in seen:
            continue
        seen.add(key)
        fresh.append(story)
    fresh.sort(key=lambda story: story["published"] or "", reverse=True)
    return {"stories": fresh[:80], "problems": problems}


class Pick(BaseModel):
    index: int = Field(ge=0)
    hook: str = Field(default="", max_length=200)
    why: str = Field(default="", max_length=200)


class Picks(BaseModel):
    picks: list[Pick] = Field(default_factory=list, max_length=20)


_PICKS = TypeAdapter(Picks)


async def picks(stories: list[dict], cefr_level: str, count: int, router: AIRouter | None = None) -> list[dict]:
    """The AI's best stories for learners at this level, each with a hook; indexes outside the list are dropped."""
    if not stories:
        return []
    shown = stories[:40]
    prompt = await asyncio.to_thread(lambda: _env.get_template("news_picks.txt").render(items=shown, cefr_level=cefr_level, count=count))
    router = router or build_ai_router_from_settings()
    try:
        result = await router.generate(GenerationRequest(prompt=prompt, json_schema=Picks.model_json_schema(),
                                                         deadline_seconds=settings.AI_REQUEST_DEADLINE_SECONDS,
                                                         purpose="news_picks"))
        chosen = parse_and_validate(result.text, _PICKS).picks
    except ProviderError as exc:
        raise ValidationError(f"The AI could not choose stories right now ({type(exc).__name__}); the headlines are below") from exc
    except SchemaValidationError as exc:
        raise ValidationError("The AI's choice was not usable; try again, or choose from the headlines") from exc
    result_list, used = [], set()
    for pick in chosen:
        if pick.index < len(shown) and pick.index not in used:
            used.add(pick.index)
            result_list.append({**shown[pick.index], "hook": pick.hook, "why": pick.why})
    return result_list[:count]


# ---------------------------------------------------------------- the owner's feeds

async def list_feeds(db: aiosqlite.Connection) -> list[dict]:
    cursor = await db.execute("SELECT id, url, name, enabled FROM news_feeds ORDER BY position, name")
    return [{**dict(row), "enabled": bool(row["enabled"])} for row in await cursor.fetchall()]


async def save_feeds(db: aiosqlite.Connection, feeds: list[dict]) -> list[dict]:
    """Replace the feed list (at most 12; http(s) addresses)."""
    if len(feeds) > 12:
        raise ValidationError("Keep at most 12 news feeds")
    for feed in feeds:
        if not str(feed.get("url", "")).startswith(("http://", "https://")):
            raise ValidationError("A feed address starts with http:// or https://")
    await db.execute("DELETE FROM news_feeds")
    for position, feed in enumerate(feeds):
        await db.execute("INSERT INTO news_feeds (id, url, name, enabled, position) VALUES (?, ?, ?, ?, ?)",
                         (feed.get("id") or uuid.uuid4().hex, feed["url"].strip(), (feed.get("name") or feed["url"]).strip()[:80],
                          int(bool(feed.get("enabled", True))), position))
    return await list_feeds(db)


def clear_cache() -> None:
    _cache.clear()

