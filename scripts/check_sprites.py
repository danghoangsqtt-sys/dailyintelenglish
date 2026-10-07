r"""Check a character's sprite pack against its calm__closed picture (Phase 32): is every picture the same canvas, the same body
and the same head position, so that switching pictures does not make the character jump?

    venv\Scripts\python scripts\check_sprites.py alex
    venv\Scripts\python scripts\check_sprites.py lina --folder D:\DataAdmin\Daily_Intel_English\data\library\sprites_inbox

Exit code 0 when every picture passes, 1 otherwise. An AI image editor redraws the whole picture, so the pictures are never identical
pixel for pixel; the limits below are what a smooth video needs:

  every picture      1280 x 1536, transparent corners, the top of the head within 6 px and the middle of the head within 10 px of the reference
  an expression      the torso edges (rows 55 to 90% of the figure) within 8 px, the silhouette below the head differs by at most 4%
  a gesture          the head zone silhouette differs by at most 4%, the top of the head within 6 px (the arms may differ)
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np
from PIL import Image

DEFAULT_FOLDER = Path(r"D:\DataAdmin\Daily_Intel_English\data\library\sprites_inbox")
SIZE = (1280, 1536)
TOP_LIMIT = 6
HEAD_SIDE_LIMIT = 10
EDGE_LIMIT = 8
SILHOUETTE_LIMIT = 4.0


def load(path: Path) -> np.ndarray:
    return np.asarray(Image.open(path).convert("RGBA"))


def bbox(alpha: np.ndarray) -> tuple[int, int, int, int]:
    ys, xs = np.where(alpha)
    return int(xs.min()), int(ys.min()), int(xs.max()), int(ys.max())


def torso_edges(alpha: np.ndarray, top: int, bottom: int) -> tuple[float, float]:
    """Mean left and right edge of the figure over the torso rows (55 to 90% of the figure's height)."""
    first, last = top + int((bottom - top) * 0.55), top + int((bottom - top) * 0.90)
    lefts, rights = [], []
    for y in range(first, last, 6):
        xs = np.where(alpha[y])[0]
        if len(xs):
            lefts.append(xs.min())
            rights.append(xs.max())
    return float(np.mean(lefts)), float(np.mean(rights))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("character")
    parser.add_argument("--folder", default=str(DEFAULT_FOLDER))
    parser.add_argument("--list-failed", action="store_true", help="print only the file names of the pictures that fail, one per line")
    parser.add_argument("--reference", default=None, help="compare with this file instead of <character>__calm__closed.png")
    args = parser.parse_args()
    folder, who = Path(args.folder), args.character.lower()
    reference_path = folder / (args.reference or f"{who}__calm__closed.png")
    if not reference_path.is_file():
        print(f"missing {reference_path}")
        return 1
    reference = load(reference_path)
    ref_alpha = reference[..., 3] > 20
    rx0, ry0, rx1, ry1 = bbox(ref_alpha)
    head_end = ry0 + int((ry1 - ry0) * 0.20)  # head and neck only (no shoulders, so raised arms do not count as head)
    ref_head_x = float(np.where(ref_alpha[:head_end])[1].mean())
    ref_left, ref_right = torso_edges(ref_alpha, ry0, ry1)
    quiet = args.list_failed
    failed_names: list[str] = []
    if not quiet:
        print(f"reference {reference_path.name}: top margin {ry0 / SIZE[1]:.1%}")
    if not quiet:
        print(f"{'file':34} {'top':>5} {'torso edges':>12} {'below-head diff%':>17} {'head diff%':>11}  result")
    failed = 0
    for path in sorted(folder.glob(f"{who}__*.png")):
        picture = Image.open(path)
        if picture.size != SIZE:
            if not quiet:
                print(f"{path.name:34} wrong canvas size {picture.size}, expected {SIZE}")
            failed += 1
            failed_names.append(path.name)
            continue
        data = load(path)
        alpha = data[..., 3] > 20
        corners = all(data[y, x, 3] == 0 for y in (0, -1) for x in (0, -1))
        x0, y0, x1, y1 = bbox(alpha)
        left, right = torso_edges(alpha, y0, y1)
        head_x = float(np.where(alpha[:head_end])[1].mean()) if alpha[:head_end].any() else -9999.0
        edge_shift = max(abs(left - ref_left), abs(right - ref_right))
        head_xor = (alpha[:head_end] ^ ref_alpha[:head_end]).sum() / max(1, ref_alpha[:head_end].sum()) * 100
        body_xor = (alpha[head_end:] ^ ref_alpha[head_end:]).sum() / max(1, ref_alpha[head_end:].sum()) * 100
        problems = []
        if not corners:
            problems.append("corners not transparent")
        if abs(y0 - ry0) > TOP_LIMIT:
            problems.append(f"head top moved {y0 - ry0:+d}px")
        if abs(head_x - ref_head_x) > HEAD_SIDE_LIMIT:
            problems.append(f"head moved sideways {head_x - ref_head_x:+.0f}px")
        if "gesture" in path.name:
            if head_xor > SILHOUETTE_LIMIT:
                problems.append(f"head differs {head_xor:.1f}%")
        else:
            if edge_shift > EDGE_LIMIT:
                problems.append(f"torso moved {edge_shift:.0f}px")
            if body_xor > SILHOUETTE_LIMIT:
                problems.append(f"body differs {body_xor:.1f}%")
        if problems and path.name != reference_path.name:
            failed += 1
            failed_names.append(path.name)
        if not quiet:
            print(f"{path.name:34} {y0 - ry0:+5d} {edge_shift:12.1f} {body_xor:17.1f} {head_xor:11.1f}  "
              f"{'OK' if not problems else '; '.join(problems)}")
    if quiet:
        print("\n".join(failed_names))
    else:
        print(f"\n{failed} picture(s) failed")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
