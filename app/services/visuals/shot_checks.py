"""Task 20.11: detect an extra person between the two people of a duo shot (pure, no GPU).

The worker's anime-seg cut-out gives a foreground alpha. The band between the two faces
(from 0.8 head-heights right of the left nose to 0.8 left of the right nose, one head-height
above and below the noses) is background in a normal duo; a third person fills it.
Calibrated on the 20.11 spike renders: third person 0.558-0.585, normal duos <= 0.464.
"""

from __future__ import annotations

from typing import Any

import numpy as np
from PIL import Image

from app.services.visuals.geometry import _KEYS

EXTRA_PERSON_THRESHOLD = 0.5


def head_gap_box(people: list[dict[str, Any]], size: tuple[int, int]) -> tuple[int, int, int, int] | None:
    if len(people) != 2:
        return None
    left, right = (dict(zip(_KEYS, person["points"], strict=True))["nose"] for person in people)
    unit = people[0]["head_h"] * size[1]
    x0, x1 = round(left[0] + 0.8 * unit), round(right[0] - 0.8 * unit)
    y0, y1 = round(max(0.0, left[1] - unit)), round(min(float(size[1]), left[1] + unit))
    return (x0, y0, x1, y1) if x1 - x0 >= 8 and y1 - y0 >= 8 else None


def gap_occupancy(cutout: Image.Image, box: tuple[int, int, int, int]) -> float:
    """Share of the band that anime-seg marks as foreground (alpha > 0.5)."""
    alpha = np.asarray(cutout.getchannel("A").crop(box), dtype=np.float32) / 255.0
    return round(float((alpha > 0.5).mean()), 3)
