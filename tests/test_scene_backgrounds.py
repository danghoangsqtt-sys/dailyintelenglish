"""Phase 31: the owner's own scene backgrounds (assets_background/assets/<key>.png + prompts/<key>.txt) become scene plates."""

from __future__ import annotations

from PIL import Image

from app.core.config import settings
from app.services.visuals import shot_library_service as lib
from tests.test_visuals_project_api import client, data  # noqa: F401


def _folder():
    folder = lib.backgrounds_dir()
    (folder / "assets").mkdir(parents=True, exist_ok=True)
    (folder / "prompts").mkdir(parents=True, exist_ok=True)
    return folder


def test_backgrounds_named_by_scene_key_become_the_scene_plates_with_their_prompts(client):  # noqa: F811
    folder = _folder()
    Image.new("RGB", (1536, 864), (10, 120, 200)).save(folder / "assets" / "cafe.png")
    Image.new("RGB", (1448, 1086), (30, 140, 30)).save(folder / "assets" / "Park.jpg")  # 4:3: cropped to 16:9
    Image.new("RGB", (1536, 864), (9, 9, 9)).save(folder / "assets" / "nowhere.png")
    (folder / "assets" / "notes.txt").write_text("not a picture")
    (folder / "prompts" / "cafe.txt").write_text("a quiet cafe, two chairs", encoding="utf-8-sig")
    assert data(client.get("/api/visuals/library/backgrounds"))["images"] == 3

    result = data(client.post("/api/visuals/library/backgrounds/import"))
    assert sorted(item["scene_id"] for item in result["imported"]) == ["builtin-cafe", "builtin-park"]
    assert [item["cropped"] for item in result["imported"] if item["scene_id"] == "builtin-park"] == [True]
    assert [item["file"] for item in result["skipped"]] == ["nowhere.png"] and "unknown scene" in result["skipped"][0]["reason"]

    scenes = {scene["id"]: scene for scene in data(client.get("/api/visuals/scenes"))}
    assert scenes["builtin-cafe"]["preview_url"] and scenes["builtin-park"]["preview_url"]
    plate = settings.DATA_DIR / "library" / "scenes" / "builtin-cafe" / "preview.png"
    assert Image.open(plate).getpixel((5, 5)) == (10, 120, 200)
    park = Image.open(settings.DATA_DIR / "library" / "scenes" / "builtin-park" / "preview.png")
    assert abs(park.width / park.height - 16 / 9) < 0.01
    assert (plate.parent / "prompt.txt").read_text(encoding="utf-8") == "a quiet cafe, two chairs"  # the BOM is dropped
    assert client.get(scenes["builtin-cafe"]["preview_url"]).headers["content-type"] == "image/png"


def test_importing_again_changes_nothing_and_a_new_picture_replaces_the_plate(client):  # noqa: F811
    folder = _folder()
    Image.new("RGB", (1536, 864), (1, 2, 3)).save(folder / "assets" / "cafe.png")
    assert len(data(client.post("/api/visuals/library/backgrounds/import"))["imported"]) == 1
    again = data(client.post("/api/visuals/library/backgrounds/import"))
    assert again["imported"] == [] and again["unchanged"] == ["cafe.png"]
    Image.new("RGB", (1536, 864), (200, 100, 50)).save(folder / "assets" / "cafe.png")
    assert len(data(client.post("/api/visuals/library/backgrounds/import"))["imported"]) == 1
    plate = settings.DATA_DIR / "library" / "scenes" / "builtin-cafe" / "preview.png"
    assert Image.open(plate).getpixel((5, 5)) == (200, 100, 50)


def test_an_empty_or_missing_folder_is_not_an_error(client):  # noqa: F811
    assert data(client.get("/api/visuals/library/backgrounds"))["images"] == 0
    result = data(client.post("/api/visuals/library/backgrounds/import"))
    assert result == {"imported": [], "unchanged": [], "skipped": []}
