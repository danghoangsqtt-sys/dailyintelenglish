"""Task 19.2 (Phase 19, ENH-013) -- real Edge TTS WordBoundary capture test.

Unlike every other TTS-touching test in this suite (all monkeypatch `_synthesize_edge_tts`
to avoid the network), this one calls the real, free Edge TTS endpoint on purpose: the whole
point of this test is that the boundary event shape and units are what
`tts_service._synthesize_edge_tts` assumes (D19.2-a) -- a mocked fixture would test the
assertion without ever testing that assumption. Skips cleanly, not a failure, when the
network is unavailable (D19.2-f) -- narrowly on connection-level exceptions
(`aiohttp.ClientError`/`OSError`), never a blanket `except Exception`, so a real bug in the
capture code still fails the test instead of being swallowed as "no network".

Never touches `data/app.db` -- this test does no DB work at all.
"""

import io

import aiohttp
import pytest
from pydub import AudioSegment

from app.services.tts_service import _synthesize_edge_tts

# 6 words, B1-shaped, inside the card's 5-8 word range.
TEST_LINE = "The weather today is absolutely beautiful."
TEST_SPEAKER = {"accent": "american", "gender": "female", "speed": 1.0, "volume": 1.0, "pitch": 0.0}

# Generous, real-evidence-based tolerance (D19.2-f): a real probe measured the last word's
# offset+duration ending ~0.9s before the clip's actual end (trailing pause/breath after the
# final word is normal Edge TTS behaviour, not something a per-word timestamp covers).
_MAX_TRAILING_GAP_SECONDS = 1.0


async def test_word_boundaries_match_real_edge_tts_output():
    try:
        audio_bytes, word_boundaries = await _synthesize_edge_tts(TEST_LINE, TEST_SPEAKER)
    except (aiohttp.ClientError, OSError) as exc:
        pytest.skip(f"Edge TTS network unavailable: {exc}")

    expected_words = [w.strip(".,?!") for w in TEST_LINE.split()]
    assert [wb.text for wb in word_boundaries] == expected_words

    offsets = [wb.offset_sec for wb in word_boundaries]
    assert offsets == sorted(offsets), "word offsets must be monotonic non-decreasing"

    clip_duration_seconds = len(AudioSegment.from_file(io.BytesIO(audio_bytes))) / 1000
    last_word = word_boundaries[-1]
    last_word_end = last_word.offset_sec + last_word.duration_sec
    assert last_word_end <= clip_duration_seconds + 0.05, "a word must not end after the clip does"
    assert clip_duration_seconds - last_word_end <= _MAX_TRAILING_GAP_SECONDS, (
        f"last word ends {clip_duration_seconds - last_word_end:.3f}s before the clip -- "
        f"further than the {_MAX_TRAILING_GAP_SECONDS}s real-trailing-pause tolerance, "
        "suggesting a scaling/unit bug rather than normal trailing silence"
    )

    # Real-numbers datapoint for the handover (Task 19.2 Evidence).
    print(
        f"\n[word-boundary probe] line={TEST_LINE!r} words={len(word_boundaries)} "
        f"clip_duration={clip_duration_seconds:.3f}s last_word_end={last_word_end:.3f}s"
    )
