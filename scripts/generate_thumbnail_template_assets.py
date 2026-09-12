"""Generate or verify the five deterministic grayscale thumbnail template assets."""

from __future__ import annotations

import argparse
import sys
from collections.abc import Callable
from pathlib import Path

from PIL import Image, ImageDraw

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.core.constants import THUMBNAIL_HEIGHT_16X9, THUMBNAIL_WIDTH_16X9  # noqa: E402

TEMPLATE_DIR = PROJECT_ROOT / "frontend" / "static" / "thumbnail_templates"
CanvasBuilder = Callable[[], Image.Image]


def _canvas(shade: int) -> tuple[Image.Image, ImageDraw.ImageDraw]:
    """Create one grayscale 16:9 canvas and its drawing context."""
    image = Image.new("L", (THUMBNAIL_WIDTH_16X9, THUMBNAIL_HEIGHT_16X9), shade)
    return image, ImageDraw.Draw(image)


def _minimal_clean() -> Image.Image:
    image, draw = _canvas(236)
    draw.rectangle((0, 0, 34, THUMBNAIL_HEIGHT_16X9), fill=45)
    draw.rounded_rectangle((850, 78, 1190, 642), radius=48, fill=198)
    draw.ellipse((940, 160, 1100, 320), fill=118)
    draw.line((910, 415, 1130, 415), fill=88, width=18)
    draw.line((955, 475, 1085, 475), fill=138, width=18)
    return image


def _gradient_bold() -> Image.Image:
    image, draw = _canvas(0)
    for x in range(THUMBNAIL_WIDTH_16X9):
        shade = int(28 + (205 * x / (THUMBNAIL_WIDTH_16X9 - 1)))
        draw.line((x, 0, x, THUMBNAIL_HEIGHT_16X9), fill=shade)
    draw.polygon(((850, 0), (1280, 0), (1280, 430), (1080, 570)), fill=232)
    draw.polygon(((980, 720), (1280, 500), (1280, 720)), fill=92)
    return image


def _modern_split() -> Image.Image:
    image, draw = _canvas(44)
    draw.rectangle((640, 0, 1280, 720), fill=214)
    draw.polygon(((590, 0), (760, 0), (690, 720), (520, 720)), fill=132)
    draw.ellipse((825, 125, 1125, 425), fill=92)
    draw.rounded_rectangle((790, 500, 1160, 560), radius=30, fill=160)
    return image


def _dynamic_wave() -> Image.Image:
    image, draw = _canvas(18)
    for offset, shade, width in ((-220, 82, 72), (-80, 138, 54), (80, 205, 38)):
        draw.arc((520 + offset, 80, 1420 + offset, 980), 190, 335, fill=shade, width=width)
    draw.ellipse((1020, 80, 1190, 250), fill=188)
    draw.ellipse((1080, 140, 1130, 190), fill=250)
    return image


def _podcast_classic() -> Image.Image:
    image, draw = _canvas(224)
    draw.rounded_rectangle((70, 70, 1210, 650), radius=52, fill=194, outline=72, width=14)
    draw.ellipse((790, 155, 1110, 475), fill=68)
    draw.rounded_rectangle((925, 235, 975, 420), radius=25, fill=218)
    draw.arc((850, 235, 1050, 505), 15, 165, fill=218, width=18)
    draw.line((950, 505, 950, 565), fill=218, width=18)
    draw.line((885, 565, 1015, 565), fill=218, width=18)
    return image


BUILDERS: dict[str, CanvasBuilder] = {
    "minimal_clean": _minimal_clean,
    "gradient_bold": _gradient_bold,
    "modern_split": _modern_split,
    "dynamic_wave": _dynamic_wave,
    "podcast_classic": _podcast_classic,
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
    print(f"OK: {len(BUILDERS)} thumbnail template assets match deterministic sources")
    return True


def main() -> int:
    """Generate assets, or verify them when called with --check."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="verify assets without rewriting")
    args = parser.parse_args()
    if args.check:
        return 0 if check_assets() else 1
    generate_assets()
    print(f"Generated {len(BUILDERS)} thumbnail template assets in {TEMPLATE_DIR}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
