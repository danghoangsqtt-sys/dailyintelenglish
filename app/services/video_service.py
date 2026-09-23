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
import os
import subprocess
import uuid
from datetime import datetime, timezone
from pathlib import Path

import aiosqlite

from app.core.config import settings
from app.core.constants import (
    VIDEO_HEIGHT_SHORTS,
    VIDEO_RENDER_TIMEOUT_MIN_SECONDS,
    VIDEO_RENDER_TIMEOUT_PER_AUDIO_SECOND,
    VIDEO_TEMPLATE_IDS,
    VIDEO_TEMPLATE_LABELS,
    VIDEO_WIDTH_SHORTS,
)
from app.core.exceptions import VideoRenderError
from app.core.paths import get_project_root

TEMPLATE_DIR = get_project_root() / "frontend" / "static" / "video_backgrounds"


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


def _render_timeout_seconds(audio_duration_seconds: float) -> float:
    """Bounded ffmpeg timeout for one render pass (Task 16.2, ENH-008): scales with
    the audio it has to encode, with a generous floor for short clips. Both ffmpeg
    passes render the same underlying audio length, so they share this one formula."""
    return max(VIDEO_RENDER_TIMEOUT_MIN_SECONDS, VIDEO_RENDER_TIMEOUT_PER_AUDIO_SECOND * audio_duration_seconds)


def _rendering_temp_path(output_path: Path) -> Path:
    """The temp sibling a render writes to before an atomic replace (Task 16.2,
    Amendment B) -- never the final path directly. Keeps the `.mp4` extension so
    ffmpeg still infers the right container from it."""
    return output_path.with_name(f"{output_path.stem}.rendering{output_path.suffix}")


def _publish_rendered_output(temp_path: Path, output_path: Path, context: str) -> None:
    """Atomically publish a completed render, `temp_path` -> `output_path` (Task 16.2,
    Amendment B). `os.replace` can itself fail on Windows (N4) -- most realistically a
    `PermissionError` if the prior `output_path` is open elsewhere (e.g. the Video Studio
    preview streaming it through `FileResponse`, which opens without `FILE_SHARE_DELETE`).
    On any such failure the temp file is cleaned up (never left behind) and a
    user-actionable `VideoRenderError` is raised instead of a raw `OSError` -- the prior
    video itself is untouched either way, since `os.replace` never partially applies."""
    try:
        os.replace(temp_path, output_path)
    except OSError as exc:
        temp_path.unlink(missing_ok=True)
        raise VideoRenderError(
            f"{context} finished, but could not replace the previous video "
            f"({type(exc).__name__}) -- is it open in a player or being downloaded "
            "elsewhere? Close it and try again."
        ) from None


def _render_video_sync(
    background_path: Path, audio_path: str, srt_path: Path, output_path: Path, audio_duration_seconds: float
) -> None:
    """Blocking ffmpeg subprocess call — must run in a thread (asyncio.to_thread), never
    on the event loop directly (this task's Forbidden Scope).

    Task 14.10 (D14): `-t {audio_duration_seconds}` replaces `-shortest`.
    `-shortest` measurably overshoots on this exact command shape at real durations
    (confirmed: exactly matched at 10s, ~2.5s tail at ~300s, reproduced directly and
    root-caused to `-shortest` only stopping further *reads* once the audio input
    ends while frames already buffered in libx264's B-frame reordering pipeline still
    get flushed afterward -- Gate B-3 measured this exact 2.48s gap). `-t` is a hard,
    frame-accurate output cutoff regardless of encoder buffering, using the duration
    AudioService already measured for real (`audio_jobs.duration_seconds`) rather
    than a second ffprobe call.

    Task 16.2 (ENH-008, Amendment B): renders into a temp sibling and only atomically
    replaces `output_path` on success. `-y` truncates whatever it's pointed at the
    instant a render starts, and `mark_video_job_failed` (BUG-017) deliberately leaves
    the DB row pointing at the prior successful video on any failure -- rendering
    straight into the final path would let a timed-out (or otherwise failed) re-render
    delete or truncate the file that row still points at.
    """
    temp_path = _rendering_temp_path(output_path)
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
        "-t", str(audio_duration_seconds),
        str(temp_path),
    ]
    timeout = _render_timeout_seconds(audio_duration_seconds)
    try:
        result = subprocess.run(command, capture_output=True, text=True, timeout=timeout)
    except subprocess.TimeoutExpired:
        temp_path.unlink(missing_ok=True)
        raise VideoRenderError(f"ffmpeg video render timed out after {timeout:g} s") from None
    if result.returncode != 0:
        temp_path.unlink(missing_ok=True)
        raise VideoRenderError(f"ffmpeg video render failed: {result.stderr[-500:]}")
    _publish_rendered_output(temp_path, output_path, "ffmpeg video render")


def _render_vertical_sync(source_mp4_path: Path, output_path: Path, audio_duration_seconds: float) -> None:
    """Second ffmpeg pass: reformat an already-rendered 16:9 MP4 into a 9:16 vertical MP4.

    Blurred-background-pad technique (Task 2.5b research — the real convention used by
    YouTube Shorts/TikTok/Reels tooling): the source is scaled+cropped to fill the full
    vertical canvas as a blurred backdrop, then the same source scaled to fit the width
    is overlaid centered on top. Runs over the finished 16:9 render, not a rewrite of the
    tested subtitle-burn path in `_render_video_sync` — audio is copied, not re-encoded,
    since the audio content itself never changes. `source_mp4_path` is always the final,
    already-replaced `video.mp4` from `_render_video_sync` -- this pass only runs after
    that one has returned successfully.

    Must run in a thread (asyncio.to_thread), never on the event loop directly.

    Task 16.2 (ENH-008, Amendment B): same temp-then-atomic-replace write as
    `_render_video_sync`, and the same timeout budget (same underlying audio length).
    """
    temp_path = _rendering_temp_path(output_path)
    filter_complex = (
        f"[0:v]scale={VIDEO_WIDTH_SHORTS}:{VIDEO_HEIGHT_SHORTS}:force_original_aspect_ratio=increase,"
        f"crop={VIDEO_WIDTH_SHORTS}:{VIDEO_HEIGHT_SHORTS},gblur=sigma=20[bg];"
        f"[0:v]scale={VIDEO_WIDTH_SHORTS}:-2[fg];"
        f"[bg][fg]overlay=(W-w)/2:(H-h)/2,format=yuv420p[v]"
    )
    command = [
        settings.FFMPEG_PATH,
        "-y",
        "-i", str(source_mp4_path),
        "-filter_complex", filter_complex,
        "-map", "[v]",
        "-map", "0:a",
        "-c:v", "libx264",
        "-c:a", "copy",
        str(temp_path),
    ]
    timeout = _render_timeout_seconds(audio_duration_seconds)
    try:
        result = subprocess.run(command, capture_output=True, text=True, timeout=timeout)
    except subprocess.TimeoutExpired:
        temp_path.unlink(missing_ok=True)
        raise VideoRenderError(f"ffmpeg vertical (9:16) render timed out after {timeout:g} s") from None
    if result.returncode != 0:
        temp_path.unlink(missing_ok=True)
        raise VideoRenderError(f"ffmpeg vertical (9:16) render failed: {result.stderr[-500:]}")
    _publish_rendered_output(temp_path, output_path, "ffmpeg vertical (9:16) render")


def _write_video_outputs_sync(background_path: Path, output_dir: Path, srt_path: Path, srt_content: str) -> None:
    """Blocking filesystem prep for a video render — must run in a thread, never on the
    event loop directly (this task's Forbidden Scope)."""
    if not background_path.is_file():
        raise VideoRenderError(f"Background template not found: {background_path.stem}")
    output_dir.mkdir(parents=True, exist_ok=True)
    srt_path.write_text(srt_content, encoding="utf-8")


async def generate_video(
    project_id: str, audio_job: dict | None, template_id: str, aspect_ratio: str = "16:9"
) -> dict:
    """Render a project's completed audio mix into an MP4 with a background + burned-in subtitles.

    Args:
        project_id: Project UUID.
        audio_job: The project's `audio_jobs` row (from `audio_service.get_audio_job`).
        template_id: One of `VIDEO_TEMPLATE_IDS`.
        aspect_ratio: One of `VIDEO_ASPECT_RATIOS`. `"16:9"` (default) renders only the
            existing background+subtitle path, unchanged. `"9:16"` additionally renders a
            second, vertical MP4 via `_render_vertical_sync` (Task 2.5b) — a real gap
            found by Task 2.1c's QA pass (no 9:16 output existed anywhere before this).

    Raises:
        VideoRenderError: If no completed audio mix exists yet, or ffmpeg fails.
    """
    if audio_job is None or audio_job.get("status") != "complete":
        raise VideoRenderError("Cannot generate video: the audio mix hasn't been generated yet.")

    background_path = TEMPLATE_DIR / f"{template_id}.png"
    output_dir = settings.DATA_DIR / "video" / project_id
    srt_path = output_dir / "subtitles.srt"
    mp4_path = output_dir / "video.mp4"
    mp4_path_vertical = output_dir / "video_vertical.mp4"

    await asyncio.to_thread(
        _write_video_outputs_sync, background_path, output_dir, srt_path, generate_srt(audio_job["timestamps"])
    )

    try:
        await asyncio.to_thread(
            _render_video_sync,
            background_path, audio_job["mp3_path"], srt_path, mp4_path, audio_job["duration_seconds"],
        )
    except VideoRenderError:
        raise
    except Exception as exc:
        raise VideoRenderError(f"Video rendering failed: {exc}") from exc

    result = {"mp4_path": str(mp4_path), "srt_path": str(srt_path), "background_image": template_id}

    if aspect_ratio == "9:16":
        try:
            await asyncio.to_thread(
                _render_vertical_sync, mp4_path, mp4_path_vertical, audio_job["duration_seconds"]
            )
        except VideoRenderError:
            raise
        except Exception as exc:
            raise VideoRenderError(f"Vertical video rendering failed: {exc}") from exc
        result["mp4_path_vertical"] = str(mp4_path_vertical)
    else:
        # A previous call for this project may have rendered a vertical file (Task 2.6b
        # fix): it was derived from the 16:9 render/subtitle-burn we just replaced, so
        # it's now stale and would otherwise linger on disk as an orphan even though the
        # DB row's mp4_path_vertical is about to go back to NULL (nothing references it
        # any more, but nothing deleted it either — found in the post-Task-2.5 audit).
        await asyncio.to_thread(mp4_path_vertical.unlink, missing_ok=True)

    return result


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
