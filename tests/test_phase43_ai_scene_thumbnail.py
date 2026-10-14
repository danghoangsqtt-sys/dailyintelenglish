"""Phase 43 (D122): the "AI scene" thumbnail -- Qwen-Image-Edit-2511 draws both characters (their sprites as references) in
a topic scene; the app chooses the frame and adds the headline, badges and logo. GPU-free tests."""

from __future__ import annotations

import importlib.util

import pytest
from PIL import Image

from backend.ai.image import recipes
from backend.core.paths import AI_DIR
from tests.test_visuals_project_api import client  # noqa: F401


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
    assert "heads and faces do not overlap" in prompt and "Medium shot from the waist up" in prompt
    assert "in a busy outdoor fruit market on a clear sunny day" in prompt and "left part shows the place itself" in prompt
    assert "natural daylight" in prompt and "darker" not in prompt and "hair colour" in prompt
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
    wide = tc.render(inputs, suggestion, "16x9", 0, "qwen_scene")
    tall = tc.render(inputs, suggestion, "9x16", 0, "qwen_scene")
    assert wide.size == tc.SIZES["16x9"] and tall.size == tc.SIZES["9x16"]
    # the right part of the frame (the faces) is not shaded or written on: same colour as the drawn picture
    graded = tc.grade_ai_scene(picture)
    assert wide.getpixel((1000, 300)) == graded.getpixel((frame["left"] + 1000, 300))  # the faces' side is not shaded
    background = tc.ai_scene_picture(inputs["ai_scenes"][0], tc.SIZES["16x9"])
    assert background.getpixel((10, 700)) == graded.getpixel((frame["left"] + 10, 700))
    with pytest.raises(ValueError, match="no AI scene"):
        tc.render({"ai_scenes": []}, suggestion, "16x9", 0, "qwen_scene")


def test_the_grade_brightens_and_saturates_a_dull_picture():
    from PIL import ImageStat

    from backend.media import thumbnail_compose as tc

    dull = Image.new("RGB", (64, 64), (90, 80, 70))
    for x in range(64):
        dull.putpixel((x, 0), (60, 50, 45))
        dull.putpixel((x, 63), (140, 120, 100))
    graded = tc.grade_ai_scene(dull)
    assert ImageStat.Stat(graded).mean[0] > ImageStat.Stat(dull).mean[0]  # brighter


def test_a_long_supporting_line_shrinks_to_the_title_box():
    from PIL import ImageDraw

    from backend.media import thumbnail_compose as tc

    draw = ImageDraw.Draw(Image.new("RGB", (1280, 720)))
    width, _ = tc._pill(draw, "Quantity expressions B1 and more words", (60, 400), 36, "#FFD54F", "#000000",
                        max_width=380)
    assert width <= 380


# --- 43.4 API: draw the scenes, then the "AI scene" kind renders from them --------------------------------------------

@pytest.fixture
def ai_api(client, tmp_path, monkeypatch):  # noqa: F811
    from backend.ai.image.engine import FakeImageEngine
    from backend.media import thumbnail_service
    from backend.schemas.thumbnail import ThumbnailSuggestionPack
    from tests.test_thumbnail_compose import _with_sprites
    from tests.test_thumbnail_service import suggestion_json

    async def fake(project, template, variant_count, router=None):
        return ThumbnailSuggestionPack.model_validate_json(suggestion_json(variant_count))

    monkeypatch.setattr(thumbnail_service, "generate_suggestions", fake)
    monkeypatch.setattr(FakeImageEngine, "qwen_calls", [])
    monkeypatch.setattr(FakeImageEngine, "qwen_available", True)
    return client, _with_sprites(client, tmp_path), FakeImageEngine


def test_the_ai_scenes_are_drawn_with_both_sprites_and_framed_on_their_faces(ai_api):
    from tests.test_visuals_project_api import data

    client, project, engine = ai_api  # noqa: F811
    url = f"/api/projects/{project['id']}/thumbnails"
    templates = {t["id"]: t for t in data(client.get(f"/api/thumbnails/templates?project_id={project['id']}"))}
    assert templates["qwen_scene"]["available"] is False
    assert client.post(f"{url}/generate", json={"template_name": "qwen_scene", "variant_count": 3}).status_code == 422

    response = client.post(f"{url}/ai-scenes", json={"count": 3})
    assert response.status_code == 201
    scenes = response.json()["data"]
    assert [scene["index"] for scene in scenes] == [0, 1, 2]
    assert all(scene["faces"] == 2 and scene["side"] == "left" and not scene["crowded"] for scene in scenes)
    (call,) = engine.qwen_calls
    assert call["model"] == "qwen_edit" and call["detect_faces"] is True and len(call["items"]) == 3
    item = call["items"][0]
    assert (item["width"], item["height"]) == (1536, 720) and len(item["references"]) == 2
    assert all(path.endswith("smile__open.png") for path in item["references"])
    assert "picture 1" in item["prompt"] and "picture 2" in item["prompt"]
    assert client.get(scenes[0]["preview_url"]).headers["content-type"] == "image/png"

    templates = {t["id"]: t for t in data(client.get(f"/api/thumbnails/templates?project_id={project['id']}"))}
    assert templates["qwen_scene"]["available"] is True and templates["qwen_scene"]["scene_count"] == 3
    rows = data(client.post(f"{url}/generate", json={"template_name": "qwen_scene", "variant_count": 3}))
    assert len(rows) == 3 and {row["template_name"] for row in rows} == {"qwen_scene"}


def test_one_scene_can_be_drawn_again_and_the_old_picture_goes(ai_api):
    from pathlib import Path

    from backend.media import ai_scene
    from tests.test_visuals_project_api import data

    client, project, engine = ai_api  # noqa: F811
    url = f"/api/projects/{project['id']}/thumbnails/ai-scenes"
    assert client.post(url, json={"count": 2}).status_code == 201
    before = {scene["index"]: scene["image"] for scene in ai_scene.load_scenes(project["id"])}
    usual = engine.qwen_faces
    engine.qwen_faces = [[300, 100, 600, 420, 1.0], [900, 100, 1200, 420, 1.0]]  # this time the heads spread out
    try:
        scenes = data(client.post(f"{url}/1/redraw"))
    finally:
        engine.qwen_faces = usual
    assert scenes[1]["crowded"] and not scenes[0]["crowded"]
    after = {scene["index"]: scene["image"] for scene in ai_scene.load_scenes(project["id"])}
    assert after[0] == before[0] and after[1] != before[1] and not Path(before[1]).exists()
    assert client.post(f"{url}/7/redraw").status_code == 404


def test_without_the_model_the_ai_scenes_say_so(ai_api):
    client, project, engine = ai_api  # noqa: F811
    engine.qwen_available = False
    response = client.post(f"/api/projects/{project['id']}/thumbnails/ai-scenes", json={"count": 1})
    assert response.status_code == 422 and "Qwen-Image-Edit-2511" in response.json()["error"]
