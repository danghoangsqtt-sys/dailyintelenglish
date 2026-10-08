"""Phase 32: bringing a full-figure picture from the web into the sprite canvas (scripts/sprite_web_import.py), on synthetic pictures."""

import importlib.util
from pathlib import Path

import numpy as np
import pytest
from PIL import Image, ImageDraw

SCRIPT = Path(__file__).resolve().parent.parent / "scripts" / "sprite_web_import.py"
GREEN = (0, 177, 64)


@pytest.fixture(scope="module")
def web():
    spec = importlib.util.spec_from_file_location("sprite_web_import", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _figure(draw: ImageDraw.ImageDraw, ox: float, oy: float, s: float) -> None:
    def box(x0, y0, x1, y1):
        return (ox + x0 * s, oy + y0 * s, ox + x1 * s, oy + y1 * s)
    draw.ellipse(box(420, 230, 820, 640), fill=(120, 80, 60))  # hair
    draw.ellipse(box(500, 330, 740, 600), fill=(240, 200, 180))  # face
    draw.rectangle(box(380, 640, 900, 1535), fill=(250, 245, 240))  # white dress down to the bottom


def _base() -> Image.Image:
    image = Image.new("RGBA", (1280, 1536), (0, 0, 0, 0))
    _figure(ImageDraw.Draw(image), 0, 0, 1.0)
    return image


def test_the_green_background_becomes_transparent_and_a_white_dress_stays(web):
    picture = Image.new("RGB", (400, 400), GREEN)
    draw = ImageDraw.Draw(picture)
    draw.rectangle((100, 100, 300, 399), fill=(250, 245, 240))
    keyed = np.asarray(web.key_out_green(picture))
    assert keyed[10, 10, 3] == 0
    assert keyed[200, 200, 3] == 255 and tuple(keyed[200, 200, :3]) == (250, 245, 240)


def test_a_background_that_is_not_green_is_refused(web):
    with pytest.raises(ValueError, match="not green"):
        web.key_out_green(Image.new("RGB", (50, 50), (255, 255, 255)))


def test_a_smaller_shifted_figure_is_put_back_on_the_base_position(web):
    base = _base()
    # the web picture: the same figure 8% smaller, on a different canvas, shifted by some pixels
    raw = Image.new("RGB", (1024, 1536), GREEN)
    _figure(ImageDraw.Draw(raw), -70, 24, 0.92)
    figure = web.key_out_green(raw)
    base_alpha = np.asarray(base.getchannel("A"))
    # the starting guess is off by a few pixels, as a face detector's would be
    scale, dx, dy, overlap = web.refine(np.asarray(figure.getchannel("A")), base_alpha, 1 / 0.92 * 1.01, 70 / 0.92 + 9, -24 / 0.92 - 7)
    placed = np.asarray(web.place(figure, scale, dx, dy).getchannel("A")) > 20
    top, end = web.head_zone(base_alpha)
    reference = base_alpha[top:end] > 20
    union = (placed[top:end] | reference).sum()
    assert overlap > 0.93
    assert (placed[top:end] & reference).sum() / union > 0.93
