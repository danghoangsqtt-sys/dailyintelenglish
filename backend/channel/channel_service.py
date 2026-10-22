"""Task 36.5 (D103-D105): the channel plan.

A channel has topics (each one a YouTube playlist: Travel, Work, Daily life...), every topic has series (3-10 episodes) and
every episode becomes a project. The AI proposes the whole map from the owner's direction (`propose_plan`); the owner edits
it and `apply_plan` saves it; `create_projects` makes a series' numbered projects with its cast; `schedule` spreads the
episodes over the publishing weekdays, rotating topics so the channel never runs one theme for weeks; `episode_context`
tells the description and the thumbnail which series and episode a project is.
"""

from __future__ import annotations

import json
import uuid
from datetime import date, datetime, timedelta, timezone
from typing import Any

import aiosqlite
from pydantic import TypeAdapter

from backend.core.config import settings
from backend.core.exceptions import NotFoundError, ProviderError, SchemaValidationError, ValidationError
from backend.ai.llm.prompt_loader import render_channel_prompt
from backend.schemas.channel import (
    ChannelPlan, EpisodeInput, EpisodePatch, PlanRequest, ScheduleRequest, SeriesInput, SeriesPatch, TopicInput,
    TopicPatch,
)
from backend.schemas.project import ScriptConfig, SpeakerConfig
from backend.content import project_service
from backend.ai.llm.contracts import GenerationRequest
from backend.ai.llm.router import AIRouter, build_ai_router_from_settings
from backend.ai.llm.validation import parse_and_validate

_PLAN_ADAPTER = TypeAdapter(ChannelPlan)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


async def _one(db: aiosqlite.Connection, sql: str, params: tuple, what: str) -> dict:
    cursor = await db.execute(sql, params)
    row = await cursor.fetchone()
    if row is None:
        raise NotFoundError(f"{what} not found")
    return dict(row)


# ---------------------------------------------------------------- reading

async def channel(db: aiosqlite.Connection) -> dict[str, Any]:
    """The whole plan as a tree, in order, with each episode's project and progress."""
    topics = [dict(row) for row in await (await db.execute(
        "SELECT * FROM channel_topics ORDER BY position, created_at")).fetchall()]
    series = [dict(row) for row in await (await db.execute(
        "SELECT * FROM channel_series ORDER BY position, created_at")).fetchall()]
    episodes = [dict(row) for row in await (await db.execute(
        "SELECT e.*, p.name AS project_name, p.status AS project_status FROM channel_episodes e "
        "LEFT JOIN projects p ON p.id = e.project_id ORDER BY e.number")).fetchall()]
    by_series: dict[str, list[dict]] = {}
    for episode in episodes:
        by_series.setdefault(episode["series_id"], []).append(episode)
    by_topic: dict[str, list[dict]] = {}
    for item in series:
        item["cast"] = json.loads(item.pop("cast_json") or "[]")
        item["episodes"] = by_series.get(item["id"], [])
        by_topic.setdefault(item["topic_id"], []).append(item)
    for topic in topics:
        topic["series"] = by_topic.get(topic["id"], [])
    counts = {status: sum(episode["status"] == status for episode in episodes) for status in ("planned", "created", "published")}
    return {"topics": topics, "counts": counts, "episodes": len(episodes)}


async def get_topic(db: aiosqlite.Connection, topic_id: str) -> dict:
    return await _one(db, "SELECT * FROM channel_topics WHERE id = ?", (topic_id,), "Topic")


async def get_series(db: aiosqlite.Connection, series_id: str) -> dict:
    row = await _one(db, "SELECT * FROM channel_series WHERE id = ?", (series_id,), "Series")
    row["cast"] = json.loads(row.pop("cast_json") or "[]")
    return row


async def get_episode(db: aiosqlite.Connection, episode_id: str) -> dict:
    return await _one(db, "SELECT * FROM channel_episodes WHERE id = ?", (episode_id,), "Episode")


# ---------------------------------------------------------------- editing

async def _next_position(db: aiosqlite.Connection, table: str, where: str = "", params: tuple = ()) -> int:
    cursor = await db.execute(f"SELECT COALESCE(MAX(position), -1) + 1 FROM {table} {where}", params)
    return (await cursor.fetchone())[0]


async def create_topic(db: aiosqlite.Connection, body: TopicInput) -> dict:
    topic_id, now = str(uuid.uuid4()), _now()
    await db.execute(
        "INSERT INTO channel_topics (id, name, description, playlist_url, position, created_at, updated_at) "
        "VALUES (?, ?, ?, ?, ?, ?, ?)",
        (topic_id, body.name.strip(), body.description.strip(), body.playlist_url,
         await _next_position(db, "channel_topics"), now, now))
    return await get_topic(db, topic_id)


async def _patch(db: aiosqlite.Connection, table: str, row_id: str, fields: dict) -> None:
    if fields:
        await db.execute(f"UPDATE {table} SET " + ", ".join(f"{key} = ?" for key in fields) + ", updated_at = ? WHERE id = ?",
                         (*fields.values(), _now(), row_id))


async def patch_topic(db: aiosqlite.Connection, topic_id: str, patch: TopicPatch) -> dict:
    await get_topic(db, topic_id)
    await _patch(db, "channel_topics", topic_id, patch.model_dump(exclude_unset=True, exclude_none=True))
    return await get_topic(db, topic_id)


async def delete_topic(db: aiosqlite.Connection, topic_id: str) -> None:
    await get_topic(db, topic_id)
    await db.execute("DELETE FROM channel_topics WHERE id = ?", (topic_id,))  # series and episodes cascade; projects stay


async def _check_cast(db: aiosqlite.Connection, cast: list[str]) -> None:
    if len(cast) != len(set(cast)):
        raise ValidationError("A character can play only one speaker in a series")
    for character_id in cast:
        await _one(db, "SELECT id FROM characters WHERE id = ?", (character_id,), "Character")


async def create_series(db: aiosqlite.Connection, topic_id: str, body: SeriesInput) -> dict:
    await get_topic(db, topic_id)
    await _check_cast(db, body.cast)
    series_id, now = str(uuid.uuid4()), _now()
    await db.execute(
        "INSERT INTO channel_series (id, topic_id, name, description, genre, cefr_level, cast_json, duration_minutes, "
        "playlist_url, position, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (series_id, topic_id, body.name.strip(), body.description.strip(), body.genre, body.cefr_level, json.dumps(body.cast),
         body.duration_minutes, body.playlist_url,
         await _next_position(db, "channel_series", "WHERE topic_id = ?", (topic_id,)), now, now))
    await db.execute("UPDATE channel_series SET presentation_mode=?,explainer_structure=?,explainer_style=? WHERE id=?",
                     (body.presentation_mode, body.explainer_structure, body.explainer_style, series_id))
    return await get_series(db, series_id)


async def patch_series(db: aiosqlite.Connection, series_id: str, patch: SeriesPatch) -> dict:
    await get_series(db, series_id)
    fields = patch.model_dump(exclude_unset=True, exclude_none=True)
    if "cast" in fields:
        await _check_cast(db, fields["cast"])
        fields["cast_json"] = json.dumps(fields.pop("cast"))
    await _patch(db, "channel_series", series_id, fields)
    return await get_series(db, series_id)


async def delete_series(db: aiosqlite.Connection, series_id: str) -> None:
    await get_series(db, series_id)
    await db.execute("DELETE FROM channel_series WHERE id = ?", (series_id,))


async def add_episode(db: aiosqlite.Connection, series_id: str, body: EpisodeInput) -> dict:
    await get_series(db, series_id)
    cursor = await db.execute("SELECT COALESCE(MAX(number), 0) + 1 FROM channel_episodes WHERE series_id = ?", (series_id,))
    number = (await cursor.fetchone())[0]
    episode_id, now = str(uuid.uuid4()), _now()
    await db.execute(
        "INSERT INTO channel_episodes (id, series_id, number, title, brief, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
        (episode_id, series_id, number, body.title.strip(), body.brief.strip(), now, now))
    return await get_episode(db, episode_id)


async def patch_episode(db: aiosqlite.Connection, episode_id: str, patch: EpisodePatch) -> dict:
    episode = await get_episode(db, episode_id)
    fields = patch.model_dump(exclude_unset=True)
    fields = {key: value for key, value in fields.items() if value is not None or key == "publish_date"}
    if fields.get("status") == "published" and not (fields.get("video_url") or episode["video_url"]):
        raise ValidationError("Paste the video link before marking the episode published")
    if fields.get("status") in ("created", "published") and not episode["project_id"]:
        raise ValidationError("Create the episode's project first")
    await _patch(db, "channel_episodes", episode_id, fields)
    return await get_episode(db, episode_id)


async def delete_episode(db: aiosqlite.Connection, episode_id: str) -> None:
    episode = await get_episode(db, episode_id)
    await db.execute("DELETE FROM channel_episodes WHERE id = ?", (episode_id,))
    # keep the numbers continuous (Ep. 1..N) -- later episodes move up by one
    await db.execute("UPDATE channel_episodes SET number = -number WHERE series_id = ? AND number > ?",
                     (episode["series_id"], episode["number"]))
    await db.execute("UPDATE channel_episodes SET number = -number - 1 WHERE series_id = ? AND number < 0",
                     (episode["series_id"],))


# ---------------------------------------------------------------- the AI channel map (D104)

def normalize_plan(parsed: object) -> object:
    """Real-AI lesson (Tasks 36.2/36.3): the cloud model renames fields. Accept `title` for `name`, `playlists`/`themes`
    for `topics`, `episode_list`/`items` for `episodes`, plain strings for episodes."""
    if not isinstance(parsed, dict):
        return parsed
    topics = next((parsed[key] for key in ("topics", "playlists", "themes") if isinstance(parsed.get(key), list)), None)
    if topics is None:
        return parsed
    fixed_topics = []
    for topic in topics:
        if not isinstance(topic, dict):
            continue
        series_list = next((topic[key] for key in ("series", "seasons") if isinstance(topic.get(key), list)), [])
        fixed_series = []
        for series in series_list:
            if not isinstance(series, dict):
                continue
            episodes = next((series[key] for key in ("episodes", "episode_list", "items") if isinstance(series.get(key), list)), [])
            fixed_series.append({
                "name": series.get("name") or series.get("title") or "",
                "description": series.get("description") or "", "genre": series.get("genre") or "small_talk",
                "cefr_level": series.get("cefr_level") or series.get("cefr") or series.get("level") or "B1",
                "episodes": [episode if isinstance(episode, dict) and "title" in episode
                             else {"title": episode.get("name", "") if isinstance(episode, dict) else str(episode),
                                   "brief": episode.get("brief", "") if isinstance(episode, dict) else ""}
                             for episode in episodes],
            })
        fixed_topics.append({"name": topic.get("name") or topic.get("title") or "", "description": topic.get("description") or "",
                             "series": fixed_series})
    return {"topics": fixed_topics}


async def propose_plan(db: aiosqlite.Connection, request: PlanRequest, router: AIRouter | None = None) -> dict:
    """The AI's channel map, checked; nothing is saved until the owner applies it."""
    cursor = await db.execute("SELECT name FROM channel_topics ORDER BY position")
    existing = [row[0] for row in await cursor.fetchall()]
    prompt = await render_channel_prompt(request=request.model_copy(update={"existing_topics": existing}))
    router = router or build_ai_router_from_settings()
    try:
        result = await router.generate(GenerationRequest(prompt=prompt, json_schema=ChannelPlan.model_json_schema(),
                                                         deadline_seconds=settings.AI_REQUEST_DEADLINE_SECONDS,
                                                         purpose="channel_plan"))
    except ProviderError as exc:
        raise ValidationError(f"The AI could not plan the channel right now ({type(exc).__name__}); try again") from exc
    text = result.text
    try:
        text = json.dumps(normalize_plan(json.loads(text)))
    except (json.JSONDecodeError, TypeError):
        pass
    try:
        plan = parse_and_validate(text, _PLAN_ADAPTER)
    except SchemaValidationError as exc:
        raise ValidationError(f"The AI's channel map was not usable ({exc}); try again") from exc
    return plan.model_dump()


async def apply_plan(db: aiosqlite.Connection, plan: ChannelPlan, cast: list[str] | None = None) -> dict:
    """Save an approved map: new topics are added after the existing ones; a topic with the same name as an existing one
    receives the new series instead of being duplicated."""
    cursor = await db.execute("SELECT id, name FROM channel_topics")
    by_name = {row["name"].strip().lower(): row["id"] for row in await cursor.fetchall()}
    for topic in plan.topics:
        topic_id = by_name.get(topic.name.strip().lower())
        if topic_id is None:
            topic_id = (await create_topic(db, TopicInput(name=topic.name, description=topic.description)))["id"]
            by_name[topic.name.strip().lower()] = topic_id
        for series in topic.series:
            created = await create_series(db, topic_id, SeriesInput(
                name=series.name, description=series.description, genre=series.genre, cefr_level=series.cefr_level,
                cast=cast or []))
            for episode in series.episodes:
                await add_episode(db, created["id"], EpisodeInput(title=episode.title, brief=episode.brief))
    return await channel(db)


# ---------------------------------------------------------------- projects (D104)

async def _speakers(db: aiosqlite.Connection, cast: list[str]) -> list[SpeakerConfig]:
    from backend.library import character_profile_service as profiles

    speakers = []
    for character_id in cast:
        profile = await profiles.get_profile(db, character_id)
        voice = profile.get("voice") or {}
        speakers.append(SpeakerConfig(
            name=profile["name"], gender=profile.get("gender") or "neutral", accent=profile.get("accent") or "american",
            tts_engine=voice.get("engine") or "edge_tts", voice_id=voice.get("voice_id") or None,
            speed=voice.get("speed"), pitch=voice.get("pitch") or 0.0, volume=voice.get("volume") or 1.0))
    return speakers


async def create_projects(db: aiosqlite.Connection, series_id: str) -> dict:
    """One project per planned episode of the series, named "<series> · Ep. n: <title>", with the series' level, genre,
    length and cast (the cast also becomes the project's visual cast). Episodes that already have a project are skipped."""
    from backend.library import project_visuals_service as project_visuals

    series = await get_series(db, series_id)
    solo = series["presentation_mode"] == "solo_explainer"
    if solo and len(series["cast"]) != 1:
        raise ValidationError("Choose exactly one presenter for this Solo series")
    if not solo and len(series["cast"]) < 2:
        raise ValidationError("Choose at least two characters for the series first")
    speakers = await _speakers(db, series["cast"])
    style = (series.get("explainer_style") or "presenter") if solo else (
        series.get("explainer_style") if series.get("explainer_style") in ("chat", "wyr") else None)
    # Phase 63: a Short lasts at most 60 s
    from backend.schemas.project import SHORT_STYLES

    duration = min(series["duration_minutes"], 0.75) if style in SHORT_STYLES else series["duration_minutes"]
    cursor = await db.execute("SELECT * FROM channel_episodes WHERE series_id = ? AND project_id IS NULL ORDER BY number",
                              (series_id,))
    created = []
    for episode in [dict(row) for row in await cursor.fetchall()]:
        topic = f"{episode['title']}. {episode['brief']}".strip() if episode["brief"] else episode["title"]
        project = await project_service.create_project(db, ScriptConfig(
            name=f"{series['name']} · Ep. {episode['number']}: {episode['title']}"[:200], topic=topic[:500],
            cefr_level=series["cefr_level"], duration_minutes=duration, num_speakers=len(speakers),
            genre=series["genre"], accent=speakers[0].accent, speakers=speakers,
            presentation_mode=series["presentation_mode"],
            explainer_structure=series["explainer_structure"] if solo else None, explainer_style=style,
            # Phase 66: a news episode made from today's news carries its article
            **({"source_kind": "article", "source_text": episode["source_text"]}
               if style == "news" and episode.get("source_kind") == "article" and episode.get("source_text") else {})),
            commit=False)
        await project_visuals.set_cast(db, project["id"], [
            {"speaker_index": index, "character_id": character_id} for index, character_id in enumerate(series["cast"])])
        await db.execute("UPDATE channel_episodes SET project_id = ?, status = 'created', updated_at = ? WHERE id = ?",
                         (project["id"], _now(), episode["id"]))
        created.append({"episode_id": episode["id"], "number": episode["number"], "project_id": project["id"]})
    return {"created": created}


# ---------------------------------------------------------------- the calendar (D105)

def rotate(topics: list[list[dict]]) -> list[dict]:
    """Interleave the topics' queues: one episode per topic in turn, so the same topic never comes twice in a row while
    another still has episodes (each queue keeps its series and episode order)."""
    queues = [list(queue) for queue in topics if queue]
    order: list[dict] = []
    while any(queues):
        for queue in queues:
            if queue:
                order.append(queue.pop(0))
    return order


def publishing_days(start: date, weekdays: list[int], count: int) -> list[date]:
    days, day = [], start
    while len(days) < count:
        if day.weekday() in weekdays:
            days.append(day)
        day += timedelta(days=1)
    return days


async def schedule(db: aiosqlite.Connection, request: ScheduleRequest) -> dict:
    """Give every not-yet-published episode a publishing date, rotating topics (published ones keep theirs)."""
    tree = await channel(db)
    queues = []
    for topic in tree["topics"]:
        queue = []
        for series in topic["series"]:
            queue += [episode for episode in series["episodes"]
                      if request.include_published or episode["status"] != "published"]
        queues.append(queue)
    order = rotate(queues)
    days = publishing_days(date.fromisoformat(request.start_date), request.weekdays, len(order))
    for episode, day in zip(order, days, strict=True):
        await db.execute("UPDATE channel_episodes SET publish_date = ?, updated_at = ? WHERE id = ?",
                         (day.isoformat(), _now(), episode["id"]))
    return await channel(db)


# ---------------------------------------------------------------- what a project is in the channel

async def episode_context(db: aiosqlite.Connection, project_id: str) -> dict | None:
    """The series block of a project's description and the thumbnail's episode number; None for a project outside the plan."""
    cursor = await db.execute(
        "SELECT e.*, s.name AS series_name, s.playlist_url AS series_playlist, t.name AS topic_name, "
        "t.playlist_url AS topic_playlist FROM channel_episodes e JOIN channel_series s ON s.id = e.series_id "
        "JOIN channel_topics t ON t.id = s.topic_id WHERE e.project_id = ?", (project_id,))
    row = await cursor.fetchone()
    if row is None:
        return None
    episode = dict(row)
    cursor = await db.execute("SELECT number, title, video_url, status FROM channel_episodes WHERE series_id = ? ORDER BY number",
                              (episode["series_id"],))
    siblings = [dict(item) for item in await cursor.fetchall()]

    def link(number: int) -> dict | None:
        found = next((item for item in siblings if item["number"] == number), None)
        return {"number": number, "title": found["title"], "url": found["video_url"]} if found else None

    return {"series": episode["series_name"], "topic": episode["topic_name"], "number": episode["number"],
            "total": len(siblings), "title": episode["title"],
            "playlist_url": episode["series_playlist"] or episode["topic_playlist"],
            "previous": link(episode["number"] - 1), "next": link(episode["number"] + 1)}
