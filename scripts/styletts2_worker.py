"""Task 21.1b (Phase 21 spike, Amendment A) -- StyleTTS 2 TTS worker process.

Runs INSIDE `venv-styletts2/` (Python 3.11 -- `styletts2==0.1.6` cannot be built on this
project's own Python 3.14: it resolves `transformers==4.40.2` -> `tokenizers==0.19.1`,
which has no 3.14 wheel and fails its Rust/PyO3 source build with "the configured Python
interpreter version (3.14) is newer than PyO3's maximum supported version (3.12)". See
`.viepilot/phases/21-tts-kokoro/tasks/task-21.1b.md` D21.1b-a for the full real
investigation). Never imported by `app/` or by any script running under the project's own
`venv/` -- invoked only as a subprocess, exactly like `scripts/kokoro_worker.py`
(Task 21.1) and `video-renderer/`'s Remotion subprocess before it.

Protocol (mirrors `kokoro_worker.py`, with two additions noted below): reads one line of
JSON per request from stdin until stdin closes (EOF = parent is done, exit cleanly), and
writes exactly one line of JSON per request to stdout, flushed immediately.

**Addition 1 -- a startup handshake line.** Kokoro was CPU-only, so its worker could just
load and go. StyleTTS 2 is GPU-based and shares one 12 GB RTX 3060 with Ollama qwen
(7-8 GB when loaded via the cloud-AI fallback chain), so the parent has to learn the
device decision *before* it commits to this engine. The first stdout line is therefore
always one of:

    {"status": "ready", "device": "cuda", "free_vram_mb": 10286, ...}
    {"status": "unavailable", "reason": "insufficient_vram", "free_vram_mb": 3916, ...}

On `"unavailable"` the worker exits 0 without loading anything and the parent falls back
to Edge TTS -- D21.1b-e option (ii), the same shape as Task 19.7's I36 fallback
invariant. The 6144 MB default threshold is a real measured number, not a round guess:
this project's own RTX 3060 reports 10286 MiB free at idle but only 3916 MiB free with
`qwen3.5:9b` loaded (real `nvidia-smi` + `ollama ps` measurement, task-21.1b.md
D21.1b-e), and StyleTTS 2's own claimed need is 4-6 GB -- so 6144 sits in the measured
gap between a safe and an unsafe state.

**Addition 2 -- explicit `load`/`unload` commands.** D21.1b-e option (i): a worker can be
spawned and kept alive without holding VRAM, then load before a batch and release after,
so the GPU is free for the qwen fallback in between. A synthesis request auto-loads if
the model is not resident, so a parent that does not care can ignore both commands.

Requests (one JSON object per line):

    {"text": "...", "target_voice_path": ".../1221-135767-0014.wav",
     "output_path": ".../line0_female.wav"}
    {"command": "load"}
    {"command": "unload"}
    {"command": "analyze_voice", "path": ".../1221-135767-0014.wav"}
    {"command": "stats"}

Responses:

    {"status": "ok", "duration_sec": 3.15, "wall_time_sec": 1.09, "rtf": 0.35, ...}
    {"status": "error", "message": "..."}

A per-request failure never crashes the worker -- the next request is still processed.
Binary audio never crosses the pipe; only file paths and JSON.

`analyze_voice` exists because StyleTTS 2 is a **reference-audio voice-cloning model, not
a named-voice model** (confirmed by reading the installed `styletts2/tts.py`: `inference`'s
only voice parameter is `target_voice_path`, "Path to audio file of target voice to
clone"). The spike's two "voices" are therefore two reference clips picked out of the
upstream `reference_audio.zip`, and the male/female pick has to be confirmed by a real
pitch measurement rather than guessed from a LibriTTS speaker-id filename. `librosa` lives
in this venv, not the project's own, so the measurement runs here and the parent asks for
it over the same protocol.
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

# Real finding, confirmed by reading `styletts2/tts.py` directly: the package writes to
# stdout in at least three places that would corrupt this JSON protocol --
# `nltk.download('punkt')` runs unconditionally at **module import time** (line 3 of
# tts.py, before any of our code gets control) and prints `[nltk_data] ...` lines, and
# `load_model()` prints "Invalid or missing model checkpoint path. Loading default
# model..." plus a matching config line on every default-path load. Task 21.1 hit the
# same class of bug with `huggingface_hub`/`misaki` and established the fix: save the real
# stdout handle, point this process's own stdout at stderr for the rest of its life, and
# write every protocol response through `_PROTOCOL_STDOUT` explicitly -- never `print()`.
_PROTOCOL_STDOUT = sys.stdout
sys.stdout = sys.stderr

PROJECT_ROOT = Path(__file__).resolve().parent.parent
MODEL_CACHE_DIR = PROJECT_ROOT / "models" / "styletts2"

# D21.1b-b: `styletts2` fetches every checkpoint through the `cached_path` library, whose
# cache root is read from this env var (confirmed in the installed
# `cached_path/common.py`: `os.getenv("CACHED_PATH_CACHE_ROOT", Path.home() / ".cache" /
# "cached_path")`). Redirecting it keeps the ~873 MB of weights inside `models/styletts2/`
# -- gitignored by the existing `models/*` rule -- instead of the user's global cache,
# mirroring Task 21.1's `HF_HOME` redirect for Kokoro. `NLTK_DATA` does the same for the
# import-time `punkt` download. Both must be set before `styletts2` is imported.
os.environ.setdefault("CACHED_PATH_CACHE_ROOT", str(MODEL_CACHE_DIR / "cached_path"))
os.environ.setdefault("NLTK_DATA", str(MODEL_CACHE_DIR / "nltk_data"))

# D21.1b-e: the real measured safety threshold. Overridable so the spike report can show
# behaviour on both sides of it without editing code.
DEFAULT_MIN_FREE_VRAM_MB = int(os.environ.get("DIE_STYLETTS2_MIN_FREE_VRAM_MB", "6144"))

# `inference()`'s own default and the rate `scipy.io.wavfile.write` is handed.
OUTPUT_SAMPLE_RATE_HZ = 24000


def _log(message: str) -> None:
    """Diagnostic logging to stderr only -- stdout is reserved for the JSON protocol."""
    print(message, file=sys.stderr, flush=True)


def _write_protocol_line(payload: dict[str, Any]) -> None:
    _PROTOCOL_STDOUT.write(json.dumps(payload) + "\n")
    _PROTOCOL_STDOUT.flush()


def _query_free_vram_mb() -> int | None:
    """Free VRAM per `nvidia-smi`, or None when there is no usable NVIDIA GPU.

    Deliberately shells out instead of asking torch: this runs **before** torch is
    imported, so a machine that must not touch the GPU at all (threshold not met) never
    pays a CUDA-context initialisation, and a machine with no driver at all just gets None
    instead of an import-time failure.
    """
    try:
        completed = subprocess.run(
            ["nvidia-smi", "--query-gpu=memory.free", "--format=csv,noheader,nounits"],
            capture_output=True,
            text=True,
            timeout=15,
            check=True,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    first_line = completed.stdout.strip().splitlines()[0] if completed.stdout.strip() else ""
    try:
        return int(first_line.strip())
    except ValueError:
        return None


def _ensure_punkt_tab() -> None:
    """Fetch the tokenizer data `styletts2` actually needs but never downloads itself.

    Real latent bug, found reading the installed sources and then reproduced: `tts.py`
    calls `nltk.download('punkt')` at import, but the `nltk==3.10.3` that resolves under
    `styletts2==0.1.6` has `word_tokenize` -> `PunktTokenizer` look up
    `tokenizers/punkt_tab/<lang>/` instead (nltk/tokenize/punkt.py). With only `punkt`
    present, the first `inference()` call raises `LookupError: Resource 'punkt_tab' not
    found` -- on any machine, network or not. Checked here, once per model load, so the
    failure is a clear load error instead of a mid-batch synthesis error.
    """
    import nltk

    try:
        nltk.data.find("tokenizers/punkt_tab/english/")
        return
    except LookupError:
        pass
    _log("styletts2_worker: fetching nltk 'punkt_tab' (needed by word_tokenize)...")
    nltk.download("punkt_tab", download_dir=os.environ["NLTK_DATA"], quiet=True)
    # Re-check rather than trusting download()'s return value: it reports failure by
    # printing, not by raising (real behaviour -- see the `punkt` failure in the stderr
    # log of any offline or proxied run).
    nltk.data.find("tokenizers/punkt_tab/english/")


def _rss_mb() -> float | None:
    try:
        import psutil
    except ImportError:  # psutil arrives transitively; never fail a request over it
        return None
    return round(psutil.Process().memory_info().rss / (1024 * 1024), 1)


class StyleTTS2Worker:
    """Owns the model's lifetime, the per-voice style cache, and the device decision."""

    def __init__(self, device: str, min_free_vram_mb: int) -> None:
        self.device = device
        self.min_free_vram_mb = min_free_vram_mb
        self._tts: Any | None = None
        # `inference(ref_s=...)` accepts a pre-computed style vector, so `compute_style`
        # runs once per reference clip instead of once per line. Task 21.1's real finding
        # that a first-ever voice use pays a one-time cost (line 0 `am_michael`, RTF 1.03
        # vs ~0.28 for every warm clip) is exactly what this cache is here to avoid.
        self._style_cache: dict[str, Any] = {}
        self.load_seconds: float | None = None
        self.import_seconds: float | None = None

    # -- model lifetime ----------------------------------------------------------------

    @property
    def loaded(self) -> bool:
        return self._tts is not None

    def load(self) -> dict[str, Any]:
        if self._tts is not None:
            return {"already_loaded": True}

        _log("styletts2_worker: importing styletts2 (one-time cost)...")
        import_start = time.monotonic()
        from styletts2 import tts as styletts2_tts

        self.import_seconds = round(time.monotonic() - import_start, 3)
        _log(f"styletts2_worker: import done in {self.import_seconds:.2f}s")
        _ensure_punkt_tab()

        _log("styletts2_worker: loading model (downloads ~873 MB on first ever run)...")
        load_start = time.monotonic()
        self._tts = styletts2_tts.StyleTTS2()
        self.load_seconds = round(time.monotonic() - load_start, 3)
        resolved_device = getattr(self._tts, "device", "unknown")
        _log(
            f"styletts2_worker: model loaded in {self.load_seconds:.2f}s "
            f"on device={resolved_device}"
        )
        if self.device == "cuda" and str(resolved_device) != "cuda":
            # Do not silently synthesize 6 CPU clips while the report claims GPU numbers.
            raise RuntimeError(
                f"requested device=cuda but StyleTTS2 resolved device={resolved_device} "
                "(torch.cuda.is_available() was False -- check the CUDA build of torch)"
            )
        return {
            "already_loaded": False,
            "import_sec": self.import_seconds,
            "model_load_sec": self.load_seconds,
            "device": str(resolved_device),
        }

    def unload(self) -> dict[str, Any]:
        """Release the model and its VRAM -- D21.1b-e option (i), so the GPU is free for
        the Ollama qwen fallback between synthesis batches."""
        was_loaded = self._tts is not None
        self._tts = None
        self._style_cache.clear()
        freed_vram = None
        if was_loaded:
            import gc

            import torch

            gc.collect()
            if torch.cuda.is_available():
                torch.cuda.empty_cache()
                freed_vram = _query_free_vram_mb()
        return {"was_loaded": was_loaded, "free_vram_mb": freed_vram}

    # -- work --------------------------------------------------------------------------

    def _style_for(self, target_voice_path: Path) -> Any:
        key = str(target_voice_path)
        if key not in self._style_cache:
            assert self._tts is not None
            self._style_cache[key] = self._tts.compute_style(str(target_voice_path))
        return self._style_cache[key]

    def synthesize(self, request: dict[str, Any]) -> dict[str, Any]:
        text = request["text"]
        output_path = Path(request["output_path"])
        target_voice_path = Path(request["target_voice_path"])
        if not target_voice_path.is_file():
            raise FileNotFoundError(f"target_voice_path not found: {target_voice_path}")

        load_info = {}
        if not self.loaded:
            load_info = self.load()

        style_start = time.monotonic()
        ref_s = self._style_for(target_voice_path)
        style_seconds = time.monotonic() - style_start

        output_path.parent.mkdir(parents=True, exist_ok=True)
        assert self._tts is not None
        synth_start = time.monotonic()
        audio = self._tts.inference(
            text,
            output_wav_file=str(output_path),
            output_sample_rate=OUTPUT_SAMPLE_RATE_HZ,
            # Upstream defaults, stated explicitly so the spike report can cite the exact
            # settings behind the clips the owner listens to.
            alpha=float(request.get("alpha", 0.3)),
            beta=float(request.get("beta", 0.7)),
            diffusion_steps=int(request.get("diffusion_steps", 5)),
            embedding_scale=float(request.get("embedding_scale", 1)),
            ref_s=ref_s,
        )
        wall_time_sec = time.monotonic() - synth_start

        duration_sec = len(audio) / OUTPUT_SAMPLE_RATE_HZ
        response: dict[str, Any] = {
            "status": "ok",
            "duration_sec": round(duration_sec, 4),
            "wall_time_sec": round(wall_time_sec, 4),
            "style_compute_sec": round(style_seconds, 4),
            "rtf": round(wall_time_sec / duration_sec, 4) if duration_sec else None,
            "device": self.device,
            "rss_mb": _rss_mb(),
            "free_vram_mb": _query_free_vram_mb(),
            # D21.1b-d: empty by design, not by omission. `inference()`'s real return is
            # "audio data as a Numpy array" and nothing else -- there is no native
            # word-timing output to forward. The model *does* predict per-phoneme-token
            # frame durations internally (`pred_dur` in tts.py, ~12.5 ms per frame at the
            # 300-sample mel hop), but `inference()` discards them, so recovering word
            # boundaries needs either a small fork of that method or the
            # `whisper-timestamped` forced-alignment post-process the card names. Both are
            # 21.2 production work; this spike measures quality, and the owner's listening
            # test does not need timings.
            "word_boundaries": [],
        }
        if load_info:
            response["load_info"] = load_info
        return response

    def analyze_voice(self, request: dict[str, Any]) -> dict[str, Any]:
        """Median F0 of a reference clip, so a male/female pick is measured, not guessed.

        `librosa.pyin` rather than a plain autocorrelation: it is already installed here
        (StyleTTS 2 depends on it) and it reports voiced/unvoiced frames, so silence and
        breaths do not drag the median around.
        """
        import librosa
        import numpy as np

        path = Path(request["path"])
        if not path.is_file():
            raise FileNotFoundError(f"voice clip not found: {path}")
        waveform, sample_rate = librosa.load(str(path), sr=None, mono=True)
        f0, voiced_flag, _ = librosa.pyin(
            waveform,
            sr=sample_rate,
            fmin=float(librosa.note_to_hz("C2")),  # ~65 Hz, below any adult speaker
            fmax=float(librosa.note_to_hz("C6")),  # ~1047 Hz, above any adult speaker
        )
        voiced_f0 = f0[voiced_flag & ~np.isnan(f0)]
        if voiced_f0.size == 0:
            raise RuntimeError(f"no voiced frames detected in {path.name}")
        median_f0 = float(np.median(voiced_f0))
        return {
            "status": "ok",
            "filename": path.name,
            "sample_rate": int(sample_rate),
            "duration_sec": round(waveform.shape[0] / sample_rate, 4),
            "median_f0_hz": round(median_f0, 2),
            # The 165 Hz split is the conventional adult male/female boundary; reported
            # alongside the raw number so the report can show the measurement, not just
            # the verdict.
            "inferred_gender": "male" if median_f0 < 165 else "female",
            "voiced_frames": int(voiced_f0.size),
        }

    def stats(self) -> dict[str, Any]:
        return {
            "status": "ok",
            "loaded": self.loaded,
            "device": self.device,
            "import_sec": self.import_seconds,
            "model_load_sec": self.load_seconds,
            "cached_styles": sorted(Path(key).name for key in self._style_cache),
            "rss_mb": _rss_mb(),
            "free_vram_mb": _query_free_vram_mb(),
        }


def _decide_device(requested: str, min_free_vram_mb: int) -> tuple[str, dict[str, Any]]:
    """D21.1b-e option (ii): refuse the GPU rather than risk a CUDA OOM mid-render.

    Returns the device to use and the handshake detail explaining why. `auto` is the
    production policy -- use the GPU when there is measurably enough room, otherwise
    report `unavailable` so the parent falls back to Edge TTS. `--allow-cpu` turns the
    refusal into a CPU run instead, which is what makes a measurement run possible on a
    machine with no NVIDIA GPU at all (the audio is identical either way -- same weights,
    same seeds; only wall time differs).
    """
    free_vram_mb = _query_free_vram_mb()
    detail: dict[str, Any] = {
        "free_vram_mb": free_vram_mb,
        "min_free_vram_mb": min_free_vram_mb,
        "requested_device": requested,
    }
    if requested == "cpu":
        detail["reason"] = "cpu_requested"
        return "cpu", detail
    if requested == "cuda":
        detail["reason"] = "cuda_forced"
        return "cuda", detail
    if free_vram_mb is None:
        detail["reason"] = "no_nvidia_gpu"
        return "unavailable", detail
    if free_vram_mb < min_free_vram_mb:
        detail["reason"] = "insufficient_vram"
        return "unavailable", detail
    detail["reason"] = "sufficient_vram"
    return "cuda", detail


def _handle(worker: StyleTTS2Worker, request: dict[str, Any]) -> dict[str, Any]:
    command = request.get("command")
    if command is None:
        return worker.synthesize(request)
    if command == "load":
        return {"status": "ok", **worker.load()}
    if command == "unload":
        return {"status": "ok", **worker.unload()}
    if command == "analyze_voice":
        return worker.analyze_voice(request)
    if command == "stats":
        return worker.stats()
    raise ValueError(f"unknown command: {command!r}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="StyleTTS 2 subprocess worker")
    parser.add_argument(
        "--device",
        choices=["auto", "cuda", "cpu"],
        default="auto",
        help="auto applies the real D21.1b-e free-VRAM policy (default)",
    )
    parser.add_argument(
        "--allow-cpu",
        action="store_true",
        help="run on CPU instead of reporting unavailable when the GPU is unusable",
    )
    parser.add_argument(
        "--min-free-vram-mb",
        type=int,
        default=DEFAULT_MIN_FREE_VRAM_MB,
        help=f"free-VRAM floor before the GPU is used (default {DEFAULT_MIN_FREE_VRAM_MB})",
    )
    parser.add_argument(
        "--preload",
        action="store_true",
        help="load the model during startup instead of on the first synthesis request",
    )
    args = parser.parse_args(argv)

    device, detail = _decide_device(args.device, args.min_free_vram_mb)
    if device == "unavailable" and args.allow_cpu:
        detail["fallback"] = "cpu_allowed_by_flag"
        device = "cpu"
    if device == "unavailable":
        _write_protocol_line({"status": "unavailable", **detail})
        _log(f"styletts2_worker: not loading -- {detail['reason']}, exiting cleanly")
        return 0
    if device == "cpu":
        # `StyleTTS2.__init__` has no device parameter -- it picks
        # `'cuda' if torch.cuda.is_available() else 'cpu'` itself (real signature,
        # installed tts.py). Hiding the GPU from CUDA is therefore the only way to force
        # CPU, and it must happen before anything in this process imports torch.
        os.environ["CUDA_VISIBLE_DEVICES"] = ""

    worker = StyleTTS2Worker(device=device, min_free_vram_mb=args.min_free_vram_mb)
    handshake: dict[str, Any] = {"status": "ready", "device": device, **detail}
    if args.preload:
        try:
            handshake["load"] = worker.load()
        except Exception as exc:  # noqa: BLE001 -- report the failure over the protocol
            _write_protocol_line(
                {"status": "error", "message": f"{type(exc).__name__}: {exc}"}
            )
            return 1
    handshake["rss_mb"] = _rss_mb()
    _write_protocol_line(handshake)
    _log("styletts2_worker: ready, waiting for requests on stdin")

    for raw_line in sys.stdin:
        line = raw_line.strip()
        if not line:
            continue
        try:
            response = _handle(worker, json.loads(line))
        except Exception as exc:  # noqa: BLE001 -- a bad request must not kill the worker
            response = {"status": "error", "message": f"{type(exc).__name__}: {exc}"}
        _write_protocol_line(response)

    _log("styletts2_worker: stdin closed, exiting")
    return 0


if __name__ == "__main__":
    sys.exit(main())
