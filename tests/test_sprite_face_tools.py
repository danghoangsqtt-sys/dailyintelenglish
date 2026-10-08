"""Phase 32: putting an edited face back into a base sprite (scripts/sprite_face_tools.py), on synthetic pictures."""

import importlib.util
from pathlib import Path

import numpy as np
import pytest
from PIL import Image, ImageDraw

SCRIPT = Path(__file__).resolve().parent.parent / "scripts" / "sprite_face_tools.py"


@pytest.fixture(scope="module")
def tools():
    spec = importlib.util.spec_from_file_location("sprite_face_tools", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _base() -> Image.Image:
    image = Image.new("RGBA", (1280, 1536), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)
    draw.ellipse((420, 230, 820, 640), fill=(120, 80, 60, 255))  # the hair
    draw.ellipse((500, 330, 740, 600), fill=(240, 200, 180, 255))  # the face
    draw.rectangle((380, 640, 900, 1535), fill=(250, 245, 240, 255))  # the body to the bottom edge
    return image


def test_the_crop_box_holds_the_head_and_neck_but_not_the_clothes(tools):
    x0, y0, x1, y1 = tools.crop_box(np.asarray(_base().getchannel("A")))
    assert y0 < 230 and y1 < 700 and x0 < 420 and x1 > 820  # above the hair, down to the shoulders only, as wide as the hair


def test_pasting_a_face_changes_only_the_ellipse_and_keeps_the_transparency(tools):
    base = _base()
    box = (396, 206, 844, 662)
    crop = tools.flatten(base, box)
    edited = crop.copy()
    ImageDraw.Draw(edited).rectangle((190, 314, 250, 344), fill=(200, 30, 40))  # a new mouth (crop coordinates)
    ellipse = (crop.width / 2, crop.height * 0.6, 130.0, 150.0)
    result = tools.paste_face(base, edited, box, ellipse)
    before, after = np.asarray(base), np.asarray(result)
    assert (before[..., 3] == after[..., 3]).all()  # the silhouette is the base's
    changed = (np.abs(before[..., :3].astype(int) - after[..., :3].astype(int)).max(axis=2) > 0) & (before[..., 3] > 0)
    ys, xs = np.where(changed)
    assert changed.any() and xs.min() >= box[0] and xs.max() < box[2] and ys.min() >= box[1] and ys.max() < box[3]
    assert after[535, 620, 0] > 150 and after[535, 620, 1] < 100  # the new mouth is in
    assert (before[1000:1500] == after[1000:1500]).all()  # the body is untouched


def test_compose_makes_a_picture_for_every_edited_head_and_reports_the_missing_ones(tools, tmp_path, monkeypatch, capsys):
    inbox, heads = tmp_path / "inbox", tmp_path / "heads"
    (heads / "edited").mkdir(parents=True)
    inbox.mkdir()
    base = _base()
    base.save(inbox / "lina__calm__closed.png")
    box = (396, 206, 844, 662)
    meta = {"crop_box": box, "ellipse": (224.0, 270.0, 130.0, 150.0)}
    (heads / "lina_head_meta.json").write_text(__import__("json").dumps(meta), encoding="utf-8")
    tools.flatten(base, box).save(heads / "edited" / "lina__smile__open.png")
    monkeypatch.setattr(tools, "INBOX", inbox)
    monkeypatch.setattr(tools, "HEADS", heads)
    assert tools.compose("lina") == 0
    out = capsys.readouterr().out
    assert (inbox / "lina__smile__open.png").is_file() and "composed 1: smile__open" in out and "still missing 13" in out
