"""Phase 25 (D52-D55): the branded intro/outro voice lines.

Every Enhanced episode opens with Jenny saying the channel greeting + a wish and closes with a
farewell. The wish and farewell are picked deterministically per project (a re-render keeps the
same lines, different episodes vary). Synthesised audio is cached by voice + text.
"""

from __future__ import annotations

import asyncio
import hashlib
from pathlib import Path
from typing import Any

import edge_tts
from pydub import AudioSegment

from app.core.config import settings
from app.core.exceptions import TTSError

BRAND_VOICE = "en-US-JennyNeural"  # owner pick, spike 25.1
GREETING = "Welcome to Daily Beyond English Channel!"
WISHES = (
    "Wishing you a wonderful time learning English today!",
    "Good luck with your studies, and enjoy the lesson!",
    "Wishing you every success on your English journey!",
    "Let's learn something new together today!",
    "Have fun, stay curious, and keep improving!",
    "Wishing you a productive and happy day of learning!",
    "Relax, listen closely, and enjoy every word!",
    "May today's lesson bring you one step closer to your goals!",
    "Wishing you confidence and success in every conversation!",
    "Grab a coffee, get comfortable, and let's begin!",
    "Keep going, you are doing great!",
    "Wishing you a bright day full of new words!",
)
FAREWELL = "Thanks for watching Daily Beyond English!"
FAREWELLS = (
    "Keep practising, and see you in the next lesson.",
    "Take care, and see you next time.",
    "Keep learning every day, and good luck!",
    "Don't forget to subscribe, and see you soon.",
    "Practice a little every day, and you will go far.",
    "Have a great day, and see you in the next episode.",
    "Keep up the good work, and see you next time.",
    "Stay curious, and see you in the next lesson.",
)

VOICE_START_INTRO_S = 0.4
VOICE_START_OUTRO_S = 0.5
MIN_SLIDE_S = 6.0
INTRO_TAIL_S = 1.0  # after the greeting: the wish lingers, then the dissolve into the episode
OUTRO_TAIL_S = 1.8  # after the farewell: the chips and the final fade
EDGE_ATTEMPTS = 2


def pick(project_id: str, items: tuple[str, ...], salt: str) -> str:
    """Deterministic per project; `salt` keeps the wish and the farewell independent."""
    digest = hashlib.sha256(f"{salt}:{project_id}".encode("utf-8")).digest()
    return items[int.from_bytes(digest[:4], "big") % len(items)]


def brand_lines(project_id: str) -> dict[str, str]:
    wish = pick(project_id, WISHES, "wish")
    farewell = pick(project_id, FAREWELLS, "farewell")
    return {"wish": wish, "greeting_text": f"{GREETING} {wish}", "farewell_text": f"{FAREWELL} {farewell}",
            "farewell_line": farewell}


def brand_timing(greeting_s: float | None, farewell_s: float | None) -> dict[str, float]:
    """Slide lengths follow the voice, never shorter than MIN_SLIDE_S."""
    intro = max(MIN_SLIDE_S, VOICE_START_INTRO_S + (greeting_s or 0) + INTRO_TAIL_S)
    outro = max(MIN_SLIDE_S, VOICE_START_OUTRO_S + (farewell_s or 0) + OUTRO_TAIL_S)
    return {"intro_s": round(intro, 2), "outro_s": round(outro, 2),
            "greeting_start_s": VOICE_START_INTRO_S, "farewell_start_s": VOICE_START_OUTRO_S}


def voice_cache_path(text: str, voice: str = BRAND_VOICE) -> Path:
    key = hashlib.sha1(f"{voice}|{text}".encode("utf-8")).hexdigest()
    return settings.DATA_DIR / "brand_voice" / f"{key}.mp3"


def _duration_s(path: Path) -> float:
    return round(len(AudioSegment.from_file(path)) / 1000, 3)


async def _edge_save(text: str, voice: str, path: Path) -> None:
    last: Exception | None = None
    for _ in range(EDGE_ATTEMPTS):
        try:
            await edge_tts.Communicate(text, voice).save(str(path))
            if path.is_file() and path.stat().st_size > 0:
                return
        except Exception as exc:  # noqa: BLE001 -- Edge TTS sometimes returns an empty stream once
            last = exc
        await asyncio.sleep(0.5)
    path.unlink(missing_ok=True)
    raise TTSError(f"Edge TTS could not speak the brand line: {last}")


async def synthesize(text: str, voice: str = BRAND_VOICE) -> dict[str, Any]:
    """Speak `text` with the brand voice (cached); returns its path and duration."""
    path = voice_cache_path(text, voice)
    if not await asyncio.to_thread(path.is_file):
        path.parent.mkdir(parents=True, exist_ok=True)
        temporary = path.with_suffix(".part.mp3")
        await _edge_save(text, voice, temporary)
        await asyncio.to_thread(temporary.replace, path)
    return {"path": str(path), "duration_s": await asyncio.to_thread(_duration_s, path)}


async def brand_audio(project_id: str) -> dict[str, Any]:
    """The lines, their voice files and the slide timing for one episode."""
    lines = brand_lines(project_id)
    greeting = await synthesize(lines["greeting_text"])
    farewell = await synthesize(lines["farewell_text"])
    return {**lines, "greeting": greeting, "farewell": farewell,
            **brand_timing(greeting["duration_s"], farewell["duration_s"])}
