"""Task 22.9 spike: can librosa measure tempo / energy / brightness of the owner's library tracks
reliably enough to classify them? Not shipped.

    venv\\Scripts\\python scripts\\spike_music_analysis.py
"""

from __future__ import annotations

import json
import sys
import time
from pathlib import Path

import librosa
import numpy as np

ROOT = Path(__file__).resolve().parent.parent
LIBRARY = ROOT / "data" / "music_library"
SR = 22050
WINDOW_S = 90  # analyse a window from the middle: intros/outros are often sparse


def analyse(path: Path) -> dict:
    started = time.monotonic()
    total = librosa.get_duration(path=str(path))
    offset = max(0.0, total / 2 - WINDOW_S / 2)
    y, sr = librosa.load(str(path), sr=SR, mono=True, offset=offset, duration=min(WINDOW_S, total))
    tempo, beats = librosa.beat.beat_track(y=y, sr=sr)
    onset = librosa.onset.onset_strength(y=y, sr=sr)
    rms = librosa.feature.rms(y=y)[0]
    centroid = librosa.feature.spectral_centroid(y=y, sr=sr)[0]
    return {
        "file": path.name[:48], "seconds": round(total, 1),
        "bpm": round(float(np.atleast_1d(tempo)[0]), 1), "beats": int(len(beats)),
        "rms_db": round(float(20 * np.log10(np.mean(rms) + 1e-9)), 1),
        "onset_mean": round(float(np.mean(onset)), 2),
        "centroid_hz": round(float(np.median(centroid))),
        "analyse_s": round(time.monotonic() - started, 2),
    }


def main() -> int:
    for path in sorted(LIBRARY.glob("*.mp3")):
        print(json.dumps(analyse(path)), flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
