"""Task 28.1 round 3b: portraits only, closer to the owner's references (youthful idol-like faces, fair skin,
deep focus, the man's thick fringe), with a negative prompt per character. Not shipped. No face is copied.

    venv-image\Scripts\python scripts\spike_style_semireal3b.py --out data\tmp\style-semireal3b [--tokens-only]
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import spike_style_semireal as base  # noqa: E402
import torch  # noqa: E402

STYLES = {
    "E1_bright": "editorial portrait photograph, bright soft daylight, deep focus, crisp sharp details, high resolution",
    "E2_warm": "editorial portrait photograph, warm soft light, deep focus, crisp sharp details, high resolution",
}
COMMON_NEG = ("blurry, bokeh, depth of field, low resolution, cartoon, anime, 3d render, ugly, asymmetrical face, "
              "tan skin, mature, watermark, deformed, extra person, glasses, jewelry")
ITEMS = {  # name -> (subject, extra negative)
    "presenter": ("beautiful young Vietnamese woman, youthful idol-like soft face, fair porcelain skin, small V-line "
                  "face, large bright eyes, very long straight black hair, side bangs, gentle smile, plain white "
                  "buttoned shirt, minimal bright cafe",
                  "open collar, cleavage, black shirt, wavy hair"),
    "student": ("handsome young Vietnamese man, youthful idol-like face, fair porcelain skin, defined jawline, calm "
                "almond eyes, thick black two-block hair, long bangs covering the forehead, plain black shirt, "
                "minimal bright cafe",
                "undercut, shaved sides, pompadour, slicked back hair, white shirt, beard"),
}
SEEDS = (7, 21, 42, 99)
SIZE = (1024, 1024)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", default="data/tmp/style-semireal3b")
    parser.add_argument("--tokens-only", action="store_true")
    args = parser.parse_args()
    if args.tokens_only:
        from huggingface_hub import snapshot_download
        from transformers import CLIPTokenizer
        tok = CLIPTokenizer.from_pretrained(snapshot_download("stabilityai/stable-diffusion-xl-base-1.0",
                                            allow_patterns=["tokenizer/*"]), subfolder="tokenizer")
        for item, (subject, neg) in ITEMS.items():
            for style, words in STYLES.items():
                print(item, style, len(tok(f"{words}, {subject}", truncation=False).input_ids),
                      "neg", len(tok(f"{COMMON_NEG}, {neg}", truncation=False).input_ids))
        return 0
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    pipe = base.build()
    base.STYLES, base.SEEDS = STYLES, SEEDS
    log = []
    for item, (subject, neg) in ITEMS.items():
        negative = f"{COMMON_NEG}, {neg}"
        for style, words in STYLES.items():
            prompt = f"{words}, {subject}"
            for seed in SEEDS:
                started = time.monotonic()
                image = pipe(prompt=prompt, negative_prompt=negative, width=SIZE[0], height=SIZE[1],
                             num_inference_steps=35, guidance_scale=6.5,
                             generator=torch.Generator("cpu").manual_seed(seed)).images[0]
                image.save(out / f"{item}_{style}_s{seed}.png")
                log.append({"item": item, "style": style, "seed": seed, "sec": round(time.monotonic() - started, 1)})
                print(json.dumps(log[-1]), flush=True)
        base.contact_sheet(out, item, SIZE)
    (out / "log.json").write_text(json.dumps(log, indent=1), encoding="utf-8")
    print("done", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
