"""OpenPose and mask geometry ported from the Phase 20 character spikes."""

from typing import Any

from PIL import Image, ImageChops, ImageDraw, ImageFilter

_KEYS = [
    "nose", "neck", "r_shoulder", "r_elbow", "r_wrist", "l_shoulder", "l_elbow", "l_wrist",
    "r_hip", "r_knee", "r_ankle", "l_hip", "l_knee", "l_ankle", "r_eye", "l_eye", "r_ear", "l_ear",
]
_UPPER_BODY = {
    "nose": (0.0, 0.0), "neck": (0.0, 0.62), "r_shoulder": (-0.85, 0.72),
    "l_shoulder": (0.85, 0.72), "r_elbow": (-0.95, 2.05), "r_wrist": (-0.9, 3.1),
    "l_elbow": (0.95, 2.05), "l_wrist": (0.9, 3.1), "r_hip": (-0.55, 3.0),
    "l_hip": (0.55, 3.0), "r_eye": (-0.13, -0.12), "l_eye": (0.13, -0.12),
    "r_ear": (-0.3, -0.05), "l_ear": (0.3, -0.05),
}
_LIMBS = [
    (2, 3), (2, 6), (3, 4), (4, 5), (6, 7), (7, 8), (2, 9), (9, 10), (10, 11),
    (2, 12), (12, 13), (13, 14), (2, 1), (1, 15), (15, 17), (1, 16), (16, 18),
]
_COLORS = [
    (255, 0, 0), (255, 85, 0), (255, 170, 0), (255, 255, 0), (170, 255, 0),
    (85, 255, 0), (0, 255, 0), (0, 255, 85), (0, 255, 170), (0, 255, 255),
    (0, 170, 255), (0, 85, 255), (0, 0, 255), (85, 0, 255), (170, 0, 255),
    (255, 0, 255), (255, 0, 170), (255, 0, 85),
]
_LEGS_STANDING = {
    "r_knee": (-0.5, 4.6), "l_knee": (0.5, 4.6),
    "r_ankle": (-0.5, 6.2), "l_ankle": (0.5, 6.2),
}


def person_pose(
    size: tuple[int, int], cx: float, nose_y: float, head_h: float, facing: str = "front",
    arms: dict[str, tuple[float, float]] | None = None,
    legs: dict[str, tuple[float, float]] | None = None,
) -> list[tuple[float, float] | None]:
    """COCO-18 pixel keypoints, with None for joints that are not drawn."""
    width, height = size
    unit = head_h * height
    local = dict(_UPPER_BODY)
    if facing in ("right", "left"):
        sign = 1 if facing == "right" else -1
        local["nose"] = (0.25 * sign, 0.0)
        local["r_eye"] = (-0.13 + 0.15 * sign, -0.12)
        local["l_eye"] = (0.13 + 0.15 * sign, -0.12)
        local.pop("l_ear" if facing == "right" else "r_ear")
        for key in ("r_shoulder", "l_shoulder", "r_hip", "l_hip"):
            x, y = local[key]
            local[key] = (x * 0.8, y)
    local.update(legs or {})
    local.update(arms or {})
    return [
        None if key not in local else (cx * width + local[key][0] * unit, nose_y * height + local[key][1] * unit)
        for key in _KEYS
    ]


def turn_head(person: dict[str, Any], side: str) -> dict[str, Any]:
    """Task 29.1: the same person with the head keypoints turned toward `side` ("right" / "left"), the body untouched.
    A frontal head makes the ControlNet pose and the face reference agree on a stare into the lens."""
    if side not in ("right", "left"):
        raise ValueError("side must be 'right' or 'left'")
    sign = 1 if side == "right" else -1
    points = dict(zip(_KEYS, person["points"], strict=True))
    neck, nose = points["neck"], points["nose"]
    if neck is None or nose is None:
        return person
    unit = person["head_h"] * 768.0  # `head_h` is a fraction of the frame height (every shot is 768 high)
    cx, ny = neck[0], nose[1]
    points["nose"] = (cx + 0.25 * unit * sign, ny)
    points["r_eye"] = (cx + (-0.13 + 0.15 * sign) * unit, ny - 0.12 * unit)
    points["l_eye"] = (cx + (0.13 + 0.15 * sign) * unit, ny - 0.12 * unit)
    points["l_ear" if side == "right" else "r_ear"] = None
    return {**person, "points": [points[key] for key in _KEYS]}


def shot_people(kind: str, staging: str, size: tuple[int, int] = (1344, 768)) -> list[dict[str, Any]]:
    """Exact r8 single/duo head heights, positions, gestures and legs."""
    if kind == "single":
        return [{"head_h": 0.30, "points": person_pose(
            size, 0.32, 0.36, 0.30, "front", {"r_elbow": (-1.0, 1.9), "r_wrist": (-0.6, 1.35)}
        )}]
    if kind == "duo_close":
        return [
            {"head_h": 0.24, "points": person_pose(
                size, 0.30, 0.38, 0.24, "right", {"l_elbow": (0.9, 1.9), "l_wrist": (1.3, 1.4)}
            )},
            {"head_h": 0.24, "points": person_pose(size, 0.70, 0.38, 0.24, "left")},
        ]
    if staging == "standing":
        return [
            {"head_h": 0.13, "points": person_pose(
                size, 0.33, 0.30, 0.13, "right", {"l_elbow": (1.0, 1.7), "l_wrist": (1.5, 1.4)},
                _LEGS_STANDING,
            )},
            {"head_h": 0.13, "points": person_pose(size, 0.67, 0.30, 0.13, "left", None, _LEGS_STANDING)},
        ]
    return [
        {"head_h": 0.15, "points": person_pose(size, 0.33, 0.32, 0.15, "right", {
            "r_elbow": (-0.9, 2.1), "r_wrist": (0.2, 2.6),
            "l_elbow": (0.9, 2.1), "l_wrist": (1.0, 2.5),
        })},
        {"head_h": 0.15, "points": person_pose(size, 0.67, 0.32, 0.15, "left", {
            "r_elbow": (-0.9, 2.1), "r_wrist": (-1.0, 2.5),
            "l_elbow": (0.9, 2.1), "l_wrist": (-0.2, 2.6),
        })},
    ]


def draw_pose_pixels(points: list[tuple[float, float] | None], size: tuple[int, int]) -> Image.Image:
    stick = max(2, round(4 * size[1] / 512))
    canvas = Image.new("RGB", size, (0, 0, 0))
    draw = ImageDraw.Draw(canvas)
    for index, (a, b) in enumerate(_LIMBS):
        pa, pb = points[a - 1], points[b - 1]
        if pa is not None and pb is not None:
            draw.line([pa, pb], fill=tuple(int(c * 0.6) for c in _COLORS[index]), width=stick * 2)
    for index, point in enumerate(points):
        if point is not None:
            x, y = point
            draw.ellipse((x - stick, y - stick, x + stick, y + stick), fill=_COLORS[index])
    return canvas


def draw_people(people: list[dict[str, Any]], size: tuple[int, int]) -> Image.Image:
    canvas = Image.new("RGB", size, (0, 0, 0))
    for person in people:
        layer = draw_pose_pixels(person["points"], size)
        canvas = Image.composite(layer, canvas, layer.convert("L").point(lambda v: 255 if v > 0 else 0))
    return canvas


def half_masks(size: tuple[int, int]) -> tuple[Image.Image, Image.Image]:
    width, height = size
    left, right = Image.new("L", size, 0), Image.new("L", size, 0)
    ImageDraw.Draw(left).rectangle((0, 0, width // 2 - 1, height - 1), fill=255)
    ImageDraw.Draw(right).rectangle((width // 2, 0, width - 1, height - 1), fill=255)
    return left, right


def silhouette_mask(
    points: list[tuple[float, float] | None], size: tuple[int, int], head_h: float = 0.24,
) -> Image.Image:
    height = size[1]
    unit = head_h * height
    p = dict(zip(_KEYS, points, strict=True))
    mask = Image.new("L", size, 0)
    draw = ImageDraw.Draw(mask)
    arm = max(2, round(0.42 * unit))
    for chain in (("r_shoulder", "r_elbow", "r_wrist"), ("l_shoulder", "l_elbow", "l_wrist")):
        joints = [p[k] for k in chain if p[k] is not None]
        if len(joints) >= 2:
            draw.line(joints, fill=255, width=arm, joint="curve")
        for x, y in joints:
            radius = arm * (0.8 if (x, y) == joints[-1] else 0.5)
            draw.ellipse((x - radius, y - radius, x + radius, y + radius), fill=255)
    rs, ls, rh, lh = p["r_shoulder"], p["l_shoulder"], p["r_hip"], p["l_hip"]
    widen = 0.25 * unit
    draw.polygon([
        (rs[0] - widen, rs[1] - widen), (ls[0] + widen, ls[1] - widen),
        (lh[0] + widen * 1.5, max(lh[1], height)),
        (rh[0] - widen * 1.5, max(rh[1], height)),
    ], fill=255)
    nx, ny = p["nose"]
    draw.ellipse((nx - 0.62 * unit, ny - 0.78 * unit, nx + 0.62 * unit, ny + 0.62 * unit), fill=255)
    grow = max(3, round(0.1 * unit)) | 1
    return mask.filter(ImageFilter.MaxFilter(grow)).filter(ImageFilter.GaussianBlur(max(2, round(0.08 * unit))))


def background_mask(people: list[dict[str, Any]], size: tuple[int, int], grow: int = 31) -> Image.Image:
    """Task 23.2: where the scene-plate reference applies -- everything except the
    (dilated) person silhouettes, so the plate never paints over a character."""
    union = Image.new("L", size, 0)
    for person in people:
        union = ImageChops.lighter(union, silhouette_mask(person["points"], size, person["head_h"]))
    union = union.point(lambda value: 255 if value > 20 else 0).filter(ImageFilter.MaxFilter(grow | 1))
    return ImageChops.invert(union)


def refine_mask(person: dict[str, Any], size: tuple[int, int], half: Image.Image) -> Image.Image:
    """Feathered silhouette strictly clipped to its person's half."""
    return ImageChops.multiply(silhouette_mask(person["points"], size, person["head_h"]), half)


def hand_boxes(
    points: list[tuple[float, float] | None], size: tuple[int, int], head_h: float = 0.20,
) -> list[dict[str, Any]]:
    width, height = size
    unit = head_h * height
    named = dict(zip(_KEYS, points, strict=True))
    side = round(2.2 * unit)
    boxes = []
    for elbow_key, wrist_key in (("r_elbow", "r_wrist"), ("l_elbow", "l_wrist")):
        elbow, wrist = named[elbow_key], named[wrist_key]
        if elbow is None or wrist is None:
            continue
        cx = wrist[0] + 0.35 * (wrist[0] - elbow[0])
        cy = wrist[1] + 0.35 * (wrist[1] - elbow[1])
        if not (0 <= cx < width and 0 <= cy < height):
            continue
        left = min(max(0, round(cx - side / 2)), width - side)
        top = min(max(0, round(cy - side / 2)), height - side)
        boxes.append({"hand": wrist_key, "box": (left, top, left + side, top + side),
                      "center": (round(cx - left), round(cy - top)), "radius": round(0.9 * unit)})
    return boxes


def hand_mask(side: int, center: tuple[int, int], radius: int) -> Image.Image:
    mask = Image.new("L", (side, side), 0)
    cx, cy = center
    ImageDraw.Draw(mask).ellipse((cx - radius, cy - radius, cx + radius, cy + radius), fill=255)
    return mask.filter(ImageFilter.GaussianBlur(max(1, radius // 5)))


def paste_hand(
    render: Image.Image, fixed_crop: Image.Image, box: tuple[int, int, int, int], mask: Image.Image,
) -> Image.Image:
    left, top, right, bottom = box
    out = render.convert("RGB").copy()
    patch = fixed_crop.convert("RGB").resize((right - left, bottom - top), Image.Resampling.LANCZOS)
    region = out.crop(box)
    out.paste(Image.composite(patch, region, mask.resize(patch.size)), (left, top))
    return out


# Task 24.3: a beat's action as a pose. Offsets are in head units from the neck (x) and the nose
# (y) for the arm on the image-left side of a front-facing person (its right arm); the arm that
# faces a duo partner on the right is mirrored. Keyword order matters: the first match wins.
ACTION_CATEGORIES = ("point", "drink", "phone", "think", "wave", "work", "walk", "talk")
ACTION_KEYWORDS = {
    "point": ("point", "show", "map", "board", "gesturing to"),
    "drink": ("coffee", "tea", "drink", "sip", "cup", "juice"),
    "phone": ("phone", "call", "texting"),
    "think": ("think", "wonder", "chin", "ponder"),
    "wave": ("wave", "waving", "greet", "goodbye", "hello"),
    "work": ("laptop", "computer", "typing", "writing", "notebook", "reading", "book", "plans",
             "document", "paper", "studying", "desk"),
    "walk": ("walk", "stroll", "hike", "hiking"),
}
ACTION_POSES: dict[str, dict[str, Any]] = {
    "talk": {"arm": ((-1.0, 1.9), (-0.6, 1.35))},
    "point": {"arm": ((-1.35, 1.15), (-2.25, 0.85))},
    "drink": {"arm": ((-0.95, 1.9), (-0.3, 0.95))},
    "phone": {"arm": ((-0.95, 1.6), (-0.45, 0.3))},
    "think": {"arm": ((-0.7, 2.2), (-0.1, 0.7))},
    "wave": {"arm": ((-1.35, 1.0), (-1.5, -0.25))},
    "work": {"arm": ((-0.8, 2.2), (-0.3, 2.75)), "other": ((0.8, 2.2), (0.3, 2.75))},
    "walk": {"arm": ((-0.95, 2.05), (-0.75, 3.0)),
             "legs": {"r_knee": (-0.6, 4.6), "r_ankle": (-0.95, 6.1), "l_knee": (0.45, 4.6), "l_ankle": (0.8, 6.2)}},
}


def action_category(action: str | None) -> str:
    text = (action or "").lower()
    for category in ACTION_CATEGORIES[:-1]:
        if any(word in text for word in ACTION_KEYWORDS[category]):
            return category
    return "talk"


def beat_people(kind: str, staging: str, size: tuple[int, int], categories: list[str]) -> list[dict[str, Any]]:
    """`shot_people` with each person's gesturing arm (and, for walking, legs that are already
    drawn) replaced by their beat action's pose. `talk` keeps the proven r8 geometry unchanged."""
    people = shot_people(kind, staging, size)
    height = size[1]
    for index, (person, category) in enumerate(zip(people, categories, strict=True)):
        if category == "talk":
            continue
        pose = ACTION_POSES[category]
        named = dict(zip(_KEYS, person["points"], strict=True))
        unit = person["head_h"] * height
        anchor_x, anchor_y = named["neck"][0], named["nose"][1]
        # The left duo person faces their partner on the right; a single person stands in the left
        # third, so their action opens toward the empty right of the frame (never off-frame).
        toward_right = kind == "single" or index == 0
        sign, near, far = (-1, "l", "r") if toward_right else (1, "r", "l")

        def place(key: str, offset: tuple[float, float], mirror: int) -> None:
            named[key] = (anchor_x + mirror * offset[0] * unit, anchor_y + offset[1] * unit)

        elbow, wrist = pose["arm"]
        place(f"{near}_elbow", elbow, sign)
        place(f"{near}_wrist", wrist, sign)
        if "other" in pose:
            elbow, wrist = pose["other"]
            place(f"{far}_elbow", elbow, sign)
            place(f"{far}_wrist", wrist, sign)
        if "legs" in pose and named["r_knee"] is not None:
            for key, offset in pose["legs"].items():
                place(key, offset, 1)
        person["points"] = [named[key] for key in _KEYS]
    return people
