"""Pure data adapters used only by the versioned plain-Edge migration."""

import json
import re

from backend.ai.tts.vocal_cues import caption_text
from backend.core.constants import EDGE_TTS_VOICE_MAP


_EDGE_VOICE = re.compile(r"^en-[A-Za-z0-9-]+Neural$")


def edge_voice_id(voice: str | None, accent: str | None, gender: str | None) -> str:
    """Keep a valid pinned Edge voice, otherwise restore the existing defaults."""
    if isinstance(voice, str) and _EDGE_VOICE.fullmatch(voice):
        return voice
    voices = EDGE_TTS_VOICE_MAP.get(accent, EDGE_TTS_VOICE_MAP["american"])
    return voices.get(gender, voices["neutral"])


def plain_config(value: str | None) -> str | None:
    """Normalize legacy voice settings without dropping other project fields."""
    if not value:
        return value
    try:
        data = json.loads(value)
    except (TypeError, ValueError):
        return value
    if not isinstance(data, dict):
        return value
    before = json.dumps(data, sort_keys=True, ensure_ascii=False)
    for speaker in data.get("speakers", []) or []:
        if not isinstance(speaker, dict):
            continue
        speaker["tts_engine"] = "edge_tts"
        speaker["voice_description"] = ""
        voice = speaker.get("voice_id")
        if voice and (not isinstance(voice, str) or not _EDGE_VOICE.fullmatch(voice)):
            speaker["voice_id"] = None
    if isinstance(data.get("source_text"), str):
        data["source_text"] = caption_text(data["source_text"])
    if json.dumps(data, sort_keys=True, ensure_ascii=False) == before:
        return value
    return json.dumps(data, ensure_ascii=False)
