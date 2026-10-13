"""Task 36.5 (D103-D105): the channel plan -- topics, series, episodes, the AI map and the publishing calendar."""

import time

import aiosqlite
from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from app.core.responses import ok
from app.db.database import get_db
from app.db.transactions import read_transaction, write_transaction
from app.models.channel import (
    ChannelPlan,
    EpisodeInput,
    EpisodePatch,
    PlanRequest,
    ScheduleRequest,
    SeriesInput,
    SeriesPatch,
    TopicInput,
    TopicPatch,
)
from app.services import channel_service, dashboard_service

router = APIRouter(prefix="/api/channel", tags=["channel"])


class ApplyPlanRequest(BaseModel):
    plan: ChannelPlan
    cast: list[str] = Field(default_factory=list, max_length=6)  # the default cast of every new series


@router.get("")
async def get_channel(db: aiosqlite.Connection = Depends(get_db)) -> dict:
    started_at = time.perf_counter()
    async with read_transaction():
        result = await channel_service.channel(db)
    return ok(result, started_at=started_at)


@router.get("/dashboard")
async def get_dashboard(db: aiosqlite.Connection = Depends(get_db)) -> dict:
    """Task 36.7 (D106-D108): stats, today's actions, the roadmap, the production board and the next two weeks."""
    started_at = time.perf_counter()
    async with read_transaction():
        result = await dashboard_service.dashboard(db)
    return ok(result, started_at=started_at)


@router.post("/plan/propose")
async def propose_plan(body: PlanRequest, db: aiosqlite.Connection = Depends(get_db)) -> dict:
    """The AI's channel map (nothing saved): topics -> series -> episode titles."""
    started_at = time.perf_counter()
    result = await channel_service.propose_plan(db, body)  # AI call, no lock held
    return ok(result, started_at=started_at)


@router.post("/plan/apply")
async def apply_plan(body: ApplyPlanRequest, db: aiosqlite.Connection = Depends(get_db)) -> dict:
    started_at = time.perf_counter()
    async with write_transaction(db):
        result = await channel_service.apply_plan(db, body.plan, body.cast)
    return ok(result, started_at=started_at)


@router.post("/topics")
async def create_topic(body: TopicInput, db: aiosqlite.Connection = Depends(get_db)) -> dict:
    async with write_transaction(db):
        result = await channel_service.create_topic(db, body)
    return ok(result)


@router.patch("/topics/{topic_id}")
async def patch_topic(topic_id: str, body: TopicPatch, db: aiosqlite.Connection = Depends(get_db)) -> dict:
    async with write_transaction(db):
        result = await channel_service.patch_topic(db, topic_id, body)
    return ok(result)


@router.delete("/topics/{topic_id}")
async def delete_topic(topic_id: str, db: aiosqlite.Connection = Depends(get_db)) -> dict:
    async with write_transaction(db):
        await channel_service.delete_topic(db, topic_id)
    return ok({"deleted": topic_id})


@router.post("/topics/{topic_id}/series")
async def create_series(topic_id: str, body: SeriesInput, db: aiosqlite.Connection = Depends(get_db)) -> dict:
    async with write_transaction(db):
        result = await channel_service.create_series(db, topic_id, body)
    return ok(result)


@router.patch("/series/{series_id}")
async def patch_series(series_id: str, body: SeriesPatch, db: aiosqlite.Connection = Depends(get_db)) -> dict:
    async with write_transaction(db):
        result = await channel_service.patch_series(db, series_id, body)
    return ok(result)


@router.delete("/series/{series_id}")
async def delete_series(series_id: str, db: aiosqlite.Connection = Depends(get_db)) -> dict:
    async with write_transaction(db):
        await channel_service.delete_series(db, series_id)
    return ok({"deleted": series_id})


@router.post("/series/{series_id}/episodes")
async def add_episode(series_id: str, body: EpisodeInput, db: aiosqlite.Connection = Depends(get_db)) -> dict:
    async with write_transaction(db):
        result = await channel_service.add_episode(db, series_id, body)
    return ok(result)


@router.post("/series/{series_id}/projects")
async def create_projects(series_id: str, db: aiosqlite.Connection = Depends(get_db)) -> dict:
    """One numbered project per planned episode of the series, with its cast."""
    async with write_transaction(db):
        result = await channel_service.create_projects(db, series_id)
    return ok(result)


@router.patch("/episodes/{episode_id}")
async def patch_episode(episode_id: str, body: EpisodePatch, db: aiosqlite.Connection = Depends(get_db)) -> dict:
    async with write_transaction(db):
        result = await channel_service.patch_episode(db, episode_id, body)
    return ok(result)


@router.delete("/episodes/{episode_id}")
async def delete_episode(episode_id: str, db: aiosqlite.Connection = Depends(get_db)) -> dict:
    async with write_transaction(db):
        await channel_service.delete_episode(db, episode_id)
    return ok({"deleted": episode_id})


@router.post("/schedule")
async def schedule(body: ScheduleRequest, db: aiosqlite.Connection = Depends(get_db)) -> dict:
    """Publishing dates for the unpublished episodes, rotating topics over the chosen weekdays (D105)."""
    async with write_transaction(db):
        result = await channel_service.schedule(db, body)
    return ok(result)


@router.get("/projects/{project_id}")
async def project_context(project_id: str, db: aiosqlite.Connection = Depends(get_db)) -> dict:
    async with read_transaction():
        result = await channel_service.episode_context(db, project_id)
    return ok(result)
