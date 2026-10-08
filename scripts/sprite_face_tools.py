r"""Face variants of a sprite without sending the whole figure to an image editor (Phase 32).

An image editor redraws the whole picture, drifts, and may refuse a picture it does not like for its body. These tools send it only a
harmless crop of the head and neck, and put the edited face back into the base sprite on this machine:

    venv\Scripts\python scripts\sprite_face_tools.py prepare lina      # makes data\assets_sprites\heads\lina_head_crop.png + lina_head_meta.json
    ...  the image editor edits the crop once per expression and saves  data\assets_sprites\heads\edited\lina__smile__open.png  etc.
    venv\Scripts\python scripts\sprite_face_tools.py compose lina      # writes lina__<expression>__<mouth>.png into sprites_inbox

`compose` keeps the base sprite untouched outside a feathered ellipse around the face, and keeps the base's transparency, so a result is
aligned with the base by construction (`check_sprites.py` passes). The body, the arms and the hands of the base are never changed, so this
makes the expression pictures (tiers 1 and 2) but not the gestures (tier 3).
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageFilter

ROOT = Path(r"D:\DataAdmin\Daily_Intel_English")
INBOX = ROOT / "data" / "library" / "sprites_inbox"
HEADS = ROOT / "data" / "assets_sprites" / "heads"
VENV_IMAGE = ROOT / "venv-image" / "Scripts" / "python.exe"
GREY = (190, 190, 190)
SQUARE = 1024  # side of the square edit input
HEAD_PX = 338  # the head height of the standard canvas (see normalize_sprite_base.py)
EXPRESSION_FILES = [f"{expression}__{mouth}" for expression in ("calm", "smile", "surprised", "laugh", "thinking", "worried", "serious")
                    for mouth in ("closed", "open")] + ["blink"]


def crop_box(alpha: np.ndarray) -> tuple[int, int, int, int]:
    """The head-and-neck box of a base sprite: from just above the hair to just under the chin, as wide as the hair (no clothes)."""
    ys, xs = np.where(alpha > 20)
    top = int(ys.min())
    bottom = top + int(HEAD_PX * 1.28)  # the chin is one head below the top of the hair; the neck and the top of the shoulders follow
    rows = alpha[top:bottom] > 20
    columns = np.where(rows.any(axis=0))[0]
    x0, x1 = max(0, int(columns.min()) - 24), min(alpha.shape[1], int(columns.max()) + 24)
    return x0, max(0, top - 24), x1, min(alpha.shape[0], bottom)


def flatten(rgba: Image.Image, box: tuple[int, int, int, int]) -> Image.Image:
    part = rgba.crop(box)
    background = Image.new("RGBA", part.size, GREY + (255,))
    background.alpha_composite(part)
    return background.convert("RGB")


def detect_face(crop_path: Path) -> list[float]:
    """The face box [x1, y1, x2, y2, score] in the crop, by the app's pinned face model (run in the image environment)."""
    code = ("import sys, json; sys.path.insert(0, r'%s'); from scripts.image_worker import detect_faces; "
            "print(json.dumps(detect_faces(r'%s', 0.5)))" % (ROOT, crop_path))
    result = subprocess.run([str(VENV_IMAGE), "-c", code], capture_output=True, text=True, cwd=ROOT, timeout=300)
    # the worker module sends its prints to stderr (stdout is its protocol channel): look in both for the JSON list
    output = result.stdout.splitlines() + result.stderr.splitlines()
    lines = [line for line in output if line.startswith("[[")] if result.returncode == 0 else []
    faces = json.loads(lines[-1]) if lines else []
    if not faces:
        raise SystemExit(f"no face found in {crop_path}: {result.stderr[-300:]}")
    return max(faces, key=lambda f: f[4])


def face_ellipse(face: list[float]) -> tuple[float, float, float, float]:
    """Centre and half axes of the pasted region: the detected face grown to take the forehead, the cheeks and the chin."""
    x1, y1, x2, y2 = face[:4]
    return (x1 + x2) / 2, (y1 + y2) / 2 - 0.04 * (y2 - y1), 0.64 * (x2 - x1), 0.64 * (y2 - y1)


def ellipse_mask(size: tuple[int, int], ellipse: tuple[float, float, float, float], feather: int = 16) -> np.ndarray:
    width, height = size
    cx, cy, a, b = ellipse
    ys, xs = np.mgrid[0:height, 0:width]
    inside = (((xs - cx) / a) ** 2 + ((ys - cy) / b) ** 2) <= 1.0
    mask = Image.fromarray((inside * 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(feather / 2))
    return np.asarray(mask).astype(np.float32) / 255.0


def square_input(crop: Image.Image, size: int = SQUARE) -> tuple[Image.Image, dict]:
    """The head crop centred on a square grey canvas: image tools on the web often return a square, and the padding is cut off again."""
    scale = size / max(crop.size)
    content = crop.resize((round(crop.width * scale), round(crop.height * scale)), Image.Resampling.LANCZOS)
    canvas = Image.new("RGB", (size, size), GREY)
    left, top = (size - content.width) // 2, (size - content.height) // 2
    canvas.paste(content, (left, top))
    return canvas, {"size": size, "left": left, "top": top, "width": content.width, "height": content.height}


def to_crop_size(edited: Image.Image, meta: dict) -> Image.Image:
    """An edited head picture (the crop itself, or the square made by `square_input`, at any resolution) at the size of the crop."""
    box = meta["crop_box"]
    width, height = box[2] - box[0], box[3] - box[1]
    ratio = edited.width / edited.height
    if abs(ratio - width / height) < 0.04:
        return edited.convert("RGB").resize((width, height), Image.Resampling.LANCZOS)
    info = meta["square"]
    if abs(ratio - 1.0) < 0.04:
        factor = edited.width / info["size"]
        region = (round(info["left"] * factor), round(info["top"] * factor),
                  round((info["left"] + info["width"]) * factor), round((info["top"] + info["height"]) * factor))
        return edited.convert("RGB").crop(region).resize((width, height), Image.Resampling.LANCZOS)
    raise ValueError(f"unexpected picture shape {edited.width} x {edited.height}: use the square or the crop shape")


def prepare(who: str) -> int:
    base_path = INBOX / f"{who}__calm__closed.png"
    base = Image.open(base_path).convert("RGBA")
    box = crop_box(np.asarray(base.getchannel("A")))
    HEADS.mkdir(parents=True, exist_ok=True)
    crop_path = HEADS / f"{who}_head_crop.png"
    crop = flatten(base, box)
    crop.save(crop_path)
    face = detect_face(crop_path)
    square, info = square_input(crop)
    square_path = HEADS / f"{who}_head_edit_input.png"
    square.save(square_path)
    meta = {"crop_box": box, "face": face, "ellipse": face_ellipse(face), "base": base_path.name, "square": info}
    (HEADS / f"{who}_head_meta.json").write_text(json.dumps(meta, indent=1), encoding="utf-8")
    print(f"head crop {box[2] - box[0]} x {box[3] - box[1]} px at {box[:2]}, face box {[round(v) for v in face[:4]]}")
    print(f"edit this picture once per expression (a square, for image tools that return squares): {square_path}")
    print("expected edited files in", HEADS / "edited", ":", ", ".join(f"{who}__{name}.png" for name in EXPRESSION_FILES))
    return 0


def paste_face(base: Image.Image, edited: Image.Image, box: tuple[int, int, int, int], ellipse: tuple[float, float, float, float]) -> Image.Image:
    """The base with the face of `edited` (a picture of the head crop) put in; the base's transparency is kept."""
    width, height = box[2] - box[0], box[3] - box[1]
    patch = np.asarray(edited.convert("RGB").resize((width, height), Image.Resampling.LANCZOS)).astype(np.float32)
    out = np.asarray(base.convert("RGBA")).copy()
    region = out[box[1]:box[3], box[0]:box[2], :3].astype(np.float32)
    mask = ellipse_mask((width, height), ellipse)[..., None]
    visible = (out[box[1]:box[3], box[0]:box[2], 3:4] > 0).astype(np.float32)
    out[box[1]:box[3], box[0]:box[2], :3] = np.clip(region * (1 - mask * visible) + patch * (mask * visible), 0, 255).astype(np.uint8)
    return Image.fromarray(out, "RGBA")


def compose(who: str) -> int:
    meta = json.loads((HEADS / f"{who}_head_meta.json").read_text(encoding="utf-8"))
    base = Image.open(INBOX / f"{who}__calm__closed.png").convert("RGBA")
    made, missing, rejected = [], [], []
    for name in EXPRESSION_FILES:
        if name == "calm__closed":
            continue
        source = HEADS / "edited" / f"{who}__{name}.png"
        if not source.is_file():
            missing.append(name)
            continue
        try:
            patch = to_crop_size(Image.open(source), meta)
        except ValueError as error:
            rejected.append(f"{name} ({error})")
            continue
        paste_face(base, patch, tuple(meta["crop_box"]), tuple(meta["ellipse"])).save(INBOX / f"{who}__{name}.png")
        made.append(name)
    print(f"composed {len(made)}: {', '.join(made) or '-'}")
    print(f"still missing {len(missing)}: {', '.join(missing) or '-'}")
    if rejected:
        print(f"rejected {len(rejected)}: {'; '.join(rejected)}")
    return 1 if rejected else 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("command", choices=["prepare", "compose"])
    parser.add_argument("character")
    args = parser.parse_args()
    return prepare(args.character.lower()) if args.command == "prepare" else compose(args.character.lower())


if __name__ == "__main__":
    sys.exit(main())
