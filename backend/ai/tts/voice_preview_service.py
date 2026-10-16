"""Isolated voice auditions: no project rows or production line cache are touched."""

from __future__ import annotations

import asyncio
import hashlib
import json
import os
import re
import threading
import time
import uuid
from pathlib import Path

from backend.ai.tts import tts_service, voice_catalog_service
from backend.core.config import settings
from backend.core.constants import (
    VOICE_PREVIEW_MAX_BYTES, VOICE_PREVIEW_TIMEOUT_SECONDS, VOICE_PREVIEW_TTL_SECONDS,
)
from backend.core.exceptions import NotFoundError, TTSError
from backend.schemas.tts import VoicePreviewRequest

_disk_lock = threading.RLock()
_PREVIEW_ID = re.compile(r"[0-9a-f]{64}")


def _read(root: Path, preview_id: str) -> bytes | None:
    if not _PREVIEW_ID.fullmatch(preview_id):
        return None
    with _disk_lock:
        path = root / f"{preview_id}.mp3"
        try:
            if root.resolve() not in path.resolve().parents:
                return None
            if time.time() - path.stat().st_mtime >= VOICE_PREVIEW_TTL_SECONDS:
                return None
            if path.stat().st_size > VOICE_PREVIEW_MAX_BYTES:
                return None
            return path.read_bytes() or None
        except OSError:
            return None


def _store(root: Path, preview_id: str, audio: bytes) -> None:
    if not audio or len(audio) > VOICE_PREVIEW_MAX_BYTES:
        raise TTSError("The voice preview is empty or exceeds the preview cache limit.")
    with _disk_lock:
        root.mkdir(parents=True, exist_ok=True)
        files = []
        for path in root.glob("*.mp3"):
            # Skip symlinks and never traverse subdirectories or production caches.
            if path.is_symlink():
                continue
            try:
                stat = path.stat()
            except OSError:
                continue
            if time.time() - stat.st_mtime >= VOICE_PREVIEW_TTL_SECONDS:
                path.unlink(missing_ok=True)
            else:
                files.append((stat.st_mtime, stat.st_size, path))
        target = root / f"{preview_id}.mp3"
        remaining = sum(size for _, size, path in files if path != target)
        for _, size, path in sorted(files):
            if path == target:
                continue
            if remaining + len(audio) <= VOICE_PREVIEW_MAX_BYTES:
                break
            path.unlink(missing_ok=True)
            remaining -= size
        temporary = root / f".{preview_id}.{uuid.uuid4().hex}.tmp"
        try:
            temporary.write_bytes(audio)
            os.replace(temporary, target)
        finally:
            temporary.unlink(missing_ok=True)


async def preview_voice(payload: VoicePreviewRequest) -> dict:
    """Create or reuse one bounded audition and return its opaque media URL."""
    voice = await voice_catalog_service.require_voice(payload.voice_id)
    values = payload.model_dump()
    preview_id = hashlib.sha256(
        json.dumps({"schema_version": 1, **values}, sort_keys=True, ensure_ascii=False).encode("utf-8")
    ).hexdigest()
    root = settings.DATA_DIR / "tts_preview"
    cached = await asyncio.to_thread(_read, root, preview_id)
    audio = cached
    if cached is None:
        speaker = {
            "voice_id": voice["voice_id"], "gender": voice["gender"], "accent": "american",
            "speed": payload.speed, "pitch": payload.pitch, "volume": payload.volume,
        }
        try:
            async with asyncio.timeout(VOICE_PREVIEW_TIMEOUT_SECONDS):
                audio, _ = await tts_service._synthesize_edge_tts(payload.text, speaker)
        except TimeoutError as exc:
            raise TTSError("The voice preview timed out. Please try again.") from exc
    await asyncio.to_thread(_store, root, preview_id, audio)
    return {
        "id": preview_id, "voice": voice,
        "audio_url": f"/api/tts/voices/preview/{preview_id}.mp3",
        "parameters": {"speed": payload.speed, "pitch": payload.pitch, "volume": payload.volume},
        "expires_in_seconds": VOICE_PREVIEW_TTL_SECONDS,
    }


async def read_preview(preview_id: str) -> bytes:
    """Read the whole small preview before response streaming so cleanup cannot delete an open file."""
    audio = await asyncio.to_thread(_read, settings.DATA_DIR / "tts_preview", preview_id)
    if audio is None:
        raise NotFoundError("Voice preview not found or expired. Generate a new preview.")
    return audio
