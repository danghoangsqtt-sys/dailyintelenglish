"""Phase 32 (Task 32.1): talking-sprite sets imported from the inbox, checked against the calm picture, listed and served."""

from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw

from app.services.visuals import sprite_service as sprites
from tests.test_shot_library_import import _two_characters
from tests.test_visuals_project_api import client, data, locked_character  # noqa: F401


def _figure(path: Path, head_dx: int = 0, torso_dx: int = 0, size=(1280, 1536), opaque: bool = False,
            body=(20, 30, 100, 255)) -> None:
    image = Image.new("RGBA", size, (90, 90, 90, 255) if opaque else (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)
    draw.ellipse((500 + head_dx, 200, 780 + head_dx, 520), fill=(200, 160, 140, 255))  # the head
    draw.rectangle((380 + torso_dx, 520, 900 + torso_dx, 1535), fill=body)  # the body to the bottom edge
    path.parent.mkdir(parents=True, exist_ok=True)
    image.save(path)


def _no_face_model(_path: Path) -> None:
    return None


def test_file_names_name_the_character_and_the_picture():
    assert sprites.parse_name("Alex__smile__open.png") == ("alex", "smile__open")
    assert sprites.parse_name("lina__gesture-wave.png") == ("lina", "gesture-wave")
    assert sprites.parse_name("lina__blink.png") == ("lina", "blink")
    for bad in ("lina__grin__open.png", "lina.png", "lina__smile__open.jpg", "__calm__closed.png"):
        assert sprites.parse_name(bad) is None


def test_the_check_refuses_pictures_that_would_jump(tmp_path):
    _figure(tmp_path / "calm__closed.png")
    _figure(tmp_path / "smile__open.png")
    _figure(tmp_path / "laugh__open.png", torso_dx=40)  # the body slid
    _figure(tmp_path / "gesture-wave.png", torso_dx=12)  # a gesture may move the arms a little, not the head
    _figure(tmp_path / "gesture-talk.png", body=(150, 40, 40, 255))  # but not draw the whole body again
    _figure(tmp_path / "blink.png", head_dx=60)  # the head moved
    _figure(tmp_path / "serious__open.png", size=(1000, 1000))
    files = {path.stem: path for path in tmp_path.glob("*.png")}
    accepted, refused = sprites.check_folder(files)
    assert set(accepted) == {"calm__closed", "smile__open", "gesture-wave"}
    reasons = {item["file"]: item["reason"] for item in refused}
    assert "torso moved" in reasons["laugh__open.png"]
    assert "head moved sideways" in reasons["blink.png"]
    assert "wrong canvas size" in reasons["serious__open.png"]
    assert "drawn again" in reasons["gesture-talk.png"]


def test_a_hand_cut_by_the_canvas_edge_is_refused(tmp_path):
    _figure(tmp_path / "calm__closed.png")
    _figure(tmp_path / "gesture-point.png")
    with Image.open(tmp_path / "gesture-point.png") as opened:
        picture = opened.copy()
    ImageDraw.Draw(picture).rectangle((900, 700, 1279, 760), fill=(220, 180, 160, 255))  # the arm runs off the right edge
    picture.save(tmp_path / "gesture-point.png")
    accepted, refused = sprites.check_folder({path.stem: path for path in tmp_path.glob("*.png")})
    assert "gesture-point" not in accepted
    assert "cut by the right edge" in refused[0]["reason"]


def test_an_opaque_base_refuses_the_whole_set(tmp_path):
    _figure(tmp_path / "calm__closed.png", opaque=True)
    _figure(tmp_path / "calm__open.png")
    accepted, refused = sprites.check_folder({path.stem: path for path in tmp_path.glob("*.png")})
    assert accepted == {}
    assert "transparent" in refused[0]["reason"] and "not checked" in refused[1]["reason"]


def test_the_geometric_face_ellipse_sits_in_the_head():
    image = Image.new("RGBA", (1280, 1536), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)
    draw.ellipse((500, 200, 780, 520), fill=(200, 160, 140, 255))
    draw.rectangle((380, 520, 900, 1535), fill=(20, 30, 100, 255))
    import numpy as np

    cx, cy, rx, ry = sprites.geometric_face_ellipse(np.asarray(image)[..., 3])
    assert abs(cx * 1280 - 640) < 5
    assert 200 < cy * 1536 < 520 and 0 < rx < 0.2 and 0 < ry < 0.2


async def test_the_inbox_becomes_one_set_per_character(client):  # noqa: F811
    lina, alex = _two_characters()
    inbox = sprites.inbox_dir()
    for name in ("calm__closed", "calm__open", "smile__open", "gesture-wave"):
        _figure(inbox / f"Lina__{name}.png")
    _figure(inbox / "lina__laugh__open.png", torso_dx=40)
    _figure(inbox / "alex__smile__open.png")  # no base for Alex
    _figure(inbox / "minh__calm__closed.png")  # no such character
    _figure(inbox / "notes.png")
    characters = {"lina": {"id": lina, "name": "Lina"}, "alex": {"id": alex, "name": "Alex"}}
    result = await sprites.import_inbox(characters, face=_no_face_model)
    assert [(item["name"], item["pictures"], item["face_from"]) for item in result["imported"]] == [("Lina", 4, "silhouette")]
    reasons = {item["file"]: item["reason"] for item in result["refused"]}
    assert "torso moved" in reasons["lina__laugh__open.png"]
    assert "missing" in reasons["alex__calm__closed.png"]
    assert "no library character" in reasons["minh__calm__closed.png"]
    assert result["ignored"] == ["notes.png"]
    sprite_set = sprites.load_set(lina)
    assert sprites.usable(sprite_set) and set(sprite_set["names"]) == {"calm__closed", "calm__open", "smile__open", "gesture-wave"}
    assert len(sprite_set["face_ellipse"]) == 4 and (inbox / "Lina__calm__open.png").is_file()  # the inbox keeps its files


def test_the_api_lists_imports_and_serves_the_sets(client, monkeypatch):  # noqa: F811
    lina, alex = _two_characters()
    monkeypatch.setattr(sprites, "detected_face_ellipse", _no_face_model)
    for name in ("calm__closed", "calm__open"):
        _figure(sprites.inbox_dir() / f"alex__{name}.png")
    listing = data(client.get("/api/visuals/library/sprites"))
    assert listing["inbox"] == ["alex__calm__closed.png", "alex__calm__open.png"]
    assert all(not item["has_set"] for item in listing["sets"])
    result = data(client.post("/api/visuals/library/sprites/import"))
    assert [item["name"] for item in result["imported"]] == ["Alex"]
    sets = {item["name"]: item for item in data(client.get("/api/visuals/library/sprites"))["sets"]}
    assert sets["Alex"]["usable"] and sets["Alex"]["faces"] == 2 and sets["Alex"]["gestures"] == 0
    assert not sets["Lina"]["has_set"] and "calm__closed" in sets["Lina"]["missing"]
    response = client.get(f"/api/visuals/library/sprites/{alex}/calm__open/content")
    assert response.status_code == 200 and response.headers["content-type"] == "image/png"
    assert client.get(f"/api/visuals/library/sprites/{alex}/grin/content").status_code == 404
    assert client.get(f"/api/visuals/library/sprites/{lina}/calm__open/content").status_code == 404
    # deleting the character deletes its set
    assert client.delete(f"/api/visuals/characters/{alex}?force=true").status_code in (200, 204)
    assert sprites.load_set(alex) is None
