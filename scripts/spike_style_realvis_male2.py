"""Task 28.1 round 6: a young, fair, refined male face on RealVisXL V5.0 (round 5 overshot: older, tanned, frowning).
Text descriptions only; no real person's photo is used. Not shipped.

    venv-image\Scripts\python scripts\spike_style_realvis_male2.py --out data\tmp\style-realvis-male2 [--tokens-only]
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import spike_style_realvis_male as m  # noqa: E402

m.NEGATIVE = ("blurry, low resolution, cartoon, anime, 3d render, ugly, asymmetrical face, tan skin, dark skin, baby "
              "face, round face, frown, angry, muscular, mature, stubble, smile, watermark, deformed, extra person, "
              "glasses, jewelry, white shirt, jacket")
m.VARIANTS = {
    "N1_refined": ("handsome young Vietnamese man, 21 years old, refined delicate features, slim V-line face, fair "
                   "porcelain skin, straight dark eyebrows, soft almond eyes, calm gaze, soft lips, thick "
                   "tousled black hair with long fringe over the forehead, plain black shirt, light grey "
                   "background"),
    "N2_turned": ("handsome young Vietnamese man, 21 years old, refined delicate features, slim V-line face, fair "
                  "porcelain skin, relaxed straight eyebrows, almond eyes, head slightly turned looking off camera, "
                  "full soft lips, tousled black hair with long fringe, plain black shirt, light grey background"),
    "N3_soft": ("elegant young Vietnamese man with soft masculine beauty, pale flawless skin, slender neck, "
                "almond eyes, relaxed straight eyebrows, glossy rose lips, side-swept black hair with long bangs, "
                "head tilted, looking off camera, plain black shirt, light grey background"),
}

if __name__ == "__main__":
    sys.argv = [sys.argv[0], *(a for a in sys.argv[1:]), *(["--out", "data/tmp/style-realvis-male2"]
                if "--out" not in sys.argv else [])]
    sys.exit(m.main())
