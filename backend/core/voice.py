"""Pure voice identity and revision helpers shared by profiles, projects and media."""

from __future__ import annotations

import hashlib
import json

from backend.core.constants import EDGE_TTS_VOICE_MAP, LEGACY_TTS_ENGINES
from backend.core.exceptions import ValidationError


def resolve_voice_id(speaker: dict) -> str:
    """Resolve the pinned voice, falling back only when no explicit voice was stored."""
    own = speaker.get("voice_id")
    if own:
        if not isinstance(own, str) or not own.startswith("en-") or not own.endswith("Neural"):
            raise ValidationError("The saved voice is not an English Edge TTS voice. Select a voice again.")
        return own
    accent = EDGE_TTS_VOICE_MAP.get(speaker.get("accent"), EDGE_TTS_VOICE_MAP["american"])
    return accent.get(speaker.get("gender"), accent["neutral"])


def voice_parameters(speaker: dict) -> dict:
    """The effective engine identity and synthesis settings, independent of display names."""
    voice_id = resolve_voice_id(speaker)
    engine = speaker.get("tts_engine") or "edge_tts"
    engine = LEGACY_TTS_ENGINES.get(engine, engine)
    return {
        "engine": engine, "voice_id": voice_id, "locale": voice_id.rsplit("-", 1)[0],
        "speed": speaker.get("speed") if speaker.get("speed") is not None else 1.0,
        "pitch": speaker.get("pitch") if speaker.get("pitch") is not None else 0.0,
        "volume": speaker.get("volume") if speaker.get("volume") is not None else 1.0,
    }


def fingerprint(value: object) -> str:
    """Hash canonical semantic inputs without exposing the text in logs or URLs."""
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False).encode("utf-8")).hexdigest()


def voice_revision(speaker: dict) -> str:
    """Revision for optimistic edits; persona changes are included to detect stale defaults."""
    return fingerprint({key: speaker.get(key) for key in
                        ("tts_engine", "voice_id", "accent", "gender", "speed", "pitch", "volume")})


def profile_voice_settings(row: dict) -> dict:
    """Map a character DB row to the same voice contract used by a project speaker."""
    return {
        "tts_engine": row.get("default_tts_engine") or "edge_tts",
        "voice_id": row.get("default_voice_id"), "accent": row.get("default_accent"),
        "gender": row.get("gender"), "speed": row.get("default_speed", 1.0),
        "pitch": row.get("default_pitch", 0.0), "volume": row.get("default_volume", 1.0),
    }


def line_fingerprint(project: dict, line: dict) -> dict:
    """Synthesis fingerprint for a line, also used to reject a stale network completion."""
    speaker = next((item for item in project["speakers"] if item["id"] == line["speaker_id"]), None)
    if speaker is None:
        raise ValidationError("The line's speaker no longer belongs to this project.")
    return {
        "schema_version": 1, **voice_parameters(speaker),
        "text_hash": fingerprint(line["text"]), "speaker_id": line["speaker_id"],
    }


def media_revision(project: dict, lines: list[dict], audio_job: dict | None = None, *, include_cache: bool = True) -> str:
    """Snapshot inputs for mix/render without using a generic, frequently changing updated_at."""
    return fingerprint({
        "presentation_mode": project.get("presentation_mode", "classic"),
        "explainer_structure": project.get("explainer_structure"),
        "speakers": [{"id": s["id"], "name": s["name"], "voice": voice_revision(s)} for s in project["speakers"]],
        "lines": [
            {"id": line["id"], "speaker_id": line["speaker_id"], "text": line["text"],
             "audio_cache_path": line.get("audio_cache_path") if include_cache else None}
            for line in lines
        ],
        "audio": {key: audio_job.get(key) for key in
                  ("id", "status", "mp3_path", "wav_path", "completed_at")} if audio_job else None,
    })
