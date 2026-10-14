"""Walkthrough 2026-10-14: the two thumbnail characters never overlap each other, the headline or the channel logo."""

import pytest

from backend.media import thumbnail_compose as tc


def _overlap(a, b) -> bool:
    return a[0] < b[0] + b[2] and b[0] < a[0] + a[2] and a[1] < b[1] + b[3] and b[1] < a[1] + a[3]


CASES = [("16x9", layout) for layout in tc.LAYOUTS_16X9] + [("9x16", tc.LAYOUT_9X16)]


@pytest.mark.parametrize("aspect,layout", CASES)
@pytest.mark.parametrize("figure", [(629, 648), (603, 648), (900, 600), (300, 700)])  # near-square busts, wide, narrow
def test_two_characters_have_their_own_room(aspect, layout, figure):
    size = tc.SIZES[aspect]
    width, height = size
    boxes = [tc.place_figure(figure, tc.character_slot(layout, slot, 2), size, layout["height"]) for slot in (0, 1)]
    assert not _overlap(boxes[0], boxes[1])
    x, y, w, h, _ = layout["text"]
    text = (round(x * width), round(y * height), round(w * width), round(h * height))
    logo_side = round(min(size) * tc.LOGO_SHARE)
    margin = round(min(size) * tc.MARGIN_SHARE)
    logo = (width - logo_side - margin, margin, logo_side, logo_side)
    for box in boxes:
        assert box[0] >= 0 and box[0] + box[2] <= width and box[1] + box[3] == height
        assert not _overlap(box, text) and not _overlap(box, logo)
        assert box[3] >= min(size) * 0.25  # still big enough to read the faces


def test_a_lone_character_uses_both_slots():
    layout = tc.LAYOUTS_16X9[0]
    assert tc.character_slot(layout, 0, 1) == (layout["slots"][0][0], layout["slots"][1][1])
