"""Phase 43 (D122): framing the "AI scene" thumbnail. Qwen-Image-Edit draws the two characters in a scene wider than the
frame (1536x720); the faces it actually drew decide which 1280x720 window to keep and which side gets the headline, so
the text never lands on a face whatever composition the model chose (the 2026-10-14 trials: the pair right of centre,
heads at ~32-78 % of the width). Pure functions: the face boxes come from the image worker's `count_faces` command."""

from __future__ import annotations

from typing import Sequence

FRAME = (1280, 720)
DRAW_SIZE = (1536, 720)  # drawn wider than the frame so the window can slide
HEAD_WIDEN = 0.25  # a face box widened by this share of its width on each side ~ the head with the hair
HEAD_RAISE = 0.45  # ... and raised by this share of its height (hair above the forehead)
SAFE_MARGIN = 60  # px of the 1280 frame: heads and text keep this far from the edges
TEXT_GAP = 24  # px between the headline box and the nearest head
MIN_TEXT_SHARE = 0.33  # below this the variant is "crowded": the UI offers "Draw again"
BADGE_ZONE = (0.80, 0.85)  # YouTube's duration stamp: the bottom-right corner from these shares of width and height


def head_zones(faces: Sequence[Sequence[float]]) -> list[tuple[float, float, float, float]]:
    """Each face `[x1, y1, x2, y2, (score)]` widened to its head (hair included): the area text must keep off."""
    zones = []
    for face in faces:
        x1, y1, x2, y2 = (float(value) for value in face[:4])
        width, height = x2 - x1, y2 - y1
        zones.append((x1 - width * HEAD_WIDEN, y1 - height * HEAD_RAISE, x2 + width * HEAD_WIDEN, y2))
    return zones


def choose_frame(faces: Sequence[Sequence[float]], picture_size: tuple[int, int] = DRAW_SIZE,
                 frame: tuple[int, int] = FRAME) -> dict:
    """The window to crop and where the headline goes.

    Returns {"left", "top", "side" ("left"|"right"), "free_share", "text_box" (x, y, width, height, align) as shares of
    the frame, "crowded", "faces"}. The headline side is the one with the widest free strip beside the heads; the text
    box fills that strip (minus margins), so a model that drew the pair near the middle still gets a clean title area.
    """
    picture_width, picture_height = picture_size
    frame_width, frame_height = frame
    top = max(0, (picture_height - frame_height) // 2)
    slide = max(0, picture_width - frame_width)
    zones = head_zones(faces)
    if not zones:
        return {"left": slide // 2, "top": top, "side": "left", "free_share": 0.0, "crowded": True, "faces": 0,
                "text_box": _text_box("left", 0.45 * frame_width, frame)}
    heads_left = min(zone[0] for zone in zones)
    heads_right = max(zone[2] for zone in zones)

    # text on the left: slide the window as far left as the heads allow (keeping them inside with the margin)
    left_x = int(min(slide, max(0, heads_right + SAFE_MARGIN - frame_width)))
    left_free = heads_left - left_x
    # text on the right: slide as far right as the heads allow
    right_x = int(max(0, min(slide, heads_left - SAFE_MARGIN)))
    right_free = right_x + frame_width - heads_right
    if right_free > left_free:
        side, window_left, free = "right", right_x, right_free
    else:
        side, window_left, free = "left", left_x, left_free
    free_share = max(0.0, free / frame_width)
    in_badge = any(zone[2] - window_left > frame_width * BADGE_ZONE[0] and zone[3] - top > frame_height * BADGE_ZONE[1]
                   for zone in zones)
    return {"left": window_left, "top": top, "side": side, "free_share": round(free_share, 3),
            "crowded": free_share < MIN_TEXT_SHARE or in_badge, "faces": len(zones),
            "text_box": _text_box(side, free, frame)}


def _text_box(side: str, free_px: float, frame: tuple[int, int]) -> tuple[float, float, float, float, str]:
    frame_width, _ = frame
    width = max(0.0, free_px - SAFE_MARGIN - TEXT_GAP)
    x = SAFE_MARGIN if side == "left" else frame_width - SAFE_MARGIN - width
    return (round(x / frame_width, 4), 0.21, round(width / frame_width, 4), 0.50, side)
