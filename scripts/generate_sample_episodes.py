"""Generate 3 real sample podcast episodes (A1, B1, C1) with script + audio.

Task 3.2 deliverable: "3 sample podcast scripts (A1, B1, C1) with audio". Uses the same
real-pipeline precedent as Task 2.1a's `generate_cefr_review_samples.py`: real Gemini
script generation (`script_service.generate_script`) and real Edge TTS synthesis
(`tts_service._synthesize_edge_tts`), then a real ffmpeg mix
(`audio_service.mix_project`) — nothing mocked. The topic, genre, speakers, and duration
are held constant across all 3 levels so the CEFR level is the only variable, making the
difficulty progression the clearest to compare.

Does not touch the app's real `data/app.db` (same reasoning as Task 2.1a's script:
these are one-off showcase artifacts for docs/samples/, not real user projects that
should appear on the Dashboard) — script generation and TTS synthesis are called
directly against the service layer, and the audio mix's own temporary per-line cache
files are cleaned up after mixing.

Usage:
    venv\\Scripts\\python scripts\\generate_sample_episodes.py
"""

from __future__ import annotations

import asyncio
import json
import shutil
import sys
import uuid
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from app.core.constants import GEMINI_RATE_LIMIT_RPM  # noqa: E402
from app.services import audio_service, script_service, tts_service  # noqa: E402

TOPIC = "Planning a healthy weekday routine"
GENRE = "small_talk"
ACCENT = "american"
DURATION_MINUTES = 2.0
LEVELS = ("A1", "B1", "C1")
LANGUAGE_FEATURES = {
    "collocation": True,
    "idiom": True,
    "slang": False,
    "local_expressions": False,
    "phrasal_verbs": True,
    "business_register": False,
}
SPEAKER_BLUEPRINTS = (
    {"name": "Alex", "gender": "male"},
    {"name": "Maya", "gender": "female"},
)
REQUEST_INTERVAL_SECONDS = (60.0 / GEMINI_RATE_LIMIT_RPM) + 0.1
OUTPUT_ROOT = PROJECT_ROOT / "docs" / "samples"


def _speaker_config(name: str, gender: str) -> dict[str, Any]:
    return {
        "id": str(uuid.uuid4()),
        "name": name,
        "gender": gender,
        "accent": ACCENT,
        "tts_engine": "edge_tts",
        "voice_description": "",
        "speed": 1.0,
        "pitch": 0.0,
        "volume": 1.0,
    }


def _build_config() -> dict[str, Any]:
    return {
        "speakers": [_speaker_config(b["name"], b["gender"]) for b in SPEAKER_BLUEPRINTS],
    }


async def _synthesize_all_lines(
    lines: list[script_service.ScriptLineOut],
    speakers_by_id: dict[str, dict],
    cache_dir: Path,
) -> list[dict]:
    """Real Edge TTS synthesis per line, written to a scratch cache dir for mixing."""
    cache_dir.mkdir(parents=True, exist_ok=True)
    mix_lines: list[dict] = []
    for line in lines:
        speaker = speakers_by_id[line.speaker_id]
        audio_bytes = await tts_service._synthesize_edge_tts(line.text, speaker)
        audio_path = cache_dir / f"{line.id}.mp3"
        await asyncio.to_thread(audio_path.write_bytes, audio_bytes)
        mix_lines.append(
            {"id": line.id, "speaker_id": line.speaker_id, "audio_cache_path": str(audio_path)}
        )
    return mix_lines


def _render_transcript_md(level: str, config: dict, lines: list[script_service.ScriptLineOut]) -> str:
    speakers_by_id = {s["id"]: s["name"] for s in config["speakers"]}
    parts = [
        f"# Sample Episode — CEFR {level}",
        "",
        f"- Topic: {TOPIC}",
        f"- Genre: {GENRE}",
        f"- Accent: {ACCENT}",
        f"- Duration target: {DURATION_MINUTES} minutes",
        "",
        "## Transcript",
        "",
    ]
    for line in lines:
        parts.append(f"**{speakers_by_id.get(line.speaker_id, line.speaker_id)}:** {line.text}")
        parts.append("")
    return "\n".join(parts)


async def generate_one_episode(level: str) -> dict[str, Any]:
    project_id = str(uuid.uuid4())
    config = _build_config()
    config.update(
        {
            "name": f"Sample Episode {level}",
            "topic": TOPIC,
            "cefr_level": level,
            "genre": GENRE,
            "accent": ACCENT,
            "duration_minutes": DURATION_MINUTES,
            "num_speakers": len(SPEAKER_BLUEPRINTS),
            "language_features": dict(LANGUAGE_FEATURES),
        }
    )
    speakers_by_id = {s["id"]: s for s in config["speakers"]}

    print(f"[{level}] requesting Gemini for script...", flush=True)
    lines = await script_service.generate_script(project_id, config)
    print(f"[{level}] script generated: {len(lines)} lines", flush=True)

    level_dir = OUTPUT_ROOT / level
    scratch_dir = level_dir / "_tts_cache"
    print(f"[{level}] synthesizing {len(lines)} lines via Edge TTS...", flush=True)
    mix_lines = await _synthesize_all_lines(lines, speakers_by_id, scratch_dir)

    print(f"[{level}] mixing audio...", flush=True)
    project_dict = {"id": project_id, "speakers": config["speakers"]}
    result = await audio_service.mix_project(project_dict, mix_lines)

    level_dir.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(result["mp3_path"], level_dir / "audio.mp3")
    (level_dir / "script.md").write_text(
        _render_transcript_md(level, config, lines), encoding="utf-8"
    )
    (level_dir / "script.json").write_text(
        json.dumps(
            {
                "project_id": project_id,
                "config": config,
                "lines": [line.model_dump(mode="json") for line in lines],
                "duration_seconds": result["duration_seconds"],
                "loudness_lufs": result["loudness_lufs"],
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    shutil.rmtree(scratch_dir, ignore_errors=True)

    print(
        f"[{level}] done: {len(lines)} lines, "
        f"{result['duration_seconds']}s, {result['loudness_lufs']} LUFS -> {level_dir}",
        flush=True,
    )
    return {
        "level": level,
        "line_count": len(lines),
        "duration_seconds": result["duration_seconds"],
        "loudness_lufs": result["loudness_lufs"],
        "output_dir": str(level_dir),
    }


async def main_async() -> int:
    OUTPUT_ROOT.mkdir(parents=True, exist_ok=True)
    summaries: list[dict[str, Any]] = []
    for index, level in enumerate(LEVELS):
        if index > 0:
            await asyncio.sleep(REQUEST_INTERVAL_SECONDS)
        summaries.append(await generate_one_episode(level))

    print("\nSummary:")
    for summary in summaries:
        print(
            f"  {summary['level']}: {summary['line_count']} lines, "
            f"{summary['duration_seconds']}s, {summary['loudness_lufs']} LUFS"
        )
    return 0


def main() -> int:
    return asyncio.run(main_async())


if __name__ == "__main__":
    raise SystemExit(main())
