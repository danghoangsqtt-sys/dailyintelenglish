"""Phase 96.4: a picture for each sentence."""

import pytest
from pydantic import ValidationError

from backend.content.picture_story import HOOK, PictureStory, build_beats, closing_line, story_prompt
from backend.schemas.project import CARD_STYLES, LINE_DRAWN_STYLES, SHORT_STYLES, VOICE_ONLY_STYLES


def _story(count=6, sentence="I take off my shoes"):
    return {"title": "At the beach", "lines": [{"sentence": f"{sentence} {n}", "keywords": ["shoes"], "translation_vi": "Tôi cởi giày.",
                                                "picture": f"hands pulling off a shoe {n}"} for n in range(count)]}


def test_the_challenge_each_sentence_with_its_picture_and_the_level():
    beats = build_beats(PictureStory.model_validate(_story()), "A2")
    assert beats[0][0] == HOOK and beats[-1][0] == "If you understood this, you are an A2 listener."
    assert beats[1][0] == "I take off my shoes 0." and beats[1][1]["keywords"] == ["shoes"] and beats[1][1]["translation_vi"] == "Tôi cởi giày."
    assert [card["word"] for _, card in beats[1:-1]] == [f"line {n}" for n in range(1, 7)]
    # the opening and the closing lines stand on the first and the last pictures
    assert beats[0][1]["word"] == "line 1" and beats[-1][1]["word"] == "line 6"
    assert beats[-1][1]["picture"] == "hands pulling off a shoe 5"


def test_the_article_of_the_level():
    assert closing_line("b1") == "If you understood this, you are a B1 listener."


def test_limits():
    assert len(build_beats(PictureStory.model_validate(_story(12)))) == 10
    with pytest.raises(ValidationError):
        PictureStory.model_validate(_story(3))
    with pytest.raises(ValueError, match="more than"):
        build_beats(PictureStory.model_validate(_story(sentence="I walk slowly along the long wide beach all day")))


def test_the_prompt_asks_for_what_can_be_seen_and_no_faces():
    prompt = story_prompt("At the beach", "A2", [])
    assert "own eyes" in prompt and "No face" in prompt and "cannot be seen" in prompt
    assert all("picstory" in styles for styles in (CARD_STYLES, LINE_DRAWN_STYLES, SHORT_STYLES, VOICE_ONLY_STYLES))
