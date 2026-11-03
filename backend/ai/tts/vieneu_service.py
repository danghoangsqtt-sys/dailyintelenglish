"""Phase 87 (D125): synthesize a line with a local VieNeu-TTS voice through the isolated `.venv-vieneu` worker.

The worker (`vieneu_worker.py`) is a persistent line-delimited process: loading VieNeu and Whisper takes ~11 s on CPU,
one line ~3 s after that. It is started on the first VieNeu line and closed after `VIENEU_IDLE_SECONDS` without work.
VieNeu reports no word timings, so the worker transcribes its own take with Whisper and `align_words` maps the
recognised words back onto the script words; the result has the same shape as Edge's WordBoundary list.
"""

from __future__ import annotations

import asyncio
import difflib
import json
import logging
import os
import re
import subprocess
import tempfile
import threading
import time
import unicodedata
import uuid
from pathlib import Path

from backend.core.config import settings
from backend.core.constants import (
    VIENEU_IDLE_SECONDS, VIENEU_LINE_TIMEOUT_SECONDS, VIENEU_MIN_WORD_MATCH,
)
from backend.core.exceptions import TTSError
from backend.core.paths import MODELS_DIR, RUNTIME_ROOT, VIENEU_VENV_DIR
from backend.core.voice import resolve_vieneu_voice

logger = logging.getLogger(__name__)

VIENEU_PYTHON = VIENEU_VENV_DIR / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
VIENEU_WORKER = RUNTIME_ROOT / "backend/ai/tts/vieneu_worker.py"
VIENEU_HF_HOME = MODELS_DIR / "vieneu"
SETUP_HINT = "Run scripts/setup_vieneu.ps1 to install the Vietnamese voice (VieNeu)."

# (text, offset_sec, duration_sec) per script word -- tts_service wraps these into its WordBoundary.
Boundary = tuple[str, float, float]


def is_available() -> bool:
    """Whether the isolated interpreter exists (the worker reports a missing model itself)."""
    return VIENEU_PYTHON.is_file()


# Latin words in capitals are spelled out letter by letter by the engine ("PRESS" -> "P R E S S"), so the text sent to
# it is lower-cased. Acronyms without a vowel (BBC) and the known exam names stay as they are.
_CAPS_WORD = re.compile(r"\b[A-Z][A-Z'-]*[A-Z]\b")
_KEEP_CAPS = {"TOEIC", "IELTS", "TOEFL", "CEFR", "NASA", "UNESCO", "OK"}


def tts_text(text: str) -> str:
    def lower(match: re.Match) -> str:
        word = match.group(0)
        if word in _KEEP_CAPS or not re.search(r"[AEIOUY]", word):
            return word
        return word.lower()
    return _CAPS_WORD.sub(lower, text)


def _fold(word: str) -> str:
    """Compare words without case, accents or punctuation (Whisper and the script differ in all three)."""
    word = unicodedata.normalize("NFD", word.lower().replace("đ", "d"))
    return "".join(ch for ch in word if ch.isalnum() and not unicodedata.combining(ch))


def _script_words(text: str) -> list[str]:
    words = []
    for raw in text.split():
        word = raw.strip(".,!?;:\"'“”‘’()[]…—–-")
        if _fold(word):
            words.append(word)
    return words


def align_words(text: str, recognised: list[dict], duration_sec: float) -> tuple[list[Boundary], float]:
    """Give every script word a time from Whisper's words; returns the boundaries and the share of words matched.

    Matched words take the recognised word's start/end. Unmatched words never get invented text: they share the gap
    between their matched neighbours in proportion to their length.
    """
    script = _script_words(text)
    if not script:
        return [], 0.0
    heard = [word for word in recognised if _fold(word.get("text", ""))]
    times: list[tuple[float, float] | None] = [None] * len(script)
    matcher = difflib.SequenceMatcher(a=[_fold(w) for w in script], b=[_fold(w["text"]) for w in heard], autojunk=False)
    for block in matcher.get_matching_blocks():
        for k in range(block.size):
            word = heard[block.b + k]
            times[block.a + k] = (float(word["start"]), float(word["end"]))
    matched = sum(1 for item in times if item is not None)

    index = 0
    while index < len(script):
        if times[index] is not None:
            index += 1
            continue
        end = index
        while end < len(script) and times[end] is None:
            end += 1
        gap_start = times[index - 1][1] if index > 0 else 0.0
        gap_end = times[end][0] if end < len(script) else duration_sec
        if gap_end <= gap_start:  # no room: squeeze the run into a small slot after the previous word
            gap_end = gap_start + 0.08 * (end - index)
        lengths = [max(1, len(_fold(script[k]))) for k in range(index, end)]
        cursor, span = gap_start, gap_end - gap_start
        for k, length in zip(range(index, end), lengths):
            share = span * length / sum(lengths)
            times[k] = (cursor, cursor + share)
            cursor += share
        index = end

    boundaries = [(word, round(start, 3), round(max(0.01, end - start), 3)) for word, (start, end) in zip(script, times)]
    return boundaries, matched / len(script)


class _Worker:
    """One persistent worker process; requests are serialised by the caller's lock."""

    def __init__(self) -> None:
        log_dir = settings.DATA_DIR / "tts_cache" / "logs"
        log_dir.mkdir(parents=True, exist_ok=True)
        self.stderr_file = (log_dir / f"vieneu_worker_{uuid.uuid4().hex}.log").open("w", encoding="utf-8")
        VIENEU_HF_HOME.mkdir(parents=True, exist_ok=True)
        env = {**os.environ, "HF_HOME": str(VIENEU_HF_HOME), "HF_HUB_OFFLINE": "1", "HF_HUB_DISABLE_SYMLINKS": "1",
               "PYTHONUTF8": "1", "PYTHONIOENCODING": "utf-8"}
        self.process = subprocess.Popen(
            [str(VIENEU_PYTHON), "-I", str(VIENEU_WORKER), str(settings.FFMPEG_PATH)], cwd=str(RUNTIME_ROOT),
            stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=self.stderr_file, text=True, encoding="utf-8",
            bufsize=1, env=env,
        )
        handshake = self._read_line()
        if handshake.get("status") != "ready":
            self.close()
            raise TTSError(f"The Vietnamese voice (VieNeu) could not start: {handshake.get('reason', 'unknown')}. "
                           f"{SETUP_HINT}")

    def _read_line(self) -> dict:
        assert self.process.stdout is not None
        result: list[str] = []
        reader = threading.Thread(target=lambda: result.append(self.process.stdout.readline()), daemon=True)
        reader.start()
        reader.join(VIENEU_LINE_TIMEOUT_SECONDS)
        if reader.is_alive():
            self.close()
            raise TTSError("The Vietnamese voice (VieNeu) took too long and was stopped. Try again.")
        if not result or not result[0]:
            self.close()
            raise TTSError(f"The Vietnamese voice (VieNeu) stopped unexpectedly; see {self.stderr_file.name}.")
        return json.loads(result[0])

    def request(self, payload: dict) -> dict:
        assert self.process.stdin is not None
        self.process.stdin.write(json.dumps(payload, ensure_ascii=False) + "\n")
        self.process.stdin.flush()
        reply = self._read_line()
        if reply.get("status") != "ok":
            raise TTSError(f"The Vietnamese voice (VieNeu) failed on this line: {reply.get('message', 'error')}.")
        return reply

    def alive(self) -> bool:
        return self.process.poll() is None

    def close(self) -> None:
        try:
            if self.process.stdin:
                self.process.stdin.close()
            self.process.wait(timeout=10)
        except Exception:
            self.process.kill()
        self.stderr_file.close()


_lock = threading.Lock()
_worker: _Worker | None = None
_last_used = 0.0


def _close_if_idle() -> None:
    global _worker
    with _lock:
        if _worker is not None and time.monotonic() - _last_used >= VIENEU_IDLE_SECONDS:
            _worker.close()
            _worker = None


def shutdown() -> None:
    """Stop the worker now (app shutdown, tests)."""
    global _worker
    with _lock:
        if _worker is not None:
            _worker.close()
            _worker = None


def _take(payload: dict) -> dict:
    global _worker, _last_used
    with _lock:
        if _worker is None or not _worker.alive():
            _worker = _Worker()
        try:
            return _worker.request(payload)
        finally:
            _last_used = time.monotonic()
            timer = threading.Timer(VIENEU_IDLE_SECONDS + 1, _close_if_idle)
            timer.daemon = True
            timer.start()


def _finish_audio(wav_path: Path, speed: float, volume: float) -> bytes:
    """Apply the speaker's speed (VieNeu has no rate control) and volume, and encode the cached MP3."""
    filters = []
    if abs(speed - 1.0) > 0.005:
        filters.append(f"atempo={min(2.0, max(0.5, speed)):.3f}")
    if abs(volume - 1.0) > 0.005:
        filters.append(f"volume={volume:.3f}")
    command = [str(settings.FFMPEG_PATH), "-v", "error", "-y", "-i", str(wav_path)]
    if filters:
        command += ["-af", ",".join(filters)]
    command += ["-ac", "1", "-ar", "24000", "-b:a", "128k", "-f", "mp3", "-"]
    result = subprocess.run(command, capture_output=True, check=False)
    if result.returncode != 0 or not result.stdout:
        raise TTSError("Could not encode the Vietnamese voice audio (ffmpeg).")
    return result.stdout


def _synthesize_sync(text: str, voice: str, speed: float, volume: float) -> tuple[bytes, list[Boundary]]:
    spoken = tts_text(text)
    with tempfile.TemporaryDirectory(prefix="vieneu-") as temp_dir:
        best: tuple[float, Path, dict] | None = None
        for attempt in (1, 2):
            wav_path = Path(temp_dir) / f"take{attempt}.wav"
            reply = _take({"text": spoken, "voice": voice, "output_path": str(wav_path)})
            if not wav_path.is_file() or wav_path.stat().st_size < 44:
                raise TTSError("The Vietnamese voice (VieNeu) produced no audio.")
            _, ratio = align_words(text, reply["words"], reply["duration_sec"])
            if best is None or ratio > best[0]:
                best = (ratio, wav_path, reply)
            if ratio >= VIENEU_MIN_WORD_MATCH:
                break
            logger.warning("vieneu_take_low_match attempt=%d ratio=%.2f", attempt, ratio)
        ratio, wav_path, reply = best
        boundaries, _ = align_words(text, reply["words"], reply["duration_sec"])
        audio = _finish_audio(wav_path, speed, volume)
    if abs(speed - 1.0) > 0.005:
        factor = 1.0 / min(2.0, max(0.5, speed))
        boundaries = [(word, round(start * factor, 3), round(length * factor, 3)) for word, start, length in boundaries]
    return audio, boundaries


async def synthesize(text: str, speaker: dict) -> tuple[bytes, list[Boundary]]:
    """MP3 bytes and per-script-word timings for one line, in the speaker's VieNeu preset voice."""
    if not is_available():
        raise TTSError(f"The Vietnamese voice (VieNeu) is not installed. {SETUP_HINT}")
    voice = resolve_vieneu_voice(speaker)
    speed = float(speaker.get("speed") if speaker.get("speed") is not None else 1.0)
    volume = float(speaker.get("volume") if speaker.get("volume") is not None else 1.0)
    return await asyncio.to_thread(_synthesize_sync, text, voice, speed, volume)
