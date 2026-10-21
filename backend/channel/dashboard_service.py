"""Task 36.7 (D106-D108): the channel dashboard -- what the channel has, what to do today, where it stands on the
channel-building roadmap, which step every episode is at, and the next two weeks. Read-only, computed from real data.
"""

from __future__ import annotations

from datetime import date, timedelta
from typing import Any

import aiosqlite

from backend.core.paths import get_project_root

LOGO = get_project_root() / "renderer" / "public" / "brand" / "logo.png"

# The production steps in order: (key, label, page of the step).
STEPS = (
    ("script", "Script", "/step2"), ("learning", "Learning", "/step3"), ("audio", "Audio", "/step4"),
    ("video", "Video", "/step5"), ("thumbnail", "Thumbnail", "/step6"), ("youtube", "YouTube", "/step7"),
    ("published", "Publish", "/channel"),  # ready to publish, or published
)
# Phase 56 (ENH-038): what is still missing when a step is not done, for the step bar.
STEP_TODO = {
    "script": "generate or write the script.",
    "learning": "generate the learning content (vocabulary, notes, quiz).",
    "audio": "generate the voice audio.",
    "video": "render the video.",
    "thumbnail": "create and choose a thumbnail.",
    "youtube": "prepare the YouTube package (title, description, tags).",
}
GOAL_FIRST = 10
GOAL_GROW = 50


def _check(label: str, done: bool, link: str, progress: str | None = None) -> dict:
    return {"label": label, "done": bool(done), "link": link, "progress": progress}


async def _scalar(db: aiosqlite.Connection, sql: str, params: tuple = ()) -> int:
    cursor = await db.execute(sql, params)
    row = await cursor.fetchone()
    return int(row[0] or 0) if row else 0


async def _project_steps(db: aiosqlite.Connection, project_id: str | None = None) -> list[dict]:
    """Every project (or just one) with the steps it has done and its channel episode (if any)."""
    cursor = await db.execute(
        "SELECT p.id, p.name, p.updated_at, p.created_at, "
        "EXISTS(SELECT 1 FROM script_lines s WHERE s.project_id = p.id) AS script, "
        "EXISTS(SELECT 1 FROM learning_contents l WHERE l.project_id = p.id) AS learning, "
        "EXISTS(SELECT 1 FROM audio_jobs a WHERE a.project_id = p.id AND a.status = 'complete') AS audio, "
        "EXISTS(SELECT 1 FROM video_jobs v WHERE v.project_id = p.id AND v.status = 'complete') AS video, "
        "EXISTS(SELECT 1 FROM thumbnails t WHERE t.project_id = p.id AND t.is_selected = 1) AS thumbnail, "
        "EXISTS(SELECT 1 FROM youtube_packages y WHERE y.project_id = p.id) AS youtube, "
        "e.id AS episode_id, e.number, e.title AS episode_title, e.status AS episode_status, e.publish_date, "
        "s.name AS series_name, t2.name AS topic_name "
        "FROM projects p LEFT JOIN channel_episodes e ON e.project_id = p.id "
        "LEFT JOIN channel_series s ON s.id = e.series_id LEFT JOIN channel_topics t2 ON t2.id = s.topic_id "
        + ("WHERE p.id = ? " if project_id is not None else "") + "ORDER BY p.updated_at DESC",
        (project_id,) if project_id is not None else ())
    projects = []
    for row in await cursor.fetchall():
        item = dict(row)
        item["published"] = item["episode_status"] == "published"
        item["step"] = next((key for key, _label, _page in STEPS if not item[key]), "published")
        projects.append(item)
    return projects


def _card(project: dict) -> dict:
    page = next(page for key, _label, page in STEPS if key == project["step"])
    link = page if project["step"] == "published" else f"{page}?project_id={project['id']}"
    return {"project_id": project["id"], "name": project["name"], "series": project["series_name"],
            "topic": project["topic_name"], "number": project["number"], "title": project["episode_title"],
            "publish_date": project["publish_date"], "step": project["step"], "link": link,
            "published": project["published"]}


def _step_number(key: str) -> int:
    """The page number of a production step: Config is Step 1, Script Step 2 … YouTube Step 7."""
    return next(index for index, (step, _label, _page) in enumerate(STEPS) if step == key) + 2


async def project_progress(db: aiosqlite.Connection, project_id: str) -> dict[str, Any] | None:
    """Phase 56 (ENH-038): which of the seven steps one project has done, for the step bar. None if it does not exist."""
    rows = await _project_steps(db, project_id)
    if not rows:
        return None
    project = rows[0]
    steps = [{"number": 1, "key": "config", "label": "Config", "path": "/step1", "done": True, "todo": None}]
    steps += [{"number": _step_number(key), "key": key, "label": label, "path": page, "done": bool(project[key]),
               "todo": None if project[key] else STEP_TODO[key]}
              for key, label, page in STEPS if key != "published"]
    first_open = next((step for step in steps if not step["done"]), None)
    return {"project_id": project_id, "name": project["name"], "steps": steps,
            "next_open": first_open["number"] if first_open else None}



async def _start(db: aiosqlite.Connection, projects: list[dict]) -> dict[str, Any]:
    """Phase 56 (ENH-038): the Dashboard's "Start here" -- the project to continue and the next planned episode."""
    unfinished = next((project for project in projects if project["step"] != "published"), None)
    continue_item = None
    if unfinished:
        label = next(label for key, label, _page in STEPS if key == unfinished["step"])
        continue_item = {"project_id": unfinished["id"], "name": unfinished["name"], "step": unfinished["step"],
                         "step_number": _step_number(unfinished["step"]), "step_label": label,
                         "link": _card(unfinished)["link"]}
    cursor = await db.execute(
        "SELECT e.number, e.title, e.publish_date, s.id AS series_id, s.name AS series, t.name AS topic "
        "FROM channel_episodes e JOIN channel_series s ON s.id = e.series_id JOIN channel_topics t ON t.id = s.topic_id "
        "WHERE e.project_id IS NULL AND e.status = 'planned' "
        "ORDER BY e.publish_date IS NULL, e.publish_date, t.position, s.position, e.number LIMIT 1")
    row = await cursor.fetchone()
    next_episode = None
    if row:
        next_episode = dict(row)
        next_episode["link"] = f"/channel#series-{row['series_id']}"
    return {"continue": continue_item, "next_episode": next_episode,
            "has_plan": await _scalar(db, "SELECT COUNT(*) FROM channel_topics") > 0}


async def dashboard(db: aiosqlite.Connection, today: date | None = None) -> dict[str, Any]:
    from backend.library import character_profile_service as profiles

    today = today or date.today()
    projects = await _project_steps(db)
    by_project = {project["id"]: project for project in projects}

    # ---- stats
    topics = await _scalar(db, "SELECT COUNT(*) FROM channel_topics")
    series = await _scalar(db, "SELECT COUNT(*) FROM channel_series")
    cursor = await db.execute("SELECT status, COUNT(*) FROM channel_episodes GROUP BY status")
    episodes = {status: 0 for status in ("planned", "created", "published")}
    episodes.update({row[0]: row[1] for row in await cursor.fetchall()})
    produced = sum(1 for project in projects if project["youtube"] and project["video"])
    stats = {"topics": topics, "series": series, "episodes": episodes, "projects": len(projects), "produced": produced}

    cursor = await db.execute(
        "SELECT e.id, e.number, e.title, e.publish_date, e.status, e.project_id, s.name AS series, t.name AS topic "
        "FROM channel_episodes e JOIN channel_series s ON s.id = e.series_id JOIN channel_topics t ON t.id = s.topic_id "
        "WHERE e.publish_date IS NOT NULL ORDER BY e.publish_date, t.position, s.position, e.number")
    dated = [dict(row) for row in await cursor.fetchall()]
    upcoming = [episode for episode in dated if episode["status"] != "published" and episode["publish_date"] >= today.isoformat()]
    next_publish = upcoming[0] if upcoming else None

    # ---- today's actions
    actions: list[dict] = []
    soon = (today + timedelta(days=7)).isoformat()
    for episode in upcoming:
        if episode["publish_date"] > soon:
            break
        project = by_project.get(episode["project_id"]) if episode["project_id"] else None
        if project is None:
            actions.append({"label": f"{episode['series']} · Ep. {episode['number']} goes out {episode['publish_date']}: "
                                     "create its project", "link": "/channel", "kind": "due"})
        elif project["step"] != "published":
            label = next(label for key, label, _page in STEPS if key == project["step"])
            actions.append({"label": f"{episode['series']} · Ep. {episode['number']} goes out {episode['publish_date']}: "
                                     f"next step {label}", "link": _card(project)["link"], "kind": "due"})
    pending = await _scalar(db, "SELECT COUNT(*) FROM activity_library WHERE review_state = 'pending'")
    if pending:
        actions.append({"label": f"{pending} illustration{'s' if pending != 1 else ''} waiting for your approval",
                        "link": "/activities", "kind": "review"})
    cursor = await db.execute("SELECT name FROM channel_series WHERE json_array_length(cast_json) < 2 ORDER BY position")
    no_cast = [row[0] for row in await cursor.fetchall()]
    if no_cast:
        actions.append({"label": f"Choose the characters of {len(no_cast)} series ({', '.join(no_cast[:3])}"
                                 f"{'…' if len(no_cast) > 3 else ''})", "link": "/channel", "kind": "plan"})

    # ---- roadmap (D107)
    character_rows = await profiles.list_profiles(db)
    video_ready = sum(1 for profile in character_rows if profile.get("readiness", {}).get("video_ready"))
    talking_ready = sum(1 for profile in character_rows if profile.get("readiness", {}).get("talking_ready"))
    music = await _scalar(db, "SELECT COUNT(*) FROM music_tracks")
    topics_without_series = await _scalar(
        db, "SELECT COUNT(*) FROM channel_topics t WHERE NOT EXISTS (SELECT 1 FROM channel_series s WHERE s.topic_id = t.id)")
    topics_without_playlist = await _scalar(db, "SELECT COUNT(*) FROM channel_topics WHERE playlist_url = ''")
    published = episodes["published"]
    recent = sum(1 for episode in dated if episode["status"] == "published"
                 and (today - timedelta(days=14)).isoformat() <= episode["publish_date"] <= today.isoformat())
    ahead_dates = sum(1 for episode in upcoming if episode["publish_date"] <= (today + timedelta(days=14)).isoformat())
    ahead_produced = sum(1 for project in projects if project["episode_id"] and not project["published"]
                         and project["youtube"] and project["video"])
    cursor = await db.execute(
        "SELECT t.name, SUM(e.status = 'published') FROM channel_topics t LEFT JOIN channel_series s ON s.topic_id = t.id "
        "LEFT JOIN channel_episodes e ON e.series_id = s.id GROUP BY t.id")
    per_topic = [(row[0], int(row[1] or 0)) for row in await cursor.fetchall()]
    first_complete = any(project["youtube"] and project["video"] for project in projects)
    stages = [
        {"key": "identity", "title": "Channel identity", "checks": [
            _check("Channel logo", LOGO.is_file(), "/settings"),
            _check("Two characters ready for videos", video_ready >= 2, "/characters", f"{min(video_ready, 2)}/2"),
            _check("Two talking characters (sprites)", talking_ready >= 2, "/characters", f"{min(talking_ready, 2)}/2"),
            _check("Three music tracks", music >= 3, "/music", f"{min(music, 3)}/3"),
        ]},
        {"key": "plan", "title": "Channel plan", "checks": [
            _check("Three topics (playlists)", topics >= 3, "/channel", f"{min(topics, 3)}/3"),
            _check("Every topic has a series", topics > 0 and topics_without_series == 0, "/channel"),
            _check("Every series has its characters", series > 0 and not no_cast, "/channel"),
            _check("Playlist links on the topics", topics > 0 and topics_without_playlist == 0, "/channel"),
            _check("Publishing dates planned", bool(dated), "/channel"),
        ]},
        {"key": "first10", "title": f"First {GOAL_FIRST} episodes", "checks": [
            _check("First episode complete (video + YouTube package)", first_complete, "/"),
            _check(f"{GOAL_FIRST} episodes produced", produced >= GOAL_FIRST, "/", f"{min(produced, GOAL_FIRST)}/{GOAL_FIRST}"),
            _check(f"{GOAL_FIRST} episodes published", published >= GOAL_FIRST, "/channel",
                   f"{min(published, GOAL_FIRST)}/{GOAL_FIRST}"),
        ]},
        {"key": "weekly", "title": "Weekly rhythm", "checks": [
            _check("Three episodes published in the last two weeks", recent >= 3, "/channel", f"{min(recent, 3)}/3"),
            _check("Three episodes dated in the next two weeks", ahead_dates >= 3, "/channel", f"{min(ahead_dates, 3)}/3"),
            _check("Three episodes produced ahead", ahead_produced >= 3, "/", f"{min(ahead_produced, 3)}/3"),
        ]},
        {"key": "grow", "title": "Grow the channel", "checks": [
            _check(f"{GOAL_GROW} episodes published", published >= GOAL_GROW, "/channel",
                   f"{min(published, GOAL_GROW)}/{GOAL_GROW}"),
            _check("Every topic has five published episodes", bool(per_topic) and all(count >= 5 for _n, count in per_topic),
                   "/channel"),
            _check("Shorts and TikTok clips (coming in Phase 37)", False, "/"),
        ]},
    ]
    for stage in stages:
        stage["done"] = all(check["done"] for check in stage["checks"])
        stage["progress"] = f"{sum(check['done'] for check in stage['checks'])}/{len(stage['checks'])}"
    current = next((index for index, stage in enumerate(stages) if not stage["done"]), len(stages) - 1)
    next_check = next((check for check in stages[current]["checks"] if not check["done"]), None)
    roadmap = {"stages": stages, "current": current,
               "next": {"label": next_check["label"], "link": next_check["link"]} if next_check else None}

    # ---- the production board (D108) and the next two weeks
    columns = [{"key": key, "label": label, "items": []} for key, label, _page in STEPS]
    for project in projects:
        if project["step"] == "published" and not project["episode_id"]:
            continue  # finished outside the channel plan: nothing left to do here
        next(column for column in columns if column["key"] == project["step"])["items"].append(_card(project))
    for column in columns:
        column["items"].sort(key=lambda item: (item["publish_date"] or "9999", item["series"] or "", item["number"] or 0))
    end = (today + timedelta(days=13)).isoformat()
    calendar = [episode for episode in dated if today.isoformat() <= episode["publish_date"] <= end]
    return {"stats": stats, "next_publish": next_publish, "actions": actions[:8], "roadmap": roadmap,
            "board": columns, "calendar": calendar, "today": today.isoformat(), "start": await _start(db, projects)}
