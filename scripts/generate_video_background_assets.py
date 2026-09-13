"""Generate or verify the deterministic Video Studio background template assets."""

from __future__ import annotations

import argparse
import sys
from collections.abc import Callable
from pathlib import Path

from PIL import Image, ImageDraw

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.core.constants import VIDEO_HEIGHT_STANDARD, VIDEO_WIDTH_STANDARD  # noqa: E402

TEMPLATE_DIR = PROJECT_ROOT / "frontend" / "static" / "video_backgrounds"
CanvasBuilder = Callable[[], Image.Image]


def _canvas(fill: tuple[int, int, int]) -> tuple[Image.Image, ImageDraw.ImageDraw]:
    """Create one RGB 16:9 canvas and its drawing context."""
    image = Image.new("RGB", (VIDEO_WIDTH_STANDARD, VIDEO_HEIGHT_STANDARD), fill)
    return image, ImageDraw.Draw(image)


def _midnight() -> Image.Image:
    """Plain dark navy — deliberately quiet so burned-in subtitles stay readable."""
    image, draw = _canvas((13, 15, 20))
    draw.rectangle((0, VIDEO_HEIGHT_STANDARD - 6, VIDEO_WIDTH_STANDARD, VIDEO_HEIGHT_STANDARD), fill=(124, 58, 237))
    return image


def _deep_purple() -> Image.Image:
    """Vertical dark-to-purple gradient."""
    image, draw = _canvas((0, 0, 0))
    top = (18, 14, 28)
    bottom = (54, 28, 90)
    for y in range(VIDEO_HEIGHT_STANDARD):
        ratio = y / (VIDEO_HEIGHT_STANDARD - 1)
        color = tuple(int(top[i] + (bottom[i] - top[i]) * ratio) for i in range(3))
        draw.line((0, y, VIDEO_WIDTH_STANDARD, y), fill=color)
    return image


def _charcoal_wave() -> Image.Image:
    """Dark charcoal with a subtle low-contrast arc accent, kept away from subtitle safe area."""
    image, draw = _canvas((17, 18, 22))
    for offset, shade, width in ((-160, (28, 30, 38), 90), (60, (24, 26, 33), 60)):
        draw.arc((420 + offset, -300, 1600 + offset, 500), 200, 340, fill=shade, width=width)
    return image


BUILDERS: dict[str, CanvasBuilder] = {
    "midnight": _midnight,
    "deep_purple": _deep_purple,
    "charcoal_wave": _charcoal_wave,
}


def generate_assets() -> None:
    """Write all deterministic template PNGs to the checked-in asset directory."""
    TEMPLATE_DIR.mkdir(parents=True, exist_ok=True)
    for template_id, builder in BUILDERS.items():
        builder().save(TEMPLATE_DIR / f"{template_id}.png", format="PNG", compress_level=9)


def check_assets() -> bool:
    """Return whether every checked-in PNG matches its deterministic generated pixels."""
    for template_id, builder in BUILDERS.items():
        asset_path = TEMPLATE_DIR / f"{template_id}.png"
        if not asset_path.is_file():
            print(f"MISSING: {asset_path.relative_to(PROJECT_ROOT)}")
            return False
        with Image.open(asset_path) as actual:
            expected = builder()
            if actual.mode != expected.mode or actual.size != expected.size:
                print(f"MISMATCH: {asset_path.relative_to(PROJECT_ROOT)} mode/size")
                return False
            if actual.tobytes() != expected.tobytes():
                print(f"MISMATCH: {asset_path.relative_to(PROJECT_ROOT)} pixels")
                return False
    print(f"OK: {len(BUILDERS)} video background template assets match deterministic sources")
    return True


def main() -> int:
    """Generate assets, or verify them when called with --check."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="verify assets without rewriting")
    args = parser.parse_args()
    if args.check:
        return 0 if check_assets() else 1
    generate_assets()
    print(f"Generated {len(BUILDERS)} video background template assets in {TEMPLATE_DIR}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
