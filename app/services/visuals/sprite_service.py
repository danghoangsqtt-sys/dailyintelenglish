"""Phase 32 (Task 32.1): the talking-sprite sets of the library characters.

A sprite set is a folder per character, `data/library/sprites/<character_id>/<name>.png`, with a `sprite_set.json` (D32-a): the
pictures are made outside the app (one transparent 1280 x 1536 PNG per expression and mouth, a blink, the gestures) and copied into
`data/library/sprites_inbox` as `<character name>__<name>.png`. The import checks that every picture lines up with the character's
`calm__closed` picture (the rules `scripts/check_sprites.py` reports) and refuses the ones that do not, with the reason.

The video draws one body (the calm picture, or a gesture) and puts the face of the current expression and mouth on it inside a feathered
ellipse, so the body never shimmers when the mouth moves (D32-c); `sprite_set.json` holds that ellipse and each picture's head offset.
"""

from __future__ import annotations

import asyncio
import json
import shutil
import subprocess
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable

import aiosqlite
import numpy as np
from PIL import Image

from app.core.config import settings
from app.core.paths import get_project_root

SIZE = (1280, 1536)
EXPRESSIONS = ("calm", "smile", "laugh", "surprised", "thinking", "worried", "serious")
MOUTHS = ("closed", "open")
GESTURES = ("talk", "point", "think", "open", "heart", "listen", "wave")
FACE_NAMES = tuple(f"{expression}__{mouth}" for expression in EXPRESSIONS for mouth in MOUTHS) + ("blink",)
GESTURE_NAMES = tuple(f"gesture-{gesture}" for gesture in GESTURES)
ALL_NAMES = FACE_NAMES + GESTURE_NAMES
BASE = "calm__closed"
MINIMUM = ("calm__closed", "calm__open")  # a set the video can use: the face must at least open and close its mouth

# the limits of scripts/check_sprites.py (what a smooth video needs)
TOP_LIMIT = 6
HEAD_SIDE_LIMIT = 10
EDGE_LIMIT = 8
GESTURE_EDGE_LIMIT = 20  # owner 2026-10-08: a gesture moves the arms; a body that is bigger, smaller or shifted is refused
SILHOUETTE_LIMIT = 4.0
HEAD_FRACTION = 0.20
EDGE_PIXELS = 8  # a figure touching the left, right or top edge of the canvas over more pixels than this is cut off (a hand, the hair)
SET_FILE = "sprite_set.json"


def sprites_root() -> Path:
    return settings.DATA_DIR / "library" / "sprites"


def inbox_dir() -> Path:
    return settings.DATA_DIR / "library" / "sprites_inbox"


def sprite_dir(character_id: str) -> Path:
    return sprites_root() / character_id


def parse_name(filename: str) -> tuple[str, str] | None:
    """`alex__smile__open.png` -> ("alex", "smile__open"); None for a file that is not a sprite picture."""
    if not filename.lower().endswith(".png"):
        return None
    stem = filename[:-4]
    who, separator, name = stem.partition("__")
    if not separator or not who or name not in ALL_NAMES:
        return None
    return who.strip().lower(), name


# ---------------------------------------------------------------- the alignment check (pure, shared with check_sprites.py)

def _bbox(alpha: np.ndarray) -> tuple[int, int, int, int]:
    ys, xs = np.where(alpha)
    return int(xs.min()), int(ys.min()), int(xs.max()), int(ys.max())


def _torso_edges(alpha: np.ndarray, top: int, bottom: int) -> tuple[float, float]:
    """Mean left and right edge of the figure over the torso rows (55 to 90% of the figure's height)."""
    first, last = top + int((bottom - top) * 0.55), top + int((bottom - top) * 0.90)
    lefts, rights = [], []
    for y in range(first, last, 6):
        xs = np.where(alpha[y])[0]
        if len(xs):
            lefts.append(xs.min())
            rights.append(xs.max())
    return (float(np.mean(lefts)), float(np.mean(rights))) if lefts else (0.0, 0.0)


class Reference:
    """What the pictures of a set are compared with: the calm, closed-mouth picture."""

    def __init__(self, rgba: np.ndarray):
        self.alpha = rgba[..., 3] > 20
        x0, self.top, x1, self.bottom = _bbox(self.alpha)
        self.head_end = self.top + int((self.bottom - self.top) * HEAD_FRACTION)
        self.head_x = float(np.where(self.alpha[:self.head_end])[1].mean())
        self.left, self.right = _torso_edges(self.alpha, self.top, self.bottom)


def measure(rgba: np.ndarray, reference: Reference, gesture: bool) -> dict:
    """The check of one picture against the reference: its numbers and its problems (empty when it passes)."""
    if (rgba.shape[1], rgba.shape[0]) != SIZE:
        return {"problems": [f"wrong canvas size {rgba.shape[1]} x {rgba.shape[0]}, expected {SIZE[0]} x {SIZE[1]}"]}
    if rgba.shape[2] < 4 or not all(rgba[y, x, 3] == 0 for y in (0, -1) for x in (0, -1)):
        return {"problems": ["the background is not transparent (the four corners must be)"]}
    alpha = rgba[..., 3] > 20
    if not alpha.any():
        return {"problems": ["the picture is empty"]}
    x0, y0, x1, y1 = _bbox(alpha)
    left, right = _torso_edges(alpha, y0, y1)
    head_end = reference.head_end
    cut = [side for side, pixels in (("left", alpha[:, 0].sum()), ("right", alpha[:, -1].sum()), ("top", alpha[0].sum()))
           if pixels > EDGE_PIXELS]
    head_x = float(np.where(alpha[:head_end])[1].mean()) if alpha[:head_end].any() else -9999.0
    edge_shift = max(abs(left - reference.left), abs(right - reference.right))
    ref_alpha = reference.alpha
    head_xor = float((alpha[:head_end] ^ ref_alpha[:head_end]).sum() / max(1, ref_alpha[:head_end].sum()) * 100)
    body_xor = float((alpha[head_end:] ^ ref_alpha[head_end:]).sum() / max(1, ref_alpha[head_end:].sum()) * 100)
    problems = [f"the figure is cut by the {side} edge of the canvas" for side in cut]
    if abs(y0 - reference.top) > TOP_LIMIT:
        problems.append(f"head top moved {y0 - reference.top:+d}px")
    if abs(head_x - reference.head_x) > HEAD_SIDE_LIMIT:
        problems.append(f"head moved sideways {head_x - reference.head_x:+.0f}px")
    if gesture:
        if head_xor > SILHOUETTE_LIMIT:
            problems.append(f"head differs {head_xor:.1f}%")
        if edge_shift > GESTURE_EDGE_LIMIT:
            problems.append(f"body moved {edge_shift:.0f}px (a gesture may move the arms, not the body)")
    else:
        if edge_shift > EDGE_LIMIT:
            problems.append(f"torso moved {edge_shift:.0f}px")
        if body_xor > SILHOUETTE_LIMIT:
            problems.append(f"body differs {body_xor:.1f}%")
    return {
        "top": y0 - reference.top, "edge_shift": edge_shift, "body_diff": body_xor, "head_diff": head_xor,
        "head_dx": head_x - reference.head_x, "head_dy": y0 - reference.top, "problems": problems,
    }


# ---------------------------------------------------------------- the face ellipse

def geometric_face_ellipse(alpha: np.ndarray) -> list[float]:
    """A fallback when the face model is not installed: the face inside the head zone of the silhouette (hair included), as fractions
    of the canvas [cx, cy, rx, ry]. The head is about a fifth of the figure; the face is the lower two thirds of it."""
    mask = alpha > 20
    ys = np.where(mask.any(axis=1))[0]
    top, bottom = int(ys.min()), int(ys.max())
    head = (bottom - top) * 0.22
    rows = mask[top:int(top + head)]
    xs = np.where(rows.any(axis=0))[0]
    cx = (xs.min() + xs.max()) / 2
    cy = top + head * 0.58
    return [cx / alpha.shape[1], cy / alpha.shape[0], head * 0.30 / alpha.shape[1], head * 0.40 / alpha.shape[0]]


def detected_face_ellipse(base_path: Path) -> list[float] | None:
    """The face found by the app's face model (in the image environment), grown to take the forehead, the cheeks and the chin, as
    fractions of the canvas [cx, cy, rx, ry]; None when the image environment is missing or finds no face."""
    from app.services.visuals.engine import IMAGE_PYTHON

    if not IMAGE_PYTHON.is_file():
        return None
    root = get_project_root()
    with tempfile.TemporaryDirectory() as temp:
        probe = Path(temp) / "probe.png"
        with Image.open(base_path) as opened:
            picture = opened.convert("RGBA")
        flat = Image.new("RGBA", picture.size, (190, 190, 190, 255))
        flat.alpha_composite(picture)
        flat.convert("RGB").save(probe)
        code = ("import sys, json; sys.path.insert(0, r'%s'); from scripts.image_worker import detect_faces; "
                "print(json.dumps(detect_faces(r'%s', 0.5)))" % (root, probe))
        try:
            result = subprocess.run([str(IMAGE_PYTHON), "-c", code], capture_output=True, text=True, cwd=root, timeout=300)
        except (OSError, subprocess.SubprocessError):
            return None
    output = result.stdout.splitlines() + result.stderr.splitlines()
    found = [line for line in output if line.startswith("[[")] if result.returncode == 0 else []
    faces = json.loads(found[-1]) if found else []
    if not faces:
        return None
    x1, y1, x2, y2 = max(faces, key=lambda face: face[4])[:4]
    width, height = SIZE
    return [(x1 + x2) / 2 / width, ((y1 + y2) / 2 - 0.04 * (y2 - y1)) / height, 0.64 * (x2 - x1) / width, 0.64 * (y2 - y1) / height]


# ---------------------------------------------------------------- the import

def _load(path: Path) -> np.ndarray:
    with Image.open(path) as opened:
        return np.asarray(opened.convert("RGBA"))


def check_folder(files: dict[str, Path]) -> tuple[dict[str, dict], list[dict]]:
    """Measures every picture of one character's files against its `calm__closed` one: (accepted name -> measures, refused list)."""
    reference_rgba = _load(files[BASE])
    size = (reference_rgba.shape[1], reference_rgba.shape[0])
    corners_clear = all(reference_rgba[y, x, 3] == 0 for y in (0, -1) for x in (0, -1))
    if size != SIZE or not corners_clear or not (reference_rgba[..., 3] > 20).any():
        reason = f"the base picture must be a transparent {SIZE[0]} x {SIZE[1]} PNG (it is {size[0]} x {size[1]}" + \
                 ("" if corners_clear else ", not transparent") + ")"
        refused = [{"file": files[BASE].name, "reason": reason}]
        refused += [{"file": path.name, "reason": "not checked: the base picture was refused"}
                    for name, path in sorted(files.items()) if name != BASE]
        return {}, refused
    reference = Reference(reference_rgba)
    accepted: dict[str, dict] = {BASE: {"head_dx": 0.0, "head_dy": 0}}
    refused: list[dict] = []
    for name, path in sorted(files.items()):
        if name == BASE:
            continue
        result = measure(_load(path), reference, name.startswith("gesture-"))
        if result["problems"]:
            refused.append({"file": path.name, "reason": "; ".join(result["problems"])})
        else:
            accepted[name] = {"head_dx": round(result["head_dx"], 1), "head_dy": int(result["head_dy"])}
    return accepted, refused


async def characters_by_key(db: aiosqlite.Connection) -> dict[str, dict]:
    cursor = await db.execute("SELECT id, name FROM characters ORDER BY created_at, id")
    return {row["name"].strip().lower(): {"id": row["id"], "name": row["name"]} for row in await cursor.fetchall()}


def list_inbox() -> list[str]:
    folder = inbox_dir()
    return sorted(path.name for path in folder.glob("*.png")) if folder.is_dir() else []


def _write_set(character_id: str, files: dict[str, Path], accepted: dict[str, dict],
               face: Callable[[Path], list[float] | None]) -> dict:
    target = sprite_dir(character_id)
    if target.exists():
        shutil.rmtree(target)
    target.mkdir(parents=True)
    for name in accepted:
        shutil.copyfile(files[name], target / f"{name}.png")
    ellipse = face(target / f"{BASE}.png")
    source = "face model"
    if ellipse is None:
        ellipse, source = geometric_face_ellipse(_load(target / f"{BASE}.png")[..., 3]), "silhouette"
    meta = {
        "canvas": list(SIZE), "face_ellipse": [round(value, 4) for value in ellipse], "face_from": source,
        "pictures": accepted, "imported_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
    }
    (target / SET_FILE).write_text(json.dumps(meta, indent=1), encoding="utf-8")
    return meta


async def import_inbox(characters: dict[str, dict], face: Callable[[Path], list[float] | None] | None = None) -> dict:
    """Imports the sprite pictures of the inbox, one set per library character (`characters_by_key`: the file name prefix is the
    character's name). A set replaces the character's previous one. The inbox keeps its files. Touches no table."""
    face = face or detected_face_ellipse
    groups: dict[str, dict[str, Path]] = {}
    ignored: list[str] = []
    for filename in list_inbox():
        parsed = parse_name(filename)
        if parsed is None:
            ignored.append(filename)
            continue
        who, name = parsed
        groups.setdefault(who, {})[name] = inbox_dir() / filename
    imported, refused = [], []
    for who, files in sorted(groups.items()):
        character = characters.get(who)
        if character is None:
            refused += [{"file": path.name, "reason": f"no library character is called \"{who}\""} for path in files.values()]
            continue
        if BASE not in files:
            refused.append({"file": f"{who}__{BASE}.png", "reason": "missing: every set needs its calm, closed-mouth picture"})
            continue
        accepted, refused_here = await asyncio.to_thread(check_folder, files)
        refused += refused_here
        if not accepted:
            continue
        meta = await asyncio.to_thread(_write_set, character["id"], files, accepted, face)
        imported.append({"character_id": character["id"], "name": character["name"], "pictures": len(accepted),
                         "face_from": meta["face_from"]})
    return {"folder": str(inbox_dir()), "imported": imported, "refused": refused, "ignored": ignored}


def load_set(character_id: str) -> dict | None:
    """The imported set of a character: its meta and the names of its pictures; None without a set."""
    folder = sprite_dir(character_id)
    meta_path = folder / SET_FILE
    if not meta_path.is_file():
        return None
    meta = json.loads(meta_path.read_text(encoding="utf-8"))
    names = [name for name in meta.get("pictures", {}) if (folder / f"{name}.png").is_file()]
    return {**meta, "names": names, "folder": str(folder)}


def usable(sprite_set: dict | None) -> bool:
    return sprite_set is not None and all(name in sprite_set["names"] for name in MINIMUM)


async def list_sets(db: aiosqlite.Connection) -> list[dict]:
    """Per library character: its sprite set (pictures, gestures, what is missing) or none."""
    cursor = await db.execute("SELECT id, name FROM characters ORDER BY created_at, id")
    rows = [dict(row) for row in await cursor.fetchall()]
    views = []
    for row in rows:
        sprite_set = await asyncio.to_thread(load_set, row["id"])
        names = sprite_set["names"] if sprite_set else []
        views.append({
            "character_id": row["id"], "name": row["name"], "has_set": sprite_set is not None, "usable": usable(sprite_set),
            "faces": len([name for name in names if name in FACE_NAMES]), "faces_total": len(FACE_NAMES),
            "gestures": len([name for name in names if name in GESTURE_NAMES]), "gestures_total": len(GESTURE_NAMES),
            "missing": [name for name in ALL_NAMES if name not in names] if sprite_set else list(ALL_NAMES),
            "imported_at": sprite_set["imported_at"] if sprite_set else None,
            "face_from": sprite_set["face_from"] if sprite_set else None,
        })
    return views


async def remove_set(character_id: str) -> None:
    await asyncio.to_thread(shutil.rmtree, sprite_dir(character_id), True)
