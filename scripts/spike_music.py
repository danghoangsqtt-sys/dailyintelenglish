r"""Task 22.1 spike: ACE-Step 1.5 instrumental beds on the RTX 3060. Not shipped.

Runs in venv-music (Python 3.11, the versions pinned by ACE-Step 1.5's own uv.lock):

    venv-music\Scripts\python scripts\spike_music.py --out data\tmp\music-spike

For each style family (D49) it makes (a) one 8-minute piece and (b) one 150 s piece looped to
8 minutes with 3 s equal-power crossfades (D47), logging wall time and peak VRAM; then it
compares the 0.6B and 1.7B planner LMs on one family. MP3 copies are made for listening.
"""

from __future__ import annotations

import argparse
import json
import math
import os
import subprocess
import sys
import threading
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ACE_ROOT = ROOT / "models" / "music" / "ACE-Step-1.5"
sys.path.insert(0, str(ACE_ROOT))
os.environ.setdefault("HF_HOME", str(ROOT / "models" / "music" / "hf"))

import torch  # noqa: E402
import torchaudio  # noqa: E402

from acestep.handler import AceStepHandler  # noqa: E402
from acestep.inference import GenerationConfig, GenerationParams, generate_music  # noqa: E402
from acestep.llm_inference import LLMHandler  # noqa: E402

FAMILIES = {
    "lofi": "lofi hip hop, mellow, soft electric piano, warm bass, vinyl crackle, relaxed, background music, instrumental",
    "acoustic": "acoustic guitar and warm piano, gentle, soft strings, calm, background music, instrumental",
    "upbeat": "bright upbeat corporate pop, light percussion, ukulele, claps, positive, background music, instrumental",
}
FULL_SECONDS, LOOP_SECONDS, CROSSFADE_SECONDS = 480, 150, 3.0


class VramSampler:
    """Peak nvidia-smi memory.used while a block runs (covers non-torch allocations too)."""

    def __init__(self) -> None:
        self.peak, self._stop = 0, threading.Event()

    def _run(self) -> None:
        while not self._stop.is_set():
            try:
                used = int(subprocess.run(
                    ["nvidia-smi", "--query-gpu=memory.used", "--format=csv,noheader,nounits"],
                    capture_output=True, text=True, timeout=5).stdout.strip().splitlines()[0])
                self.peak = max(self.peak, used)
            except Exception:
                pass
            time.sleep(0.5)

    def __enter__(self):
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()
        return self

    def __exit__(self, *exc) -> None:
        self._stop.set()
        self._thread.join()


def loop_with_crossfade(source: Path, target: Path, seconds: float) -> None:
    wave, rate = torchaudio.load(str(source))
    fade = int(CROSSFADE_SECONDS * rate)
    ramp = torch.linspace(0, math.pi / 2, fade)
    fade_in, fade_out = torch.sin(ramp), torch.cos(ramp)  # equal-power
    out = wave.clone()
    while out.shape[1] < seconds * rate:
        tail, head = out[:, -fade:] * fade_out, wave[:, :fade] * fade_in
        out = torch.cat([out[:, :-fade], tail + head, wave[:, fade:]], dim=1)
    torchaudio.save(str(target), out[:, :int(seconds * rate)], rate)


def to_mp3(source: Path) -> Path:
    target = source.with_suffix(".mp3")
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(source), "-b:a", "192k", str(target)], check=True)
    return target


def generate(dit, llm, caption: str, seconds: int, seed: int, out: Path, name: str, log: list, lm: str) -> Path:
    """lm "none": DiT only. Otherwise the LM only fills metadata (BPM, key, a rewritten caption),
    never the audio codes: run 1 showed the full LM plan of an 8-minute piece took ~6 min and left
    too little VRAM for the 480 s decode (2.24 GB free, 2.9 GB needed)."""
    torch.cuda.reset_peak_memory_stats()
    started = time.monotonic()
    with VramSampler() as sampler:
        result = generate_music(
            dit, llm,
            GenerationParams(caption=caption, lyrics="[Instrumental]", instrumental=True, duration=seconds, seed=seed,
                             thinking=False, use_cot_metas=llm is not None, use_cot_caption=llm is not None,
                             use_cot_language=False),
            GenerationConfig(batch_size=1, use_random_seed=False, seeds=[seed], audio_format="wav"),
            save_dir=str(out / "raw"),
        )
    if not result.success:
        raise RuntimeError(f"{name}: {result.error}")
    produced = Path(result.audios[0]["path"])
    target = out / f"{name}.wav"
    produced.replace(target)
    info = torchaudio.info(str(target))
    entry = {"name": name, "lm": lm, "requested_s": seconds, "seconds": round(info.num_frames / info.sample_rate, 1),
             "sample_rate": info.sample_rate, "wall_s": round(time.monotonic() - started, 1),
             "torch_peak_mb": round(torch.cuda.max_memory_allocated() / 2**20), "smi_peak_mb": sampler.peak}
    log.append(entry)
    print(json.dumps(entry), flush=True)
    return target


def load(lm_model: str | None):
    dit = AceStepHandler()
    message, ok = dit.initialize_service(project_root=str(ACE_ROOT), config_path="acestep-v15-turbo",
                                         device="cuda", offload_to_cpu=False)
    if not ok:
        raise RuntimeError(f"DiT init failed: {message}")
    if lm_model is None:
        return dit, None
    llm = LLMHandler()
    message, ok = llm.initialize(checkpoint_dir=str(ACE_ROOT / "checkpoints"), lm_model_path=lm_model,
                                 backend="pt", device="cuda", offload_to_cpu=True, dtype=None)
    if not ok:
        raise RuntimeError(f"LM init failed: {message}")
    return dit, llm


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", default=str(ROOT / "data" / "tmp" / "music-spike"))
    parser.add_argument("--only-lm", choices=["lm17", "lm06"],
                        help="rerun just this LM comparison and merge it into an existing log.json")
    args = parser.parse_args()
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    log_path = out / "log.json"
    log: list = []
    if args.only_lm:
        log = [e for e in json.loads(log_path.read_text(encoding="utf-8")) if args.only_lm not in e["name"]]
    else:
        run_dit_only(out, log)
    lms = (("acestep-5Hz-lm-1.7B", "lm17"), ("acestep-5Hz-lm-0.6B", "lm06"))
    for lm_model, tag in lms:
        if args.only_lm and tag != args.only_lm:
            continue
        try:
            dit, llm = load(lm_model)
            for seconds in (LOOP_SECONDS, FULL_SECONDS):
                to_mp3(generate(dit, llm, FAMILIES["lofi"], seconds, 7, out, f"lofi_{seconds}s_{tag}", log, tag))
            del dit, llm
            torch.cuda.empty_cache()
        except Exception as exc:  # record and continue with the next LM
            log.append({"name": tag, "error": f"{type(exc).__name__}: {exc}"[:300]})
            print(json.dumps(log[-1]), flush=True)
    log_path.write_text(json.dumps(log, indent=1), encoding="utf-8")
    print("done", flush=True)
    return 0


def run_dit_only(out: Path, log: list) -> None:
    started = time.monotonic()
    dit, llm = load(None)
    log.append({"name": "load DiT turbo", "wall_s": round(time.monotonic() - started, 1)})
    for family, caption in FAMILIES.items():
        full = generate(dit, llm, caption, FULL_SECONDS, 7, out, f"{family}_full_480s", log, "none")
        source = generate(dit, llm, caption, LOOP_SECONDS, 7, out, f"{family}_loopsrc_150s", log, "none")
        looped = out / f"{family}_looped_480s.wav"
        loop_with_crossfade(source, looped, FULL_SECONDS)
        for path in (full, source, looped):
            to_mp3(path)
    del dit
    torch.cuda.empty_cache()


if __name__ == "__main__":
    sys.exit(main())
