"""Task 28.1 round 5: a more handsome male character on RealVisXL V5.0 (owner feedback 2026-10-06: the woman
is approved, the man's face is not handsome enough). Text descriptions only; no real person's photo is used as
a face reference. Not shipped.

    venv-image\Scripts\python scripts\spike_style_realvis_male.py --out data\tmp\style-realvis-male [--tokens-only]
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import spike_style_realvis as rv  # noqa: E402
import torch  # noqa: E402
from PIL import Image, ImageDraw  # noqa: E402

STYLE = "editorial portrait photograph, soft studio light, deep focus, crisp sharp details, high resolution"
NEGATIVE = ("blurry, low resolution, cartoon, anime, 3d render, ugly, asymmetrical face, tan skin, boyish, baby "
            "face, round face, soft jaw, thin eyebrows, smile, watermark, deformed, extra person, glasses, jewelry, "
            "white shirt, jacket, beard")
VARIANTS = {
    "M1_sharp": ("handsome young Vietnamese man, chiseled V-shaped jawline, high cheekbones, strong straight dark "
                 "eyebrows, narrow almond eyes, intense gaze, defined lips, slim face, fair skin, "
                 "thick black hair with a textured side-swept fringe, plain black shirt, light grey background"),
    "M2_model": ("striking male model, young Vietnamese man, sharp jawline, long straight dark eyebrows, deep-set "
                 "narrow eyes, calm cool expression, full defined lips, slender face, pale flawless skin, thick "
                 "tousled black hair falling over the forehead, plain black shirt, plain light grey background"),
    "M3_idol": ("idol-like visual, handsome young Vietnamese man, refined masculine face, sharp straight "
                "eyebrows, clear almond eyes, soft intense gaze, defined lips, V-line chin, fair luminous skin, "
                "voluminous layered black hair with curtain fringe, plain black shirt, plain light grey background"),
}
SEEDS = (7, 21, 42, 99)


def sheet(out: Path) -> None:
    width = 480
    image = Image.new("RGB", (width * len(SEEDS), (width + 26) * len(VARIANTS)), "white")
    draw = ImageDraw.Draw(image)
    for row, variant in enumerate(VARIANTS):
        for column, seed in enumerate(SEEDS):
            tile = Image.open(out / f"{variant}_s{seed}.png").resize((width, width))
            image.paste(tile, (column * width, row * (width + 26) + 26))
        draw.text((8, row * (width + 26) + 6), f"{variant}  (seeds {', '.join(map(str, SEEDS))})", fill="black")
    image.save(out / "sheet_male.png")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", default="data/tmp/style-realvis-male")
    parser.add_argument("--tokens-only", action="store_true")
    args = parser.parse_args()
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    if args.tokens_only:
        from transformers import CLIPTokenizer
        folder = next((rv.ROOT / "models/image/hub/models--SG161222--RealVisXL_V5.0/snapshots").iterdir())
        tok = CLIPTokenizer.from_pretrained(folder, subfolder="tokenizer")
        for name, subject in VARIANTS.items():
            print(name, len(tok(f"{STYLE}, {subject}", truncation=False).input_ids))
        print("negative", len(tok(NEGATIVE, truncation=False).input_ids))
        return 0
    pipe = rv.build()
    log = []
    for variant, subject in VARIANTS.items():
        for seed in SEEDS:
            started = time.monotonic()
            image = pipe(prompt=f"{STYLE}, {subject}", negative_prompt=NEGATIVE, width=1024, height=1024,
                         num_inference_steps=35, guidance_scale=6.5,
                         generator=torch.Generator("cpu").manual_seed(seed)).images[0]
            image.save(out / f"{variant}_s{seed}.png")
            log.append({"variant": variant, "seed": seed, "sec": round(time.monotonic() - started, 1)})
            print(json.dumps(log[-1]), flush=True)
    sheet(out)
    print("done", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
