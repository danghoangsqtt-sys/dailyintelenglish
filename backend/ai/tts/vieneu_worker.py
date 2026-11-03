"""The local VieNeu TTS worker process (runs INSIDE `.venv-vieneu/`, never imported by the app).

Phase 87 (D125). Line-delimited JSON over stdin/stdout, the same shape as the image worker: one handshake line
(`{"status": "ready"}` or `{"status": "unavailable", "reason": ...}`), then one reply per request line.

Request:  {"text": str, "voice": str, "output_path": str}
Reply:    {"status": "ok", "sample_rate": int, "duration_sec": float, "words": [{"text", "start", "end"}]}
          {"status": "error", "message": str}

The words are Whisper's word timestamps for the synthesized take; the app aligns them onto the script words. The
model files live in HF_HOME (set by the app to backend/ai/models/vieneu). Runs on CPU (ONNX); no torch is installed.
"""

from __future__ import annotations

import json
import subprocess
import sys
import traceback


def _reply(payload: dict) -> None:
    sys.stdout.write(json.dumps(payload, ensure_ascii=False) + "\n")
    sys.stdout.flush()


def _pcm16k(path: str, ffmpeg: str):
    """Decode through ffmpeg (faster-whisper's PyAV path breaks with the av version vieneu pins)."""
    import numpy as np

    raw = subprocess.run([ffmpeg, "-v", "error", "-i", path, "-ac", "1", "-ar", "16000", "-f", "s16le", "-"],
                         capture_output=True, check=True).stdout
    return np.frombuffer(raw, np.int16).astype(np.float32) / 32768


def main() -> int:
    # Run with -I, which ignores PYTHONIOENCODING: the pipes carry Vietnamese text, so they are UTF-8 explicitly.
    sys.stdin.reconfigure(encoding="utf-8")
    sys.stdout.reconfigure(encoding="utf-8")
    try:
        from faster_whisper import WhisperModel
        from vieneu import Vieneu

        tts = Vieneu()
        whisper = WhisperModel("small", device="cpu", compute_type="int8")
    except Exception as exc:  # report why the environment cannot run, then exit
        _reply({"status": "unavailable", "reason": f"{type(exc).__name__}: {exc}"})
        traceback.print_exc(file=sys.stderr)
        return 1
    ffmpeg = sys.argv[1] if len(sys.argv) > 1 else "ffmpeg"
    _reply({"status": "ready", "voices": [voice_id for _, voice_id in tts.list_preset_voices()]})

    for line in sys.stdin:
        if not line.strip():
            continue
        try:
            request = json.loads(line)
            audio = tts.infer(request["text"], voice=request["voice"])
            tts.save(audio, request["output_path"])
            sample_rate = getattr(tts, "sample_rate", 48_000)
            segments, _ = whisper.transcribe(_pcm16k(request["output_path"], ffmpeg), language="vi",
                                             word_timestamps=True, beam_size=5)
            words = [{"text": word.word.strip(), "start": round(word.start, 3), "end": round(word.end, 3)}
                     for segment in segments for word in (segment.words or [])]
            _reply({"status": "ok", "sample_rate": sample_rate, "duration_sec": round(len(audio) / sample_rate, 3),
                    "words": words})
        except Exception as exc:
            # The message stays generic: third-party errors can repeat the input text.
            _reply({"status": "error", "message": type(exc).__name__})
            traceback.print_exc(file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
