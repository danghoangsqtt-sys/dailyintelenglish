"""Task 28.1 round 2: beautiful faces, crisp editorial look (owner feedback 2026-10-06). Not shipped.

    venv-image\Scripts\python scripts\spike_style_semireal2.py --out data\tmp\style-semireal2
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import spike_style_semireal as base  # noqa: E402  (pipeline builder + contact sheet)
import torch  # noqa: E402

base.SEEDS = (7, 21)
base.STYLES = {
    "E1_bright": ("editorial fashion photograph, bright airy natural light, crisp sharp focus, clean fine details, "
                  "high resolution, soft warm tones"),
    "E2_warm": ("cinematic editorial photograph, warm golden glow, crisp sharp focus, rich fine details, "
                "high resolution, luminous skin"),
}
FACE_F = "beautiful, flawless clear skin, delicate features, large bright eyes"
FACE_M = "handsome, clear skin, delicate sharp features, bright eyes"
NEGATIVE = ("blurry, out of focus, soft focus, bokeh, haze, noise, grain, low resolution, cartoon, anime, "
            "illustration, 3d render, plastic skin, ugly, asymmetrical face, wrinkles, blemishes, dull skin, text, "
            "watermark, deformed, bad anatomy, extra fingers, deformed hands, extra person, crowd")
base.ITEMS = {
    "presenter_glasses": (f"{FACE_F}, young Vietnamese woman English teacher, long wavy brown hair, round "
                          "black-framed glasses, plain cream blouse, gentle smile, portrait, bright cozy room",
                          (1024, 1024)),
    "presenter_noglasses": (f"{FACE_F}, young Vietnamese woman English teacher, long wavy brown hair, "
                            "plain cream blouse, gentle smile, portrait, bright cozy room", (1024, 1024)),
    "student": (f"{FACE_M}, young Vietnamese man university student, short neat black hair, plain light blue "
                "shirt, calm friendly face, portrait, bright cafe", (1024, 1024)),
    "duo_cafe": (f"two attractive Vietnamese people talking face to face, {FACE_F}, woman with round black "
                 "glasses in plain cream blouse on the left, handsome man with no glasses in plain light blue "
                 "shirt on the right, sitting at a table in a bright cafe", (1344, 768)),
}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", default="data/tmp/style-semireal2")
    out = Path(parser.parse_args().out)
    out.mkdir(parents=True, exist_ok=True)
    pipe = base.build()
    log = []
    for item, (subject, size) in base.ITEMS.items():
        for style, words in base.STYLES.items():
            prompt = f"{words}, {subject}"
            tokens = len(pipe.tokenizer(prompt, truncation=False).input_ids)
            for seed in base.SEEDS:
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
