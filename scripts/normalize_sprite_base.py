r"""Put a character's base sprite on the standard canvas at the standard scale (Phase 32): no generation, only a resize and a paste.

    venv\Scripts\python scripts\normalize_sprite_base.py lina --source-head-px 349

The head (top of the hair to the chin) is scaled to the height of Alex's (338 px on the 1280 x 1536 canvas), so that two characters made
in different sessions have the same scale on screen. The figure is centred and sits on the BOTTOM edge of the canvas: the video places
every sprite on the bottom edge of the frame, so a shorter character (a shorter cut, a smaller body) then has her head lower than the
taller one, which is the natural height difference. The picture that was there is kept in data/assets_sprites/old/.
"""

from __future__ import annotations

import argparse
import shutil
import sys
from pathlib import Path

from PIL import Image

INBOX = Path(r"D:\DataAdmin\Daily_Intel_English\data\library\sprites_inbox")
OLD = Path(r"D:\DataAdmin\Daily_Intel_English\data\assets_sprites\old")
CANVAS = (1280, 1536)
TARGET_HEAD_PX = 338


def normalize(path: Path, source_head_px: float, target_head_px: float = TARGET_HEAD_PX) -> tuple[int, int, int]:
    """Rewrite `path` on the standard canvas; returns (new width, new height, top of the figure on the canvas)."""
    with Image.open(path) as opened:
        picture = opened.convert("RGBA")
    box = picture.getchannel("A").point(lambda v: 255 if v > 20 else 0).getbbox()
    figure = picture.crop(box)
    scale = target_head_px / source_head_px
    figure = figure.resize((round(figure.width * scale), round(figure.height * scale)), Image.Resampling.LANCZOS)
    canvas = Image.new("RGBA", CANVAS, (0, 0, 0, 0))
    left = (CANVAS[0] - figure.width) // 2
    top = CANVAS[1] - figure.height
    canvas.alpha_composite(figure, (left, top))
    canvas.save(path)
    return figure.width, figure.height, top


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("character")
    parser.add_argument("--source-head-px", type=float, required=True, help="height of the head (hair top to chin) in the base picture, in pixels")
    parser.add_argument("--head-px", type=float, default=TARGET_HEAD_PX)
    parser.add_argument("--folder", default=str(INBOX))
    args = parser.parse_args()
    path = Path(args.folder) / f"{args.character.lower()}__calm__closed.png"
    if not path.is_file():
        print(f"missing {path}")
        return 1
    OLD.mkdir(parents=True, exist_ok=True)
    backup = OLD / f"{path.stem}_original_before_normalize.png"
    if not backup.exists():
        shutil.copy2(path, backup)
    width, height, top = normalize(path, args.source_head_px, args.head_px)
    print(f"{path.name}: figure {width} x {height} on {CANVAS[0]} x {CANVAS[1]}, top of the figure at y={top}; original kept in {backup}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
