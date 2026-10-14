"""Task 36.3/36.4 (D90-D92): the composed episode thumbnail and the outside-AI picture, through the real API."""

from __future__ import annotations

import hashlib
import io
import json
import re
import sqlite3
from pathlib import Path

import pytest
from PIL import Image

from backend.core.config import settings
from backend.schemas.thumbnail import ThumbnailSuggestionPack
from backend.media import thumbnail_service
from backend.library import sprite_service
from tests.test_activity_illustrations import _project_with_inserts
from tests.test_sprite_service import _figure
from tests.test_thumbnail_service import suggestion_json
from tests.test_visuals_project_api import client, data  # noqa: F401


@pytest.fixture(autouse=True)
def fake_suggestions(monkeypatch):
    async def fake(project, template, variant_count, router=None):
        return ThumbnailSuggestionPack.model_validate_json(suggestion_json(variant_count))

    monkeypatch.setattr(thumbnail_service, "generate_suggestions", fake)


def _with_sprites(client, tmp_path) -> dict:  # noqa: F811
    """A project whose two cast characters have talking sprites and whose storyboard uses an approved activity picture."""
    project = _project_with_inserts(client)
    with sqlite3.connect(settings.db_path) as connection:
        cast = connection.execute("SELECT character_id FROM project_cast WHERE project_id = ? ORDER BY speaker_index",
                                  (project["id"],)).fetchall()
    for index, (character_id,) in enumerate(cast):
        files = {}
        for name in ("calm__closed", "calm__open", "smile__open", "surprised__open"):
            files[name] = tmp_path / f"sprite-{index}-{name}.png"
            _figure(files[name], body=(40 + 80 * index, 30, 100, 255))
        accepted, _ = sprite_service.check_folder(files)
        sprite_service._write_set(character_id, files, accepted, lambda _path: None)
    return project


def test_composed_thumbnails_use_the_cast_sprites_and_the_episode_pictures(client, tmp_path):  # noqa: F811
    project = _with_sprites(client, tmp_path)
    rows = data(client.post(f"/api/projects/{project['id']}/thumbnails/generate",
                            json={"template_name": "composed", "variant_count": 3}))
    assert len(rows) == 3 and {row["template_name"] for row in rows} == {"composed"}
    sidecar = json.loads((settings.DATA_DIR / "thumbnails" / project["id"] / rows[0]["revision"] / "render.json")
                         .read_text(encoding="utf-8"))
    composition = sidecar["composition"]
    assert composition["backgrounds"] and composition["backgrounds"][0].endswith("generic-pack.png")  # the matched insert
    assert sorted(character["slot"] for character in composition["characters"]) == [0, 1]
    assert composition["cefr"] == project["cefr_level"].upper()
    hashes = set()
    for row in rows:
        response = client.get(row["assets"]["16x9"]["png"])
        assert response.status_code == 200
        with Image.open(io.BytesIO(response.content)) as image:
            assert image.size == (1280, 720)
        hashes.add(hashlib.sha256(response.content).hexdigest())
    assert len(hashes) == 3  # each variant changes the layout and the expressions


def test_an_edit_re_renders_the_same_composition(client, tmp_path):  # noqa: F811
    project = _with_sprites(client, tmp_path)
    row = data(client.post(f"/api/projects/{project['id']}/thumbnails/generate",
                           json={"template_name": "composed", "variant_count": 3}))[0]
    edited = data(client.patch(f"/api/projects/{project['id']}/thumbnails/{row['id']}", json={
        "revision": row["revision"], "headline": "Weekend Trip English", "palette": row["suggestion"]["palette"]}))
    assert edited["suggestion"]["headline"] == "Weekend Trip English"
    sidecar = json.loads((settings.DATA_DIR / "thumbnails" / project["id"] / edited["revision"] / "render.json")
                         .read_text(encoding="utf-8"))
    assert sidecar["composition"]["characters"] and sidecar["composition"]["backgrounds"]


def test_the_outside_ai_prompt_names_the_characters_and_links_their_pictures(client, tmp_path):  # noqa: F811
    project = _with_sprites(client, tmp_path)
    result = data(client.get(f"/api/projects/{project['id']}/thumbnails/outside-prompt"))
    assert "16:9" in result["prompt"] and "No text" in result["prompt"] and "attached picture 1" in result["prompt"]
    assert "packing" in result["prompt"]  # the storyboard's illustration
    assert [picture["number"] for picture in result["pictures"]] == [1, 2]
    for picture in result["pictures"]:
        assert picture["name"] in result["prompt"]
        assert client.get(picture["url"]).status_code == 200


def test_the_outside_ai_picture_is_uploaded_checked_and_used(client, tmp_path):  # noqa: F811
    project = _with_sprites(client, tmp_path)
    url = f"/api/projects/{project['id']}/thumbnails"
    assert client.post(f"{url}/generate", json={"template_name": "outside_ai", "variant_count": 3}).status_code == 422
    assert client.post(f"{url}/outside-image", files={"file": ("x.png", b"not a picture", "image/png")}).status_code == 422
    small = io.BytesIO()
    Image.new("RGB", (320, 180), "#123456").save(small, format="PNG")
    assert client.post(f"{url}/outside-image", files={"file": ("s.png", small.getvalue(), "image/png")}).status_code == 422
    good = io.BytesIO()
    Image.new("RGB", (1536, 864), "#2A7F62").save(good, format="JPEG")
    response = client.post(f"{url}/outside-image", files={"file": ("ai.jpg", good.getvalue(), "image/jpeg")})
    assert response.status_code == 201
    assert client.get(f"{url}/outside-image").headers["content-type"] == "image/png"
    templates = data(client.get(f"/api/thumbnails/templates?project_id={project['id']}"))
    assert templates[1]["id"] == "outside_ai" and templates[1]["available"]
    rows = data(client.post(f"{url}/generate", json={"template_name": "outside_ai", "variant_count": 3}))
    picture = client.get(rows[0]["assets"]["16x9"]["png"]).content
    with Image.open(io.BytesIO(picture)) as image:
        corner = image.convert("RGB").getpixel((1260, 700))  # bottom-right: the uploaded picture, no sprite drawn there
    assert abs(corner[1] - 0x7F) < 40 and Path(thumbnail_service.outside_image_path(project["id"])).is_file()


def test_vertical_cover_preserves_both_people_and_keeps_content_in_the_platform_safe_area(tmp_path):
    from PIL import ImageDraw

    from backend.media import thumbnail_compose as compose
    from backend.schemas.thumbnail import ThumbnailSuggestion

    source = Image.new("RGB", (1280, 720), "#34543A")
    painter = ImageDraw.Draw(source)
    painter.rectangle((0, 0, 150, 719), fill="#F06420")
    painter.rectangle((151, 0, 300, 719), fill="#14A8B5")
    painter.rectangle((650, 250, 750, 350), fill="blue")
    painter.rectangle((1000, 250, 1100, 350), fill="red")
    source_path = tmp_path / "pair.png"
    source.save(source_path)
    suggestion = ThumbnailSuggestion(headline="Master Market English", supporting_text="Bargaining made easy",
                                     topic_keywords=["market"], palette={"primary": "#2D6A4F", "secondary": "#40916C",
                                                                     "accent": "#FFD700", "text": "#FFFFFF"})
    cover = compose.render({"outside_image": str(source_path), "cefr": "B1", "episode": 2}, suggestion,
                           "9x16", 0, "outside_ai")
    assert cover.size == (720, 1280)
    assert cover.getpixel((390, 378))[2] > 200  # the first person is still visible
    assert cover.getpixel((560, 378))[0] > 200  # so is the second person
    assert abs(cover.getpixel((100, 1100))[0] - cover.getpixel((500, 1100))[0]) > 80  # scene fills the lower canvas

    safe, photo, headline = compose.PORTRAIT_SAFE, compose.PORTRAIT_PHOTO, compose.PORTRAIT_HEADLINE
    zone_source = (Path(__file__).resolve().parents[1] / "renderer" / "src" / "safeZone.ts").read_text(encoding="utf-8")
    for typescript_name, python_name in (("left", "left"), ("right", "right"), ("top", "top"), ("bottom", "bottom"),
                                         ("columnX", "column_x"), ("columnFromY", "column_from_y")):
        original = re.search(rf"\b{typescript_name}:\s*(\d+)", zone_source)
        assert original and safe[python_name] == round(int(original.group(1)) * 2 / 3)
    assert safe["left"] <= photo[0] < photo[2] <= safe["right"]
    assert safe["top"] <= photo[1] < photo[3] < safe["column_from_y"]
    assert safe["left"] <= headline[0] and headline[0] + headline[2] <= safe["column_x"]
    assert safe["column_from_y"] < headline[1] and headline[1] + headline[3] < safe["bottom"]


def test_long_vertical_thumbnail_text_is_shortened_inside_the_safe_box():
    from PIL import ImageDraw

    from backend.media import thumbnail_compose as compose

    draw = ImageDraw.Draw(Image.new("RGB", (720, 1280)))
    title = "SUPERCALIFRAGILISTICEXPIALIDOCIOUS" * 2
    support = "Bargaining made easy with a very long supporting message for a small vertical cover"
    short_title = compose._shorten_to_fit(title, lambda value: compose._portrait_headline_fits(draw, value))
    short_support = compose._shorten_to_fit(support, lambda value: compose._portrait_support_fits(draw, value))
    assert short_title.endswith("…") and compose._portrait_headline_fits(draw, short_title)
    assert short_support.endswith("…") and compose._portrait_support_fits(draw, short_support)


def test_the_outside_prompt_keeps_the_title_side_free_and_the_faces_big():
    """Walkthrough 2026-10-14: ChatGPT put the pair in the middle, under the app's left-side title. The people go in the
    right 55 %, heads apart, faces large; the topic is said once, without a double full stop."""
    from backend.media.thumbnail_service import outside_prompt

    topic = "Shopping at the Market. The group navigates the local market."
    composition = {"characters": [
        {"slot": 0, "name": "Hoang", "character_id": "h", "names": ["smile__open"]},
        {"slot": 1, "name": "Kim", "character_id": "k", "names": ["smile__open"]},
    ]}
    prompt = outside_prompt({"topic": topic}, composition, [])["prompt"]
    assert "right 55%" in prompt and "must not overlap" in prompt and "left 45% of the picture is background only" in prompt
    assert "about a third of the picture's height" in prompt and "four corners" in prompt
    assert prompt.count("navigates the local market") == 1 and ".." not in prompt
    assert "Hoang (attached picture 1)" in prompt and "Kim (attached picture 2)" in prompt
    with_actions = outside_prompt({"topic": topic}, composition, ["weighing tomatoes at a stall"])["prompt"]
    assert "a bright, detailed scene of weighing tomatoes at a stall" in with_actions
