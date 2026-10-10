"""Phase 32 (Task 32.2): mouth states from the loudness of the speech, faces and gestures per line."""

from __future__ import annotations

import subprocess

import numpy as np
import pytest

from app.core.config import settings
from app.services.visuals import sprite_plan as plan

FPS = 30
ALL = {f"{e}__{m}" for e in ("calm", "smile", "laugh", "surprised", "thinking", "worried", "serious") for m in ("closed", "open")} | {
    "blink"} | {f"gesture-{g}" for g in ("talk", "point", "think", "open", "heart", "listen", "wave")}


def test_loud_frames_open_the_mouth_without_flicker():
    loudness = np.zeros(60, dtype=np.float32)
    loudness[10:20] = 0.5  # a syllable
    loudness[21] = 0.5  # one quiet frame inside it is filled
    loudness[20] = 0.01
    loudness[30] = 0.5  # a one-frame click is dropped
    loudness[40:46] = 0.4
    intervals = plan.mouth_intervals(loudness, FPS, 0.0, 2.0)
    assert intervals == [[round(10 / 30, 3), round(16 / 30, 3)], [round(18 / 30, 3), round(22 / 30, 3)],  # 12 frames flap
                         [round(40 / 30, 3), round(46 / 30, 3)]]


def test_a_silent_line_keeps_the_mouth_closed():
    assert plan.mouth_intervals(np.zeros(90, dtype=np.float32), FPS, 0.5, 2.5) == []
    assert plan.mouth_intervals(np.ones(10, dtype=np.float32), FPS, 2.0, 3.0) == []  # the line is past the audio


def test_words_are_the_fallback_without_audio():
    words = [{"text": "Hi", "startSec": 1.0, "endSec": 1.3}, {"text": "a", "startSec": 1.3, "endSec": 1.35}]
    assert plan.mouth_from_words(words) == [[1.0, 1.24]]


def test_the_rms_of_a_frame_is_measured_in_its_own_window():
    samples = np.concatenate([np.zeros(16000), np.full(16000, 0.5)]).astype(np.float32)
    rms = plan.frame_rms(samples, 16000, FPS)
    assert len(rms) == 60 and rms[10] == 0 and abs(rms[45] - 0.5) < 1e-6


def test_the_loudness_of_a_real_audio_file(tmp_path):
    path = tmp_path / "tone.wav"
    try:
        subprocess.run([settings.FFMPEG_PATH, "-v", "error", "-f", "lavfi", "-i", "sine=frequency=300:duration=1", "-af",
                        "volume=0.5", str(path)], check=True, capture_output=True, timeout=60)
    except (OSError, subprocess.CalledProcessError):
        pytest.skip("ffmpeg is not available")
    loudness = plan.loudness_per_frame(path, FPS)
    assert 29 <= len(loudness) <= 31 and loudness[15] > 0.02  # lavfi sine is 1/8 full scale, then halved


@pytest.mark.parametrize(("text", "beat", "expected"), [
    ("We met in the park.", None, "calm"),
    ("We met in the park.", "serious", "serious"),
    ("Oh no, I lost my keys!", None, "worried"),
    ("Haha, that is so funny.", None, "laugh"),
    ("Wow, really!", None, "surprised"),
    ("That's great!", None, "smile"),
    ("Maybe we should go?", None, "thinking"),
    ("Do you like coffee?", None, "calm"),
    ("Oh no!", "calm", "worried"),
])
def test_the_face_follows_the_beat_then_the_text(text, beat, expected):
    assert plan.line_expression(text, beat) == expected


@pytest.mark.parametrize(("text", "expression", "duration", "count", "expected"), [
    ("Hello, Lina!", "smile", 1.0, 0, "wave"),
    ("Thanks a lot.", "calm", 1.0, 0, "heart"),
    ("Look over there.", "calm", 1.0, 0, "point"),
    ("I don't know, maybe.", "calm", 1.0, 0, "open"),
    ("Let me see.", "thinking", 1.0, 0, "think"),
    ("A long explanation of the menu.", "calm", 5.0, 0, "talk"),
    ("Another long explanation here.", "calm", 5.0, 1, None),
    ("Short.", "calm", 1.0, 0, None),
])
def test_gestures_follow_the_text(text, expression, duration, count, expected):
    assert plan.line_gesture(text, expression, duration, count) == expected


def test_the_plan_uses_only_pictures_that_exist():
    lines = [
        {"startSec": 0.0, "endSec": 1.0, "text": "Hello!", "words": [{"text": "Hello", "startSec": 0.1, "endSec": 0.6}]},
        {"startSec": 1.2, "endSec": 8.0, "text": "Haha, it was a very long and funny story.", "words": []},
        {"startSec": 8.2, "endSec": 9.0, "text": "Narrator.", "words": []},
    ]
    available = {0: ALL, 1: {"calm__closed", "calm__open", "smile__closed"}}
    result = plan.build_plan(lines, [0, 1, None], [None, None, None], available, None, FPS)
    assert result[0]["slot"] == 0 and result[0]["gesture"] == "wave" and result[0]["mouth"] == [[0.1, 0.54]]
    assert result[0]["expression"] == "smile" and result[0]["listenerExpression"] == "calm"  # Lina's smile has no open mouth
    assert result[1]["expression"] == "calm" and result[1]["gesture"] is None  # Lina has no laugh pictures, no gestures
    assert result[1]["listenerGesture"] == "listen" and result[1]["listenerExpression"] == "calm"
    assert result[2] == {"slot": None, "expression": "calm", "listenerExpression": "calm", "gesture": None,
                         "listenerGesture": None, "mouth": [], "visibleSlots": [0, 1]}


def test_the_plan_uses_the_storyboard_pair_for_a_third_speaker():
    lines = [
        {"startSec": 0.0, "endSec": 1.0, "text": "First.", "words": []},
        {"startSec": 1.0, "endSec": 2.0, "text": "Third.", "words": []},
    ]
    available = {0: ALL, 1: ALL, 2: ALL}

    result = plan.build_plan(
        lines, [0, 2], [None, None], available, None, FPS, [[0, 1], [0, 2]],
    )

    assert result[0]["visibleSlots"] == [0, 1]
    assert result[1]["slot"] == 2 and result[1]["visibleSlots"] == [0, 2]
    assert result[1]["listenerExpression"] == "calm"
