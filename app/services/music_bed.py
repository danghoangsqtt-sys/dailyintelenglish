"""Task 22.4 (D51): the background-music bed under an episode's voice.

Pure signal math on float32 arrays shaped (channels, samples), so every rule is unit-testable:

- `fit`: the bed starts at the track's own beginning; a longer track is cut, a shorter one is
  looped with equal-power crossfades (never a hard cut).
- `envelope`: per-sample gain. The music is *open* in the intro, the outro and long pauses, and
  *ducked* under speech. Ramps finish before a line starts, short gaps stay ducked (no pumping),
  and the bed fades in at the start and fades out to silence on the very last sample.
- `normalise` brings every track to the same loudness first, so the levels mean the same thing for
  any file the owner downloads.
"""

from __future__ import annotations

import math
from pathlib import Path

import numpy as np
import pyloudnorm as pyln
from pydub import AudioSegment

from app.core.constants import (
    MUSIC_ATTACK_S,
    MUSIC_BED_LUFS,
    MUSIC_CROSSFADE_S,
    MUSIC_DUCK_DB,
    MUSIC_FADE_IN_S,
    MUSIC_FADE_OUT_S,
    MUSIC_MERGE_GAP_S,
    MUSIC_RELEASE_S,
    TARGET_LOUDNESS_LUFS,
)

SAMPLE_RATE = 44100
CHANNELS = 2
GRID_S = 0.01  # the envelope is designed on a 10 ms grid, then interpolated to samples
MAX_GAIN_DB = 24.0
PEAK_CEILING = 10 ** (-1.0 / 20)  # -1 dBFS


def decode(path: Path) -> np.ndarray:
    """Any file pydub/ffmpeg can read -> float32 (2, n) at 44.1 kHz."""
    segment = AudioSegment.from_file(path).set_frame_rate(SAMPLE_RATE).set_channels(CHANNELS).set_sample_width(2)
    samples = np.array(segment.get_array_of_samples(), dtype=np.float32) / 32768.0
    return samples.reshape(-1, CHANNELS).T.copy()


def from_segment(segment: AudioSegment) -> np.ndarray:
    segment = segment.set_frame_rate(SAMPLE_RATE).set_channels(CHANNELS).set_sample_width(2)
    samples = np.array(segment.get_array_of_samples(), dtype=np.float32) / 32768.0
    return samples.reshape(-1, CHANNELS).T.copy()


def to_segment(audio: np.ndarray) -> AudioSegment:
    clipped = np.clip(audio, -1.0, 32767 / 32768)
    interleaved = (clipped.T.reshape(-1) * 32768.0).astype(np.int16)
    return AudioSegment(interleaved.tobytes(), frame_rate=SAMPLE_RATE, sample_width=2, channels=CHANNELS)


def loudness(audio: np.ndarray) -> float:
    """Integrated EBU R128 loudness; -inf for silence or anything too short to gate."""
    if audio.shape[1] < int(0.5 * SAMPLE_RATE):
        reps = math.ceil(0.5 * SAMPLE_RATE / max(1, audio.shape[1]))
        audio = np.tile(audio, reps)
    return float(pyln.Meter(SAMPLE_RATE).integrated_loudness(audio.T))


def normalise(audio: np.ndarray, target_lufs: float) -> np.ndarray:
    measured = loudness(audio)
    if not math.isfinite(measured):
        return audio
    gain_db = max(-MAX_GAIN_DB, min(MAX_GAIN_DB, target_lufs - measured))
    return audio * np.float32(10 ** (gain_db / 20))


def fit(music: np.ndarray, samples: int, crossfade_s: float = MUSIC_CROSSFADE_S) -> np.ndarray:
    """Exactly `samples` long, starting at the track's beginning."""
    length = music.shape[1]
    if length == 0:
        return np.zeros((music.shape[0], samples), dtype=np.float32)
    if length >= samples:
        return music[:, :samples].copy()
    fade = int(crossfade_s * SAMPLE_RATE)
    if length < 2 * fade:  # too short to crossfade into itself: plain repeat
        return np.tile(music, math.ceil(samples / length))[:, :samples].copy()
    ramp = np.linspace(0, math.pi / 2, fade, dtype=np.float32)
    fade_in, fade_out = np.sin(ramp), np.cos(ramp)  # equal power: sin^2 + cos^2 = 1
    out = music.copy()
    while out.shape[1] < samples:
        seam = out[:, -fade:] * fade_out + music[:, :fade] * fade_in
        out = np.concatenate([out[:, :-fade], seam, music[:, fade:]], axis=1)
    return out[:, :samples].copy()


def _moving_average(values: np.ndarray, width: int) -> np.ndarray:
    if width <= 1:
        return values
    padded = np.pad(values, (width // 2, width - 1 - width // 2), mode="edge")
    return np.convolve(padded, np.ones(width) / width, mode="valid")


def duck_windows(spans: list[tuple[float, float]], total_s: float) -> list[tuple[float, float]]:
    """Speech spans widened by attack/release, with windows closer than the merge gap joined."""
    windows: list[tuple[float, float]] = []
    for start, end in sorted(spans):
        window = (max(0.0, start - MUSIC_ATTACK_S), min(total_s, end + MUSIC_RELEASE_S))
        if windows and window[0] - windows[-1][1] < MUSIC_MERGE_GAP_S:
            windows[-1] = (windows[-1][0], max(windows[-1][1], window[1]))
        else:
            windows.append(window)
    return windows


def envelope(samples: int, spans: list[tuple[float, float]], *, duck_db: float = MUSIC_DUCK_DB,
             fade_in_s: float = MUSIC_FADE_IN_S, fade_out_s: float = MUSIC_FADE_OUT_S) -> np.ndarray:
    """Linear gain per sample. `spans` are speech (start_s, end_s) on the bed's own timeline."""
    total_s = samples / SAMPLE_RATE
    steps = max(2, math.ceil(total_s / GRID_S) + 1)
    grid_t = np.arange(steps) * GRID_S
    target_db = np.zeros(steps)
    for start, end in duck_windows(spans, total_s):
        target_db[(grid_t >= start) & (grid_t <= end)] = duck_db
    # A moving average of a step is a linear ramp centred on the step. Windows start `attack`
    # before speech, so a ramp 2 x attack long is fully down exactly when the first word starts,
    # and windows end `release` after speech, so the music only rises once the line is over.
    smoothed_db = _moving_average(target_db, max(1, round(2 * MUSIC_ATTACK_S / GRID_S)))
    gain = 10 ** (smoothed_db / 20)
    sample_t = np.arange(samples) / SAMPLE_RATE
    per_sample = np.interp(sample_t, grid_t, gain).astype(np.float32)
    fade_in = min(fade_in_s, total_s / 2)
    fade_out = min(fade_out_s, total_s / 2)
    if fade_in > 0:
        per_sample *= np.clip(sample_t / fade_in, 0.0, 1.0).astype(np.float32)
    if fade_out > 0:
        # Reaches exactly 0 on the last sample.
        remaining = (samples - 1 - np.arange(samples)) / SAMPLE_RATE
        per_sample *= np.clip(remaining / fade_out, 0.0, 1.0).astype(np.float32)
    return per_sample


def build_bed(music: np.ndarray, samples: int, spans: list[tuple[float, float]]) -> np.ndarray:
    """Normalise -> fit -> envelope: the finished bed, `samples` long."""
    fitted = fit(normalise(music, MUSIC_BED_LUFS), samples)
    return fitted * envelope(samples, spans)


def mix(voice: np.ndarray, bed: np.ndarray, target_lufs: float = TARGET_LOUDNESS_LUFS) -> np.ndarray:
    """Voice + bed, loudness-normalised like every mix, then never above -1 dBFS peak."""
    mixed = normalise(voice + bed, target_lufs)
    peak = float(np.max(np.abs(mixed))) if mixed.size else 0.0
    if peak > PEAK_CEILING:
        mixed = mixed * np.float32(PEAK_CEILING / peak)
    return mixed
