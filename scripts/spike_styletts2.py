"""Task 21.1b (Phase 21 spike, Amendment A) -- StyleTTS 2 measurement runner.

Runs in this project's own `venv/` (Python 3.14). Orchestrates:
  1. Fetches the same 3 real B1 script lines Task 21.1 used (line 0/24/29 of the pinned
     demo project, `mode=ro`) so the owner compares StyleTTS 2 against the Kokoro STOP
     and the Edge TTS baseline on identical text (D21.1b-c).
  2. Fetches the upstream `reference_audio.zip` voice-cloning clips into
     `models/styletts2/reference_audio/` and picks one male + one female anonymous
     LibriTTS speaker by a real median-F0 measurement, not by filename (D21.1b-c:
     StyleTTS 2 clones a reference clip -- it has no named-voice list to pick from).
  3. Spawns `scripts/styletts2_worker.py` inside `venv-styletts2/` (Python 3.11, see
     task-21.1b.md D21.1b-a), synthesizes each line with both reference voices, and
     records `nvidia-smi` + `ollama ps` snapshots before load, after load, after
     synthesis and after unload -- the GPU-sharing evidence D21.1b-e asks for. Run it
     once with Ollama idle and once with `qwen3.5:9b` loaded to get both sides.
  4. Synthesizes the same 3 lines with the same 2 Edge TTS voices through Task 21.1's own
     helpers (imported from `spike_kokoro.py`, not re-implemented), so the Edge TTS side
     of the comparison is produced by the identical method as 21.1's.
  5. Saves 12 self-describing clips + `spike_comparison_styletts2.mp3` under
     `data/tmp/phase21_styletts2_spike/` and prints a JSON measurement block to stdout
     -- `docs/operations/phase21-spike-styletts2.md` is filled in by hand from it.

**Read-only, always.** The real DB is opened via SQLite's `mode=ro` URI, same as every
prior Phase 19/21 spike.

Usage (owner's machine -- the GPU measurement needs the real RTX 3060):
    venv\\Scripts\\python scripts\\spike_styletts2.py
    venv\\Scripts\\python scripts\\spike_styletts2.py --allow-cpu   # no usable GPU

`--allow-cpu` still produces valid listening clips (same weights, same fixed seeds --
`tts.py` seeds torch/numpy/random at import), only the wall-time/RTF numbers differ.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import re
import shutil
import subprocess
import sys
import time
import urllib.request
import zipfile
from pathlib import Path
from typing import Any

import aiosqlite

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from app.core.config import settings  # noqa: E402

# `scripts/` is sys.path[0] when this file runs as a script, so Task 21.1's runner is
# importable by module name. Its helpers are reused as-is: the Edge TTS baseline and the
# comparison-mp3 layout must match 21.1's exactly for the three-way A/B to be fair.
from spike_kokoro import (  # noqa: E402
    EDGE_VOICES,
    PINNED_PROJECT_ID,
    SpikeError,
    _build_comparison_mp3,
    _edge_tts_request,
    _fetch_test_lines,
)

VENV_STYLETTS2_DIR = PROJECT_ROOT / "venv-styletts2"
# 21.1's runner hardcoded `Scripts\python.exe` (Windows-only); this one also resolves the
# POSIX layout so the worker side can be exercised off the owner's machine.
STYLETTS2_WORKER_PYTHON = VENV_STYLETTS2_DIR / (
    "Scripts/python.exe" if os.name == "nt" else "bin/python"
)
STYLETTS2_WORKER_SCRIPT = PROJECT_ROOT / "scripts" / "styletts2_worker.py"
MODEL_CACHE_DIR = PROJECT_ROOT / "models" / "styletts2"
SPIKE_OUTPUT_DIR = settings.DATA_DIR / "tmp" / "phase21_styletts2_spike"

# D21.1b-c: same HF repo the package's own `tts.py` fetches the LibriTTS checkpoint
# from (`yl4579/StyleTTS2-LibriTTS`, the original research authors' repo).
REFERENCE_AUDIO_URL = (
    "https://huggingface.co/yl4579/StyleTTS2-LibriTTS/resolve/main/reference_audio.zip"
)
REFERENCE_AUDIO_DIR = MODEL_CACHE_DIR / "reference_audio"
# Plain LibriTTS utterance ids (`<speaker>-<chapter>-<utterance>.wav`). Excludes by
# construction the zip's author-recorded demo clips (named after the paper's authors)
# and its emotion-labelled clips (`anger.wav`, `sleepy.wav`, ...) -- neither is an
# anonymous "neutral narration" voice.
LIBRITTS_SPEAKER_CLIP = re.compile(r"^\d+-\d+-\d+\.wav$")
# Typical adult median F0. Among clips on the right side of the worker's 165 Hz split,
# the one closest to its gender's typical value is picked -- the most "neutral" voice,
# not the most extreme one.
TYPICAL_F0_HZ = {"male": 120.0, "female": 210.0}

WORKER_EXIT_TIMEOUT_SECONDS = 60.0


def _ensure_reference_audio() -> list[Path]:
    """Download + extract `reference_audio.zip` once; return the anonymous LibriTTS clips."""
    REFERENCE_AUDIO_DIR.mkdir(parents=True, exist_ok=True)
    zip_path = MODEL_CACHE_DIR / "reference_audio.zip"
    if not zip_path.is_file():
        partial_path = zip_path.with_suffix(".zip.partial")
        try:
            with urllib.request.urlopen(REFERENCE_AUDIO_URL, timeout=120) as response:
                with open(partial_path, "wb") as handle:
                    shutil.copyfileobj(response, handle)
        except OSError as exc:
            partial_path.unlink(missing_ok=True)
            raise SpikeError(f"could not download {REFERENCE_AUDIO_URL}: {exc}") from exc
        partial_path.replace(zip_path)
    if not any(REFERENCE_AUDIO_DIR.rglob("*.wav")):
        with zipfile.ZipFile(zip_path) as archive:
            archive.extractall(REFERENCE_AUDIO_DIR)

    clips = sorted(
        path for path in REFERENCE_AUDIO_DIR.rglob("*.wav")
        if LIBRITTS_SPEAKER_CLIP.match(path.name) and "__MACOSX" not in path.parts
    )
    if not clips:
        raise SpikeError(f"no anonymous LibriTTS-speaker clips found under {REFERENCE_AUDIO_DIR}")
    return clips


def _gpu_snapshot(label: str) -> dict[str, Any]:
    """Real `nvidia-smi` + `ollama ps` state at one point in the run (D21.1b-e)."""
    snapshot: dict[str, Any] = {"label": label, "at_monotonic_sec": round(time.monotonic(), 3)}
    try:
        completed = subprocess.run(
            ["nvidia-smi", "--query-gpu=memory.used,memory.free,memory.total",
             "--format=csv,noheader,nounits"],
            capture_output=True, text=True, timeout=15, check=True,
        )
        used, free, total = (int(value.strip()) for value in completed.stdout.splitlines()[0].split(","))
        snapshot.update({"vram_used_mb": used, "vram_free_mb": free, "vram_total_mb": total})
    except (OSError, subprocess.SubprocessError, ValueError, IndexError):
        snapshot["vram_used_mb"] = snapshot["vram_free_mb"] = snapshot["vram_total_mb"] = None
    try:
        completed = subprocess.run(["ollama", "ps"], capture_output=True, text=True, timeout=15, check=True)
        snapshot["ollama_ps"] = completed.stdout.strip()
    except (OSError, subprocess.SubprocessError):
        snapshot["ollama_ps"] = None
    return snapshot


class _WorkerClient:
    """Line-delimited JSON over the worker's stdin/stdout (same protocol as 21.1)."""

    def __init__(self, device: str, allow_cpu: bool) -> None:
        if not STYLETTS2_WORKER_PYTHON.is_file():
            raise SpikeError(
                f"{STYLETTS2_WORKER_PYTHON} not found -- set up venv-styletts2 first: "
                "py -3.11 -m venv venv-styletts2 && "
                "venv-styletts2\\Scripts\\pip install -r requirements-styletts2.txt"
            )
        SPIKE_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        self.stderr_log = SPIKE_OUTPUT_DIR / "styletts2_worker_stderr.log"
        command = [str(STYLETTS2_WORKER_PYTHON), str(STYLETTS2_WORKER_SCRIPT), "--device", device]
        if allow_cpu:
            command.append("--allow-cpu")
        self._stderr_handle = open(self.stderr_log, "w", encoding="utf-8")
        self.process = subprocess.Popen(
            command,
            cwd=PROJECT_ROOT,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=self._stderr_handle,
            text=True,
            encoding="utf-8",
            bufsize=1,
        )
        self.handshake = self._read_line()

    def _read_line(self) -> dict[str, Any]:
        assert self.process.stdout is not None
        response_line = self.process.stdout.readline()
        if not response_line:
            raise SpikeError(
                f"styletts2_worker closed stdout unexpectedly (crashed?) -- see {self.stderr_log}"
            )
        return json.loads(response_line)

    def request(self, payload: dict[str, Any]) -> dict[str, Any]:
        assert self.process.stdin is not None
        self.process.stdin.write(json.dumps(payload) + "\n")
        self.process.stdin.flush()
        return self._read_line()

    def close(self) -> None:
        if self.process.stdin and not self.process.stdin.closed:
            self.process.stdin.close()
        try:
            self.process.wait(timeout=WORKER_EXIT_TIMEOUT_SECONDS)
        finally:
            self._stderr_handle.close()


def _pick_voices(
    worker: _WorkerClient, clips: list[Path], overrides: dict[str, str | None]
) -> tuple[dict[str, Path], list[dict[str, Any]]]:
    """Measure every candidate, then pick per gender (or honour an explicit override)."""
    measurements = []
    for clip in clips:
        result = worker.request({"command": "analyze_voice", "path": str(clip)})
        if result.get("status") != "ok":
            raise SpikeError(f"analyze_voice failed for {clip.name}: {result.get('message')}")
        measurements.append({**result, "path": str(clip)})

    by_name = {Path(item["path"]).name: item for item in measurements}
    picks: dict[str, Path] = {}
    for gender, typical_f0 in TYPICAL_F0_HZ.items():
        override = overrides.get(gender)
        if override:
            if override not in by_name:
                raise SpikeError(f"--{gender}-voice {override!r} is not one of {sorted(by_name)}")
            picks[gender] = Path(by_name[override]["path"])
            continue
        candidates = [item for item in measurements if item["inferred_gender"] == gender]
        if not candidates:
            raise SpikeError(f"no reference clip measured as {gender} -- pass --{gender}-voice explicitly")
        best = min(candidates, key=lambda item: abs(item["median_f0_hz"] - typical_f0))
        picks[gender] = Path(best["path"])
    return picks, measurements


async def _main(args: argparse.Namespace) -> dict[str, Any]:
    db_uri = f"file:{settings.db_path.as_posix()}?mode=ro"
    db = await aiosqlite.connect(db_uri, uri=True)
    db.row_factory = aiosqlite.Row
    try:
        project, lines = await _fetch_test_lines(db)
    finally:
        await db.close()

    reference_clips = _ensure_reference_audio()
    SPIKE_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    gpu_snapshots = [_gpu_snapshot("before_worker_start")]
    worker = _WorkerClient(device=args.device, allow_cpu=args.allow_cpu)
    if worker.handshake.get("status") != "ready":
        worker.close()
        # This IS a real D21.1b-e result (the policy refusing an unsafe GPU), so it is
        # returned as data instead of a traceback -- rerun with Ollama idle, or with
        # --allow-cpu, to get clips.
        return {
            "project_id": PINNED_PROJECT_ID,
            "worker_handshake": worker.handshake,
            "gpu_snapshots": gpu_snapshots,
            "clips": [],
            "note": "worker refused to load under the free-VRAM policy; no clips synthesized",
        }

    clips: list[dict[str, Any]] = []
    clip_paths_in_order: list[Path] = []
    try:
        voice_picks, voice_measurements = _pick_voices(
            worker, reference_clips, {"male": args.male_voice, "female": args.female_voice}
        )
        load_result = worker.request({"command": "load"})
        if load_result.get("status") != "ok":
            raise SpikeError(f"model load failed: {load_result.get('message')}")
        gpu_snapshots.append(_gpu_snapshot("after_model_load"))

        for line in lines:
            for gender, voice_path in voice_picks.items():
                filename = f"styletts2_{gender}_{voice_path.stem}_line{line['index']}.wav"
                output_path = SPIKE_OUTPUT_DIR / filename
                result = worker.request(
                    {"text": line["text"], "target_voice_path": str(voice_path),
                     "output_path": str(output_path)}
                )
                clips.append(
                    {"engine": "styletts2", "voice": voice_path.name, "gender": gender,
                     "line_index": line["index"], "filename": filename, **result}
                )
                if result["status"] == "ok":
                    clip_paths_in_order.append(output_path)

        gpu_snapshots.append(_gpu_snapshot("after_synthesis"))
        worker_stats = worker.request({"command": "stats"})
        unload_result = worker.request({"command": "unload"})
        gpu_snapshots.append(_gpu_snapshot("after_unload"))
    finally:
        worker.close()

    for line in lines:
        for gender, voice_id in EDGE_VOICES.items():
            filename = f"edge_{gender}_line{line['index']}.mp3"
            output_path = SPIKE_OUTPUT_DIR / filename
            result = await _edge_tts_request(line["text"], voice_id, output_path)
            clips.append(
                {"engine": "edge_tts", "voice": voice_id, "gender": gender,
                 "line_index": line["index"], "filename": filename, **result}
            )
            if result["status"] == "ok":
                clip_paths_in_order.append(output_path)

    comparison_path = SPIKE_OUTPUT_DIR / "spike_comparison_styletts2.mp3"
    _build_comparison_mp3(clip_paths_in_order, comparison_path)

    return {
        "project": {"id": project["id"], "name": project["name"], "topic": project["topic"],
                    "cefr_level": project["cefr_level"]},
        "lines": [{"index": line_data["index"], "text": line_data["text"],
                   "speaker": line_data["speaker"]["name"]} for line_data in lines],
        "worker_handshake": worker.handshake,
        "voice_picks": {gender: path.name for gender, path in voice_picks.items()},
        "voice_measurements": voice_measurements,
        "model_load": load_result,
        "clips": clips,
        "worker_stats": worker_stats,
        "unload": unload_result,
        "gpu_snapshots": gpu_snapshots,
        "comparison_mp3": str(comparison_path),
        "worker_stderr_log": str(worker.stderr_log),
    }


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Task 21.1b StyleTTS 2 spike runner")
    parser.add_argument("--device", choices=["auto", "cuda", "cpu"], default="auto",
                        help="passed to the worker; auto applies the D21.1b-e free-VRAM policy")
    parser.add_argument("--allow-cpu", action="store_true",
                        help="synthesize on CPU instead of stopping when the GPU is unusable")
    parser.add_argument("--male-voice", help="reference clip filename to use instead of the F0 pick")
    parser.add_argument("--female-voice", help="reference clip filename to use instead of the F0 pick")
    return parser.parse_args()


if __name__ == "__main__":
    measurements = asyncio.run(_main(_parse_args()))
    print(json.dumps(measurements, indent=2))
