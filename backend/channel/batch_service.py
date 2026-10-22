"""Phase 66 (ENH-048): Shorts in batches -- one topic + one Shorts template -> 5-10 AI ideas, saved as a dated Channel
plan series so the night automation (Phase 62) makes them, or made into projects at once."""

from __future__ import annotations

import asyncio
import json
from datetime import date, timedelta
from typing import Any, Literal

import aiosqlite
from jinja2 import Environment, FileSystemLoader, StrictUndefined
from pydantic import BaseModel, Field, TypeAdapter, field_validator

from backend.ai.llm.contracts import GenerationRequest
from backend.ai.llm.router import AIRouter, build_ai_router_from_settings
from backend.ai.llm.validation import parse_and_validate
from backend.channel import channel_service
from backend.core import paths
from backend.core.config import settings
from backend.core.exceptions import ProviderError, SchemaValidationError, ValidationError
from backend.schemas.channel import EpisodeInput, SeriesInput, TopicInput
from backend.core.constants import CEFR_LEVELS
from backend.schemas.project import CONVERSATION_SHORT_STYLES, SHORT_STYLES

# What each template asks of an idea (shown to the AI)
TEMPLATES = {
    "news": ("English news", "one news story told in simple English"),
    "blur": ("Text on blur", "a short story, life lesson or meaningful quote about the topic"),
    "mistakes": ("Don't say / Say", "two to four common learner mistakes about one point, each with the natural phrase"),
    "wordday": ("Word of the day", "one useful word or phrase about the topic, its meaning and examples"),
    "top5": ("Top 5 phrases", "five phrases native speakers use for one situation"),
    "quiz": ("Countdown quiz", "two or three multiple-choice questions on one language point"),
    "listen": ("Listening challenge", "two or three short everyday sentences in one situation, heard at natural speed"),
    "chat": ("Chat", "a short text-message conversation between two characters in one everyday situation"),
    "wyr": ("Would you rather", "two or three would-you-rather questions on one theme, answered by the second character"),
}


class Idea(BaseModel):
    title: str = Field(min_length=1, max_length=120)
    brief: str = Field(default="", max_length=600)

    @field_validator("title", "brief")
    @classmethod
    def strip(cls, value: str) -> str:
        return " ".join(value.split())


class Ideas(BaseModel):
    ideas: list[Idea] = Field(min_length=1, max_length=12)


_IDEAS = TypeAdapter(Ideas)


class IdeasRequest(BaseModel):
    topic: str = Field(min_length=2, max_length=300)
    template: Literal["news", "blur", "mistakes", "wordday", "top5", "quiz", "listen", "chat", "wyr"]
    count: int = Field(default=7, ge=5, le=10)
    cefr_level: str = "B1"
    hint: str = Field(default="", max_length=300)

    @field_validator("cefr_level")
    @classmethod
    def level(cls, value: str) -> str:
        if value not in CEFR_LEVELS:
            raise ValueError(f"cefr_level must be one of {CEFR_LEVELS}")
        return value


class BatchItem(BaseModel):
    title: str = Field(min_length=1, max_length=120)
    brief: str = Field(default="", max_length=600)
    source_text: str = Field(default="", max_length=12000)  # a news article (today's news batch)


class CreateRequest(BaseModel):
    topic_name: str = Field(min_length=1, max_length=80)
    series_name: str = Field(min_length=1, max_length=100)
    template: Literal["news", "blur", "mistakes", "wordday", "top5", "quiz", "listen", "chat", "wyr"]
    cast: list[str] = Field(min_length=1, max_length=2)
    cefr_level: str = "B1"
    start_date: date
    every_days: int = Field(default=1, ge=1, le=14)
    items: list[BatchItem] = Field(min_length=1, max_length=12)
    make_projects: bool = False
    audience: Literal["international", "vietnamese", "both"] | None = None  # Phase 72: None = as the channel

    @field_validator("cefr_level")
    @classmethod
    def level(cls, value: str) -> str:
        if value not in CEFR_LEVELS:
            raise ValueError(f"cefr_level must be one of {CEFR_LEVELS}")
        return value


_env = Environment(loader=FileSystemLoader(str(paths.PROMPTS_DIR / "shorts")), undefined=StrictUndefined,
                   trim_blocks=True, lstrip_blocks=True)


def normalize_ideas(parsed: object) -> object:
    """Cloud models rename fields: accept items/shorts/list, name/headline for title, description/summary for brief."""
    if isinstance(parsed, list):
        parsed = {"ideas": parsed}
    if not isinstance(parsed, dict):
        return parsed
    items = next((parsed[key] for key in ("ideas", "items", "shorts", "list") if isinstance(parsed.get(key), list)), None)
    if items is None:
        return parsed
    fixed = []
    for item in items:
        if isinstance(item, str):
            fixed.append({"title": item, "brief": ""})
        elif isinstance(item, dict):
            fixed.append({"title": str(item.get("title") or item.get("name") or item.get("headline") or ""),
                          "brief": str(item.get("brief") or item.get("description") or item.get("summary") or "")})
    return {"ideas": fixed}


async def propose_ideas(db: aiosqlite.Connection, request: IdeasRequest, router: AIRouter | None = None) -> list[dict]:
    """The AI's distinct ideas for the batch (nothing is saved); titles already in the channel are avoided."""
    cursor = await db.execute("SELECT title FROM channel_episodes ORDER BY created_at DESC LIMIT 60")
    avoid = [row[0] for row in await cursor.fetchall()]
    name, rule = TEMPLATES[request.template]
    prompt = await asyncio.to_thread(lambda: _env.get_template("batch_ideas.txt").render(
        count=request.count, topic=request.topic, hint=request.hint, cefr_level=request.cefr_level, template_name=name,
        template_rule=rule, avoid=avoid))
    router = router or build_ai_router_from_settings()
    try:
        result = await router.generate(GenerationRequest(prompt=prompt, json_schema=Ideas.model_json_schema(),
                                                         deadline_seconds=settings.AI_REQUEST_DEADLINE_SECONDS,
                                                         purpose="shorts_batch_ideas"))
    except ProviderError as exc:
        raise ValidationError(f"The AI could not propose ideas right now ({type(exc).__name__}); try again") from exc
    text = result.text
    try:
        text = json.dumps(normalize_ideas(json.loads(text)))
    except (json.JSONDecodeError, TypeError):
        pass
    try:
        ideas = parse_and_validate(text, _IDEAS).ideas
    except SchemaValidationError as exc:
        raise ValidationError(f"The AI's ideas were not usable ({exc}); try again") from exc
    seen, unique = set(), []
    for idea in ideas:
        key = idea.title.lower()
        if key not in seen and key not in {title.lower() for title in avoid}:
            seen.add(key)
            unique.append(idea.model_dump())
    return unique[:request.count]


def publishing_dates(start: date, every_days: int, count: int) -> list[date]:
    return [start + timedelta(days=every_days * index) for index in range(count)]


async def create_batch(db: aiosqlite.Connection, request: CreateRequest) -> dict[str, Any]:
    """Save the batch as a series (topic found by name or made) with dated episodes; their articles are kept for the
    projects. With `make_projects`, the projects are made at once."""
    conversation = request.template in CONVERSATION_SHORT_STYLES
    if conversation and len(request.cast) != 2:
        raise ValidationError("A chat or would-you-rather batch needs two characters")
    if not conversation and len(request.cast) != 1:
        raise ValidationError("Choose one narrator for this batch")
    cursor = await db.execute("SELECT id, name FROM channel_topics")
    topic_id = next((row["id"] for row in await cursor.fetchall() if row["name"].strip().lower() == request.topic_name.strip().lower()), None)
    if topic_id is None:
        topic_id = (await channel_service.create_topic(db, TopicInput(name=request.topic_name)))["id"]
    series = await channel_service.create_series(db, topic_id, SeriesInput(
        name=request.series_name, presentation_mode="classic" if conversation else "solo_explainer",
        explainer_style=request.template, cefr_level=request.cefr_level, cast=request.cast, duration_minutes=0.75,
        genre="small_talk" if conversation else "informational"))
    if request.audience:
        from backend.content import audience

        await audience.set_series(db, series["id"], request.audience)
    dates = publishing_dates(request.start_date, request.every_days, len(request.items))
    for item, day in zip(request.items, dates, strict=True):
        episode = await channel_service.add_episode(db, series["id"], EpisodeInput(title=item.title, brief=item.brief))
        article = item.source_text.strip() if request.template == "news" else ""
        await db.execute("UPDATE channel_episodes SET publish_date = ?, source_kind = ?, source_text = ? WHERE id = ?",
                         (day.isoformat(), "article" if article else "", article, episode["id"]))
    created = (await channel_service.create_projects(db, series["id"]))["created"] if request.make_projects else []
    return {"series_id": series["id"], "topic_id": topic_id, "episodes": len(request.items), "projects": len(created),
            "first_date": dates[0].isoformat(), "last_date": dates[-1].isoformat()}


assert set(TEMPLATES) == set(SHORT_STYLES), "every Shorts template has a batch rule"
