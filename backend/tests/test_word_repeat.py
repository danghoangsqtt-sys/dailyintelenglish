"""Phase 96 (D147-D151): the Word of the day Short -- one word, its picture, six sayings and one example."""

import json

import pytest
from pydantic import ValidationError

from backend.content.word_repeat import REPEATS, WordCard, build_beats, example_uses_word, word_prompt
from backend.schemas.project import LINE_DRAWN_STYLES

WORD = {"word": "Meticulous", "ipa": "məˈtɪk.jə.ləs", "part_of_speech": "adjective", "meaning_en": "very careful about small details",
        "meaning_vi": "tỉ mỉ, cẩn thận", "example_en": "He is meticulous in his work.", "example_vi": "Ông ấy tỉ mỉ trong công việc.",
        "picture": "hands carefully painting a violin"}


def test_six_sayings_then_one_example():
    beats = build_beats(WordCard.model_validate(WORD))
    assert [text for text, _ in beats] == ["Meticulous."] * REPEATS + ["He is meticulous in his work."]
    assert REPEATS == 6 and [card["beat"] for _, card in beats] == ["repeat"] * 6 + ["example"]
    assert [card["repeat"] for _, card in beats[:6]] == [1, 2, 3, 4, 5, 6]
    # every line can draw the whole video
    assert all(card["meaning_vi"] == "tỉ mỉ, cẩn thận" and card["ipa"] == "/məˈtɪk.jə.ləs/" and card["word"] == "meticulous" for _, card in beats)


def test_the_example_must_use_the_word():
    with pytest.raises(ValueError, match="does not use the word"):
        build_beats(WordCard.model_validate({**WORD, "example_en": "She checks every small thing twice."}))
    assert example_uses_word(WordCard.model_validate({**WORD, "word": "study", "example_en": "She studies at night."}))


def test_a_long_sentence_is_not_a_word():
    with pytest.raises(ValidationError):
        WordCard.model_validate({**WORD, "word": "a very long phrase here"})


def test_stray_chinese_is_removed():
    assert WordCard.model_validate({**WORD, "meaning_vi": "tỉ mỉ也"}).meaning_vi == "tỉ mỉ"


def test_the_prompt_uses_the_owner_word_and_forbids_faces():
    prompt = word_prompt("Careful work", "B1", ["meticulous"])
    assert '"meticulous"' in prompt and "nobody's face" in prompt and "said six times" in prompt
    assert "wordday" in LINE_DRAWN_STYLES


async def test_a_word_without_the_image_model_or_a_library_picture_has_none(db, monkeypatch, tmp_path):
    from backend.core.config import settings
    from backend.media import short_pictures

    monkeypatch.setattr(settings, "DATA_DIR", tmp_path)
    monkeypatch.setattr("backend.ai.image.engine.generation_available", lambda: False)
    assert await short_pictures.ensure_pictures(db, "p1", "wordday", [{}]) == {}
    assert await short_pictures.ensure_pictures(db, "p1", "wordday", [{"word": "cozy", "picture": "a warm room"}]) == {}


async def test_an_uploaded_picture_is_cropped_to_9_16_and_used(db, monkeypatch, tmp_path):
    import io

    from PIL import Image

    from backend.core.config import settings
    from backend.core.exceptions import ValidationError as AppValidationError
    from backend.media import short_pictures

    monkeypatch.setattr(settings, "DATA_DIR", tmp_path)
    monkeypatch.setattr("backend.ai.image.engine.generation_available", lambda: False)
    buffer = io.BytesIO()
    Image.new("RGB", (1600, 900), "red").save(buffer, "JPEG")
    path = await short_pictures.upload("p1", "cozy", buffer.getvalue())
    with Image.open(path) as image:
        assert image.size == short_pictures.PICTURE_SIZE
    assert await short_pictures.ensure_pictures(db, "p1", "wordday", [{"word": "cozy", "picture": "a warm room"}]) == {"cozy": path}
    with pytest.raises(AppValidationError):
        await short_pictures.upload("p1", "cozy", b"not a picture")


def test_cards_survive_json():
    assert json.loads(json.dumps(build_beats(WordCard.model_validate(WORD))[0][1]))["word"] == "meticulous"
