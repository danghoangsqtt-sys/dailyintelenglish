"""Task 20.11: measure a person's garment colours on a finished shot (pure, no GPU).

The shot geometry is known (the OpenPose skeleton drew the person), so the top is sampled
from a strip inside the torso (between the shoulders and the hips, away from the arms and
the hair) and the bottom from the thighs when the knees are in frame. Ink outlines and deep
shadow are dropped, then the median HSV is classified against the locked colour name.
"""

from __future__ import annotations

import colorsys
from typing import Any

import numpy as np
from PIL import Image

from app.services.visuals.geometry import _KEYS

MIN_PIXELS = 400


def _points(person: dict[str, Any]) -> dict[str, tuple[float, float] | None]:
    return dict(zip(_KEYS, person["points"], strict=True))


def top_box(person: dict[str, Any], size: tuple[int, int]) -> tuple[int, int, int, int] | None:
    p = _points(person)
    shoulders = [p["r_shoulder"], p["l_shoulder"]]
    hips = [p["r_hip"], p["l_hip"]]
    if None in shoulders or None in hips:
        return None
    x0, x1 = sorted(point[0] for point in shoulders)
    top = sum(point[1] for point in shoulders) / 2
    bottom = min(sum(point[1] for point in hips) / 2, size[1])
    inset = 0.28 * (x1 - x0)
    box = (x0 + inset, top + 0.2 * (bottom - top), x1 - inset, top + 0.6 * (bottom - top))
    return _clip(box, size)


def bottom_box(person: dict[str, Any], size: tuple[int, int]) -> tuple[int, int, int, int] | None:
    p = _points(person)
    hips, knees = [p["r_hip"], p["l_hip"]], [p["r_knee"], p["l_knee"]]
    if None in hips or None in knees:
        return None
    hip_y = sum(point[1] for point in hips) / 2
    knee_y = sum(point[1] for point in knees) / 2
    if knee_y > size[1]:
        return None
    x0, x1 = sorted(point[0] for point in hips)
    box = (x0 - 0.1 * (x1 - x0), hip_y + 0.3 * (knee_y - hip_y), x1 + 0.1 * (x1 - x0), knee_y)
    return _clip(box, size)


def _clip(box: tuple[float, ...], size: tuple[int, int]) -> tuple[int, int, int, int] | None:
    x0, y0, x1, y1 = (round(value) for value in box)
    x0, y0, x1, y1 = max(0, x0), max(0, y0), min(size[0], x1), min(size[1], y1)
    return (x0, y0, x1, y1) if x1 - x0 >= 8 and y1 - y0 >= 8 else None


def measure(image: Image.Image, box: tuple[int, int, int, int],
            include_dark: bool = False) -> dict[str, float] | None:
    """Median hue (degrees), saturation and value (0..1) of the region, outlines excluded.

    Pixels darker than v 0.22 are cel outlines and are dropped. For a **black** garment those pixels are the
    garment itself (a photograph has no outlines), so `include_dark` keeps them (Phase 28 calibration)."""
    hsv = np.asarray(image.convert("RGB").crop(box).convert("HSV"), dtype=np.float32).reshape(-1, 3) / 255.0
    kept = hsv if include_dark else hsv[hsv[:, 2] > 0.22]
    if len(kept) < MIN_PIXELS:
        return None
    s, v = float(np.median(kept[:, 1])), float(np.median(kept[:, 2]))
    # Circular median of the hue is approximated by the dominant 10-degree bin's mean.
    hues = kept[kept[:, 1] > 0.12, 0] * 360.0
    if len(hues) >= MIN_PIXELS // 4:
        bins = np.floor(hues / 10.0).astype(int) % 36
        dominant = np.bincount(bins, minlength=36).argmax()
        h = float(np.mean(hues[bins == dominant]))
    else:
        h = float(np.median(kept[:, 0]) * 360.0)
    return {"h": round(h, 1), "s": round(s, 3), "v": round(v, 3)}


def _hue_in(h: float, low: float, high: float) -> bool:
    return low <= h <= high if low <= high else (h >= low or h <= high)


def matches(colour: str, hsv: dict[str, float]) -> bool:
    """Whether a measured median HSV is plausibly the locked colour name (models.COLORS)."""
    h, s, v = hsv["h"], hsv["s"], hsv["v"]
    rules = {
        "white": s < 0.2 and v > 0.72,
        # Phase 28 (measured on the real shot job, Task 28.4b/28.5): a photographed black shirt reads value <= 0.16 even
        # with a blue cast from shadow (saturation up to 0.37); a dark NAVY shirt reads value >= 0.18 with saturation
        # 0.32-0.42, which the old `v < 0.35` accepted as black (7 of 7 duo shots). A lit, low-saturation dark (a charcoal
        # or a studio black) still passes.
        "black": v < 0.16 or (s < 0.25 and v < 0.42),
        "grey": s < 0.18 and 0.3 <= v <= 0.85,
        "navy blue": _hue_in(h, 185, 255) and v < 0.72 and s > 0.2,
        # Cel-shaded light blue reads as a pale cyan: hue 85-185, saturation 0.09-0.2 (calibrated
        # on the 20.11 spike sheets), so the band is wide in hue and narrow in saturation.
        "light blue": _hue_in(h, 80, 245) and 0.06 <= s < 0.65 and v > 0.5,
        "red": _hue_in(h, 340, 15) and s > 0.45 and v > 0.3,
        "pink": _hue_in(h, 290, 20) and s < 0.6 and v > 0.55,
        "yellow": _hue_in(h, 30, 68) and s > 0.3 and v > 0.5,
        "orange": _hue_in(h, 14, 40) and s > 0.5 and v > 0.5,
        "green": _hue_in(h, 70, 170) and s > 0.18,
        "beige": _hue_in(h, 18, 58) and s < 0.45 and v > 0.55,
        "brown": _hue_in(h, 5, 45) and s > 0.25 and v < 0.62,
    }
    return bool(rules.get(colour, True))


def check_person(image: Image.Image, person: dict[str, Any], character: dict[str, Any],
                 check_bottom: bool = True) -> dict[str, Any]:
    """{'top': {...}, 'bottom': {...}|None, 'ok': bool}; an unmeasurable region never fails."""
    result: dict[str, Any] = {"ok": True}
    parts = [("top", top_box, character["top_color"])]
    # A dress is one garment: the thighs below it are skin, not the bottom colour (Phase 31).
    if check_bottom and character["top_item"] != character["bottom_item"]:
        parts.append(("bottom", bottom_box, character["bottom_color"]))
    for name, box_of, colour in parts:
        box = box_of(person, image.size)
        hsv = measure(image, box, include_dark=colour == "black") if box else None
        passed = True if hsv is None else matches(colour, hsv)
        result[name] = {"expected": colour, "measured": hsv, "box": box, "ok": passed}
        result["ok"] = result["ok"] and passed
    return result


def describe(hsv: dict[str, float] | None) -> str:
    if hsv is None:
        return "n/a"
    r, g, b = colorsys.hsv_to_rgb(hsv["h"] / 360.0, hsv["s"], hsv["v"])
    return f"#{round(r * 255):02x}{round(g * 255):02x}{round(b * 255):02x}"
