"""Phase 96.6: the Basic vs Advanced Short."""

import pytest

from backend.content.level_up import LevelUp, build_beats, level_prompt
from backend.schemas.project import LINE_DRAWN_STYLES, SHORT_STYLES, VOICE_ONLY_STYLES


def _level(count=4):
    pairs = [("I'm tired", "I'm beat"), ("Good luck", "Break a leg"), ("I'm very busy", "I'm swamped"), ("I'm happy", "I'm over the moon"),
             ("I fell asleep", "I nodded off"), ("Leave me alone", "Give me a break"), ("It's easy", "It's a piece of cake")]
    return {"theme": "everyday", "pairs": [{"basic": basic, "advanced": advanced, "meaning_en": "when tired.", "meaning_vi": "mệt.", "picture": "a sofa"}
                                           for basic, advanced in pairs[:count]]}


def test_each_pair_is_the_basic_then_the_advanced_phrase():
    beats = build_beats(LevelUp.model_validate(_level()))
    assert [text for text, _ in beats[:4]] == ["I'm tired.", "I'm beat.", "I'm beat.", "Good luck."]
    assert [card["beat"] for _, card in beats[:3]] == ["basic", "advanced", "advanced"]
    # the picture of a pair is named by its advanced phrase, on all of its lines
    assert beats[0][1]["word"] == beats[2][1]["word"] == "I'm beat" and beats[1][1]["meaning_vi"] == "mệt"


def test_at_most_five_pairs_no_repeats_and_no_pair_of_the_same_phrase():
    assert len(build_beats(LevelUp.model_validate(_level(7)))) == 15
    same = _level(3)
    same["pairs"][1] = {**same["pairs"][1], "advanced": "good luck"}
    with pytest.raises(ValueError, match="different pairs"):
        build_beats(LevelUp.model_validate(same))


def test_the_prompt_asks_for_real_phrases_and_no_faces():
    prompt = level_prompt("Feelings", "A2", [])
    assert "never invent" in prompt and "real moment" in prompt and "Never draw the words of an idiom literally" in prompt


def test_nobody_is_on_screen():
    assert "levelup" in LINE_DRAWN_STYLES and "levelup" in SHORT_STYLES and "levelup" in VOICE_ONLY_STYLES


def test_an_edited_card_keeps_its_phrases():
    """Found 2026-11-04: the edit check dropped the two phrases of a card."""
    from backend.content.beats_service import checked_card

    card = checked_card("levelup", {"beat": "advanced", "number": 2, "word": "I'm beat", "basic": "I'm tired", "advanced": "I'm beat", "picture": "a sofa"})
    assert (card["basic"], card["advanced"], card["number"]) == ("I'm tired", "I'm beat", 2)
