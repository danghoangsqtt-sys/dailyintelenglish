"""Task 28.1 round 3: the owner's reference faces, editorial only (owner 2026-10-06). Not shipped.
Female: very long straight black hair, fair skin, all white. Male (4 photographic references): thick black
hair with a soft fringe to the brows, fair skin, sharp features, all black. No face is copied.

    venv-image\\Scripts\\python scripts\\spike_style_semireal3.py --out data\\tmp\\style-semireal3
    venv-image\\Scripts\\python scripts\\spike_style_semireal3.py --tokens-only
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
    "E1_bright": "editorial photograph, bright airy natural light, crisp sharp focus, high resolution",
    "E2_warm": "cinematic editorial photograph, warm golden light, crisp sharp focus, high resolution",
}
NEGATIVE = ("blurry, out of focus, soft focus, bokeh, haze, noise, grain, low resolution, cartoon, anime, "
            "illustration, 3d render, plastic skin, ugly, asymmetrical face, blemishes, dull skin, text, watermark, "
            "deformed, bad anatomy, extra fingers, deformed hands, extra person, glasses, jewelry, patterned clothes")
WOMAN = ("beautiful young Vietnamese woman, very long straight silky black hair, soft side bangs, fair luminous "
         "skin, delicate face, large dark eyes, gentle smile, plain white shirt")
MAN = ("handsome young Vietnamese man, thick glossy black hair, soft fringe to the eyebrows, fair clear skin, "
       "sharp jawline, almond dark eyes, calm gaze, plain black shirt")
ITEMS = {  # name -> (subject, size, seeds)
    "presenter": (f"{WOMAN}, portrait, bright cafe", (1024, 1024), (7, 21, 42, 99)),
    "student": (f"{MAN}, portrait, bright cafe", (1024, 1024), (7, 21, 42, 99)),
    "duo_cafe": ("two young Vietnamese people talking, beautiful woman with long straight black hair in plain white "
                 "shirt on the left, handsome man with black fringe hair in plain black shirt on the right, "
                 "table in a bright cafe", (1344, 768), (7, 21)),
}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", default="data/tmp/style-semireal3")
    parser.add_argument("--tokens-only", action="store_true")
    args = parser.parse_args()
    if args.tokens_only:
        from transformers import CLIPTokenizer
        from huggingface_hub import snapshot_download
        path = snapshot_download("stabilityai/stable-diffusion-xl-base-1.0", allow_patterns=["tokenizer/*"])
        tok = CLIPTokenizer.from_pretrained(path, subfolder="tokenizer")
        for item, (subject, _, _) in ITEMS.items():
            for style, words in STYLES.items():
                print(item, style, len(tok(f"{words}, {subject}", truncation=False).input_ids))
        print("negative", len(tok(NEGATIVE, truncation=False).input_ids))
        return 0
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    pipe = base.build()
    base.STYLES = STYLES
    log = []
    for item, (subject, size, seeds) in ITEMS.items():
        base.SEEDS = seeds
        for style, words in STYLES.items():
            prompt = f"{words}, {subject}"
            tokens = len(pipe.tokenizer(prompt, truncation=False).input_ids)
            for seed in seeds:
                started = time.monotonic()
                image = pipe(prompt=prompt, negative_prompt=NEGATIVE, width=size[0], height=size[1],
                             num_inference_steps=35, guidance_scale=6.5,
                             generator=torch.Generator("cpu").manual_seed(seed)).images[0]
                image.save(out / f"{item}_{style}_s{seed}.png")
                log.append({"item": item, "style": style, "seed": seed, "tokens": tokens,
                            "sec": round(time.monotonic() - started, 1)})
                print(json.dumps(log[-1]), flush=True)
        base.contact_sheet(out, item, size)
    (out / "log.json").write_text(json.dumps(log, indent=1), encoding="utf-8")
    print("done", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
