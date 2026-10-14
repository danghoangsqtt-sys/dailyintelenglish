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
