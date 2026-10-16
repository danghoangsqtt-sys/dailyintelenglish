"""Phase 37 (D98-D101): highlight clips for YouTube Shorts and TikTok.

The AI proposes 1-3 complete passages of the episode (30-90 s, measured from the real audio timestamps) with a hook title;
the owner adjusts the first/last line and the hook, approves, and each approved clip renders as a frame range of the
vertical episode (`video_service.render_vertical`). Every clip gets a 9:16 cover (the episode's characters, its hook as the
headline) and separate Shorts and TikTok texts ready to paste.
"""

from __future__ import annotations

import asyncio
import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import aiosqlite
from jinja2 import Environment, FileSystemLoader, StrictUndefined
from pydantic import BaseModel, Field, TypeAdapter

from backend.core.config import settings
from backend.core.exceptions import NotFoundError, ProviderError, SchemaValidationError, ValidationError
from backend.core.paths import PROMPTS_DIR
from backend.ai.llm.contracts import GenerationRequest
from backend.ai.llm.router import AIRouter, build_ai_router_from_settings
from backend.ai.llm.validation import parse_and_validate

MIN_SECONDS, MAX_SECONDS = 30.0, 90.0
SHORTS_TITLE_LIMIT = 100
_env = Environment(loader=FileSystemLoader(str(PROMPTS_DIR / "shorts")), undefined=StrictUndefined)


class ProposedClip(BaseModel):
    line_from: int = Field(ge=0)
    line_to: int = Field(ge=0)
    hook: str = Field(min_length=1, max_length=80)
    reason: str = Field(default="", max_length=300)


class ClipProposal(BaseModel):
    clips: list[ProposedClip] = Field(min_length=1, max_length=5)


class ClipPatch(BaseModel):
    line_from: int | None = Field(default=None, ge=0)
    line_to: int | None = Field(default=None, ge=0)
    hook: str | None = Field(default=None, min_length=1, max_length=80)
    status: str | None = None


_PROPOSAL = TypeAdapter(ClipProposal)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def clip_seconds(timestamps: list[dict], line_from: int, line_to: int) -> float:
    return float(timestamps[line_to]["end_sec"]) - float(timestamps[line_from]["start_sec"])


def check_range(timestamps: list[dict], line_from: int, line_to: int) -> None:
    """A clip is consecutive lines that exist, 30-90 s long."""
    if not 0 <= line_from <= line_to < len(timestamps):
        raise ValidationError("The clip's first and last lines must be lines of the script, in order")
    seconds = clip_seconds(timestamps, line_from, line_to)
    if not MIN_SECONDS <= seconds <= MAX_SECONDS:
        raise ValidationError(f"A clip lasts {MIN_SECONDS:.0f}-{MAX_SECONDS:.0f} s; this one is {seconds:.1f} s")


def valid_clips(proposal: ClipProposal, timestamps: list[dict]) -> list[ProposedClip]:
    """Keep the proposed clips that are in range, 30-90 s long and do not overlap an earlier one."""
    kept: list[ProposedClip] = []
    for clip in proposal.clips:
        try:
            check_range(timestamps, clip.line_from, clip.line_to)
        except ValidationError:
            continue
        if any(clip.line_from <= other.line_to and other.line_from <= clip.line_to for other in kept):
            continue
        kept.append(clip)
    return kept


async def _context(db: aiosqlite.Connection, project_id: str) -> tuple[dict, list[dict], list[dict], dict | None]:
    from backend.media import audio_service
    from backend.content import learning_service, project_service

    project = await project_service.get_project(db, project_id)
    audio = await audio_service.get_audio_job(db, project_id)
    if audio is None or audio.get("status") != "complete" or not audio.get("timestamps"):
        raise ValidationError("Generate the episode audio first: clips are cut from its measured timings")
    learning = await learning_service.get_learning_content(db, project_id)
    return project, audio["timestamps"], audio, learning


async def list_clips(db: aiosqlite.Connection, project_id: str) -> list[dict]:
    cursor = await db.execute("SELECT * FROM short_clips WHERE project_id = ? ORDER BY line_from", (project_id,))
    return [dict(row) for row in await cursor.fetchall()]


async def get_clip(db: aiosqlite.Connection, project_id: str, clip_id: str) -> dict:
    cursor = await db.execute("SELECT * FROM short_clips WHERE id = ? AND project_id = ?", (clip_id, project_id))
    row = await cursor.fetchone()
    if row is None:
        raise NotFoundError("Clip not found")
    return dict(row)


def normalize_proposal(parsed: object) -> object:
    """Real-AI lesson: accept `start_line`/`end_line`, `from`/`to`, `title` for the documented names."""
    if not isinstance(parsed, dict) or not isinstance(parsed.get("clips"), list):
        return parsed
    fixed = []
    for clip in parsed["clips"]:
        if isinstance(clip, dict):
            fixed.append({"line_from": clip.get("line_from", clip.get("start_line", clip.get("from"))),
                          "line_to": clip.get("line_to", clip.get("end_line", clip.get("to"))),
                          "hook": clip.get("hook") or clip.get("title") or "", "reason": clip.get("reason") or ""})
    return {"clips": fixed}


async def propose(db: aiosqlite.Connection, project_id: str, count: int = 3, router: AIRouter | None = None) -> list[dict]:
    """The AI's clips replace the not-yet-rendered ones; rendered clips stay."""
    project, timestamps, _audio, learning = await _context(db, project_id)
    names = {speaker["id"]: speaker["name"] for speaker in project["speakers"]}
    lines = [{"index": index, "start": float(stamp["start_sec"]), "end": float(stamp["end_sec"]),
              "speaker": stamp.get("label") or names.get(stamp.get("speaker_id"), ""), "text": stamp.get("text") or ""}
             for index, stamp in enumerate(timestamps)]
    words = [item["word"] for item in (learning or {}).get("vocabulary", [])] + \
        [item["phrase"] for section in ("idioms", "collocations", "phrasal_verbs") for item in (learning or {}).get(section, [])]
    prompt = await asyncio.to_thread(_env.get_template("clip_proposal.txt").render, topic=project["topic"],
                                     cefr_level=project["cefr_level"], lines=lines, learning=words, count=count,
                                     min_seconds=int(MIN_SECONDS), max_seconds=int(MAX_SECONDS))
    router = router or build_ai_router_from_settings()
    try:
        result = await router.generate(GenerationRequest(prompt=prompt, json_schema=ClipProposal.model_json_schema(),
                                                         deadline_seconds=settings.AI_REQUEST_DEADLINE_SECONDS,
                                                         purpose="short_clips"))
    except ProviderError as exc:
        raise ValidationError(f"The AI could not propose clips right now ({type(exc).__name__}); try again") from exc
    text = result.text
    try:
        text = json.dumps(normalize_proposal(json.loads(text)))
    except (json.JSONDecodeError, TypeError):
        pass
    try:
        proposal = parse_and_validate(text, _PROPOSAL)
    except SchemaValidationError as exc:
        raise ValidationError(f"The AI's clips were not usable ({exc}); try again") from exc
    clips = valid_clips(proposal, timestamps)
    if not clips:
        raise ValidationError("The AI found no complete 30-90 s passage; try again or make one by hand")
    await db.execute("DELETE FROM short_clips WHERE project_id = ? AND status != 'rendered'", (project_id,))
    now = _now()
    for clip in clips:
        await db.execute(
            "INSERT INTO short_clips (id, project_id, line_from, line_to, hook, reason, created_at, updated_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (str(uuid.uuid4()), project_id, clip.line_from, clip.line_to, clip.hook.strip(), clip.reason.strip(), now, now))
    return await list_clips(db, project_id)


async def create_clip(db: aiosqlite.Connection, project_id: str, line_from: int, line_to: int, hook: str) -> dict:
    _project, timestamps, _audio, _learning = await _context(db, project_id)
    check_range(timestamps, line_from, line_to)
    clip_id, now = str(uuid.uuid4()), _now()
    await db.execute("INSERT INTO short_clips (id, project_id, line_from, line_to, hook, created_at, updated_at) "
                     "VALUES (?, ?, ?, ?, ?, ?, ?)", (clip_id, project_id, line_from, line_to, hook.strip(), now, now))
    return await get_clip(db, project_id, clip_id)


async def update_clip(db: aiosqlite.Connection, project_id: str, clip_id: str, patch: ClipPatch) -> dict:
    clip = await get_clip(db, project_id, clip_id)
    fields = patch.model_dump(exclude_unset=True, exclude_none=True)
    if "status" in fields and fields["status"] not in ("proposed", "approved"):
        raise ValidationError("A clip can be proposed or approved; rendering sets it rendered")
    if "line_from" in fields or "line_to" in fields:
        _project, timestamps, _audio, _learning = await _context(db, project_id)
        check_range(timestamps, fields.get("line_from", clip["line_from"]), fields.get("line_to", clip["line_to"]))
        fields.setdefault("status", "proposed")  # a changed passage is approved again before rendering
    if fields.get("hook"):
        fields["hook"] = fields["hook"].strip()
    if fields:
        await db.execute("UPDATE short_clips SET " + ", ".join(f"{key} = ?" for key in fields) + ", updated_at = ? WHERE id = ?",
                         (*fields.values(), _now(), clip_id))
    return await get_clip(db, project_id, clip_id)


async def delete_clip(db: aiosqlite.Connection, project_id: str, clip_id: str) -> None:
    await get_clip(db, project_id, clip_id)
    await db.execute("DELETE FROM short_clips WHERE id = ?", (clip_id,))


def clip_folder(project_id: str, clip_id: str) -> Path:
    return settings.DATA_DIR / "video" / project_id / "shorts" / clip_id


async def render_cover(db: aiosqlite.Connection, project: dict, clip: dict) -> str:
    """The clip's 9:16 cover: the episode's composed thumbnail with the hook as its headline."""
    from backend.schemas.thumbnail import ThumbnailSuggestion
    from backend.media import thumbnail_compose

    from backend.db.transactions import read_transaction

    async with read_transaction():
        inputs = await thumbnail_compose.composition_inputs(db, project)
    suggestion = ThumbnailSuggestion.model_validate({
        "headline": clip["hook"][:80], "supporting_text": f"{project['cefr_level'].upper()} English", "topic_keywords": ["english"],
        "palette": {"primary": "#0E5E3A", "secondary": "#2BB673", "accent": "#FFD23F", "text": "#FFFFFF"}})
    folder = clip_folder(project["id"], clip["id"])
    if project.get("_attempt_id"):
        folder /= project["_attempt_id"]
    path = folder / "cover.jpg"

    def draw() -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        thumbnail_compose.render(inputs, suggestion, "9x16", 0, "composed").save(path, quality=90)

    await asyncio.to_thread(draw)
    return str(path)


# ---------------------------------------------------------------- the texts (D101)

def _learning_lines(learning: dict | None, count: int = 3) -> list[str]:
    items = [f"{item['word']} — {item['definition_vi']}" for item in (learning or {}).get("vocabulary", [])]
    items += [f"{item['phrase']} — {item['meaning_vi']}" for section in ("idioms", "collocations", "phrasal_verbs")
              for item in (learning or {}).get(section, [])]
    return items[:count]


def packages(project: dict, clip: dict, learning: dict | None, hashtags: list[str], full_video_url: str = "") -> dict:
    """Separate texts for YouTube Shorts and TikTok: Shorts has a title (with #Shorts), a short description with three
    learning items, the full episode's link and hashtags; TikTok has one caption with a hook and at most five hashtags."""
    hook = clip["hook"].strip()
    title = f"{hook} #Shorts"
    if len(title) > SHORTS_TITLE_LIMIT:
        title = f"{hook[:SHORTS_TITLE_LIMIT - 9].rstrip()} #Shorts"
    learn = _learning_lines(learning)
    tags = [tag for tag in hashtags if tag.lower() != "shorts"]
    description = [f"{hook} — English conversation ({project['cefr_level'].upper()}) from Daily Beyond English."]
    if learn:
        description.append("📚 Learn:\n" + "\n".join(f"• {line}" for line in learn))
    description.append(f"▶️ Full episode: {full_video_url}" if full_video_url else "▶️ Full episode on our channel.")
    description.append(" ".join(["#Shorts", *[f"#{tag}" for tag in tags[:6]]]))
    tiktok_tags = ["LearnEnglish", "EnglishTips", *[tag for tag in tags if tag not in ("LearnEnglish", "EnglishTips")]][:5]
    caption = [f"{hook} 🎧", f"Learn real English ({project['cefr_level'].upper()}) in under a minute."]
    if learn:
        caption.append(f"Today: {learn[0]}")
    caption.append(" ".join(f"#{tag}" for tag in tiktok_tags))
    return {"shorts": {"title": title, "description": "\n\n".join(description)}, "tiktok": {"caption": "\n".join(caption)}}


def public(clip: dict, project: dict, learning: dict | None, hashtags: list[str], full_video_url: str,
           timestamps: list[dict]) -> dict[str, Any]:
    base = f"/api/projects/{project['id']}/shorts/{clip['id']}"
    return {**{key: clip[key] for key in ("id", "line_from", "line_to", "hook", "reason", "status")},
            "seconds": round(clip_seconds(timestamps, clip["line_from"], clip["line_to"]), 1)
            if clip["line_to"] < len(timestamps) else None,
            "video_url": f"{base}/video.mp4" if clip["mp4_path"] else None,
            "cover_url": f"{base}/cover.jpg" if clip["cover_path"] else None,
            "packages": packages(project, clip, learning, hashtags, full_video_url)}
