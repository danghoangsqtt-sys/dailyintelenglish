r"""Bring full-figure sprite pictures made on the web (ChatGPT) into the sprite pack (Phase 32): key out the green, put on the canvas, align.

    venv\Scripts\python scripts\sprite_web_import.py lina
    venv\Scripts\python scripts\sprite_web_import.py lina --raw D:\some\folder

The web returns an ordinary picture (any size, a flat green background, the figure a little larger, smaller or shifted each time). For
every data\assets_sprites\web_raw\<character>__<name>.png this tool:

  1. makes the green background transparent (the key colour is read from the border of the picture) and removes the green fringe;
  2. finds the face (the app's face model) and scales and places the figure so that its face matches the face of the base picture;
  3. refines scale and position by matching the silhouette of the head zone against the base (the top 20% of the figure);
  4. writes <character>__<name>.png on the 1280 x 1536 canvas into data\library\sprites_inbox.

Then `check_sprites.py` says which pictures are still too far off the base (those are made again on the web). The base picture
<character>__calm__closed.png is never touched.
"""

from __future__ import annotations

import argparse
import subprocess
import sys
import tempfile
from pathlib import Path

import numpy as np
from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parent))
import sprite_face_tools as tools  # noqa: E402

ROOT = tools.ROOT
INBOX = tools.INBOX
RAW = ROOT / "data" / "assets_sprites" / "web_raw"
CANVAS = (1280, 1536)
HEAD_FRACTION = 0.20


def key_out_green(rgb: Image.Image) -> Image.Image:
    """RGBA from a picture on a flat green background: the key greenness is read from the border, the fringe is despilled."""
    data = np.asarray(rgb.convert("RGB")).astype(np.float32)
    green = data[..., 1] - np.maximum(data[..., 0], data[..., 2])
    border = np.concatenate([green[0], green[-1], green[:, 0], green[:, -1]])
    key = float(np.median(border))
    if key < 40:
        raise ValueError("the background is not green: ask for a flat #00B140 background")
    low, high = 0.30 * key, 0.85 * key
    alpha = 1.0 - np.clip((green - low) / (high - low), 0.0, 1.0)
    alpha[alpha < 0.04] = 0.0
    limit = np.maximum(data[..., 0], data[..., 2])
    data[..., 1] = np.where(alpha < 1.0, np.minimum(data[..., 1], limit), data[..., 1])
    out = np.dstack([np.clip(data, 0, 255), alpha * 255]).astype(np.uint8)
    return Image.fromarray(out, "RGBA")


def head_zone(alpha: np.ndarray) -> tuple[int, int]:
    """Rows [top, end) of the head zone of a figure (the top 20% of its height)."""
    ys = np.where((alpha > 20).any(axis=1))[0]
    top, bottom = int(ys.min()), int(ys.max())
    return top, top + int((bottom - top) * HEAD_FRACTION)


def refine(raw_alpha: np.ndarray, ref_alpha: np.ndarray, scale: float, dx: float, dy: float) -> tuple[float, float, float, float]:
    """Best (scale, dx, dy) near the start by the overlap of the head-zone silhouettes, at half resolution; returns them with the overlap.

    `raw_alpha` is the alpha of the web picture, `ref_alpha` the base's alpha on the canvas; a point (x, y) of the web picture lands at
    (scale * x + dx, scale * y + dy) on the canvas.
    """
    top, end = head_zone(ref_alpha)
    first_row = max(0, top - 8) // 2 * 2
    reference = ref_alpha[first_row:end + 8:2, ::2] > 20
    best = (-1.0, scale, dx, dy)
    half = Image.fromarray(((raw_alpha > 20) * 255).astype(np.uint8))
    for factor in (0.97, 0.98, 0.99, 1.0, 1.01, 1.02, 1.03):
        s = scale * factor
        size = (max(1, round(half.width * s / 2)), max(1, round(half.height * s / 2)))
        mask = np.asarray(half.resize(size, Image.Resampling.BILINEAR)) > 127
        for j in range(-8, 9):
            for i in range(-8, 9):
                ox, oy = round(dx / 2) + i, round(dy / 2) + j - first_row // 2
                window = np.zeros(reference.shape, dtype=bool)
                x0, y0 = max(0, ox), max(0, oy)
                x1, y1 = min(window.shape[1], ox + mask.shape[1]), min(window.shape[0], oy + mask.shape[0])
                if x1 <= x0 or y1 <= y0:
                    continue
                window[y0:y1, x0:x1] = mask[y0 - oy:y1 - oy, x0 - ox:x1 - ox]
                union = (window | reference).sum()
                score = (window & reference).sum() / union if union else 0.0
                if score > best[0]:
                    best = (score, s, (ox + 0) * 2.0, (oy + first_row // 2) * 2.0)
    return best[1], best[2], best[3], best[0]


def place(figure: Image.Image, scale: float, dx: float, dy: float) -> Image.Image:
    """The RGBA figure scaled and shifted onto a transparent canvas (outside parts are cut off)."""
    coefficients = (1 / scale, 0, -dx / scale, 0, 1 / scale, -dy / scale)
    return figure.transform(CANVAS, Image.Transform.AFFINE, coefficients, resample=Image.Resampling.BICUBIC)


def face_box(picture: Image.Image, work: Path) -> list[float] | None:
    path = work / "face_probe.png"
    picture.convert("RGB").save(path)
    try:
        return tools.detect_face(path)
    except SystemExit:
        return None


def import_one(raw_path: Path, base: Image.Image, base_face: list[float] | None, work: Path) -> tuple[Image.Image, float]:
    raw = Image.open(raw_path).convert("RGB")
    figure = key_out_green(raw)
    ref_alpha = np.asarray(base.getchannel("A"))
    raw_alpha = np.asarray(figure.getchannel("A"))
    face = face_box(raw, work)
    if face and base_face:
        scale = (base_face[2] - base_face[0]) / (face[2] - face[0])
        dx = (base_face[0] + base_face[2]) / 2 - scale * (face[0] + face[2]) / 2
        dy = (base_face[1] + base_face[3]) / 2 - scale * (face[1] + face[3]) / 2
    else:  # no face found: fit the height of the figure, bottom on the bottom edge, centred
        ys, xs = np.where(raw_alpha > 20)
        ry = np.where(ref_alpha > 20)[0]
        scale = (ry.max() - ry.min()) / (ys.max() - ys.min())
        dx = CANVAS[0] / 2 - scale * (xs.min() + xs.max()) / 2
        dy = CANVAS[1] - scale * ys.max()
    scale, dx, dy, overlap = refine(raw_alpha, ref_alpha, scale, dx, dy)
    return place(figure, scale, dx, dy), overlap


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("character")
    parser.add_argument("--raw", default=str(RAW))
    args = parser.parse_args()
    who, raw_folder = args.character.lower(), Path(args.raw)
    base_path = INBOX / f"{who}__calm__closed.png"
    if not base_path.is_file():
        print(f"missing {base_path}")
        return 1
    base = Image.open(base_path).convert("RGBA")
    files = sorted(p for p in raw_folder.glob(f"{who}__*.png") if p.name != base_path.name)
    if not files:
        print(f"no {who}__*.png in {raw_folder}")
        return 1
    made, failed = 0, []
    with tempfile.TemporaryDirectory() as temp:
        work = Path(temp)
        flat = tools.flatten(base, (0, 0, base.width, base.height))
        flat.save(work / "base_probe.png")
        try:
            base_face = tools.detect_face(work / "base_probe.png")
        except SystemExit:
            base_face = None
        for path in files:
            try:
                picture, overlap = import_one(path, base, base_face, work)
            except ValueError as error:
                failed.append(f"{path.name} ({error})")
                continue
            picture.save(INBOX / path.name)
            made += 1
            print(f"{path.name:34} head overlap {overlap:.2f}")
    print(f"imported {made} of {len(files)} into {INBOX}")
    if failed:
        print("not imported: " + "; ".join(failed))
    check = subprocess.run([sys.executable, str(Path(__file__).with_name("check_sprites.py")), who], capture_output=True, text=True)
    print(check.stdout.rstrip())
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
