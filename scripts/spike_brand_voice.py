"""Task 25.1 spike: three female Edge TTS voices saying the channel greeting and farewell. Not shipped.

    venv\\Scripts\\python scripts\\spike_brand_voice.py

Writes data/tmp/brand-spike/<voice>_{greeting,farewell}.mp3 and prints each duration.
"""

from __future__ import annotations

import asyncio
import json
import sys
from pathlib import Path

import edge_tts
from pydub import AudioSegment

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from app.services import audio_service  # noqa: E402,F401  (puts ffmpeg/ffprobe on PATH for pydub)

OUT = ROOT / "data" / "tmp" / "brand-spike"
VOICES = ["en-US-AvaMultilingualNeural", "en-US-JennyNeural", "en-GB-SoniaNeural"]
TEXTS = {
    "greeting": "Welcome to Daily Intel English Channel! Wishing you a wonderful time learning English today.",
    "farewell": "Thanks for watching Daily Intel English! Keep practising, and see you in the next lesson.",
}


async def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    available = {voice["ShortName"] for voice in await edge_tts.list_voices()}
    report = []
    for voice in VOICES:
        if voice not in available:
            report.append({"voice": voice, "error": "not offered by Edge TTS"})
            continue
        for kind, text in TEXTS.items():
            path = OUT / f"{voice}_{kind}.mp3"
            await edge_tts.Communicate(text, voice).save(str(path))
            report.append({"voice": voice, "kind": kind, "file": path.name,
                           "seconds": round(len(AudioSegment.from_file(path)) / 1000, 2)})
    print(json.dumps(report, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
