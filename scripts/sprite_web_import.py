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
from PIL import Image, ImageFilter

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
    low, high = 0.30 * key, 0.70 * key  # 0.70: the web's green is uneven near the corners (measured 2026-10-08)
    alpha = 1.0 - np.clip((green - low) / (high - low), 0.0, 1.0)
    alpha[alpha < 0.04] = 0.0
    limit = np.maximum(data[..., 0], data[..., 2])
    # the green spill: every pixel within 4 px of the background (not only the half-transparent ones: the hair's outer strands are
    # opaque but tinted) has its green held to its red or blue
    near_background = np.asarray(Image.fromarray(((alpha < 0.5) * 255).astype(np.uint8)).filter(ImageFilter.MaxFilter(9))) > 0
    data[..., 1] = np.where(near_background | (alpha < 1.0), np.minimum(data[..., 1], limit), data[..., 1])
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


def _shift_by_phase(a: np.ndarray, b: np.ndarray) -> tuple[int, int, float]:
    """Where `b` sits in `a` (both grey, `b` no larger): (dx, dy, mean absolute difference over the overlap), by phase correlation."""
    height, width = max(a.shape[0], b.shape[0]), max(a.shape[1], b.shape[1])
    fill_a, fill_b = float(np.median(a)), float(np.median(b))
    pa = np.full((height, width), fill_a, np.float32)
    pa[:a.shape[0], :a.shape[1]] = a
    pb = np.full((height, width), fill_b, np.float32)
    pb[:b.shape[0], :b.shape[1]] = b
    spectrum = np.fft.fft2(pa - fill_a) * np.conj(np.fft.fft2(pb - fill_b))
    peak = np.fft.ifft2(spectrum / (np.abs(spectrum) + 1e-6)).real
    dy, dx = np.unravel_index(int(np.argmax(peak)), peak.shape)
    dy = dy - height if dy > height // 2 else dy
    dx = dx - width if dx > width // 2 else dx
    y0, x0 = max(0, dy), max(0, dx)
    y1, x1 = min(a.shape[0], dy + b.shape[0]), min(a.shape[1], dx + b.shape[1])
    if y1 - y0 < 50 or x1 - x0 < 50:
        return int(dx), int(dy), 1e9
    error = float(np.abs(a[y0:y1, x0:x1] - b[y0 - dy:y1 - dy, x0 - dx:x1 - dx]).mean())
    return int(dx), int(dy), error


def register(raw: Image.Image, base: Image.Image) -> tuple[float, int, int, float]:
    """How a region edit that the image tool also rescaled and cropped maps onto the base input: (scale, dx, dy, error) with the raw
    pixel (u, v) = the base scaled by `scale`, pixel (u + dx, v + dy). Coarse scale search at a quarter size, then fine."""
    raw_grey = np.asarray(raw.convert("L"), dtype=np.float32)
    base_grey = base.convert("L")

    def try_scale(scale: float, step: int) -> tuple[int, int, float]:
        scaled = base_grey.resize((round(base.width * scale / step), round(base.height * scale / step)), Image.Resampling.BILINEAR)
        small = raw_grey if step == 1 else np.asarray(raw.convert("L").resize(
            (round(raw.width / step), round(raw.height / step)), Image.Resampling.BILINEAR), dtype=np.float32)
        return _shift_by_phase(np.asarray(scaled, dtype=np.float32), small)

    coarse = min((try_scale(s, 4)[2], s) for s in np.arange(0.90, 1.1001, 0.005))[1]
    fine = min((try_scale(s, 2)[2], s) for s in np.arange(coarse - 0.006, coarse + 0.0061, 0.001))[1]
    # last, at full size in steps of 0.0002 (a 1536-pixel canvas then lands within a third of a pixel: no jitter between twins)
    error, best = min((try_scale(s, 1)[2], s) for s in np.arange(fine - 0.001, fine + 0.00101, 0.0002))
    dx, dy, error = try_scale(best, 1)
    return float(best), dx, dy, error


def import_registered(raw_path: Path, base_input: Image.Image) -> tuple[Image.Image, str]:
    """A region edit returned at another size or crop: put back on the canvas exactly where the base input had it, then keyed."""
    raw = Image.open(raw_path).convert("RGB")
    scale, dx, dy, error = register(raw, base_input)
    if error > 12:
        raise ValueError(f"does not match the base input (difference {error:.1f}): it was drawn again, make it again")
    green = tuple(int(v) for v in np.median(np.concatenate([np.asarray(raw)[0], np.asarray(raw)[-1]]), axis=0))
    canvas = raw.transform(CANVAS, Image.Transform.AFFINE, (scale, 0, -dx, 0, scale, -dy),
                           resample=Image.Resampling.BICUBIC, fillcolor=green)
    return key_out_green(canvas), f"registered: scale {scale:.3f}, shift {dx:+d},{dy:+d}, difference {error:.1f}"


def twin_source(path: Path, who: str, placed: dict[str, Image.Image], base_input: Image.Image) -> Image.Image:
    """The picture a region edit was made from, on green: an open mouth was made from its closed twin (calm__open from the base
    input), everything else from the base input. Registering a twin on its own closed picture keeps the pair within a fraction
    of a pixel, so the face does not jump when the mouth moves."""
    stem = path.stem
    if not stem.endswith("__open") or stem == f"{who}__calm__open":
        return base_input
    closed = stem[:-len("__open")] + ("__closed" if not stem.startswith(f"{who}__gesture-") else "")
    if closed not in placed:
        return base_input
    flat = Image.new("RGBA", CANVAS, (0, 177, 64, 255))
    flat.alpha_composite(placed[closed])
    return flat.convert("RGB")


def import_resized(raw_path: Path) -> Image.Image:
    """A picture made by a region edit of the green base input: the same framing, only smaller. It is resized to the canvas and
    keyed, never moved (moving it by a pixel or two would make the face jump between pictures that should match)."""
    raw = Image.open(raw_path).convert("RGB")
    if abs(raw.width / raw.height - CANVAS[0] / CANVAS[1]) > 0.01:
        raise ValueError(f"not the base's shape ({raw.width} x {raw.height}): use --align")
    return key_out_green(raw.resize(CANVAS, Image.Resampling.LANCZOS))


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


def face_only(who: str, names: list[str]) -> list[str]:
    """Rewrite imported expression pictures as the base body with only the web picture's face pasted in (a picture whose body drifted)."""
    meta = tools.json.loads((tools.HEADS / f"{who}_head_meta.json").read_text(encoding="utf-8"))
    box, ellipse = tuple(meta["crop_box"]), tuple(meta["ellipse"])
    base = Image.open(INBOX / f"{who}__calm__closed.png").convert("RGBA")
    done = []
    for name in names:
        path = INBOX / f"{who}__{name}.png"
        if not path.is_file():
            continue
        tools.paste_face(base, tools.flatten(Image.open(path).convert("RGBA"), box), box, ellipse).save(path)
        done.append(name)
    return done


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("character")
    parser.add_argument("--raw", default=str(RAW))
    parser.add_argument("--face-only", default="", help="comma list of expressions (for example thinking__open) to keep as the base body plus the web face")
    parser.add_argument("--base-input", default=None,
                        help="the green base input the region edits were made from (default: web_inputs/INPUT_<character>__calm__closed.png)")
    parser.add_argument("--align", action="store_true",
                        help="pictures drawn again by the image tool (other size and place): find the face and align them. Without it the "
                             "pictures are region edits of the base input and are only resized")
    args = parser.parse_args()
    who, raw_folder = args.character.lower(), Path(args.raw)
    base_path = INBOX / f"{who}__calm__closed.png"
    if not base_path.is_file():
        print(f"missing {base_path}")
        return 1
    base = Image.open(base_path).convert("RGBA")
    # subfolders too; the closed pictures first, so that an open-mouth twin is registered on its own closed picture
    files = sorted((p for p in raw_folder.rglob(f"{who}__*.png") if p.name != base_path.name),
                   key=lambda p: (p.stem.endswith("__open"), p.name))
    if not files:
        print(f"no {who}__*.png in {raw_folder}")
        return 1
    base_input_path = Path(args.base_input) if args.base_input else ROOT / "data" / "assets_sprites" / "web_inputs" / f"INPUT_{who}__calm__closed.png"
    base_input = Image.open(base_input_path).convert("RGB") if base_input_path.is_file() else None
    made, failed = 0, []
    placed: dict[str, Image.Image] = {}
    with tempfile.TemporaryDirectory() as temp:
        work = Path(temp)
        base_face = None
        if args.align:
            tools.flatten(base, (0, 0, base.width, base.height)).save(work / "base_probe.png")
            try:
                base_face = tools.detect_face(work / "base_probe.png")
            except SystemExit:
                base_face = None
        for path in files:
            try:
                if args.align:
                    picture, overlap = import_one(path, base, base_face, work)
                    note = f"head overlap {overlap:.2f}"
                else:
                    with Image.open(path) as probe:
                        same_shape = abs(probe.width / probe.height - CANVAS[0] / CANVAS[1]) <= 0.01
                    if same_shape:
                        picture, note = import_resized(path), "resized"
                    else:  # the image tool also rescaled and cropped it: find where it sits on its source picture
                        picture, note = import_registered(path, twin_source(path, who, placed, base_input))
            except ValueError as error:
                failed.append(f"{path.name} ({error})")
                continue
            picture.save(INBOX / path.name)
            placed[path.stem] = picture
            made += 1
            print(f"{path.name:34} {note}")
    print(f"imported {made} of {len(files)} into {INBOX}")
    if args.face_only:
        print("face only (base body kept): " + ", ".join(face_only(who, [n.strip() for n in args.face_only.split(",") if n.strip()])))
    if failed:
        print("not imported: " + "; ".join(failed))
    check = subprocess.run([sys.executable, str(Path(__file__).with_name("check_sprites.py")), who], capture_output=True, text=True)
    print(check.stdout.rstrip())
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
