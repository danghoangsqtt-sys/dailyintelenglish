"""Task 28.1 round 3: the owner's reference faces (female: long straight black hair, fair skin, white
outfit; male: messy black hair, pale sharp features, black outfit). Not shipped.

    venv-image\Scripts\python scripts\spike_style_semireal3.py --out data\tmp\style-semireal3
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

EDITORIAL = {
    "E1_bright": ("editorial fashion photograph, bright airy natural light, crisp sharp focus, clean fine details, "
                  "high resolution, soft warm tones"),
    "E2_warm": ("cinematic editorial photograph, warm golden glow, crisp sharp focus, rich fine details, "
                "high resolution, luminous skin"),
}
ILLUSTRATED = {
    "I_illustrated": ("semi-realistic digital illustration, manhwa style, sharp clean line art, detailed shading, "
                      "soft cinematic light, high resolution"),
}
NEG_PHOTO = ("blurry, out of focus, soft focus, bokeh, haze, noise, grain, low resolution, cartoon, anime, "
             "illustration, 3d render, plastic skin, ugly, asymmetrical face, wrinkles, blemishes, dull skin, text, "
             "watermark, deformed, bad anatomy, extra fingers, deformed hands, extra person, crowd, glasses, "
             "patterned clothes, jacket, hat")
NEG_ILL = ("blurry, low resolution, photo, 3d render, ugly, asymmetrical face, text, watermark, deformed, bad "
           "anatomy, extra fingers, deformed hands, extra person, crowd, glasses, patterned clothes")
WOMAN = ("beautiful young Vietnamese woman, very long straight silky black hair with soft side-parted bangs, fair "
         "luminous skin, soft delicate face, large dark eyes, gentle smile, natural coral lips, plain white "
         "button-up shirt")
MAN = ("handsome young Vietnamese man, messy layered black hair with bangs falling over his eyes, pale flawless "
       "skin, sharp jawline, slim narrow dark eyes, calm cool expression, plain black shirt")
ITEMS = {  # name -> (subject, size, styles, negative, seeds)
    "presenter": (f"{WOMAN}, portrait, bright cozy cafe", (1024, 1024), EDITORIAL, NEG_PHOTO, (7, 21, 42)),
    "student": (f"{MAN}, portrait, bright cozy cafe", (1024, 1024), EDITORIAL, NEG_PHOTO, (7, 21, 42)),
    "student_illustrated": (f"{MAN}, portrait, bright cafe background", (1024, 1024), ILLUSTRATED, NEG_ILL,
                            (7, 21, 42)),
    "duo_cafe": ("two attractive Vietnamese people talking face to face, woman with very long straight black hair "
                 "in a plain white shirt on the left, handsome man with messy black hair in a plain black shirt on "
                 "the right, sitting at a table in a bright cafe", (1344, 768), EDITORIAL, NEG_PHOTO, (7, 21)),
}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", default="data/tmp/style-semireal3")
    out = Path(parser.parse_args().out)
    out.mkdir(parents=True, exist_ok=True)
    pipe = base.build()
    log = []
    for item, (subject, size, styles, negative, seeds) in ITEMS.items():
        base.STYLES, base.SEEDS = styles, seeds
        for style, words in styles.items():
            prompt = f"{words}, {subject}"
            tokens = len(pipe.tokenizer(prompt, truncation=False).input_ids)
            for seed in seeds:
                started = time.monotonic()
                image = pipe(prompt=prompt, negative_prompt=negative, width=size[0], height=size[1],
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
