"""Phase 66 (ENH-048): Shorts in batches (AI ideas -> a dated Channel series) and today's news (feeds + AI picks)."""

import time

import aiosqlite
from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from backend.channel import batch_service
from backend.content import news_service
from backend.content.link_reader import read_link
from backend.core.responses import ok
from backend.db.database import get_db
from backend.db.transactions import read_transaction, write_transaction

router = APIRouter(prefix="/api/shorts-batch", tags=["shorts-batch"])
news_router = APIRouter(prefix="/api/news", tags=["news"])


@router.post("/ideas")
async def batch_ideas(body: batch_service.IdeasRequest, db: aiosqlite.Connection = Depends(get_db)) -> dict:
    """The AI's distinct Short ideas for one topic and template (nothing is saved)."""
    started_at = time.perf_counter()
    ideas = await batch_service.propose_ideas(db, body)  # AI call, no lock held (the read is a plain SELECT)
    return ok({"ideas": ideas}, started_at=started_at)


@router.post("/create")
async def batch_create(body: batch_service.CreateRequest, db: aiosqlite.Connection = Depends(get_db)) -> dict:
    """Save the batch as a dated Channel series (and its projects when asked)."""
    started_at = time.perf_counter()
    async with write_transaction(db):
        result = await batch_service.create_batch(db, body)
    return ok(result, started_at=started_at)


class FeedIn(BaseModel):
    id: str | None = Field(default=None, max_length=64)
    url: str = Field(min_length=8, max_length=2000)
    name: str = Field(default="", max_length=80)
    enabled: bool = True


class PicksRequest(BaseModel):
    cefr_level: str = "B1"
    count: int = Field(default=5, ge=1, le=10)


class ArticlesRequest(BaseModel):
    links: list[str] = Field(min_length=1, max_length=10)


@news_router.get("/feeds")
async def get_feeds(db: aiosqlite.Connection = Depends(get_db)) -> dict:
    async with read_transaction():
        return ok({"feeds": await news_service.list_feeds(db)})


@news_router.put("/feeds")
async def put_feeds(body: list[FeedIn], db: aiosqlite.Connection = Depends(get_db)) -> dict:
    async with write_transaction(db):
        feeds = await news_service.save_feeds(db, [item.model_dump() for item in body])
    news_service.clear_cache()
    return ok({"feeds": feeds})


@news_router.get("/today")
async def get_today(db: aiosqlite.Connection = Depends(get_db)) -> dict:
    """The stories of the last 36 hours from the enabled feeds (and any feed that could not be read)."""
    started_at = time.perf_counter()
    async with read_transaction():
        feeds = await news_service.list_feeds(db)
    return ok(await news_service.today(feeds), started_at=started_at)


@news_router.post("/picks")
async def post_picks(body: PicksRequest, db: aiosqlite.Connection = Depends(get_db)) -> dict:
    """The AI's best stories of today for learners at this level, each with a hook."""
    started_at = time.perf_counter()
    async with read_transaction():
        feeds = await news_service.list_feeds(db)
    stories = (await news_service.today(feeds))["stories"]
    return ok({"picks": await news_service.picks(stories, body.cefr_level, body.count)}, started_at=started_at)


@news_router.post("/articles")
async def post_articles(body: ArticlesRequest) -> dict:
    """The text of each chosen story's page (Phase 63 link reader), for a news batch; a page that cannot be read says why."""
    started_at = time.perf_counter()
    results = []
    for link in body.links:
        try:
            page = await read_link(link)
            results.append({"url": link, "title": page["title"], "text": page["text"], "error": ""})
        except Exception as exc:  # one unreadable page does not stop the others
            results.append({"url": link, "title": "", "text": "", "error": str(exc) or type(exc).__name__})
    return ok({"articles": results}, started_at=started_at)
