"""Parser and decoded timing checks for Phase 74 vocal directions."""

import io

import pytest
from pydub import AudioSegment

from backend.ai.tts import tts_service
from backend.ai.tts.tts_service import WordBoundary, _join_vocal_parts_sync
from backend.ai.tts.vocal_cues import caption_text, has_vocal_cues, split_vocal_cues, to_omnivoice_text


def test_legacy_and_variant_tags_keep_clean_caption_text():
    text = "Hello [cười:ha-ha] there [cười:hi-hi]. [thở dài] [hắng giọng] Okay."
    parts = split_vocal_cues(text)
    assert [part.kind for part in parts].count("cue") == 4
    assert [part.text for part in parts if part.kind == "cue"] == [
        "Ha, ha!", "Hee, hee!", "Ahh...", "Ahem.",
    ]
    assert caption_text(text) == "Hello there. Okay."
    assert has_vocal_cues(text)
    assert not has_vocal_cues("[unknown] Hello")
    assert caption_text("[unknown] Hello") == "[unknown] Hello"


def test_ahem_lowers_only_the_first_short_clause():
    parts = split_vocal_cues("[hắng giọng] We should talk now. Then return to normal.")
    assert parts[0].kind == "cue"
    assert parts[1].text == "We should talk now."
    assert parts[1].pitch_delta_hz < 0
    assert parts[2].text == "Then return to normal."
    assert parts[2].pitch_delta_hz == 0


def test_omnivoice_cue_conversion_and_unsupported_ahem():
    assert to_omnivoice_text("Hi [cười:ha-ha], [cười:hi-hi] and [thở dài].") == (
        "Hi [laughter], [laughter] and [sigh]."
    )
    with pytest.raises(ValueError, match="does not support"):
        to_omnivoice_text("[hắng giọng] Let's talk.")


def test_decoded_segments_shift_only_dialogue_word_boundaries():
    def mp3(duration_ms: int) -> bytes:
        output = io.BytesIO()
        AudioSegment.silent(duration=duration_ms).export(output, format="mp3")
        return output.getvalue()

    audio, words = _join_vocal_parts_sync([
        ("speech", mp3(210), [WordBoundary("Hello", 0.03, 0.07)]),
        ("cue", mp3(180), [WordBoundary("Ha", 0.01, 0.08)]),
        ("speech", mp3(260), [WordBoundary("there", 0.04, 0.09)]),
    ])
    assert len(audio) > 0
    assert [word.text for word in words] == ["Hello", "there"]
    assert 0.35 <= words[1].offset_sec <= 0.5


@pytest.mark.asyncio
async def test_ahem_uses_selected_voice_and_restores_pitch(monkeypatch):
    output = io.BytesIO()
    AudioSegment.silent(duration=180).export(output, format="mp3")
    calls = []

    async def fake_edge(text: str, speaker: dict, *, pitch_delta_hz: int = 0):
        calls.append((text, speaker["voice_id"], pitch_delta_hz))
        return output.getvalue(), [WordBoundary(text.split()[0], 0.02, 0.05)]

    monkeypatch.setattr(tts_service, "_synthesize_edge_tts", fake_edge)
    audio, words = await tts_service._synthesize_with_vocal_cues(
        "[hắng giọng] We should talk. Then continue.", {"voice_id": "en-GB-RyanNeural"},
    )
    assert audio
    assert [call[2] for call in calls] == [0, -10, 0]
    assert {call[1] for call in calls} == {"en-GB-RyanNeural"}
    assert [word.text for word in words] == ["We", "Then"]
