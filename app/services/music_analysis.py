"""Task 22.9: automatic classification of a library track (blocking; run in a thread).

Spike `scripts/spike_music_analysis.py` on the owner's Pixabay tracks: tempo detection is ambiguous
(the same track gives 83 or 123 BPM, 74 or 144), so BPM is only an estimate for display. Onset
density (attacks per second) orders the tracks the way their names describe them, so the pace class
comes from it -- taken as the median of three 30 s windows (25/50/75 %): a single middle window
flipped two tracks across a threshold because it fell on a quiet break.
"""

from __future__ import annotations

import math
from pathlib import Path
from typing import Any

SAMPLE_RATE = 22050
WINDOW_S = 30.0
WINDOW_AT = (0.25, 0.5, 0.75)  # three windows; the median onset rate ignores one sparse break
CALM_BELOW = 4.2  # onsets per second (calibrated on the spike tracks)
LIVELY_FROM = 5.8
BRIGHT_FROM_HZ = 2000.0
PACES = ("calm", "medium", "lively")


def classify_pace(onset_rate: float) -> str:
    if onset_rate < CALM_BELOW:
        return "calm"
    return "lively" if onset_rate >= LIVELY_FROM else "medium"


def suggest_mood(pace: str, brightness_hz: float) -> str:
    """A starting suggestion, shown as "(auto)"; the owner's mood always wins."""
    bright = brightness_hz >= BRIGHT_FROM_HZ
    if pace == "lively":
        return "upbeat" if bright else "inspiring"
    if pace == "medium":
        return "inspiring" if bright else "acoustic"
    return "calm" if bright else "lofi"


def analyse(path: Path) -> dict[str, Any] | None:
    """Pace, ~BPM, energy and brightness of one file; None when it cannot be decoded."""
    try:
        import librosa  # heavy import, only when a track is analysed
        import numpy as np

        total = float(librosa.get_duration(path=str(path)))
        windows = [
            librosa.load(str(path), sr=SAMPLE_RATE, mono=True, offset=max(0.0, total * at - WINDOW_S / 2),
                         duration=min(WINDOW_S, total))[0]
            for at in WINDOW_AT
        ]
    except Exception:  # noqa: BLE001 -- any undecodable file is simply "not analysed"
        return None
    sr = SAMPLE_RATE
    windows = [window for window in windows if len(window) >= 2 * sr and np.any(window)]
    if not windows:
        return None
    rates = [len(librosa.onset.onset_detect(y=window, sr=sr, units="time")) / (len(window) / sr) for window in windows]
    onset_rate = float(np.median(rates))
    y = np.concatenate(windows)
    tempo = librosa.feature.tempo(y=y, sr=sr)[0]
    rms = float(np.mean(librosa.feature.rms(y=y)[0]))
    centroid = float(np.median(librosa.feature.spectral_centroid(y=y, sr=sr)[0]))
    pace = classify_pace(onset_rate)
    return {
        "bpm": round(float(tempo), 1) if math.isfinite(float(tempo)) and tempo > 0 else None,
        "onset_rate": round(onset_rate, 2),
        "energy_db": round(20 * math.log10(rms + 1e-9), 1),
        "brightness_hz": round(centroid),
        "pace": pace,
        "mood_auto": suggest_mood(pace, centroid),
    }
