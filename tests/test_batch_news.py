"""Phase 66 (ENH-048): Shorts in batches (AI ideas -> a dated Channel series) and today's news (feeds + AI picks)."""
from datetime import date, datetime, timezone

import httpx
import pytest

from backend.ai.llm.contracts import GenerationResult
from backend.channel import batch_service
from backend.content import news_service
from backend.core.exceptions import ValidationError
from tests.test_visuals_project_api import client, data, locked_character  # noqa: F401

NOW = datetime(2026, 10, 22, 12, 0, tzinfo=timezone.utc)
RSS = b"""<?xml version="1.0"?><rss version="2.0"><channel><title>World</title>
<item><title>Storm hits the coast</title><link>https://news.example/storm</link><description>&lt;p&gt;Schools closed.&lt;/p&gt;</description>
<pubDate>Wed, 22 Oct 2026 08:00:00 GMT</pubDate></item>
<item><title>Old story</title><link>https://news.example/old</link><pubDate>Mon, 19 Oct 2026 08:00:00 GMT</pubDate></item>
<item><title>No link</title></item>
</channel></rss>"""
ATOM = b"""<?xml version="1.0" encoding="utf-8"?><feed xmlns="http://www.w3.org/2005/Atom"><title>Science</title>
<entry><title>New bike lanes open</title><link rel="alternate" href="https://news.example/bikes"/><summary>Twelve kilometres.</summary>
<updated>2026-10-22T10:30:00Z</updated></entry>
<entry><title>Storm hits the coast</title><link href="https://other.example/storm-copy"/><updated>2026-10-22T09:00:00Z</updated></entry>
</feed>"""


class Router:
    def __init__(self, text):
        self.text, self.prompts = text, []

    async def generate(self, request):
        self.prompts.append(request.prompt)
        return GenerationResult(text=self.text, provider="test", model="fixture", latency_ms=1, attempt=1, prompt_hash="a" * 64)


# ---------------------------------------------------------------- feeds

def test_rss_and_atom_items_are_read_and_unsafe_documents_refused():
    rss = news_service.parse_feed(RSS, "World")
    assert [item["title"] for item in rss] == ["Storm hits the coast", "Old story"]
    assert rss[0]["summary"] == "Schools closed." and rss[0]["published"] == "2026-10-22T08:00:00+00:00"
    atom = news_service.parse_feed(ATOM, "Science")
    assert atom[0] == {"title": "New bike lanes open", "link": "https://news.example/bikes", "summary": "Twelve kilometres.",
                       "source": "Science", "published": "2026-10-22T10:30:00+00:00"}
    with pytest.raises(ValidationError, match="document type"):
        news_service.parse_feed(b'<?xml version="1.0"?><!DOCTYPE x [<!ENTITY a "b">]><rss/>', "Bad")
    with pytest.raises(ValidationError, match="not an RSS"):
        news_service.parse_feed(b"<html><p>hello", "Page")


async def test_today_keeps_fresh_unique_stories_newest_first_and_lists_feed_problems():
    def handler(request):
        if request.url.path == "/world.rss":
            return httpx.Response(200, content=RSS)
        if request.url.path == "/science.atom":
            return httpx.Response(200, content=ATOM)
        return httpx.Response(500)

    feeds = [{"url": "https://feeds.example/world.rss", "name": "World", "enabled": True},
             {"url": "https://feeds.example/science.atom", "name": "Science", "enabled": True},
             {"url": "https://feeds.example/broken", "name": "Broken", "enabled": True},
             {"url": "https://feeds.example/off", "name": "Off", "enabled": False}]
    result = await news_service.today(feeds, now=NOW, transport=httpx.MockTransport(handler))
    assert [story["title"] for story in result["stories"]] == ["New bike lanes open", "Storm hits the coast"]
    assert result["problems"] == [{"feed": "Broken", "error": "The feed answered with an error (500)"}]


async def test_the_ai_picks_only_real_headlines():
    stories = [{"title": f"Story {i}", "summary": "", "source": "World", "link": f"https://n.example/{i}", "published": None} for i in range(3)]
    router = Router('{"picks": [{"index": 2, "hook": "Big news!", "why": "clear"}, {"index": 9, "hook": "x"}, {"index": 2, "hook": "again"}]}')
    picks = await news_service.picks(stories, "B1", 5, router=router)
    assert [(pick["title"], pick["hook"]) for pick in picks] == [("Story 2", "Big news!")]
    assert "[0] Story 0" in router.prompts[0] and "CEFR B1" in router.prompts[0]
    assert await news_service.picks([], "B1", 5, router=router) == []


def test_the_feed_list_is_saved_and_checked(client):  # noqa: F811
    feeds = data(client.get("/api/news/feeds"))["feeds"]
    assert [feed["name"] for feed in feeds] == ["BBC News — World", "NPR News"]
    saved = data(client.put("/api/news/feeds", json=[{"url": "https://feeds.example/a.rss", "name": "A", "enabled": False}]))["feeds"]
    assert [(feed["name"], feed["enabled"]) for feed in saved] == [("A", False)]
    assert client.put("/api/news/feeds", json=[{"url": "ftp://feeds.example/a", "name": "A"}]).status_code == 422


# ---------------------------------------------------------------- batches

async def test_ideas_are_distinct_and_renamed_fields_are_accepted(db):
    router = Router('{"items": [{"name": "Bored or boring", "description": "-ed vs -ing"}, {"headline": "Bored or boring"},'
                    ' {"title": "Fun or funny", "brief": "two adjectives"}, "Lend or borrow"]}')
    ideas = await batch_service.propose_ideas(db, batch_service.IdeasRequest(topic="Confusing words", template="mistakes", count=5), router=router)
    assert [idea["title"] for idea in ideas] == ["Bored or boring", "Fun or funny", "Lend or borrow"]
    assert "Don't say / Say" in router.prompts[0] and "exactly 5 items" in router.prompts[0]


def test_a_batch_becomes_a_dated_series_and_its_articles_reach_the_projects(client):  # noqa: F811
    narrator = locked_character("Anchor", "red")
    body = {"topic_name": "Shorts", "series_name": "English News Week", "template": "news", "cast": [narrator], "cefr_level": "B1",
            "start_date": "2026-10-23", "every_days": 2, "make_projects": True,
            "items": [{"title": "Storm on the coast", "brief": "Schools close", "source_text": "A storm reached the coast. " * 10},
                      {"title": "New bike lanes", "brief": "Twelve kilometres"}]}
    result = data(client.post("/api/shorts-batch/create", json=body))
    assert (result["episodes"], result["projects"], result["first_date"], result["last_date"]) == (2, 2, "2026-10-23", "2026-10-25")
    tree = data(client.get("/api/channel"))
    series = next(s for topic in tree["topics"] for s in topic["series"] if s["id"] == result["series_id"])
    assert series["explainer_style"] == "news" and [e["publish_date"] for e in series["episodes"]] == ["2026-10-23", "2026-10-25"]
    first = data(client.get(f"/api/projects/{series['episodes'][0]['project_id']}"))
    second = data(client.get(f"/api/projects/{series['episodes'][1]['project_id']}"))
    assert (first["explainer_style"], first["source_kind"]) == ("news", "article") and first["source_text"].startswith("A storm")
    assert second["source_kind"] == ""
    again = data(client.post("/api/shorts-batch/create", json={**body, "series_name": "Second", "make_projects": False}))
    assert again["topic_id"] == result["topic_id"] and again["projects"] == 0  # the same playlist is reused
    wrong = client.post("/api/shorts-batch/create", json={**body, "template": "chat"})
    assert wrong.status_code == 422 and "two characters" in wrong.json()["error"]
    assert batch_service.publishing_dates(date(2026, 10, 30), 3, 3) == [date(2026, 10, 30), date(2026, 11, 2), date(2026, 11, 5)]
