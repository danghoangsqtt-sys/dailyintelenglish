"""Phase 32 (Task 32.2): what each talking sprite does on each line -- its face, its gesture and when its mouth is open.

Pure functions plus one ffmpeg decode. The mouth follows the loudness of the speech (D32-d), the face follows the storyboard beat and
simple rules on the text (D32-e), the gestures follow rules on the text (D32-f). The Remotion composition (`spriteTimeline.ts`) only
reads the result; nothing here depends on React.
"""

from __future__ import annotations

import re
import shutil
import subprocess
from pathlib import Path

import numpy as np

from app.core.config import settings

SAMPLE_RATE = 16000
OPEN_FRACTION = 0.35  # a frame is open above 35% of the line's 90th-percentile loudness
MIN_RUN_FRAMES = 2  # shorter open runs are dropped, shorter closed gaps are filled (no flicker)
MAX_OPEN_FRAMES = 8  # a longer open run (a long vowel, words run together) flaps: 6 frames open, 2 closed (D32-d, measured 2026-10-08)
FLAP_OPEN, FLAP_CLOSED = 6, 2
WORD_CLOSE_SEC = 0.06  # word-timestamp fallback: the mouth closes this long before each word ends
TALK_GESTURE_SEC = 4.0
LISTEN_GESTURE_SEC = 6.0


def loudness_per_frame(audio_path: str | Path, fps: int) -> np.ndarray:
    """RMS loudness of the audio per video frame (mono 16 kHz decode by ffmpeg)."""
    ffmpeg = shutil.which(settings.FFMPEG_PATH) or settings.FFMPEG_PATH
    result = subprocess.run(
        [ffmpeg, "-v", "error", "-i", str(audio_path), "-ac", "1", "-ar", str(SAMPLE_RATE), "-f", "s16le", "-"],
        capture_output=True, timeout=600, check=True,
    )
    samples = np.frombuffer(result.stdout, dtype=np.int16).astype(np.float32) / 32768.0
    return frame_rms(samples, SAMPLE_RATE, fps)


def frame_rms(samples: np.ndarray, sample_rate: int, fps: int) -> np.ndarray:
    frames = int(np.ceil(len(samples) * fps / sample_rate))
    out = np.zeros(frames, dtype=np.float32)
    for frame in range(frames):
        start, end = int(frame * sample_rate / fps), int((frame + 1) * sample_rate / fps)
        chunk = samples[start:end]
        out[frame] = float(np.sqrt(np.mean(chunk * chunk))) if len(chunk) else 0.0
    return out


def _runs(flags: list[bool]) -> list[tuple[int, int]]:
    runs, start = [], None
    for index, flag in enumerate(flags + [False]):
        if flag and start is None:
            start = index
        elif not flag and start is not None:
            runs.append((start, index))
            start = None
    return runs


def mouth_intervals(loudness: np.ndarray, fps: int, start_sec: float, end_sec: float) -> list[list[float]]:
    """When the mouth is open during one line, as [start, end] seconds: loud frames, with no run or gap shorter than 2 frames."""
    first, last = max(0, int(round(start_sec * fps))), min(len(loudness), int(round(end_sec * fps)))
    if last <= first:
        return []
    values = loudness[first:last]
    peak = float(np.percentile(values, 90))
    if peak <= 1e-4:
        return []
    flags = [bool(value > OPEN_FRACTION * peak) for value in values]
    for start, end in _runs([not flag for flag in flags]):  # fill short gaps inside speech
        if 0 < start and end < len(flags) and end - start < MIN_RUN_FRAMES:
            flags[start:end] = [True] * (end - start)
    runs = []
    for start, end in _runs(flags):
        while end - start > MAX_OPEN_FRAMES:
            runs.append((start, start + FLAP_OPEN))
            start += FLAP_OPEN + FLAP_CLOSED
        if end - start >= MIN_RUN_FRAMES:
            runs.append((start, end))
    return [[round((first + start) / fps, 3), round((first + end) / fps, 3)] for start, end in runs]


def mouth_from_words(words: list[dict]) -> list[list[float]]:
    """Fallback without the audio: open during each word, closing a moment before it ends."""
    intervals = []
    for word in words:
        start, end = float(word["startSec"]), float(word["endSec"])
        if end - start > 2 * WORD_CLOSE_SEC:
            intervals.append([round(start, 3), round(end - WORD_CLOSE_SEC, 3)])
    return intervals


_WORRIED = re.compile(r"\b(oh no|sorry|worried|worry|afraid|problem|scared|nervous|difficult)\b", re.I)
_LAUGH = re.compile(r"\b(haha|ha ha|funny|hilarious|lol)\b", re.I)
_SURPRISED = re.compile(r"\b(wow|really|amazing|no way|seriously|what)\b", re.I)
_GREETING = re.compile(r"\b(hi|hello|hey|bye|goodbye|see you|welcome)\b", re.I)
_THANKS = re.compile(r"\b(thank|thanks)\b", re.I)
_POINT = re.compile(r"\b(look|over there|this one|that one|see that|right there)\b", re.I)
_SHRUG = re.compile(r"\b(maybe|i don't know|i do not know|who knows|not sure|perhaps)\b", re.I)


def line_expression(text: str, beat_expression: str | None = None) -> str:
    """The speaker's face for a line: the beat's expression when the storyboard says something else than calm, else rules on the text."""
    if beat_expression and beat_expression != "calm":
        return beat_expression
    if _WORRIED.search(text):
        return "worried"
    if _LAUGH.search(text):
        return "laugh"
    if "!" in text and _SURPRISED.search(text):
        return "surprised"
    if text.rstrip().endswith("?"):
        return "thinking" if _SHRUG.search(text) else "calm"
    if "!" in text:
        return "smile"
    return "calm"


def listener_expression(speaker_expression: str) -> str:
    return "smile" if speaker_expression in ("smile", "laugh") else "calm"


def line_gesture(text: str, expression: str, duration: float, long_line_count: int) -> str | None:
    """The speaker's gesture for a line, or None (the plain body). `long_line_count` = how many lines of 4 s or more this speaker said
    before this one (every second long line gets the talking hand)."""
    if _GREETING.search(text):
        return "wave"
    if _THANKS.search(text):
        return "heart"
    if _POINT.search(text):
        return "point"
    if _SHRUG.search(text):
        return "open"
    if expression == "thinking":
        return "think"
    if duration >= TALK_GESTURE_SEC and long_line_count % 2 == 0:
        return "talk"
    return None


def _face(expression: str, available: set[str]) -> str:
    """The expression if its two mouth pictures exist, else calm."""
    return expression if {f"{expression}__closed", f"{expression}__open"} <= available else "calm"


def _gesture(gesture: str | None, available: set[str]) -> str | None:
    return gesture if gesture and f"gesture-{gesture}" in available else None


def build_plan(lines: list[dict], slots: list[int | None], beat_expressions: list[str | None],
               available: dict[int, set[str]], loudness: np.ndarray | None, fps: int,
               visible_slots: list[list[int]] | None = None) -> list[dict]:
    """One entry per line: who speaks, which one or two cast slots are visible, their faces and gestures, and the speaker's
    open-mouth intervals. `lines` use the props shape (startSec, endSec, text, words)."""
    plan: list[dict] = []
    long_lines: dict[int, int] = {}
    if visible_slots is None:
        visible_slots = [sorted(available)[:2] for _line in lines]
    for line, slot, beat_expression, visible in zip(lines, slots, beat_expressions, visible_slots, strict=True):
        visible = list(dict.fromkeys(item for item in visible if item in available))[:2]
        duration = line["endSec"] - line["startSec"]
        if slot is None:
            plan.append({"slot": None, "expression": "calm", "listenerExpression": "calm", "gesture": None,
                         "listenerGesture": None, "mouth": [], "visibleSlots": visible})
            continue
        listener = next((item for item in visible if item != slot), None)
        expression = _face(line_expression(line["text"], beat_expression), available.get(slot, set()))
        gesture = line_gesture(line["text"], expression, duration, long_lines.get(slot, 0))
        if duration >= TALK_GESTURE_SEC:
            long_lines[slot] = long_lines.get(slot, 0) + 1
        mouth = (mouth_intervals(loudness, fps, line["startSec"], line["endSec"]) if loudness is not None
                 else mouth_from_words(line.get("words") or []))
        plan.append({
            "slot": slot,
            "visibleSlots": visible,
            "expression": expression,
            "listenerExpression": _face(listener_expression(expression), available.get(listener, set())) if listener is not None else "calm",
            "gesture": _gesture(gesture, available.get(slot, set())),
            "listenerGesture": (_gesture("listen" if duration >= LISTEN_GESTURE_SEC else None, available.get(listener, set()))
                                if listener is not None else None),
            "mouth": mouth,
        })
    return plan
