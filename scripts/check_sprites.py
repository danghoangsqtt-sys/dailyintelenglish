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

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from app.services.visuals.sprite_service import SIZE, Reference, measure  # noqa: E402  (the app's import uses the same rules)

DEFAULT_FOLDER = Path(r"D:\DataAdmin\Daily_Intel_English\data\library\sprites_inbox")
TIERS = {
    1: ["calm__closed", "calm__open", "smile__closed", "smile__open", "surprised__closed", "surprised__open", "blink"],
    2: ["laugh__closed", "laugh__open", "thinking__closed", "thinking__open", "worried__closed", "worried__open",
        "serious__closed", "serious__open"],
    3: [f"gesture-{name}" for name in ("talk", "point", "think", "open", "heart", "listen", "wave")],
}


def load(path: Path) -> np.ndarray:
    return np.asarray(Image.open(path).convert("RGBA"))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("character")
    parser.add_argument("--folder", default=str(DEFAULT_FOLDER))
    parser.add_argument("--expect", default="", help="tiers that must be complete, for example 1,2 or 1,2,3: a missing picture then fails")
    parser.add_argument("--list-failed", action="store_true", help="print only the file names of the pictures that fail, one per line")
    parser.add_argument("--reference", default=None, help="compare with this file instead of <character>__calm__closed.png")
    args = parser.parse_args()
    folder, who = Path(args.folder), args.character.lower()
    reference_path = folder / (args.reference or f"{who}__calm__closed.png")
    if not reference_path.is_file():
        print(f"missing {reference_path}")
        return 1
    reference = Reference(load(reference_path))
    quiet = args.list_failed
    failed_names: list[str] = []
    if not quiet:
        print(f"reference {reference_path.name}: top margin {reference.top / SIZE[1]:.1%}")
        print(f"{'file':34} {'top':>5} {'torso edges':>12} {'below-head diff%':>17} {'head diff%':>11}  result")
    failed = 0
    for path in sorted(folder.glob(f"{who}__*.png")):
        result = measure(load(path), reference, "gesture" in path.name)
        problems = result["problems"]
        if problems and path.name != reference_path.name:
            failed += 1
            failed_names.append(path.name)
        if quiet:
            continue
        if "top" not in result:  # the canvas itself is wrong: no numbers to show
            print(f"{path.name:34} {'; '.join(problems)}")
            continue
        print(f"{path.name:34} {result['top']:+5d} {result['edge_shift']:12.1f} {result['body_diff']:17.1f} {result['head_diff']:11.1f}  "
              f"{'OK' if not problems else '; '.join(problems)}")
    expected = [f"{who}__{name}.png" for tier in (args.expect.split(",") if args.expect else []) for name in TIERS[int(tier)]]
    for name in expected:
        if not (folder / name).is_file():
            failed += 1
            failed_names.append(name)
            if not quiet:
                print(f"{name:34} MISSING")
    if quiet:
        print("\n".join(failed_names))
    else:
        print(f"\n{failed} picture(s) failed")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
