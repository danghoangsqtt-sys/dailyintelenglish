"""Task 21.1 (Phase 21 spike) -- Kokoro TTS worker process.

Runs INSIDE `venv-kokoro/` (Python 3.11 -- Kokoro has no published version compatible
with this project's own Python 3.14, see `.viepilot/phases/21-tts-kokoro/tasks/
task-21.1.md` D21.1-a for the real investigation). Never imported by `app/` or by any
script running under the project's own `venv/` -- invoked only as a subprocess, exactly
like `video-renderer/`'s Remotion subprocess pattern.

Protocol (D21.1-a): loads the Kokoro model once on startup, then reads one line of JSON
per synthesis request from stdin until stdin closes (EOF = parent is done, exit cleanly):

    {"text": "...", "voice": "af_heart", "output_path": "C:/.../line0_af_heart.wav"}

For each request, writes exactly one line of JSON to stdout (flushed immediately so the
parent can read it without buffering delay):

    {"status": "ok", "duration_sec": 3.15, "wall_time_sec": 1.09,
     "word_boundaries": [{"text": "Hey", "offset_sec": 0.275, "duration_sec": 0.2}, ...]}
    {"status": "error", "message": "..."}

A per-request failure never crashes the worker -- the next request is still processed.
Binary audio never crosses the pipe; only file paths and JSON (avoids text/binary stream
encoding pitfalls entirely).
"""

from __future__ import annotations

import json
import os
import re
import sys
import time
from pathlib import Path

# Real finding: both `huggingface_hub` (a raw `print()`, "Defaulting repo_id to...") and
# `misaki`'s on-demand `en_core_web_sm` auto-install (a pip subprocess inheriting this
# process's own stdout) write directly to stdout -- not via `logging` or the `warnings`
# module, so they can't be filtered by log level and bypass a plain `contextlib.redirect_
# stdout`-around-imports approach (the auto-install can fire lazily, on the first
# synthesis call, not just at import time). Saving the real stdout handle now and
# permanently redirecting the process's own stdout to stderr is the only robust fix --
# every protocol response below is written through `_PROTOCOL_STDOUT` explicitly, never
# through `print()`/`sys.stdout` (which stays pointed at stderr for the rest of this
# process's life).
_PROTOCOL_STDOUT = sys.stdout
sys.stdout = sys.stderr

PROJECT_ROOT = Path(__file__).resolve().parent.parent
# D21.1-b: redirects Kokoro's model download/cache into models/kokoro/ instead of the
# global ~/.cache/huggingface -- confirmed real via a live HF_HOME probe. Must be set
# before importing kokoro (huggingface_hub reads it at import/first-use time).
os.environ.setdefault("HF_HOME", str(PROJECT_ROOT / "models" / "kokoro"))


def _write_protocol_line(payload: dict) -> None:
    _PROTOCOL_STDOUT.write(json.dumps(payload) + "\n")
    _PROTOCOL_STDOUT.flush()

SAMPLE_RATE_HZ = 24000
# D21.1-d: a token is skipped from the WordBoundary-equivalent output when its text is
# entirely punctuation (matches Edge TTS's own word-only WordBoundary events -- Edge TTS
# never emits a boundary for a bare "," or "?").
_PUNCTUATION_ONLY = re.compile(r"^[^\w]+$", re.UNICODE)


def _log(message: str) -> None:
    """Diagnostic logging to stderr only -- stdout is reserved for the JSON protocol."""
    print(message, file=sys.stderr, flush=True)


def _synthesize(pipeline, text: str, voice: str, output_path: Path) -> dict:
    import numpy as np
    import soundfile as sf

    start = time.monotonic()
    segments = list(pipeline(text, voice=voice))
    if not segments:
        raise RuntimeError("Kokoro pipeline produced no output segments")

    audio_chunks = []
    word_boundaries: list[dict] = []
    time_offset_sec = 0.0
    for result in segments:
        if result.audio is None:
            raise RuntimeError("Kokoro pipeline produced a segment with no audio")
        audio_chunks.append(result.audio.numpy())
        for token in result.tokens or []:
            if token.start_ts is None or token.end_ts is None:
                continue
            if _PUNCTUATION_ONLY.match(token.text):
                continue
            word_boundaries.append(
                {
                    "text": token.text,
                    "offset_sec": round(time_offset_sec + token.start_ts, 4),
                    "duration_sec": round(token.end_ts - token.start_ts, 4),
                }
            )
        time_offset_sec += len(audio_chunks[-1]) / SAMPLE_RATE_HZ

    wall_time_sec = time.monotonic() - start
    full_audio = np.concatenate(audio_chunks) if len(audio_chunks) > 1 else audio_chunks[0]
    output_path.parent.mkdir(parents=True, exist_ok=True)
    sf.write(str(output_path), full_audio, SAMPLE_RATE_HZ)

    return {
        "status": "ok",
        "duration_sec": round(len(full_audio) / SAMPLE_RATE_HZ, 4),
        "wall_time_sec": round(wall_time_sec, 4),
        "word_boundaries": word_boundaries,
    }


def main() -> int:
    _log("kokoro_worker: importing kokoro (one-time cost)...")
    import_start = time.monotonic()
    from kokoro import KPipeline

    _log(f"kokoro_worker: import done in {time.monotonic() - import_start:.2f}s")

    load_start = time.monotonic()
    pipeline = KPipeline(lang_code="a")  # 'a' = American English
    _log(f"kokoro_worker: model loaded in {time.monotonic() - load_start:.2f}s")
    _log("kokoro_worker: ready, waiting for requests on stdin")

    for raw_line in sys.stdin:
        line = raw_line.strip()
        if not line:
            continue
        try:
            request = json.loads(line)
            response = _synthesize(
                pipeline, request["text"], request["voice"], Path(request["output_path"])
            )
        except Exception as exc:  # noqa: BLE001 -- a bad request must not kill the worker
            response = {"status": "error", "message": f"{type(exc).__name__}: {exc}"}
        _write_protocol_line(response)

    _log("kokoro_worker: stdin closed, exiting")
    return 0


if __name__ == "__main__":
    sys.exit(main())
