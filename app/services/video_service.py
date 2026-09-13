"""Renders a project's mixed audio into an MP4 with a background image and burned-in
subtitles (Task 1.7, Sub-task 1.7a — "Level 2" background+subtitle path).

Level 3 (LivePortrait avatar lip-sync) is deliberately not implemented here: it needs a
real per-speaker avatar image, and no speaker has one (`speakers.avatar_image_path` is
null, no upload feature exists) — the same class of blocker OmniVoice's `ref_audio` hit,
requiring a real user decision on where avatar images come from before writing that code.

Only processes an already-completed audio mix (from AudioService, Task 1.6) — this module
never generates audio itself, mirroring the AudioService/TTSService responsibility split.
"""

import asyncio
import subprocess
import uuid
from datetime import datetime, timezone
from pathlib import Path

import aiosqlite

from app.core.config import settings
from app.core.constants import VIDEO_TEMPLATE_IDS, VIDEO_TEMPLATE_LABELS
from app.core.exceptions import VideoRenderError

TEMPLATE_DIR = Path(__file__).resolve().parent.parent.parent / "frontend" / "static" / "video_backgrounds"


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def list_video_templates() -> list[dict]:
    """Report the fixed set of pre-rendered background templates (no custom upload yet)."""
    return [
        {
            "id": template_id,
            "display_name": VIDEO_TEMPLATE_LABELS[template_id],
            "preview_url": f"/static/video_backgrounds/{template_id}.png",
        }
        for template_id in VIDEO_TEMPLATE_IDS
    ]


def _format_srt_timestamp(seconds: float) -> str:
    """Format seconds as SRT's `HH:MM:SS,mmm` timestamp."""
    total_ms = round(seconds * 1000)
    hours, remainder = divmod(total_ms, 3_600_000)
    minutes, remainder = divmod(remainder, 60_000)
    secs, millis = divmod(remainder, 1_000)
    return f"{hours:02d}:{minutes:02d}:{secs:02d},{millis:03d}"


def generate_srt(timestamps: list[dict]) -> str:
    """Build an SRT subtitle document from AudioService's real (measured) per-line timestamps.

    Each timestamp entry is `{start_sec, end_sec, label, speaker_id, text}` — see
    audio_service.py's `_mix_project_sync`. Cues are numbered sequentially starting at 1.
    """
    blocks = []
    for index, cue in enumerate(timestamps, start=1):
        text = cue.get("text") or ""
        label = cue.get("label")
        cue_text = f"{label}: {text}" if label else text
        blocks.append(
            f"{index}\n"
            f"{_format_srt_timestamp(cue['start_sec'])} --> {_format_srt_timestamp(cue['end_sec'])}\n"
            f"{cue_text}\n"
        )
    return "\n".join(blocks)


def _escape_ffmpeg_filter_path(path: str) -> str:
    """Escape a path for use inside an ffmpeg filtergraph value (e.g. `subtitles=...`).

    ffmpeg's filter parser treats `:` as a key=value separator and `\\` as an escape
    character, so a Windows absolute path (`C:\\Users\\...`) must have both escaped before
    being wrapped in quotes — confirmed against the real installed ffmpeg build, not
    assumed from documentation alone.
    """
    return path.replace("\\", "\\\\").replace(":", "\\:")


def _render_video_sync(background_path: Path, audio_path: str, srt_path: Path, output_path: Path) -> None:
    """Blocking ffmpeg subprocess call — must run in a thread (asyncio.to_thread), never
    on the event loop directly (this task's Forbidden Scope)."""
    vf = f"subtitles='{_escape_ffmpeg_filter_path(str(srt_path))}'"
    command = [
        settings.FFMPEG_PATH,
        "-y",
        "-loop", "1",
        "-i", str(background_path),
        "-i", audio_path,
        "-vf", vf,
        "-c:v", "libx264",
        "-tune", "stillimage",
        "-c:a", "aac",
        "-b:a", "192k",
        "-pix_fmt", "yuv420p",
        "-shortest",
        str(output_path),
    ]
    result = subprocess.run(command, capture_output=True, text=True)
    if result.returncode != 0:
        raise VideoRenderError(f"ffmpeg video render failed: {result.stderr[-500:]}")


async def generate_video(project_id: str, audio_job: dict | None, template_id: str) -> dict:
    """Render a project's completed audio mix into an MP4 with a background + burned-in subtitles.

    Args:
        project_id: Project UUID.
        audio_job: The project's `audio_jobs` row (from `audio_service.get_audio_job`).
        template_id: One of `VIDEO_TEMPLATE_IDS`.

    Raises:
        VideoRenderError: If no completed audio mix exists yet, or ffmpeg fails.
    """
    if audio_job is None or audio_job.get("status") != "complete":
        raise VideoRenderError("Cannot generate video: the audio mix hasn't been generated yet.")

    background_path = TEMPLATE_DIR / f"{template_id}.png"
    if not background_path.is_file():
        raise VideoRenderError(f"Background template not found: {template_id}")

    output_dir = settings.DATA_DIR / "video" / project_id
    output_dir.mkdir(parents=True, exist_ok=True)
    srt_path = output_dir / "subtitles.srt"
    srt_path.write_text(generate_srt(audio_job["timestamps"]), encoding="utf-8")
    mp4_path = output_dir / "video.mp4"

    try:
        await asyncio.to_thread(_render_video_sync, background_path, audio_job["mp3_path"], srt_path, mp4_path)
    except VideoRenderError:
        raise
    except Exception as exc:
        raise VideoRenderError(f"Video rendering failed: {exc}") from exc

    return {"mp4_path": str(mp4_path), "srt_path": str(srt_path), "background_image": template_id}


def _row_to_video_job(row: aiosqlite.Row) -> dict:
    return dict(row)


async def get_video_job(db: aiosqlite.Connection, project_id: str) -> dict | None:
    """Fetch a project's video job row, or None if video has never been generated."""
    cursor = await db.execute(
        "SELECT id, project_id, status, mode, mp4_path, srt_path, background_image, "
        "subtitle_style_json, error_message, started_at, completed_at "
        "FROM video_jobs WHERE project_id = ?",
        (project_id,),
    )
    row = await cursor.fetchone()
    return None if row is None else _row_to_video_job(row)


async def save_video_job(
    db: aiosqlite.Connection,
    project_id: str,
    *,
    status: str,
    mode: str = "background",
    mp4_path: str | None = None,
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
        "(id, project_id, status, mode, mp4_path, srt_path, background_image, "
        "subtitle_style_json, error_message, started_at, completed_at) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?) "
        "ON CONFLICT(project_id) DO UPDATE SET "
        "status = excluded.status, mode = excluded.mode, mp4_path = excluded.mp4_path, "
        "srt_path = excluded.srt_path, background_image = excluded.background_image, "
        "error_message = excluded.error_message, started_at = excluded.started_at, "
        "completed_at = excluded.completed_at",
        (
            str(uuid.uuid4()),
            project_id,
            status,
            mode,
            mp4_path,
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
