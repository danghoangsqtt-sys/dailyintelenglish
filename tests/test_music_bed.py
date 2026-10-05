"""Task 22.4 (D51): the music bed's signal rules on synthetic signals."""

import math

import numpy as np
import pytest

from app.core.constants import (
    MUSIC_BED_LUFS,
    MUSIC_CROSSFADE_S,
    MUSIC_DUCK_DB,
    MUSIC_FADE_IN_S,
    MUSIC_FADE_OUT_S,
    TARGET_LOUDNESS_LUFS,
)
from app.services import music_bed
from app.services.music_bed import SAMPLE_RATE

SR = SAMPLE_RATE


def tone(seconds: float, frequency: float = 220.0, level: float = 0.3) -> np.ndarray:
    t = np.arange(int(seconds * SR)) / SR
    wave = (level * np.sin(2 * math.pi * frequency * t)).astype(np.float32)
    return np.stack([wave, wave])


def db_at(gain: np.ndarray, seconds: float) -> float:
    return 20 * math.log10(max(float(gain[int(seconds * SR)]), 1e-9))


# --- fit ------------------------------------------------------------------------------------

def test_a_longer_track_is_cut_from_its_beginning():
    music = tone(10)
    fitted = music_bed.fit(music, 4 * SR)
    assert fitted.shape == (2, 4 * SR)
    assert np.array_equal(fitted, music[:, :4 * SR])


def test_a_shorter_track_loops_with_equal_power_crossfades():
    music = tone(8, frequency=200)
    fitted = music_bed.fit(music, 30 * SR)
    assert fitted.shape == (2, 30 * SR)
    assert np.array_equal(fitted[:, :SR], music[:, :SR])  # still starts at the track's start
    fade = int(MUSIC_CROSSFADE_S * SR)
    # The first seam sits at 8 s - fade; the signal there is a crossfade, not silence or a jump.
    seam = fitted[0, 8 * SR - fade: 8 * SR]
    assert np.max(np.abs(seam)) > 0.1
    # No click: sample-to-sample steps never exceed the tone's own largest step by much.
    steps = np.abs(np.diff(fitted[0]))
    assert steps.max() < 2.5 * np.abs(np.diff(music[0])).max()


def test_a_very_short_track_repeats_plainly_and_silence_stays_silent():
    fitted = music_bed.fit(tone(2), 9 * SR)
    assert fitted.shape == (2, 9 * SR)
    assert np.array_equal(music_bed.fit(np.zeros((2, 0), np.float32), SR), np.zeros((2, SR)))


# --- envelope -------------------------------------------------------------------------------

def test_music_is_open_in_intro_and_outro_and_ducked_under_speech():
    total = 40 * SR
    spans = [(5.0, 9.0), (10.0, 14.0), (14.5, 20.0), (30.0, 33.0)]
    gain = music_bed.envelope(total, spans, fade_in_s=0, fade_out_s=0)
    assert db_at(gain, 2.0) == pytest.approx(0, abs=0.01)  # intro: open
    for second in (5.0, 7.0, 9.0, 12.0, 19.9, 30.0, 33.0):  # whole lines, start to end: ducked
        assert db_at(gain, second) == pytest.approx(MUSIC_DUCK_DB, abs=0.01), second
    assert db_at(gain, 9.5) == pytest.approx(MUSIC_DUCK_DB, abs=0.01)  # short gap stays ducked
    assert db_at(gain, 25.0) == pytest.approx(0, abs=0.01)  # 10 s pause: open again
    assert db_at(gain, 37.0) == pytest.approx(0, abs=0.01)  # outro: open


def test_ducking_is_complete_before_the_first_word():
    gain = music_bed.envelope(20 * SR, [(5.0, 8.0)], fade_in_s=0, fade_out_s=0)
    assert db_at(gain, 4.0) == pytest.approx(0, abs=0.01)
    assert MUSIC_DUCK_DB < db_at(gain, 4.6) < 0  # ramping down
    assert db_at(gain, 5.0) == pytest.approx(MUSIC_DUCK_DB, abs=0.01)  # fully down at the word
    assert db_at(gain, 8.15) == pytest.approx(MUSIC_DUCK_DB, abs=0.01)  # held a moment after the line
    assert db_at(gain, 10.0) == pytest.approx(0, abs=0.01)


def test_fade_in_and_fade_out_to_the_last_sample():
    total = 30 * SR
    gain = music_bed.envelope(total, [])
    assert gain[0] == 0.0
    assert gain[int(MUSIC_FADE_IN_S / 2 * SR)] == pytest.approx(0.5, abs=0.01)
    assert gain[int(MUSIC_FADE_IN_S * SR) + 10] == pytest.approx(1.0, abs=1e-3)
    assert gain[total - 1] == 0.0
    assert gain[total - 1 - int(MUSIC_FADE_OUT_S / 2 * SR)] == pytest.approx(0.5, abs=0.01)
    assert gain[total - int(MUSIC_FADE_OUT_S * SR) - 10] == pytest.approx(1.0, abs=1e-3)
    assert np.all(np.diff(gain[total - int(MUSIC_FADE_OUT_S * SR):]) <= 0)  # only ever falls


def test_short_beds_keep_their_fades_inside_the_bed():
    gain = music_bed.envelope(3 * SR, [])
    assert gain[0] == 0.0 and gain[-1] == 0.0 and gain.max() <= 1.0


# --- levels ---------------------------------------------------------------------------------

def test_every_track_is_normalised_to_the_same_open_level():
    loud = music_bed.normalise(tone(10, level=0.9), MUSIC_BED_LUFS)
    quiet = music_bed.normalise(tone(10, level=0.02), MUSIC_BED_LUFS)
    assert music_bed.loudness(loud) == pytest.approx(MUSIC_BED_LUFS, abs=0.2)
    assert music_bed.loudness(quiet) == pytest.approx(MUSIC_BED_LUFS, abs=0.2)
    silent = np.zeros((2, 5 * SR), np.float32)
    assert np.array_equal(music_bed.normalise(silent, MUSIC_BED_LUFS), silent)


def test_mix_hits_the_target_loudness_and_never_clips():
    voice = tone(20, frequency=300, level=0.2)
    bed = music_bed.build_bed(tone(7, frequency=110, level=0.8), voice.shape[1], [(1.0, 19.0)])
    mixed = music_bed.mix(voice, bed)
    assert music_bed.loudness(mixed) == pytest.approx(TARGET_LOUDNESS_LUFS, abs=0.5)
    assert float(np.max(np.abs(mixed))) <= 10 ** (-1 / 20) + 1e-6


def test_segment_round_trip_keeps_the_signal():
    music = tone(1.0)
    back = music_bed.from_segment(music_bed.to_segment(music))
    assert back.shape == music.shape
    assert np.max(np.abs(back - music)) < 1e-3
