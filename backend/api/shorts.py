"""Phase 37 (D98-D101): highlight clips for YouTube Shorts and TikTok, and their covers and texts."""

import asyncio
import time
from pathlib import Path

import aiosqlite
from fastapi import APIRouter, Depends
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

from backend.core.config import settings
from backend.core.exceptions import NotFoundError, ValidationError
from backend.core.responses import ok
from backend.db.database import get_db
from backend.db.transactions import read_transaction, write_transaction
from backend.media import audio_service, video_service
from backend.content import learning_service, project_service, shorts_service, youtube_service

router = APIRouter(prefix="/api/projects/{project_id}/shorts", tags=["shorts"])


class ProposeRequest(BaseModel):
    count: int = Field(default=3, ge=1, le=3)


class ClipInput(BaseModel):
    line_from: int = Field(ge=0)
    line_to: int = Field(ge=0)
    hook: str = Field(min_length=1, max_length=80)


class RenderRequest(BaseModel):
    caption_style: str = "outline"
    visual_mode: str = "podcast_sprites"
    still_scene_id: str | None = None


async def _views(db: aiosqlite.Connection, project_id: str, clips: list[dict]) -> list[dict]:
    project = await project_service.get_project(db, project_id)
    learning = await learning_service.get_learning_content(db, project_id)
    audio = await audio_service.get_audio_job(db, project_id)
    timestamps = (audio or {}).get("timestamps") or []
    package = await youtube_service.get_package(db, project_id)
    hashtags = (package or {}).get("hashtags") or ["LearnEnglish", "EnglishConversation"]
    cursor = await db.execute("SELECT video_url FROM channel_episodes WHERE project_id = ?", (project_id,))
    row = await cursor.fetchone()
    full_url = (row[0] if row else "") or ""  # the published full episode, linked from the Short
    return [shorts_service.public(clip, project, learning, hashtags, full_url, timestamps) for clip in clips]


@router.get("")
async def list_clips(project_id: str, db: aiosqlite.Connection = Depends(get_db)) -> dict:
    async with read_transaction():
        await project_service.get_project(db, project_id)
        clips = await _views(db, project_id, await shorts_service.list_clips(db, project_id))
    return ok(clips)


@router.post("/propose")
async def propose(project_id: str, body: ProposeRequest, db: aiosqlite.Connection = Depends(get_db)) -> dict:
    """The AI's 1-3 highlight clips (30-90 s, complete, with a hook); they replace the clips not rendered yet."""
    started_at = time.perf_counter()
    async with write_transaction(db):
        clips = await shorts_service.propose(db, project_id, body.count)
        result = await _views(db, project_id, clips)
    return ok(result, started_at=started_at)


@router.post("")
async def create_clip(project_id: str, body: ClipInput, db: aiosqlite.Connection = Depends(get_db)) -> dict:
    async with write_transaction(db):
        clip = await shorts_service.create_clip(db, project_id, body.line_from, body.line_to, body.hook)
        result = (await _views(db, project_id, [clip]))[0]
    return ok(result)


@router.patch("/{clip_id}")
async def update_clip(project_id: str, clip_id: str, body: shorts_service.ClipPatch,
                      db: aiosqlite.Connection = Depends(get_db)) -> dict:
    async with write_transaction(db):
        clip = await shorts_service.update_clip(db, project_id, clip_id, body)
        result = (await _views(db, project_id, [clip]))[0]
    return ok(result)


@router.delete("/{clip_id}")
async def delete_clip(project_id: str, clip_id: str, db: aiosqlite.Connection = Depends(get_db)) -> dict:
    async with write_transaction(db):
        await shorts_service.delete_clip(db, project_id, clip_id)
    return ok({"deleted": clip_id})


@router.post("/{clip_id}/render")
async def render_clip(project_id: str, clip_id: str, body: RenderRequest, db: aiosqlite.Connection = Depends(get_db)) -> dict:
    """Render an approved clip (a frame range of the vertical episode) and its 9:16 cover."""
    started_at = time.perf_counter()
    async with read_transaction():
        project = await project_service.get_project(db, project_id)
        clip = await shorts_service.get_clip(db, project_id, clip_id)
        audio_job = await audio_service.get_audio_job(db, project_id)
        learning = await learning_service.get_learning_content(db, project_id)
    if clip["status"] == "proposed":
        raise ValidationError("Approve the clip before rendering it")
    output = shorts_service.clip_folder(project_id, clip_id) / "clip.mp4"
    result = await video_service.render_vertical(
        project_id, audio_job, db=db, project=project, learning=learning, caption_style=body.caption_style,
        visual_mode=body.visual_mode, still_scene_id=body.still_scene_id,
        clip={"line_from": clip["line_from"], "line_to": clip["line_to"], "hook": clip["hook"]}, output_path=output)
    async with read_transaction():
        cover = await shorts_service.render_cover(db, project, clip)
    async with write_transaction(db):
        await db.execute("UPDATE short_clips SET status = 'rendered', mp4_path = ?, cover_path = ?, updated_at = ? WHERE id = ?",
                         (result["mp4_path"], cover, shorts_service._now(), clip_id))
        view = (await _views(db, project_id, [await shorts_service.get_clip(db, project_id, clip_id)]))[0]
    return ok(view, started_at=started_at)


def _inside(path: str | None, project_id: str) -> Path:
    if not path:
        raise NotFoundError("Not rendered yet")
    candidate = Path(path).resolve()
    if not candidate.is_relative_to((settings.DATA_DIR / "video" / project_id).resolve()) or not candidate.is_file():
        raise NotFoundError("File not found")
    return candidate


@router.get("/{clip_id}/video.mp4")
async def clip_video(project_id: str, clip_id: str, db: aiosqlite.Connection = Depends(get_db)) -> FileResponse:
    async with read_transaction():
        clip = await shorts_service.get_clip(db, project_id, clip_id)
    path = await asyncio.to_thread(_inside, clip["mp4_path"], project_id)
    return FileResponse(path, media_type="video/mp4", filename=f"{clip_id}-short.mp4")


@router.get("/{clip_id}/cover.jpg")
async def clip_cover(project_id: str, clip_id: str, db: aiosqlite.Connection = Depends(get_db)) -> FileResponse:
    async with read_transaction():
        clip = await shorts_service.get_clip(db, project_id, clip_id)
    path = await asyncio.to_thread(_inside, clip["cover_path"], project_id)
    return FileResponse(path, media_type="image/jpeg", headers={"Cache-Control": "no-store"})
