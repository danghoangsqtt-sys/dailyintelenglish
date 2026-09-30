"""Task 21.1b (Phase 21 spike) -- StyleTTS 2 worker process.

Runs INSIDE `venv-styletts2/` (Python 3.11 -- `styletts2`'s own `transformers==4.40.2` ->
`tokenizers==0.19.1` dependency has no prebuilt wheel for this project's own Python 3.14
and fails to build its Rust/PyO3 bindings there, confirmed real via a non-dry-run install
attempt; see `.viepilot/phases/21-tts-kokoro/tasks/task-21.1b.md` D21.1b-a). Never
imported by `app/` -- invoked only as a subprocess, mirroring `kokoro_worker.py`'s exact
shape (Task 21.1) and `video-renderer/`'s Remotion subprocess pattern (Phase 19).

Protocol -- identical to `kokoro_worker.py`: one JSON request per stdin line, one JSON
response per stdout line, EOF on stdin means the parent is done:

    {"text": "...", "target_voice_path": "C:/.../ref.wav", "output_path": "C:/.../out.wav"}

    {"status": "ok", "duration_sec": 3.15, "wall_time_sec": 1.09,
     "word_boundaries": [{"text": "Hey", "offset_sec": 0.28, "duration_sec": 0.2}, ...]}
    {"status": "error", "message": "..."}

D21.1b-d: StyleTTS 2's own `inference()` returns only a raw audio array -- no native
per-word timing (confirmed by reading the installed package's real source). This worker
runs `whisper-timestamped` as a post-synthesis forced-aligner on its own output to
recover real per-word timestamps, independent of the TTS engine itself.
"""

from __future__ import annotations

import json
import os
import sys
import time
from pathlib import Path

# Real finding (Task 21.1, carried forward): huggingface_hub, nltk, and other libraries in
# this dependency tree write raw text directly to stdout (not via `logging`), which would
# corrupt this worker's JSON protocol -- confirmed live during `styletts2` install ("nltk_data]
# Downloading package punkt..." printed to stdout on plain import). Same fix as
# `kokoro_worker.py`: redirect stdout to stderr before any imports, write protocol responses
# through a saved real-stdout handle explicitly.
_PROTOCOL_STDOUT = sys.stdout
sys.stdout = sys.stderr

PROJECT_ROOT = Path(__file__).resolve().parent.parent
# Some of styletts2's own transitive deps (e.g. anything routing through huggingface_hub)
# read HF_HOME at import/first-use time -- set before any imports, same convention as
# kokoro_worker.py's HF_HOME redirect (D21.1-b precedent).
os.environ.setdefault("HF_HOME", str(PROJECT_ROOT / "models" / "styletts2" / "hf"))
WHISPER_CACHE_DIR = PROJECT_ROOT / "models" / "styletts2" / "whisper"
OUTPUT_SAMPLE_RATE_HZ = 24000


def _write_protocol_line(payload: dict) -> None:
    _PROTOCOL_STDOUT.write(json.dumps(payload) + "\n")
    _PROTOCOL_STDOUT.flush()


def _log(message: str) -> None:
    """Diagnostic logging to stderr only -- stdout is reserved for the JSON protocol."""
    print(message, file=sys.stderr, flush=True)


def _word_boundaries_via_whisper(whisper_model, wav_path: Path) -> list[dict]:
    """D21.1b-d: forced-alignment fallback -- StyleTTS 2 itself emits no timing, so this
    re-transcribes its own real output with Whisper + word-level alignment. Real, not
    estimated: derived from the actual synthesized audio, not the input text."""
    import whisper_timestamped as wt

    result = wt.transcribe(whisper_model, str(wav_path), language="en", vad=False)
    boundaries: list[dict] = []
    for segment in result.get("segments", []):
        for word in segment.get("words", []):
            text = word.get("text", "").strip()
            if not text:
                continue
            boundaries.append(
                {
                    "text": text,
                    "offset_sec": round(word["start"], 4),
                    "duration_sec": round(word["end"] - word["start"], 4),
                }
            )
    return boundaries


def _synthesize(model, whisper_model, text: str, target_voice_path: str, output_path: Path) -> dict:
    import soundfile as sf

    output_path.parent.mkdir(parents=True, exist_ok=True)
    start = time.monotonic()
    audio = model.inference(
        text,
        target_voice_path=target_voice_path,
        output_sample_rate=OUTPUT_SAMPLE_RATE_HZ,
    )
    wall_time_sec = time.monotonic() - start

    sf.write(str(output_path), audio, OUTPUT_SAMPLE_RATE_HZ)
    duration_sec = len(audio) / OUTPUT_SAMPLE_RATE_HZ

    word_boundaries = _word_boundaries_via_whisper(whisper_model, output_path)

    return {
        "status": "ok",
        "duration_sec": round(duration_sec, 4),
        "wall_time_sec": round(wall_time_sec, 4),
        "word_boundaries": word_boundaries,
    }


def main() -> int:
    # D21.1b-b: redirects styletts2's cached_path()-based model downloads into
    # models/styletts2/ instead of the global ~/.cache/cached_path -- must be set before
    # importing/constructing the model.
    from cached_path import set_cache_dir

    set_cache_dir(PROJECT_ROOT / "models" / "styletts2")

    _log("styletts2_worker: importing styletts2 (one-time cost)...")
    import_start = time.monotonic()
    import torch
    from styletts2 import tts

    # Real finding: torch>=2.6 changed torch.load()'s default weights_only to True (a
    # real security-motivated breaking change) -- styletts2==0.1.6's own models.py calls
    # torch.load() on its real checkpoints (from the original authors' GitHub repo)
    # without passing weights_only=False. These are legacy full-training-state
    # checkpoints (real, saved before the 2.6 default flip) referencing multiple unsafe
    # globals one at a time as loading progresses (confirmed live: first `getattr`, then
    # `torch.optim.lr_scheduler.OneCycleLR` -- allow-listing each individually would be
    # real whack-a-mole against an upstream file we don't control). Since the checkpoint
    # source is verified (the original StyleTTS 2 authors' own GitHub/HF repos, D21.1b-b)
    # and this runs only inside the isolated subprocess venv, restoring the pre-2.6
    # default (weights_only=False) for this process is the honest fix -- exactly the
    # first option torch's own error message offers, not a security regression for code
    # that already trusts its model source.
    _real_torch_load = torch.load

    def _torch_load_legacy_default(*args, **kwargs):
        kwargs.setdefault("weights_only", False)
        return _real_torch_load(*args, **kwargs)

    torch.load = _torch_load_legacy_default

    _log(f"styletts2_worker: import done in {time.monotonic() - import_start:.2f}s")

    load_start = time.monotonic()
    model = tts.StyleTTS2()
    _log(f"styletts2_worker: model loaded in {time.monotonic() - load_start:.2f}s "
         f"(device={model.device})")

    whisper_start = time.monotonic()
    import whisper

    whisper_model = whisper.load_model("base.en", download_root=str(WHISPER_CACHE_DIR))
    _log(f"styletts2_worker: whisper alignment model loaded in {time.monotonic() - whisper_start:.2f}s")

    _log("styletts2_worker: ready, waiting for requests on stdin")

    for raw_line in sys.stdin:
        line = raw_line.strip()
        if not line:
            continue
        try:
            request = json.loads(line)
            response = _synthesize(
                model, whisper_model, request["text"], request["target_voice_path"],
                Path(request["output_path"]),
            )
        except Exception as exc:  # noqa: BLE001 -- a bad request must not kill the worker
            response = {"status": "error", "message": f"{type(exc).__name__}: {exc}"}
        _write_protocol_line(response)

    _log("styletts2_worker: stdin closed, exiting")
    return 0


if __name__ == "__main__":
    sys.exit(main())
