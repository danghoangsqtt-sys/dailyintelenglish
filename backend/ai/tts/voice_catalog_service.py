"""English Edge TTS metadata with a bounded, persistent last-good cache."""

from __future__ import annotations

import asyncio
import json
import logging
import math
import os
import re
import time
import uuid
import weakref
from datetime import datetime, timezone
from pathlib import Path

import edge_tts

from backend.core.config import settings
from backend.core.constants import VOICE_CATALOG_TIMEOUT_SECONDS, VOICE_CATALOG_TTL_SECONDS
from backend.core.exceptions import TTSError, ValidationError
from backend.schemas.tts import VoiceInfo

logger = logging.getLogger(__name__)
VOICE_ID_PATTERN = re.compile(r"en-[A-Za-z0-9-]+Neural")
_locks: weakref.WeakKeyDictionary = weakref.WeakKeyDictionary()


def _lock(path: Path) -> asyncio.Lock:
    loop = asyncio.get_running_loop()
    return _locks.setdefault(loop, {}).setdefault(str(path), asyncio.Lock())


def _read_cache(path: Path) -> dict | None:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        if (not isinstance(data["fetched_at"], (float, int)) or not math.isfinite(data["fetched_at"])
                or not 0 <= data["fetched_at"] <= time.time() + VOICE_CATALOG_TTL_SECONDS or not data["voices"]):
            return None
        data["voices"] = [VoiceInfo.model_validate(item).model_dump() for item in data["voices"]]
        return data
    except (OSError, ValueError, KeyError, TypeError):
        return None


def _write_cache(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.{uuid.uuid4().hex}.tmp")
    try:
        temporary.write_text(json.dumps(data), encoding="utf-8")
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


def _normalize(rows: list[dict]) -> list[dict]:
    found: dict[str, dict] = {}
    for row in rows:
        if not isinstance(row, dict):
            continue
        voice_id, locale = row.get("ShortName", ""), row.get("Locale", "")
        if not isinstance(voice_id, str) or not VOICE_ID_PATTERN.fullmatch(voice_id):
            continue
        if not isinstance(locale, str) or not locale.lower().startswith("en-"):
            continue
        gender = str(row.get("Gender", "neutral")).lower()
        if gender not in {"male", "female", "neutral"}:
            gender = "neutral"
        found[voice_id] = VoiceInfo(
            voice_id=voice_id, name=row.get("FriendlyName") or voice_id,
            locale=locale, gender=gender,
        ).model_dump()
    if not found:
        raise TTSError("Edge TTS returned no usable English voices. Please refresh the voice list.")
    return sorted(found.values(), key=lambda item: (item["locale"], item["name"], item["voice_id"]))


async def get_catalog(
    *, refresh: bool = False, locale: str = "", gender: str = "", q: str = "",
) -> dict:
    """Return English voice metadata; retain and label the last-good catalog on network failure."""
    path = settings.DATA_DIR / "tts_voice_catalog.json"
    async with _lock(path):
        cached = await asyncio.to_thread(_read_cache, path)
        stale = not cached or time.time() - cached["fetched_at"] >= VOICE_CATALOG_TTL_SECONDS
        if refresh or stale:
            try:
                async with asyncio.timeout(VOICE_CATALOG_TIMEOUT_SECONDS):
                    rows = await edge_tts.list_voices()
                if not isinstance(rows, list):
                    raise TTSError("Edge TTS returned an invalid voice catalog.")
                cached = {"fetched_at": time.time(), "voices": _normalize(rows)}
                stale = False
                try:
                    await asyncio.to_thread(_write_cache, path, cached)
                except OSError:
                    logger.warning("Voice catalog is available but could not be cached on disk")
            except Exception as exc:
                if cached is None:
                    raise TTSError("The voice list is unavailable. Check the connection and try again.") from exc
                stale = True
                logger.warning("Voice catalog refresh failed; using the last-good catalog")
        voices = cached["voices"]
        if locale:
            voices = [v for v in voices if v["locale"].lower() == locale.lower()]
        if gender:
            voices = [v for v in voices if v["gender"] == gender.lower()]
        if q.strip():
            query = q.strip().casefold()
            voices = [v for v in voices if query in f'{v["name"]} {v["voice_id"]} {v["locale"]}'.casefold()]
        return {
            "voices": voices,
            "fetched_at": datetime.fromtimestamp(cached["fetched_at"], timezone.utc).isoformat(),
            "stale": stale,
        }


async def require_voice(voice_id: str) -> dict:
    """Validate a concrete English voice against the provider's current or last-good metadata."""
    if not isinstance(voice_id, str) or not VOICE_ID_PATTERN.fullmatch(voice_id):
        raise ValidationError("Select an English Edge TTS voice from the voice list.")
    catalog = await get_catalog()
    for voice in catalog["voices"]:
        if voice["voice_id"] == voice_id:
            return voice
    raise ValidationError("The selected voice is not in the voice list. Refresh the list and select another voice.")
