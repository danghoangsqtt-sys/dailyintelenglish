"""Task 20.7 AI scene thumbnail discovery, crops and fallback."""

import io
import sqlite3
import uuid

from PIL import Image, ImageDraw

from app.core.config import settings
from tests.test_thumbnail_api import client, create_project  # noqa: F401


def add_complete_shot(project_id: str) -> str:
    shot_id = str(uuid.uuid4())
    source = settings.DATA_DIR / "visuals" / project_id / "shots" / shot_id / "final.png"
    source.parent.mkdir(parents=True, exist_ok=True)
    image = Image.new("RGB", (1344, 768), "blue")
    ImageDraw.Draw(image).rectangle((0, 0, 670, 767), fill="red")
    image.save(source)
    with sqlite3.connect(settings.db_path) as connection:
        connection.execute(
            "INSERT INTO project_shots (id, project_id, scene_id, kind, speaker_indexes, seed, final_path, "
            "status, created_at, updated_at) VALUES (?, ?, 'scene', 'duo_close', '[0,1]', 1, ?, "
            "'complete', 'now', 'now')",
            (shot_id, project_id, str(source)),
        )
    return shot_id


def test_ai_scene_template_requires_shot_renders_both_aspects_and_falls_back(client):  # noqa: F811
    project = create_project(client)
    endpoint = f"/api/thumbnails/templates?project_id={project['id']}"
    assert len(client.get(endpoint).json()["data"]) == 5
    shot_id = add_complete_shot(project["id"])
    templates = client.get(endpoint).json()["data"]
    assert len(templates) == 6
    assert templates[-1]["id"] == "ai_scene"
    assert shot_id in templates[-1]["preview_url"]
    generated = client.post(
        f"/api/projects/{project['id']}/thumbnails/generate",
        json={"template_name": "ai_scene", "variant_count": 3},
    )
    assert generated.status_code == 200, generated.text
    variants = generated.json()["data"]
    assert len(variants) == 3
    for aspect, size in (("16x9", (1280, 720)), ("9x16", (720, 1280))):
        response = client.get(variants[0]["assets"][aspect]["png"])
        assert response.status_code == 200
        with Image.open(io.BytesIO(response.content)) as rendered:
            assert rendered.size == size
            if aspect == "9x16":
                assert rendered.getpixel((size[0] // 2, size[1] // 2))[0] > 100
    edit = client.patch(
        f"/api/projects/{project['id']}/thumbnails/{variants[0]['id']}",
        json={"revision": variants[0]["revision"], "headline": "New lesson",
              "palette": variants[0]["suggestion"]["palette"]},
    )
    assert edit.status_code == 200, edit.text
    source = settings.DATA_DIR / "visuals" / project["id"] / "shots" / shot_id / "final.png"
    source.unlink()
    assert len(client.get(endpoint).json()["data"]) == 5
    unavailable = client.post(
        f"/api/projects/{project['id']}/thumbnails/generate",
        json={"template_name": "ai_scene", "variant_count": 3},
    )
    assert unavailable.status_code != 200
