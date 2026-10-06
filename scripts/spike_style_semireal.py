"""Task 28.1 spike: semi-realistic picture style on SDXL base 1.0 (like the owner's channel banner).
Not shipped. Runs inside venv-image on the GPU, outside the app (no lease; Ollama holds no model).

    venv-image\\Scripts\\python scripts\\spike_style_semireal.py --out data\\tmp\\style-semireal

Recipes A (photo), B (editorial) and C (painted) x 4 items x 2 seeds, one contact sheet per item.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
os.environ.setdefault("HF_HOME", str(ROOT / "models" / "image"))

import torch  # noqa: E402
from diffusers import AutoencoderKL, EulerAncestralDiscreteScheduler, StableDiffusionXLPipeline  # noqa: E402
from huggingface_hub import snapshot_download  # noqa: E402
from PIL import Image, ImageDraw  # noqa: E402

SEEDS = (7, 21)
PRESENTER = ("young Vietnamese woman English teacher, long wavy brown hair, round black-framed glasses, "
             "brown eyes, plain cream blouse, plain beige trousers")
STUDENT = ("young Vietnamese man university student, short neat black hair, brown eyes, plain light blue "
           "shirt, plain black trousers")
STYLES = {
    "A_photo": ("photorealistic photo, natural soft window light, shallow depth of field, 85mm lens, "
                "warm beige tones, detailed skin"),
    "B_editorial": ("cinematic editorial photograph, warm color grading, soft key light, film grain, "
                    "natural skin texture"),
    "C_painted": ("semi-realistic digital painting, soft natural light, warm tones, believable faces, "
                  "fine detail, painterly"),
}
NEGATIVE = ("cartoon, anime, illustration, drawing, 3d render, cgi, plastic skin, oversmoothed, text, watermark, "
            "deformed, bad anatomy, extra fingers, deformed hands, extra person, crowd, hat, jacket, scarf")
ITEMS = {
    "presenter": (f"{PRESENTER}, portrait, friendly smile, in a bright cozy living room", (1024, 1024)),
    "student": (f"{STUDENT}, portrait, calm friendly face, in a bright cozy cafe", (1024, 1024)),
    "cafe_plate": ("a cozy cafe interior with wooden tables and large windows, wide view, empty scene, no people",
                   (1344, 768)),
    "duo_cafe": ("two Vietnamese people talking face to face, woman in plain cream blouse and round glasses on "
                 "the left, man in plain light blue shirt on the right, sitting at a table in a cozy cafe",
                 (1344, 768)),
}


def build() -> StableDiffusionXLPipeline:
    vae = AutoencoderKL.from_pretrained(snapshot_download("madebyollin/sdxl-vae-fp16-fix",
                                        allow_patterns=["config.json", "diffusion_pytorch_model.safetensors"]),
                                        torch_dtype=torch.float16)
    path = snapshot_download("stabilityai/stable-diffusion-xl-base-1.0", allow_patterns=[
        "model_index.json", "scheduler/*", "tokenizer/*", "tokenizer_2/*", "text_encoder/config.json",
        "text_encoder/model.fp16.safetensors", "text_encoder_2/config.json",
        "text_encoder_2/model.fp16.safetensors", "unet/config.json",
        "unet/diffusion_pytorch_model.fp16.safetensors", "vae/config.json"])
    pipe = StableDiffusionXLPipeline.from_pretrained(path, vae=vae, torch_dtype=torch.float16, variant="fp16",
                                                     use_safetensors=True, add_watermarker=False).to("cuda")
    pipe.scheduler = EulerAncestralDiscreteScheduler.from_config(pipe.scheduler.config)
    pipe.vae.enable_tiling()
    pipe.set_progress_bar_config(disable=True)
    return pipe


def contact_sheet(out: Path, item: str, size: tuple[int, int]) -> None:
    width = 480
    height = round(width * size[1] / size[0])
    sheet = Image.new("RGB", (width * len(SEEDS), (height + 26) * len(STYLES)), "white")
    draw = ImageDraw.Draw(sheet)
    for row, style in enumerate(STYLES):
        for column, seed in enumerate(SEEDS):
            image = Image.open(out / f"{item}_{style}_s{seed}.png").resize((width, height))
            sheet.paste(image, (column * width, row * (height + 26) + 26))
        draw.text((8, row * (height + 26) + 6), f"{style}  (seeds {', '.join(map(str, SEEDS))})", fill="black")
    sheet.save(out / f"sheet_{item}.png")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", default=str(ROOT / "data" / "tmp" / "style-semireal"))
    args = parser.parse_args()
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    pipe = build()
    log = []
    for item, (subject, size) in ITEMS.items():
        for style, words in STYLES.items():
            prompt = f"{words}, {subject}"
            tokens = len(pipe.tokenizer(prompt, truncation=False).input_ids)
            for seed in SEEDS:
                started = time.monotonic()
                image = pipe(prompt=prompt, negative_prompt=NEGATIVE, width=size[0], height=size[1],
                             num_inference_steps=30, guidance_scale=6.0,
                             generator=torch.Generator("cpu").manual_seed(seed)).images[0]
                image.save(out / f"{item}_{style}_s{seed}.png")
                log.append({"item": item, "style": style, "seed": seed, "tokens": tokens,
                            "sec": round(time.monotonic() - started, 1)})
                print(json.dumps(log[-1]), flush=True)
        contact_sheet(out, item, size)
    (out / "log.json").write_text(json.dumps(log, indent=1), encoding="utf-8")
    print("done", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
