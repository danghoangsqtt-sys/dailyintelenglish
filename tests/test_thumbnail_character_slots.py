"""Walkthrough 2026-10-14 (owner review + YouTube thumbnail guides): the thumbnail characters are big, their heads never
touch or get covered, and they stay clear of the headline, the logo row and the bottom-right duration badge."""

import pytest
from PIL import Image, ImageDraw

from backend.media import thumbnail_compose as tc


def _bust(height: int, width_ratio: float = 0.95) -> Image.Image:
    """A head-to-chest stand-in: a round head on top of wide shoulders (like the real sprite crops)."""
    width = round(height * width_ratio)
    image = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)
    head = round(height * 0.36)
    draw.ellipse((width // 2 - head // 2, 0, width // 2 + head // 2, head), fill=(200, 160, 140, 255))
    draw.rectangle((0, round(height * 0.42), width, height), fill=(40, 60, 160, 255))
    return image


def _box(figure, at):
    return at[0], at[1], at[0] + figure.width, at[1] + figure.height


def _head(figure, at):
    left, top, right, bottom = tc.head_box(figure)
    return at[0] + left, at[1] + top, at[0] + right, at[1] + bottom


def _overlap(a, b) -> bool:
    return a[0] < b[2] and b[0] < a[2] and a[1] < b[3] and b[1] < a[3]


CASES = [("16x9", layout) for layout in tc.LAYOUTS_16X9] + [("9x16", tc.LAYOUT_9X16)]


@pytest.mark.parametrize("aspect,layout", CASES)
@pytest.mark.parametrize("ratio", [0.93, 0.97, 1.2])
def test_two_big_characters_with_their_heads_apart(aspect, layout, ratio):
    size = tc.SIZES[aspect]
    width, height = size
    placed = tc.arrange_figures(lambda h: [_bust(h, ratio), _bust(h, ratio)], layout, size)
    assert len(placed) == 2
    heads = [_head(figure, at) for figure, at in placed]
    assert not _overlap(heads[0], heads[1])
    assert abs(min(h[2] for h in heads) - max(h[0] for h in heads)) >= width * tc.HEAD_GAP - 1 or \
        heads[0][2] <= heads[1][0] or heads[1][2] <= heads[0][0]
    # the front figure does not cover the head behind it
    (back, back_at), (front, front_at) = placed
    assert not tc._covers(front, front_at, _head(back, back_at))
    x, y, w, h, _ = layout["text"]
    text = (round(x * width), round(y * height), round((x + w) * width), round((y + h) * height))
    margin = round(width * tc.SAFE_MARGIN)
    badge = (round(width * 0.80), round(height * 0.85), width, height)  # the duration badge corner
    for figure, at in placed:
        head = _head(figure, at)
        assert head[0] >= margin - 1 and head[2] <= width - margin + 1
        assert at[1] >= round(min(size) * (tc.MARGIN_SHARE + tc.LOGO_SHARE + 0.02)) - 1  # below the logo row
        assert at[1] + figure.height == height
        assert not _overlap(head, badge)
        if layout["group"] != "bottom":
            assert not _overlap(_box(figure, at), text)
    tallest = max(figure.height for figure, _ in placed)
    assert tallest >= min(size) * (0.55 if ratio < 1 else 0.45)  # big: the faces read at 150 px wide


def test_a_lone_character_is_placed_beside_the_headline():
    layout = tc.LAYOUTS_16X9[0]
    placed = tc.arrange_figures(lambda h: [_bust(h)], layout, tc.SIZES["16x9"])
    assert len(placed) == 1 and placed[0][1][0] >= round(0.495 * 1280)
