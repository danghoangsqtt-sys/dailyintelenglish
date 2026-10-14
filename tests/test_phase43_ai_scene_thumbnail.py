"""Phase 43 (D122): the "AI scene" thumbnail -- Qwen-Image-Edit-2511 draws both characters (their sprites as references) in
a topic scene; the app chooses the frame and adds the headline, badges and logo. GPU-free tests."""

from __future__ import annotations

import importlib.util

import pytest
from PIL import Image

from backend.ai.image import recipes
from backend.core.paths import AI_DIR


def _runner():
    spec = importlib.util.spec_from_file_location("qwen_runner_43", AI_DIR / "image" / "qwen_runner.py")
    runner = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(runner)
    return runner


# --- 43.1 worker: several reference pictures ------------------------------------------------------------------------

def test_a_qwen_edit_item_may_carry_one_to_three_references():
    runner = _runner()
    item = {"prompt": "p", "seed": 1, "width": 1536, "height": 720, "output_path": "x.png"}
    assert runner.validate({"model": "qwen_edit", "items": [{**item, "references": ["a.png", "b.png"]}]})[0] == "qwen_edit"
    assert runner.validate({"model": "qwen_edit", "items": [{**item, "reference": "a.png"}]})[0] == "qwen_edit"
    for bad in ([], ["a", "b", "c", "d"], "a.png", [""], [1]):
        with pytest.raises(ValueError, match="references must be"):
            runner.validate({"model": "qwen_edit", "items": [{**item, "references": bad}]})
    with pytest.raises(ValueError, match="reference"):
        runner.validate({"model": "qwen_edit", "items": [item]})
    assert runner.references_of({"references": ["a.png", "b.png"], "reference": "z.png"}) == ["a.png", "b.png"]
    assert runner.references_of({"reference": "z.png"}) == ["z.png"]


def test_a_transparent_sprite_reference_is_laid_on_white(tmp_path):
    runner = _runner()
    sprite = Image.new("RGBA", (8, 8), (0, 0, 0, 0))
    sprite.putpixel((4, 4), (200, 10, 10, 255))
    sprite.save(tmp_path / "sprite.png")
    Image.new("RGB", (8, 8), (10, 200, 10)).save(tmp_path / "photo.jpg")
    flat = runner._flat_reference(Image, str(tmp_path / "sprite.png"))
    assert flat.mode == "RGB" and flat.getpixel((0, 0)) == (255, 255, 255) and flat.getpixel((4, 4)) == (200, 10, 10)
    assert runner._flat_reference(Image, str(tmp_path / "photo.jpg")).mode == "RGB"


def test_the_ai_scene_prompt_names_both_pictures_and_keeps_a_plain_side():
    prompt = recipes.qwen_thumbnail_scene_prompt(
        ["Hoang", "Kim"], "Shopping at the Market. The group navigates the local market.", "a busy outdoor fruit market")
    assert "Hoang (the person in picture 1)" in prompt and "Kim (the person in picture 2)" in prompt
    assert "heads and faces do not overlap" in prompt and "Head-and-shoulders close-up" in prompt
    assert "in a busy outdoor fruit market" in prompt and "left part is only softly blurred background" in prompt
    assert "no text" in prompt.lower() and "no logo" in prompt and "thumbnail" not in prompt.lower()
    fallback = recipes.qwen_thumbnail_scene_prompt(["Hoang", "Kim"], "Shopping at the Market. More words.")
    assert "a real place that fits shopping at the market" in fallback
    assert "picture 1" in recipes.qwen_thumbnail_scene_prompt(["Kim"], "Cooking")


# --- 43.2 framing: the faces decide the window and the headline side ------------------------------------------------

def test_a_pair_right_of_centre_gets_the_title_on_the_left_without_touching_a_head():
    from backend.media import ai_scene

    faces = [[560, 79, 818, 397, 1.0], [901, 180, 1134, 468, 1.0]]  # measured on the real 2026-10-14 draw (seed 5)
    frame = ai_scene.choose_frame(faces)
    assert frame["side"] == "left" and frame["left"] == 0 and not frame["crowded"] and frame["faces"] == 2
    x, _, width, _, align = frame["text_box"]
    text = (x * 1280, 0, width * 1280)
    for zone in ai_scene.head_zones(faces):
        shifted = (zone[0] - frame["left"], zone[1], zone[2] - frame["left"], zone[3])
        assert text[0] + text[2] + ai_scene.TEXT_GAP <= shifted[0] + 1  # a gap before the first head
        assert shifted[2] <= 1280 - ai_scene.SAFE_MARGIN + 1  # heads inside the frame with the margin
    assert align == "left" and width >= ai_scene.MIN_TEXT_SHARE - 0.08


def test_a_pair_on_the_left_gets_the_title_on_the_right_and_the_window_slides():
    from backend.media import ai_scene

    frame = ai_scene.choose_frame([[200, 100, 420, 380], [470, 120, 680, 400]])
    assert frame["side"] == "right" and frame["text_box"][4] == "right" and not frame["crowded"]
    assert 0 <= frame["left"] <= 1536 - 1280


def test_a_crowded_or_faceless_picture_is_flagged_for_drawing_again():
    from backend.media import ai_scene

    middle = ai_scene.choose_frame([[300, 100, 600, 420], [900, 100, 1200, 420]])  # heads spread over the whole width
    assert middle["crowded"]
    nobody = ai_scene.choose_frame([])
    assert nobody["crowded"] and nobody["faces"] == 0
    in_badge = ai_scene.choose_frame([[1000, 560, 1150, 700]])  # a face down in the duration-stamp corner
    assert in_badge["crowded"]


# --- 43.3 compose: crop the chosen window, title on the free side, 9:16 from the same picture ------------------------

def test_the_ai_scene_thumbnail_is_composed_from_the_drawn_picture(tmp_path):
    from backend.media import ai_scene, thumbnail_compose as tc
    from backend.schemas.thumbnail import ThumbnailSuggestion

    picture = Image.new("RGB", ai_scene.DRAW_SIZE, (40, 120, 60))
    for x in range(1536):  # a horizontal ramp: the crop position shows in the pixels
        picture.putpixel((x, 700), (x % 256, 0, 0))
    picture.save(tmp_path / "scene.png")
    faces = [[560, 79, 818, 397], [901, 180, 1134, 468]]
    frame = ai_scene.choose_frame(faces)
    inputs = {"cefr": "B1", "episode": 2, "ai_scenes": [{"image": str(tmp_path / "scene.png"), "frame": frame,
                                                          "heads": ai_scene.head_zones(faces)}]}
    suggestion = ThumbnailSuggestion(
        headline="Shopping Like A Local", supporting_text="Quantity expressions B1 and a very long extra tail",
        topic_keywords=["market"],
        palette={"primary": "#1B5E20", "secondary": "#2E7D32", "accent": "#FFD54F", "text": "#FFFFFF"})
    wide = tc.render(inputs, suggestion, "16x9", 0, "ai_scene")
    tall = tc.render(inputs, suggestion, "9x16", 0, "ai_scene")
    assert wide.size == tc.SIZES["16x9"] and tall.size == tc.SIZES["9x16"]
    # the right part of the frame (the faces) is not shaded or written on: same colour as the drawn picture
    assert wide.getpixel((1000, 300)) == (40, 120, 60)
    background = tc.ai_scene_picture(inputs["ai_scenes"][0], tc.SIZES["16x9"])
    assert background.getpixel((10, 700)) == picture.getpixel((frame["left"] + 10, 700))
    with pytest.raises(ValueError, match="no AI scene"):
        tc.render({"ai_scenes": []}, suggestion, "16x9", 0, "ai_scene")


def test_a_long_supporting_line_shrinks_to_the_title_box():
    from PIL import ImageDraw

    from backend.media import thumbnail_compose as tc

    draw = ImageDraw.Draw(Image.new("RGB", (1280, 720)))
    width, _ = tc._pill(draw, "Quantity expressions B1 and more words", (60, 400), 36, "#FFD54F", "#000000",
                        max_width=380)
    assert width <= 380
