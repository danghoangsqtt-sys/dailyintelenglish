"""Phase 33 (Task 33.3, D84/D86): turn a picture made with an outside AI into a talking-sprite slot picture.

The outside-AI recipe is the one proven in Phase 32 (its prompt files were removed in Phase 35): one full-length base
picture on a flat green background, and every other picture a small region edit (face, mouth, eyes or arms) of its parent.
This module only does pixels -- no database, no files:

- `prepare_base`: key out the green and fit the figure on the 1280 x 1536 canvas like the existing packs (feet on the
  floor, centred, the same height).
- `prepare_edit`: put a region edit back exactly where its parent was (phase correlation, as the Phase 32 web importer
  does); when the outside AI drew the whole picture again, fall back to fitting the figure's height and head silhouette.
- `parent_on_green`: the picture the owner attaches in the outside AI (the parent sprite on the same green, canvas size).
"""

from __future__ import annotations

import io

import numpy as np
from PIL import Image, ImageFilter, UnidentifiedImageError

CANVAS = (1280, 1536)
GREEN = (0, 177, 64)
FIGURE_TOP = 150  # the base figure's top row on the canvas (the existing packs: 102 for Alex, 234 for Lina)
EDGE_MARGIN = 24  # keep the base figure off the side edges (the sprite checks refuse a figure cut by an edge)
MAX_BYTES = 20 * 1024 * 1024
MAX_PIXELS = 40_000_000
MIN_HEIGHT = 512
REGISTRATION_LIMIT = 12.0  # mean grey difference over the overlap; above it the picture was drawn again
REDRAWN_SHARE = 0.30  # a region edit (mouth, face, eyes, arms) changes well under this share of the figure
HEAD_FRACTION = 0.20
# The packs show the figure from the top of the head to mid-thigh (Alex, Lina). A full-length upload -- feet clear of the
# bottom edge -- is cut at this share of its height (mid-thigh on a standing adult is about 4.5 of 7.5 head heights).
KNEE_UP_SHARE = 0.60


class UploadError(ValueError):
    """A picture that cannot become this slot's sprite; the message is shown to the owner on the slot card."""


def open_upload(content: bytes) -> Image.Image:
    """The uploaded bytes as a verified RGB/RGBA picture, or UploadError with the reason."""
    if not content:
        raise UploadError("the file is empty")
    if len(content) > MAX_BYTES:
        raise UploadError("the file is larger than 20 MB")
    try:
        with Image.open(io.BytesIO(content)) as probe:
            probe.verify()
        picture = Image.open(io.BytesIO(content))
        if picture.format not in ("PNG", "JPEG", "WEBP"):
            raise UploadError("use a PNG, JPEG or WebP picture")
        if picture.width * picture.height > MAX_PIXELS:
            raise UploadError("the picture has more than 40 megapixels")
        picture.load()
    except UploadError:
        raise
    except (UnidentifiedImageError, OSError, SyntaxError, Image.DecompressionBombError) as exc:
        raise UploadError("this file is not a readable picture") from exc
    if picture.height < MIN_HEIGHT:
        raise UploadError(f"the picture must be at least {MIN_HEIGHT} pixels tall")
    return picture.convert("RGBA") if picture.mode in ("RGBA", "LA", "P") else picture.convert("RGB")


def _has_transparency(picture: Image.Image) -> bool:
    return picture.mode == "RGBA" and bool((np.asarray(picture.getchannel("A")) < 250).any())


def key_out_green(rgb: Image.Image) -> Image.Image:
    """RGBA from a picture on a flat green background (the logic of the Phase 32 web importer, kept identical)."""
    data = np.asarray(rgb.convert("RGB")).astype(np.float32)
    green = data[..., 1] - np.maximum(data[..., 0], data[..., 2])
    border = np.concatenate([green[0], green[-1], green[:, 0], green[:, -1]])
    key = float(np.median(border))
    if key < 40:
        raise UploadError("the background is not green: ask the AI for a flat pure green #00B140 background")
    low, high = 0.30 * key, 0.70 * key
    alpha = 1.0 - np.clip((green - low) / (high - low), 0.0, 1.0)
    alpha[alpha < 0.04] = 0.0
    limit = np.maximum(data[..., 0], data[..., 2])
    near_background = np.asarray(Image.fromarray(((alpha < 0.5) * 255).astype(np.uint8)).filter(ImageFilter.MaxFilter(9))) > 0
    data[..., 1] = np.where(near_background | (alpha < 1.0), np.minimum(data[..., 1], limit), data[..., 1])
    return Image.fromarray(np.dstack([np.clip(data, 0, 255), alpha * 255]).astype(np.uint8), "RGBA")


def _figure(picture: Image.Image) -> Image.Image:
    figure = picture if _has_transparency(picture) else key_out_green(picture)
    alpha = np.asarray(figure.getchannel("A")) > 20
    if not alpha.any():
        raise UploadError("no figure was found in the picture")
    ys = np.where(alpha.any(axis=1))[0]
    top, bottom = int(ys.min()), int(ys.max())
    if bottom < figure.height - 3:  # the feet are in the picture: a full-length picture, cut to the packs' mid-thigh framing
        cut = top + int((bottom - top) * KNEE_UP_SHARE)
        figure = figure.copy()
        figure.paste((0, 0, 0, 0), (0, cut, figure.width, figure.height))
    return figure


def _place(figure: Image.Image, scale: float, dx: float, dy: float) -> Image.Image:
    coefficients = (1 / scale, 0, -dx / scale, 0, 1 / scale, -dy / scale)
    return figure.transform(CANVAS, Image.Transform.AFFINE, coefficients, resample=Image.Resampling.BICUBIC)


def prepare_base(picture: Image.Image) -> tuple[Image.Image, dict]:
    """The base picture (`calm__closed`): the figure scaled so its top sits at FIGURE_TOP and its feet on the floor, centred."""
    figure = _figure(picture)
    ys, xs = np.where(np.asarray(figure.getchannel("A")) > 20)
    height, width = ys.max() - ys.min() + 1, xs.max() - xs.min() + 1
    scale = min((CANVAS[1] - FIGURE_TOP) / height, (CANVAS[0] - 2 * EDGE_MARGIN) / width)
    dx = CANVAS[0] / 2 - scale * (xs.min() + xs.max()) / 2
    dy = CANVAS[1] - scale * (ys.max() + 1)
    return _place(figure, scale, dx, dy), {"method": "base fit", "scale": round(float(scale), 4)}


def parent_on_green(parent: Image.Image) -> Image.Image:
    """The picture the owner attaches in the outside AI: the parent sprite on flat green, canvas size, RGB."""
    flat = Image.new("RGBA", CANVAS, (*GREEN, 255))
    flat.alpha_composite(parent.convert("RGBA"))
    return flat.convert("RGB")


def _shift_by_phase(a: np.ndarray, b: np.ndarray) -> tuple[int, int, float]:
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
    return int(dx), int(dy), float(np.abs(a[y0:y1, x0:x1] - b[y0 - dy:y1 - dy, x0 - dx:x1 - dx]).mean())


def register(raw: Image.Image, base: Image.Image) -> tuple[float, int, int, float]:
    """(scale, dx, dy, error): the raw picture is the base scaled by `scale`, shifted by (dx, dy). Coarse to fine."""
    raw_grey = np.asarray(raw.convert("L"), dtype=np.float32)
    base_grey = base.convert("L")

    def try_scale(scale: float, step: int) -> tuple[int, int, float]:
        scaled = base_grey.resize((round(base.width * scale / step), round(base.height * scale / step)),
                                  Image.Resampling.BILINEAR)
        small = raw_grey if step == 1 else np.asarray(raw.convert("L").resize(
            (round(raw.width / step), round(raw.height / step)), Image.Resampling.BILINEAR), dtype=np.float32)
        return _shift_by_phase(np.asarray(scaled, dtype=np.float32), small)

    ratio = raw.height / base.height  # the outside AI often returns another size of the same framing
    coarse = min((try_scale(s, 4)[2], s) for s in np.arange(ratio * 0.90, ratio * 1.1001, ratio * 0.005))[1]
    fine = min((try_scale(s, 2)[2], s) for s in np.arange(coarse - 0.006 * ratio, coarse + 0.0061 * ratio, 0.001 * ratio))[1]
    best = min((try_scale(s, 1)[2], s) for s in np.arange(fine - 0.001 * ratio, fine + 0.00101 * ratio, 0.0002 * ratio))[1]
    dx, dy, error = try_scale(best, 1)
    return float(best), dx, dy, error


def _head_zone(alpha: np.ndarray) -> tuple[int, int]:
    ys = np.where((alpha > 20).any(axis=1))[0]
    top, bottom = int(ys.min()), int(ys.max())
    return top, top + int((bottom - top) * HEAD_FRACTION)


def _refine(raw_alpha: np.ndarray, ref_alpha: np.ndarray, scale: float, dx: float, dy: float) -> tuple[float, float, float]:
    """Nudge (scale, dx, dy) so the head-zone silhouettes overlap best, at half resolution."""
    top, end = _head_zone(ref_alpha)
    first_row = max(0, top - 8) // 2 * 2
    reference = ref_alpha[first_row:end + 8:2, ::2] > 20
    best = (-1.0, scale, dx, dy)
    half = Image.fromarray(((raw_alpha > 20) * 255).astype(np.uint8))
    for factor in (0.97, 0.98, 0.99, 1.0, 1.01, 1.02, 1.03):
        s = scale * factor
        mask = np.asarray(half.resize((max(1, round(half.width * s / 2)), max(1, round(half.height * s / 2))),
                                      Image.Resampling.BILINEAR)) > 127
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
                    best = (score, s, ox * 2.0, (oy + first_row // 2) * 2.0)
    return best[1], best[2], best[3]


def _changed_share(candidate: Image.Image, parent: Image.Image) -> float:
    """The share of the figure (either picture's figure) whose colour moved by more than 60 (RGB distance). Colour, not grey:
    a grey hoodie and a blue one can have the same grey level."""
    a = np.asarray(candidate.convert("RGBA")).astype(np.float32)
    b = np.asarray(parent.convert("RGBA")).astype(np.float32)
    figure = (a[..., 3] > 20) | (b[..., 3] > 20)
    if not figure.any():
        return 1.0
    rgb_a = a[..., :3] * (a[..., 3:] > 20)
    rgb_b = b[..., :3] * (b[..., 3:] > 20)
    return float((np.linalg.norm(rgb_a - rgb_b, axis=2)[figure] > 60).mean())


def prepare_edit(picture: Image.Image, parent: Image.Image, base: Image.Image) -> tuple[Image.Image, dict]:
    """A region edit of `parent` (an RGBA canvas sprite) put back on the canvas where the parent is; `base` (calm__closed) is
    the reference for the fallback fit when the outside AI drew the whole picture again."""
    if not _has_transparency(picture):
        source = parent_on_green(parent)
        scale, dx, dy, error = register(picture.convert("RGB"), source)
        if error <= REGISTRATION_LIMIT:
            green = tuple(int(v) for v in np.median(np.concatenate([np.asarray(picture.convert("RGB"))[0],
                                                                       np.asarray(picture.convert("RGB"))[-1]]), axis=0))
            canvas = picture.convert("RGB").transform(CANVAS, Image.Transform.AFFINE, (scale, 0, -dx, 0, scale, -dy),
                                                      resample=Image.Resampling.BICUBIC, fillcolor=green)
            keyed = key_out_green(canvas)
            changed = _changed_share(keyed, parent)
            # The mean difference is taken over the whole picture, which is mostly the same green: a picture drawn again
            # can pass it. A region edit changes only a small part of the figure itself.
            if changed <= REDRAWN_SHARE:
                return keyed, {"method": "region edit", "difference": round(error, 1), "changed": round(changed, 3)}
    figure = _figure(picture)
    raw_alpha = np.asarray(figure.getchannel("A"))
    ref_alpha = np.asarray(base.getchannel("A"))
    ys, xs = np.where(raw_alpha > 20)
    ry = np.where(ref_alpha > 20)[0]
    scale = (ry.max() - ry.min()) / (ys.max() - ys.min())
    dx = CANVAS[0] / 2 - scale * (xs.min() + xs.max()) / 2
    dy = CANVAS[1] - scale * ys.max()
    scale, dx, dy = _refine(raw_alpha, ref_alpha, scale, dx, dy)
    return _place(figure, scale, dx, dy), {"method": "redrawn, fitted to the base", "scale": round(float(scale), 4)}
