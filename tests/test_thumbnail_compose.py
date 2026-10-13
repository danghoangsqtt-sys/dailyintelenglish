"""Task 36.3/36.4 (D90-D92): the composed episode thumbnail and the outside-AI picture, through the real API."""

from __future__ import annotations

import hashlib
import io
import json
import sqlite3
from pathlib import Path

import pytest
from PIL import Image

from app.core.config import settings
from app.models.thumbnail import ThumbnailSuggestionPack
from app.services import thumbnail_service
from app.services.visuals import sprite_service
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
