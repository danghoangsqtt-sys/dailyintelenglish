"""Legacy emotion directions are stripped from scripts; Phase 77 never synthesizes them."""

from backend.ai.tts.vocal_cues import caption_text, has_vocal_cues


def test_legacy_and_variant_tags_keep_clean_caption_text():
    text = "Hello [cười:ha-ha] there [cười:hi-hi]. [thở dài] [hắng giọng] Okay."
    assert caption_text(text) == "Hello there. Okay."
    assert has_vocal_cues(text)
    assert not has_vocal_cues("[unknown] Hello")
    assert caption_text("[unknown] Hello") == "[unknown] Hello"


def test_unannotated_dialogue_is_returned_unchanged():
    text = "  Spacing,  stays   as written . "
    assert caption_text(text) is text
