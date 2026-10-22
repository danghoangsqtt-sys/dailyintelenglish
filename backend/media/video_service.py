"""Renders a project's mixed audio into the episode MP4 with Remotion (the only video renderer since Phase 35, Task 35.5,
D89: the Standard ffmpeg background+subtitle renderer, its templates and the silent fallback were removed) and writes the
SRT subtitles beside it.

Only processes an already-completed audio mix (from AudioService, Task 1.6) — this module never generates audio itself,
mirroring the AudioService/TTSService responsibility split.
"""

import asyncio
import logging
import uuid
from datetime import datetime, timezone
from pathlib import Path

import aiosqlite

from backend.core.config import settings
from backend.core.exceptions import RemotionRenderFailedError, VideoRenderError
from backend.media import video_renderer_remotion

logger = logging.getLogger(__name__)

def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _format_srt_timestamp(seconds: float) -> str:
    """Format seconds as SRT's `HH:MM:SS,mmm` timestamp."""
    total_ms = round(seconds * 1000)
    hours, remainder = divmod(total_ms, 3_600_000)
    minutes, remainder = divmod(remainder, 60_000)
    secs, millis = divmod(remainder, 1_000)
    return f"{hours:02d}:{minutes:02d}:{secs:02d},{millis:03d}"


def generate_srt(timestamps: list[dict], offset_seconds: float = 0.0) -> str:
    """Build an SRT subtitle document from AudioService's real (measured) per-line timestamps.

    Each timestamp entry is `{start_sec, end_sec, label, speaker_id, text}` — see
    audio_service.py's `_mix_project_sync`. Cues are numbered sequentially starting at 1. `offset_seconds` shifts every cue
    (Task 35.5: the Remotion episode opens with the branded intro, so speech starts that much later in the video).
    """
    blocks = []
    for index, cue in enumerate(timestamps, start=1):
        text = cue.get("text") or ""
        label = cue.get("label")
        cue_text = f"{label}: {text}" if label else text
        blocks.append(
            f"{index}\n"
            f"{_format_srt_timestamp(cue['start_sec'] + offset_seconds)} --> "
            f"{_format_srt_timestamp(cue['end_sec'] + offset_seconds)}\n"
            f"{cue_text}\n"
        )
    return "\n".join(blocks)


def renderer_problem() -> str | None:
    """Why the video renderer cannot run on this machine (the first failing check), or None."""
    for passed, detail in (video_renderer_remotion.check_node_version(), video_renderer_remotion.check_video_renderer_deps(),
                           video_renderer_remotion.check_remotion_browser()):
        if not passed:
            return detail
    return None


def _write_srt_sync(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


async def generate_video(
    project_id: str,
    audio_job: dict | None,
    *,
    db: aiosqlite.Connection,
    project: dict,
    learning: dict | None = None,
    caption_style: str = "outline",
    visual_mode: str = "podcast_sprites",
    still_scene_id: str | None = None,
) -> dict:
    """Render a project's completed audio mix into the episode MP4 with Remotion, and write its SRT.

    Raises:
        VideoRenderError: If no completed audio mix exists yet, the renderer is not installed (the message names what is
            missing), or the render fails (the message carries Remotion's reason) -- there is no other renderer to fall back to.
    """
    if audio_job is None or audio_job.get("status") != "complete":
        raise VideoRenderError("Cannot generate video: the audio mix hasn't been generated yet.")
    problem = await asyncio.to_thread(renderer_problem)
    if problem:
        raise VideoRenderError(f"The video renderer is not ready: {problem}")
    output_dir = settings.DATA_DIR / "video" / project_id
    if project.get("_attempt_id"):
        output_dir /= project["_attempt_id"]
    try:
        # Phase 63 (ENH-045): a Short's main video is the vertical 9:16 one
        short = project.get("presentation_mode") == "solo_explainer" and project.get("explainer_style") in ("news", "blur")
        result = await video_renderer_remotion.render_via_remotion(
            db, project, audio_job, learning, output_dir / "video_remotion.mp4", caption_style=caption_style,
            visual_mode=visual_mode, still_scene_id=still_scene_id, **({"layout": "vertical"} if short else {}),
        )
    except RemotionRenderFailedError as exc:
        logger.warning("remotion_render_failed project_id=%s reason=%s", project_id, exc)
        raise VideoRenderError(f"The video could not be rendered: {exc}") from exc
    srt_path = output_dir / "subtitles.srt"
    srt = generate_srt(audio_job["timestamps"], offset_seconds=float(result.get("intro_seconds") or 0.0))
    await asyncio.to_thread(_write_srt_sync, srt_path, srt)
    return {**result, "srt_path": str(srt_path)}


async def render_vertical(
    project_id: str,
    audio_job: dict | None,
    *,
    db: aiosqlite.Connection,
    project: dict,
    learning: dict | None = None,
    caption_style: str = "outline",
    visual_mode: str = "podcast_sprites",
    still_scene_id: str | None = None,
    clip: dict | None = None,
    output_path: Path | None = None,
) -> dict:
    """Phase 37 (D98-D100): the whole episode in 1080x1920 for TikTok (`video_vertical.mp4`), or one highlight clip
    (`clip` = {line_from, line_to, hook}) for Shorts/TikTok. Same checks and errors as `generate_video`."""
    if audio_job is None or audio_job.get("status") != "complete":
        raise VideoRenderError("Cannot generate video: the audio mix hasn't been generated yet.")
    problem = await asyncio.to_thread(renderer_problem)
    if problem:
        raise VideoRenderError(f"The video renderer is not ready: {problem}")
    output = output_path or settings.DATA_DIR / "video" / project_id / "video_vertical.mp4"
    if project.get("_attempt_id"):
        output = output.parent / project["_attempt_id"] / output.name
    try:
        return await video_renderer_remotion.render_via_remotion(
            db, project, audio_job, learning, output, caption_style=caption_style, visual_mode=visual_mode,
            still_scene_id=still_scene_id, layout="vertical", clip=clip,
        )
    except RemotionRenderFailedError as exc:
        logger.warning("remotion_vertical_render_failed project_id=%s reason=%s", project_id, exc)
        raise VideoRenderError(f"The vertical video could not be rendered: {exc}") from exc


async def set_vertical_path(db: aiosqlite.Connection, project_id: str, path: str) -> None:
    await db.execute("UPDATE video_jobs SET mp4_path_vertical = ? WHERE project_id = ?", (path, project_id))


def _row_to_video_job(row: aiosqlite.Row) -> dict:
    return dict(row)


async def get_video_job(db: aiosqlite.Connection, project_id: str) -> dict | None:
    """Fetch a project's video job row, or None if video has never been generated."""
    cursor = await db.execute(
        "SELECT id, project_id, status, mode, mp4_path, mp4_path_vertical, srt_path, "
        "background_image, subtitle_style_json, error_message, started_at, completed_at "
        "FROM video_jobs WHERE project_id = ?",
        (project_id,),
    )
    row = await cursor.fetchone()
    return None if row is None else _row_to_video_job(row)


async def mark_video_job_failed(
    db: aiosqlite.Connection,
    project_id: str,
    error_message: str,
    commit: bool = True,
) -> dict:
    """Record a failed render without discarding a prior successful video."""
    now = _now()
    cursor = await db.execute(
        "UPDATE video_jobs SET status = 'error', error_message = ?, completed_at = ? "
        "WHERE project_id = ?",
        (error_message, now, project_id),
    )
    if cursor.rowcount == 0:
        await db.execute(
            "INSERT INTO video_jobs "
            "(id, project_id, status, error_message, started_at, completed_at) "
            "VALUES (?, ?, 'error', ?, ?, ?)",
            (str(uuid.uuid4()), project_id, error_message, now, now),
        )
    if commit:
        await db.commit()
    return await get_video_job(db, project_id)


async def save_video_job(
    db: aiosqlite.Connection,
    project_id: str,
    *,
    status: str,
    mode: str = "background",
    mp4_path: str | None = None,
    mp4_path_vertical: str | None = None,
    srt_path: str | None = None,
    background_image: str | None = None,
    error_message: str | None = None,
    commit: bool = True,
) -> dict:
    """Create or replace the video job row for a project (UPSERT on project_id)."""
    now = _now()
    completed_at = now if status in ("complete", "error") else None
    await db.execute(
        "INSERT INTO video_jobs "
        "(id, project_id, status, mode, mp4_path, mp4_path_vertical, srt_path, background_image, "
        "subtitle_style_json, error_message, started_at, completed_at) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?) "
        "ON CONFLICT(project_id) DO UPDATE SET "
        "status = excluded.status, mode = excluded.mode, mp4_path = excluded.mp4_path, "
        "mp4_path_vertical = excluded.mp4_path_vertical, "
        "srt_path = excluded.srt_path, background_image = excluded.background_image, "
        "error_message = excluded.error_message, started_at = excluded.started_at, "
        "completed_at = excluded.completed_at",
        (
            str(uuid.uuid4()),
            project_id,
            status,
            mode,
            mp4_path,
            mp4_path_vertical,
            srt_path,
            background_image,
            None,
            error_message,
            now,
            completed_at,
        ),
    )
    if commit:
        await db.commit()
    return await get_video_job(db, project_id)
