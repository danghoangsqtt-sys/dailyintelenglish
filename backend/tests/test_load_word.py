"""Phase 97 (D159, D160): the Load the word Short and the loop in the audio mix."""

import json

import pytest

from backend.content.load_word import LOOP_MS, LoadCard, build_beats, load_prompt
from backend.media.audio_service import loop_ms_of, looped_voice
from backend.schemas.project import CARD_STYLES, LINE_DRAWN_STYLES, SHORT_STYLES, VOICE_ONLY_STYLES

WORD = {"word": "Compensation", "ipa": "ˌkɑːmpenˈseɪʃn", "part_of_speech": "noun", "meaning_en": "money paid for a loss.", "meaning_vi": "khoản đền bù.",
        "example_en": "No amount of compensation can make up for it.", "example_vi": "Không khoản đền bù nào bù đắp được."}


def test_the_loop_the_word_once_and_the_example():
    beats = build_beats(LoadCard.model_validate(WORD))
    assert [text for text, _ in beats] == ["Compensation.", "Compensation.", "No amount of compensation can make up for it."]
    assert [card["beat"] for _, card in beats] == ["load", "reveal", "example"]
    assert beats[0][1]["loop_ms"] == LOOP_MS and "loop_ms" not in beats[1][1]
    assert beats[0][1]["ipa"] == "/ˌkɑːmpenˈseɪʃn/" and beats[0][1]["meaning_vi"] == "khoản đền bù" and beats[0][1]["word"] == "compensation"


def test_the_example_must_use_the_word():
    with pytest.raises(ValueError, match="does not use the word"):
        build_beats(LoadCard.model_validate({**WORD, "example_en": "They paid me for the damage."}))


def test_only_a_line_that_asks_for_a_loop_gets_one():
    assert loop_ms_of({"language_notes": json.dumps({"loadword": {"loop_ms": LOOP_MS}})}) == LOOP_MS
    for line in ({}, {"language_notes": "{}"}, {"language_notes": "not json"}, {"language_notes": json.dumps({"loadword": {"beat": "reveal"}})}):
        assert loop_ms_of(line) == 0


def test_the_loop_fills_its_time_and_keeps_going_faster():
    from pydub import AudioSegment
    from pydub.generators import Sine

    clip = AudioSegment.silent(duration=300, frame_rate=24000) + Sine(440).to_audio_segment(duration=800).set_frame_rate(24000) + AudioSegment.silent(duration=700, frame_rate=24000)
    looped = looped_voice(clip, 8000)
    assert abs(len(looped) - 8000) < 600  # stays within one short clip of the wanted time
    # the padding around the word is cut, so most of the loop has sound
    assert looped.dBFS > clip.dBFS


def test_the_prompt_and_the_lists():
    assert "over and over" in load_prompt("Work", "B1", [])
    assert "'compensation'" in load_prompt("Work", "B1", ["compensation"])
    assert all("loadword" in styles for styles in (CARD_STYLES, LINE_DRAWN_STYLES, SHORT_STYLES, VOICE_ONLY_STYLES))
