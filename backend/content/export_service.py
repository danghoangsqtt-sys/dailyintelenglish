"""Phase 41 (D120): the project's own output folder. The owner chooses a folder when a video project starts and ticks the
components to export; after every new version (video, vertical video, clip, thumbnail, YouTube package, audio, learning)
the ticked components that exist are copied there. Unticked components are never written, and nothing is ever deleted
from the owner's folder.
"""

from __future__ import annotations

import asyncio
import json
import logging
import shutil
import uuid
import weakref
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import aiosqlite
from pydantic import BaseModel, Field, field_validator

from backend.core.exceptions import NotFoundError, ValidationError

logger = logging.getLogger(__name__)

ITEMS = {
    "video": "Video (YouTube) + subtitles",
    "video_vertical": "Vertical video (TikTok)",
    "thumbnail": "Thumbnail",
    "youtube": "YouTube texts (titles, description, tags, pinned comment)",
    "shorts": "Shorts / TikTok clips with covers and captions",
    "audio": "Audio (MP3)",
    "script": "Script",
    "learning": "Learning pack (transcript, vocabulary, idioms…)",
}
DEFAULT_ITEMS = ["video", "thumbnail", "youtube"]
_sync_locks: weakref.WeakKeyDictionary = weakref.WeakKeyDictionary()


def _sync_lock(project_id: str) -> asyncio.Lock:
    """Serialize exports of one project without tying locks to an old test event loop."""
    loop = asyncio.get_running_loop()
    locks = _sync_locks.setdefault(loop, {})
    return locks.setdefault(project_id, asyncio.Lock())


class ExportSettings(BaseModel):
    output_dir: str = Field(min_length=3, max_length=400)
    items: list[str] = Field(default_factory=lambda: list(DEFAULT_ITEMS))

    @field_validator("output_dir")
    @classmethod
    def absolute_folder(cls, value: str) -> str:
        path = Path(value.strip().strip('"'))
        if not path.is_absolute():
            raise ValueError("Choose a full folder path, for example D:\\Videos\\My episode")
        return str(path)

    @field_validator("items")
    @classmethod
    def known_items(cls, value: list[str]) -> list[str]:
        unknown = [item for item in value if item not in ITEMS]
        if unknown:
            raise ValueError(f"Unknown components: {', '.join(unknown)}")
        return [item for item in ITEMS if item in value]  # stable order, no duplicates


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _check_folder(path: Path) -> None:
    """Create the folder if needed and prove it is writable (blocking; run in a thread)."""
    try:
        path.mkdir(parents=True, exist_ok=True)
        probe = path / ".daily-beyond-write-test"
        probe.write_text("ok", encoding="utf-8")
        probe.unlink()
    except OSError as exc:
        raise ValidationError(f"The folder cannot be used: {exc.strerror or exc}") from exc


async def get_settings(db: aiosqlite.Connection, project_id: str) -> dict | None:
    cursor = await db.execute(
        "SELECT output_dir, items_json, last_sync_at, last_error, updated_at FROM project_exports WHERE project_id = ?",
        (project_id,))
    row = await cursor.fetchone()
    if row is None:
        return None
    return {"output_dir": row[0], "items": json.loads(row[1] or "[]"), "last_sync_at": row[2],
            "last_error": row[3], "updated_at": row[4]}


async def public(db: aiosqlite.Connection, project_id: str) -> dict:
    saved = await get_settings(db, project_id)
    return {"components": [{"key": key, "label": label} for key, label in ITEMS.items()], "default_items": DEFAULT_ITEMS,
            "settings": saved}


async def save_settings(db: aiosqlite.Connection, project_id: str, body: ExportSettings) -> dict:
    cursor = await db.execute("SELECT 1 FROM projects WHERE id = ?", (project_id,))
    if await cursor.fetchone() is None:
        raise NotFoundError("Project not found")
    await db.execute(
        "INSERT INTO project_exports (project_id, output_dir, items_json, updated_at) VALUES (?, ?, ?, ?) "
        "ON CONFLICT(project_id) DO UPDATE SET output_dir = excluded.output_dir, items_json = excluded.items_json, "
        "updated_at = excluded.updated_at, last_sync_at = NULL, last_error = NULL",
        (project_id, body.output_dir, json.dumps(body.items), _now()))
    return await public(db, project_id)


async def clear_settings(db: aiosqlite.Connection, project_id: str) -> None:
    await db.execute("DELETE FROM project_exports WHERE project_id = ?", (project_id,))


# ------------------------------------------------------------------------------------------------- what to write

def _copy(source: str | Path | None, target: Path) -> bool:
    """Copy when the target is missing or differs (size or older); True when written."""
    if not source or not Path(source).is_file():
        return False
    source = Path(source)
    if target.is_file():
        here, there = source.stat(), target.stat()
        if here.st_size == there.st_size and there.st_mtime >= here.st_mtime:
            return False
    target.parent.mkdir(parents=True, exist_ok=True)
    temporary = target.with_name(f"{target.name}.{uuid.uuid4().hex}.part")
    shutil.copyfile(source, temporary)
    try:
        temporary.replace(target)
    except PermissionError:  # the old file is open (a player): keep the new one beside it
        stamped = target.with_name(f"{target.stem}-{datetime.now().strftime('%Y%m%d-%H%M%S')}{target.suffix}")
        temporary.replace(stamped)
    return True


def _text(content: str, target: Path) -> bool:
    if target.is_file() and target.read_text(encoding="utf-8") == content:
        return False
    target.parent.mkdir(parents=True, exist_ok=True)
    temporary = target.with_name(f"{target.name}.{uuid.uuid4().hex}.part")
    temporary.write_text(content, encoding="utf-8")
    temporary.replace(target)
    return True


async def _plan(db: aiosqlite.Connection, project_id: str, items: list[str]) -> list[tuple[str, Any, str]]:
    """[(kind "copy"|"text", source path or text, relative target)] for the ticked components that exist now."""
    from backend.content import learning_service, project_service, script_service, shorts_service, youtube_service
    from backend.media import audio_service, thumbnail_service, video_service

    project = await project_service.get_project(db, project_id)
    plan: list[tuple[str, Any, str]] = []
    video = await video_service.get_video_job(db, project_id) if {"video", "video_vertical"} & set(items) else None
    if "video" in items and video and video.get("status") == "complete":
        plan += [("copy", video.get("mp4_path"), "video.mp4"), ("copy", video.get("srt_path"), "subtitles.srt")]
    if "video_vertical" in items and video:
        plan.append(("copy", video.get("mp4_path_vertical"), "video_vertical.mp4"))
    if "thumbnail" in items:
        selected = next((row for row in await thumbnail_service.get_thumbnail_rows(db, project_id) if row["is_selected"]),
                        None)
        if selected:
            plan += [("copy", selected.get("image_path_16x9"), "thumbnail.png"),
                     ("copy", selected.get("image_path_9x16"), "thumbnail_9x16.png")]
    package = await youtube_service.get_package(db, project_id) if {"youtube", "shorts"} & set(items) else None
    if "youtube" in items and package:
        plan.append(("text", youtube_service._build_metadata_text(package), "youtube/metadata.txt"))
        if package.get("pinned_comments"):
            plan.append(("text", "\n\n----------\n\n".join(package["pinned_comments"]), "youtube/pinned_comment.txt"))
    learning = await learning_service.get_learning_content(db, project_id) if {"learning", "shorts"} & set(items) else None
    if "shorts" in items:
        audio = await audio_service.get_audio_job(db, project_id)
        hashtags = (package or {}).get("hashtags") or ["LearnEnglish", "EnglishConversation"]
        cursor = await db.execute("SELECT video_url FROM channel_episodes WHERE project_id = ?", (project_id,))
        row = await cursor.fetchone()
        clips = [clip for clip in await shorts_service.list_clips(db, project_id) if clip.get("status") == "rendered"]
        for number, clip in enumerate(clips, start=1):
            view = shorts_service.public(clip, project, learning, hashtags, (row[0] if row else "") or "",
                                         (audio or {}).get("timestamps") or [])
            texts = view["packages"]
            plan += [("copy", clip.get("mp4_path"), f"shorts/clip-{number}.mp4"),
                     ("copy", clip.get("cover_path"), f"shorts/clip-{number}-cover.jpg"),
                     ("text", f"YOUTUBE SHORTS\n\nTitle: {texts['shorts']['title']}\n\n{texts['shorts']['description']}\n\n"
                              f"TIKTOK\n\n{texts['tiktok']['caption']}\n", f"shorts/clip-{number}.txt")]
    if "audio" in items:
        audio_job = await audio_service.get_audio_job(db, project_id)
        if audio_job and audio_job.get("status") == "complete":
            plan.append(("copy", audio_job.get("mp3_path"), "audio.mp3"))
    lines = await script_service.get_script(db, project_id) if {"script", "learning"} & set(items) else []
    if "script" in items and lines:
        names = {speaker["id"]: speaker["name"] for speaker in project["speakers"]}
        plan.append(("text", "\n".join(f"{names.get(line['speaker_id'], 'Speaker')}: {line['text']}" for line in lines) + "\n",
                     "script.txt"))
    if "learning" in items and lines:
        plan.append(("text", youtube_service._build_transcript_and_learning_text(project, lines, learning),
                     "learning_pack.txt"))
    return plan


def _write(folder: Path, plan: list[tuple[str, Any, str]]) -> list[str]:
    written = []
    for kind, source, relative in plan:
        target = folder / relative
        if (_copy(source, target) if kind == "copy" else _text(source, target)):
            written.append(relative)
    return written


async def sync(db: aiosqlite.Connection, project_id: str) -> dict:
    """Copy the ticked components that exist into the project's folder. Returns {"written": [...]} (no folder: no-op)."""
    from backend.db.transactions import read_transaction, write_transaction

    async with _sync_lock(project_id):
        async with read_transaction():
            saved = await get_settings(db, project_id)
            if not saved:
                return {"written": [], "folder": None}
            plan = await _plan(db, project_id, saved["items"])
        error = None
        written: list[str] = []
        try:
            await asyncio.to_thread(_check_folder, Path(saved["output_dir"]))
            written = await asyncio.to_thread(_write, Path(saved["output_dir"]), plan)
        except (OSError, ValidationError) as exc:
            error = str(exc)
            logger.warning("project_export_failed project_id=%s folder=%s reason=%s", project_id, saved["output_dir"], exc)
        # A folder change or Stop can commit while the copy runs. Do not report the
        # old copy as the new folder's latest sync.
        async with write_transaction(db):
            await db.execute(
                "UPDATE project_exports SET last_sync_at = ?, last_error = ? "
                "WHERE project_id = ? AND updated_at = ?",
                (_now(), error, project_id, saved["updated_at"]),
            )
        return {"written": written, "folder": saved["output_dir"], "error": error}


async def sync_quietly(db: aiosqlite.Connection, project_id: str) -> None:
    """The automatic hook after a new version: never fails the action that triggered it."""
    try:
        result = await sync(db, project_id)
        if result["written"]:
            logger.info("project_export project_id=%s wrote=%s", project_id, ",".join(result["written"]))
    except Exception as exc:  # noqa: BLE001 -- an export problem must never break a render
        logger.warning("project_export_hook_failed project_id=%s reason=%s", project_id, exc)


def choose_folder_dialog(initial: str | None = None) -> str | None:
    """The native Windows folder picker, shown by the local server (blocking; run in a thread). None when cancelled or
    when Tk is not available (the packaged app): the page then keeps the typed path."""
    try:
        import tkinter
        from tkinter import filedialog
    except ImportError:
        return None
    root = tkinter.Tk()
    root.withdraw()
    root.attributes("-topmost", True)
    # 2026-10-14 (owner: "chọn nơi lưu vẫn bị lỗi"): the dialog opened behind the browser -- Windows does not let a
    # background server bring its window forward -- so it is raised to the top and given the focus once it exists.
    root.after(200, _raise_dialog, root, FOLDER_DIALOG_TITLE)
    try:
        chosen = filedialog.askdirectory(parent=root, initialdir=initial or str(Path.home()), mustexist=False,
                                         title=FOLDER_DIALOG_TITLE)
    finally:
        root.destroy()
    return str(Path(chosen)) if chosen else None


FOLDER_DIALOG_TITLE = "Choose the folder for this video project"


def _raise_dialog(root: Any, title: str, attempts: int = 15) -> None:
    """Find the folder dialog of this process by its title and put it on top with the keyboard focus (Windows only)."""
    import ctypes
    import os
    import sys

    if sys.platform != "win32":
        return
    user32 = ctypes.windll.user32
    found = []

    @ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.c_void_p, ctypes.c_void_p)
    def visit(hwnd, _param):
        pid = ctypes.c_ulong()
        user32.GetWindowThreadProcessId(ctypes.c_void_p(hwnd), ctypes.byref(pid))
        if pid.value == os.getpid():
            buffer = ctypes.create_unicode_buffer(256)
            user32.GetWindowTextW(ctypes.c_void_p(hwnd), buffer, 256)
            if buffer.value == title:
                found.append(hwnd)
        return True

    user32.EnumWindows(visit, 0)
    if not found:
        if attempts > 0:
            root.after(200, _raise_dialog, root, title, attempts - 1)
        return
    hwnd = ctypes.c_void_p(found[0])
    topmost, flags = ctypes.c_void_p(-1), 0x0001 | 0x0002 | 0x0040  # HWND_TOPMOST; NOSIZE | NOMOVE | SHOWWINDOW
    user32.SetWindowPos(hwnd, topmost, 0, 0, 0, 0, flags)
    user32.keybd_event(0x12, 0, 0, 0)  # a tap of Alt lets this process take the foreground
    user32.keybd_event(0x12, 0, 2, 0)
    user32.SetForegroundWindow(hwnd)
