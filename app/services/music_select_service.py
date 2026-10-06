"""Task 22.8 (D51): pick a library track for an episode by topic and length.

A deterministic score ranks every track (genre -> mood, topic words -> tags/title, length fit,
recent use); with two or more candidates the AI chooses among the top few from the topic. The AI
answer must be one of those filenames (one repair, else the top score), so the result is always a
real library file and the reason can always be shown.
"""

from __future__ import annotations

import json
import math
import re
from typing import Any

import aiosqlite

from app.core.config import settings
from app.core.exceptions import ProviderError, SchemaValidationError
from app.core.prompt_loader import render_music_pick_prompt
from app.db.transactions import read_transaction
from app.models.music import GENRE_MOODS, GENRE_PACES, MOODS, PACES
from app.services import music_library_service as library
from app.services import project_service
from app.services.ai.contracts import GenerationRequest
from app.services.ai.router import AIRouter, build_ai_router_from_settings

VIDEO_EXTRA_SECONDS = 7.5  # the Enhanced intro + outro (2.5 + 5.0), the longest video either renderer makes
TOP_CANDIDATES = 5
RECENT_EPISODES = 3
MAX_TOPIC_POINTS = 3
STOPWORDS = {
    "the", "and", "for", "you", "your", "with", "what", "how", "why", "who", "when", "where", "are", "was",
    "were", "this", "that", "from", "about", "into", "have", "has", "had", "does", "did", "its", "our",
    "their", "they", "them", "can", "will", "would", "should", "could", "best", "way", "new", "day",
}


def _words(text: str | None) -> set[str]:
    words = set()
    for word in re.findall(r"[a-z]+", (text or "").lower()):
        if len(word) >= 3 and word not in STOPWORDS:
            words.add(word[:-1] if len(word) > 4 and word.endswith("s") else word)
    return words


def format_length(seconds: float | None) -> str:
    if seconds is None:
        return "unknown length"
    total = round(seconds)
    return f"{total // 60}:{total % 60:02d}"


async def target_seconds(db: aiosqlite.Connection, project: dict[str, Any]) -> float:
    cursor = await db.execute(
        "SELECT duration_seconds FROM audio_jobs WHERE project_id = ? AND status = 'complete'", (project["id"],),
    )
    row = await cursor.fetchone()
    speech = row[0] if row and row[0] else float(project["duration_minutes"]) * 60
    return round(speech + VIDEO_EXTRA_SECONDS, 2)


async def recent_tracks(db: aiosqlite.Connection, project_id: str) -> set[str]:
    cursor = await db.execute(
        "SELECT background_music FROM audio_jobs WHERE project_id != ? AND status = 'complete' "
        "AND background_music IS NOT NULL ORDER BY completed_at DESC LIMIT ?",
        (project_id, RECENT_EPISODES),
    )
    return {row[0] for row in await cursor.fetchall()}


def score(track: dict[str, Any], genre: str, topic: str, target: float, recent: set[str]) -> dict[str, Any]:
    """Pure: the score and its parts, so the choice can be explained."""
    preferred = GENRE_MOODS.get(genre, ())
    mood = track.get("effective_mood", track.get("mood"))  # Task 22.9: the owner's mood, else the analysed one
    mood_points = 3 - preferred.index(mood) if mood in preferred else 0
    paces = GENRE_PACES.get(genre, ())
    pace = track.get("pace")
    rhythm_points = 2 - paces.index(pace) if pace in paces else 0
    matched = sorted(_words(topic) & (_words(track.get("tags")) | _words(track.get("title"))))
    topic_points = min(MAX_TOPIC_POINTS, len(matched))
    duration = track.get("duration_s")
    if not duration:
        length_points, loops = -2.0, None
    else:
        loops = max(1, math.ceil(target / duration))
        # Many repeats of a short track sound repetitive (a 68 s jingle x9 under a 10-minute talk was
        # picked in the 22.9 real check), so the penalty grows with the loops, down to -3.
        length_points = 2.0 if loops == 1 else max(-3.0, -0.5 * (loops - 1))
    recent_points = -1.5 if track["filename"] in recent else 0.0
    return {
        "filename": track["filename"], "title": track["title"], "mood": mood, "tags": track.get("tags"),
        "duration_s": duration, "length": format_length(duration), "loops": loops, "matched_words": matched,
        "fit": "covers the video" if loops == 1 else (f"loops {loops} times" if loops else "length unknown"),
        "pace": pace, "bpm": track.get("bpm"),
        "parts": {"mood": mood_points, "rhythm": rhythm_points, "topic": topic_points, "length": length_points,
                  "recent": recent_points},
        "score": mood_points + rhythm_points + topic_points + length_points + recent_points,
    }


def rule_reason(best: dict[str, Any], genre: str) -> str:
    bits = []
    if best["parts"]["mood"]:
        bits.append(f"{MOODS[best['mood']]} suits {genre.replace('_', ' ')} episodes")
    if best["parts"].get("rhythm"):
        bits.append(f"{PACES[best['pace']].lower()} fits the rhythm of the talk")
    if best["matched_words"]:
        bits.append(f"tags match the topic ({', '.join(best['matched_words'])})")
    if best["loops"] == 1:
        bits.append("long enough for the whole video")
    elif best["loops"]:
        bits.append(f"loops {best['loops']} times to cover the video")
    if best["parts"]["recent"]:
        bits.append("used recently, but still the best fit")
    return "; ".join(bits) or "the only usable track"


def pick_schema(filenames: list[str]) -> dict:
    return {"type": "object", "properties": {"filename": {"type": "string", "enum": filenames},
                                              "reason": {"type": "string"}}, "required": ["filename", "reason"]}


def parse_pick(text: str, filenames: list[str]) -> tuple[str, str]:
    try:
        parsed = json.loads(text)
    except json.JSONDecodeError as exc:
        raise SchemaValidationError(f"the answer is not valid JSON ({exc.msg})") from exc
    if not isinstance(parsed, dict):
        raise SchemaValidationError("the answer must be a JSON object with filename and reason")
    filename = str(parsed.get("filename", "")).strip()
    if filename not in filenames:
        raise SchemaValidationError("filename is not one of the candidate filenames")
    reason = " ".join(str(parsed.get("reason", "")).split())[:200]
    return filename, reason


async def suggest(db: aiosqlite.Connection, project_id: str, router: AIRouter | None = None) -> dict[str, Any]:
    async with read_transaction():
        project = await project_service.get_project(db, project_id)
        target = await target_seconds(db, project)
        recent = await recent_tracks(db, project_id)
    tracks = await library.list_tracks(db)
    ranked = sorted((score(track, project["genre"], project["topic"], target, recent) for track in tracks),
                    key=lambda item: (-item["score"], item["title"].lower()))
    candidates = ranked[:TOP_CANDIDATES]
    result: dict[str, Any] = {"target_s": target, "candidates": candidates, "filename": None, "title": None,
                              "reason": "The Music Library is empty.", "path": "none"}
    if not candidates:
        return result
    best = candidates[0]
    result.update(filename=best["filename"], title=best["title"], reason=rule_reason(best, project["genre"]),
                  path="single" if len(candidates) == 1 else "rule")
    if len(candidates) == 1:
        return result
    filenames = [item["filename"] for item in candidates]
    router = router or build_ai_router_from_settings()
    previous_error = ""
    for attempt in range(2):
        prompt = await render_music_pick_prompt(
            topic=project["topic"], genre=project["genre"], cefr_level=project["cefr_level"],
            target_minutes=round(target / 60, 1), candidates=candidates, previous_error=previous_error,
        )
        request = GenerationRequest(prompt=prompt, json_schema=pick_schema(filenames),
                                    deadline_seconds=settings.AI_REQUEST_DEADLINE_SECONDS, purpose="music_pick")
        try:
            answer = await router.generate(request)
        except ProviderError as exc:
            result["ai_error"] = f"AI unavailable ({type(exc).__name__})"
            break
        try:
            filename, reason = parse_pick(answer.text, filenames)
        except SchemaValidationError as exc:
            previous_error = result["ai_error"] = str(exc)
            continue
        chosen = next(item for item in candidates if item["filename"] == filename)
        result.update(filename=filename, title=chosen["title"], reason=reason or rule_reason(chosen, project["genre"]),
                      path="ai" if attempt == 0 else "ai_repaired")
        result.pop("ai_error", None)
        break
    return result

