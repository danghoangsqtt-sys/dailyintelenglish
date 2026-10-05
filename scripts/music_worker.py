r"""Task 22.2 (Phase 22) -- local ACE-Step 1.5 music worker process.

Runs INSIDE `venv-music/` (Python 3.11, pinned in `requirements-music.txt`). It is a separate
venv and a subprocess for the same reasons as `image_worker.py`:
- ACE-Step's torch pins differ from every other venv here;
- it must stay out of the packaged .exe;
- a worker that exits returns all of its VRAM, which the Task 20.1 GPU lease relies on.
The parent (`app/services/music/engine.py`) holds that lease while this process is alive.

Protocol: the same line-delimited JSON over stdin/stdout as `image_worker.py`. The first line
is a handshake (`ready` / `unavailable`), then there is one response per request. A
per-request failure never kills the worker.

    {"command": "load", "lm": "none" | "0.6B" | "1.7B"}
    {"command": "generate", "caption": "...", "duration_s": 480, "seed": 7,
     "strategy": "full" | "loop", "output_path": ".../track.wav"}
    {"command": "stats"}
    {"command": "unload"}

Spike 22.1 (docs/operations/phase22-spike-music.md) measured on the RTX 3060 12 GB:
- DiT-only, 480 s: ~34 s, torch peak ~6.9 GB;
- the LM only fills metadata (BPM, key, rewritten caption), never the audio codes. The full
  "thinking" plan took ~6 min for 480 s and then failed ACE-Step's own VRAM preflight.

ACE-Step 1.5 code and weights: MIT (checked 2026-10-05). The source checkout and weights live in
models/music/ACE-Step-1.5 (gitignored).
"""

from __future__ import annotations

import argparse
import json
import math
import os
import shutil
import sys
import time
import uuid
from pathlib import Path
from typing import Any

# Only `_write_protocol_line` may touch the real stdout: ACE-Step and transformers print freely.
_PROTOCOL_STDOUT = sys.stdout
sys.stdout = sys.stderr

PROJECT_ROOT = Path(__file__).resolve().parent.parent
ACE_ROOT = PROJECT_ROOT / "models" / "music" / "ACE-Step-1.5"
os.environ.setdefault("HF_HOME", str(PROJECT_ROOT / "models" / "music" / "hf"))

DIT_CONFIG = "acestep-v15-turbo"
LM_MODELS = {"0.6B": "acestep-5Hz-lm-0.6B", "1.7B": "acestep-5Hz-lm-1.7B"}
MODEL_ID = f"ACE-Step 1.5 {DIT_CONFIG}"
MAX_PIECE_SECONDS = 600  # ACE-Step's own duration limit
LOOP_SEGMENT_SECONDS = 150
CROSSFADE_SECONDS = 3.0


def _log(message: str) -> None:
    print(message, file=sys.stderr, flush=True)


def _write_protocol_line(payload: dict[str, Any]) -> None:
    _PROTOCOL_STDOUT.write(json.dumps(payload) + "\n")
    _PROTOCOL_STDOUT.flush()


def _mb(value: int) -> int:
    return round(value / 2**20)


def piece_seconds(duration_s: float, strategy: str) -> float:
    """Length of the one piece ACE-Step makes: the whole track, or a segment to loop."""
    if strategy == "full" and duration_s <= MAX_PIECE_SECONDS:
        return duration_s
    return min(LOOP_SEGMENT_SECONDS, duration_s)


def loop_with_crossfade(torch: Any, torchaudio: Any, source: Path, target: Path, seconds: float) -> None:
    """Repeat `source` to `seconds` with equal-power crossfades (spike 22.1)."""
    wave, rate = torchaudio.load(str(source))
    fade = int(CROSSFADE_SECONDS * rate)
    ramp = torch.linspace(0, math.pi / 2, fade)
    fade_in, fade_out = torch.sin(ramp), torch.cos(ramp)
    out = wave.clone()
    while out.shape[1] < seconds * rate:
        tail, head = out[:, -fade:] * fade_out, wave[:, :fade] * fade_in
        out = torch.cat([out[:, :-fade], tail + head, wave[:, fade:]], dim=1)
    torchaudio.save(str(target), out[:, :int(seconds * rate)], rate)


class MusicWorker:
    def __init__(self, device: str) -> None:
        import torch
        import torchaudio

        self.torch, self.torchaudio, self.device = torch, torchaudio, device
        self.dit: Any = None
        self.llm: Any = None
        self.lm = "none"

    def load(self, request: dict[str, Any]) -> dict[str, Any]:
        lm = request.get("lm", "none")
        if lm != "none" and lm not in LM_MODELS:
            raise ValueError(f"unknown lm: {lm!r}")
        if self.dit is not None:
            if lm == self.lm:
                return {"status": "ok", "already_loaded": True, "model": MODEL_ID, "lm": lm}
            self.unload()
        started = time.monotonic()
        sys.path.insert(0, str(ACE_ROOT))
        from acestep.handler import AceStepHandler
        from acestep.llm_inference import LLMHandler

        dit = AceStepHandler()
        message, ok = dit.initialize_service(project_root=str(ACE_ROOT), config_path=DIT_CONFIG,
                                             device=self.device, offload_to_cpu=False)
        if not ok:
            raise RuntimeError(f"DiT init failed: {message}")
        llm = None
        if lm != "none":
            llm = LLMHandler()
            message, ok = llm.initialize(checkpoint_dir=str(ACE_ROOT / "checkpoints"), lm_model_path=LM_MODELS[lm],
                                         backend="pt", device=self.device, offload_to_cpu=True, dtype=None)
            if not ok:
                raise RuntimeError(f"LM init failed: {message}")
        self.dit, self.llm, self.lm = dit, llm, lm
        return {"status": "ok", "model": MODEL_ID, "lm": lm, "wall_time_sec": round(time.monotonic() - started, 3)}

    def generate(self, request: dict[str, Any]) -> dict[str, Any]:
        if self.dit is None:
            raise RuntimeError("no model loaded -- send load first")
        from acestep.inference import GenerationConfig, GenerationParams, generate_music

        torch, torchaudio = self.torch, self.torchaudio
        caption, seed = str(request["caption"]), int(request["seed"])
        duration_s, strategy = float(request["duration_s"]), request.get("strategy", "full")
        if strategy not in ("full", "loop"):
            raise ValueError(f"unknown strategy: {strategy!r}")
        output_path = Path(request["output_path"])
        output_path.parent.mkdir(parents=True, exist_ok=True)
        piece = piece_seconds(duration_s, strategy)
        work_dir = output_path.parent / f".raw-{uuid.uuid4().hex}"
        if self.device == "cuda":
            torch.cuda.reset_peak_memory_stats()
        started = time.monotonic()
        try:
            uses_lm = self.llm is not None
            result = generate_music(
                self.dit, self.llm,
                GenerationParams(caption=caption, lyrics="[Instrumental]", instrumental=True, duration=piece,
                                 seed=seed, thinking=False, use_cot_metas=uses_lm, use_cot_caption=uses_lm,
                                 use_cot_language=False),
                GenerationConfig(batch_size=1, use_random_seed=False, seeds=[seed], audio_format="wav"),
                save_dir=str(work_dir),
            )
            if not result.success:
                raise RuntimeError(f"generation failed: {result.error}")
            produced = Path(result.audios[0]["path"])
            looped = piece < duration_s
            if looped:
                loop_with_crossfade(torch, torchaudio, produced, output_path, duration_s)
            else:
                shutil.move(str(produced), str(output_path))
        finally:
            shutil.rmtree(work_dir, ignore_errors=True)
        info = torchaudio.info(str(output_path))
        return {
            "status": "ok", "output_path": str(output_path), "model": MODEL_ID, "lm": self.lm,
            "strategy": "loop" if looped else "full", "piece_s": piece,
            "duration_s": round(info.num_frames / info.sample_rate, 2), "sample_rate": info.sample_rate,
            "wall_time_sec": round(time.monotonic() - started, 3),
            "vram_peak_mb": _mb(torch.cuda.max_memory_allocated()) if self.device == "cuda" else None,
        }

    def stats(self) -> dict[str, Any]:
        torch = self.torch
        return {
            "status": "ok", "loaded": self.dit is not None, "lm": self.lm, "device": self.device,
            "vram_allocated_mb": _mb(torch.cuda.memory_allocated()) if self.device == "cuda" else None,
            "vram_reserved_mb": _mb(torch.cuda.memory_reserved()) if self.device == "cuda" else None,
        }

    def unload(self) -> dict[str, Any]:
        import gc

        was_loaded = self.dit is not None
        self.dit, self.llm, self.lm = None, None, "none"
        gc.collect()
        if self.device == "cuda":
            self.torch.cuda.empty_cache()
        # The real release is the process exit; this is reported so the gap stays visible.
        return {"status": "ok", "was_loaded": was_loaded, **{k: v for k, v in self.stats().items() if k != "status"}}


def _handle(worker: MusicWorker, request: dict[str, Any]) -> dict[str, Any]:
    command = request.get("command")
    if command == "load":
        return worker.load(request)
    if command == "generate":
        return worker.generate(request)
    if command == "stats":
        return worker.stats()
    if command == "unload":
        return worker.unload()
    raise ValueError(f"unknown command: {command!r}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="ACE-Step 1.5 music worker (Task 22.2)")
    parser.parse_args(argv)

    import torch

    base = {"torch": torch.__version__, "torch_cuda_build": torch.version.cuda,
            "cuda_available": torch.cuda.is_available()}
    if not torch.cuda.is_available():
        # ACE-Step on CPU takes minutes per piece; never measure CPU while claiming GPU.
        reason = "cpu_only_torch_build" if torch.version.cuda is None else "no_cuda_device"
        _write_protocol_line({"status": "unavailable", "reason": reason, **base})
        return 0
    if not (ACE_ROOT / "acestep").is_dir() or not (ACE_ROOT / "checkpoints" / DIT_CONFIG).is_dir():
        _write_protocol_line({"status": "unavailable", "reason": "ace_step_missing", **base})
        return 0

    worker = MusicWorker("cuda")
    _write_protocol_line({"status": "ready", "device": "cuda", "gpu_name": torch.cuda.get_device_name(0), **base})
    _log("music_worker: ready on cuda")

    for raw_line in sys.stdin:
        line = raw_line.strip()
        if not line:
            continue
        try:
            response = _handle(worker, json.loads(line))
        except Exception as exc:  # noqa: BLE001 -- a bad request must not kill the worker
            response = {"status": "error", "message": f"{type(exc).__name__}: {exc}"}
        _write_protocol_line(response)

    _log("music_worker: stdin closed, exiting")
    return 0


if __name__ == "__main__":
    sys.exit(main())
