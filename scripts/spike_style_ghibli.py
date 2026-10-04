"""Style spike (2026-10-04) -- historical evidence code, not shipped. Task 20.10 (O11) removed the
studio-named wording and the franchise-named LoRA from the product; the "lora" variant here only
reproduces the 20.9 comparison.

Original purpose: owner's Ghibli-like cel-anime references vs the r3 watercolor recipe.

Runs inside venv-image on the GPU, outside the app (no lease; stop Ollama models first).
Compares, at identical seeds:
  A  sdxl  : SDXL base + new cel-anime recipe
  B  lora  : SDXL base + new recipe + ntc-ai "Studio Ghibli style" slider LoRA (MIT)
  C  anim  : Animagine XL 4.0 + Danbooru-tag version of the recipe (Open RAIL++-M)
  O  old   : SDXL base + the current r3 watercolor recipe (baseline)

    venv-image\\Scripts\\python scripts\\spike_style_ghibli.py --out owner-runs/style-ghibli
"""

from __future__ import annotations

import argparse
import gc
import json
import os
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
os.environ.setdefault("HF_HOME", str(ROOT / "models" / "image"))
sys.path.insert(0, str(ROOT))

import torch  # noqa: E402
from diffusers import AutoencoderKL, EulerAncestralDiscreteScheduler, StableDiffusionXLPipeline  # noqa: E402
from huggingface_hub import hf_hub_download, snapshot_download  # noqa: E402
from PIL import Image  # noqa: E402

from app.services.visuals import recipes  # noqa: E402

LAN = {"gender": "female", "age_group": "young", "ethnicity": "Vietnamese", "role": "university student",
       "hair": "long black hair", "eyes": "brown eyes", "top_color": "yellow", "top_item": "sweater",
       "bottom_color": "navy blue", "bottom_item": "jeans"}
MINH = {"gender": "male", "age_group": "young", "ethnicity": "Vietnamese", "role": "university student",
        "hair": "short neat black hair", "eyes": "brown eyes", "top_color": "light blue",
        "top_item": "slim-fit shirt", "bottom_color": "black", "bottom_item": "slim trousers"}
CAFE = {"place": "a cozy cafe", "staging": "seated"}
PATH = {"place": "a countryside path with wildflowers", "staging": "standing"}

OLD_NEGATIVE = (
    "3d render, photorealistic, photo, text, logo, watermark, blurry, deformed, bad anatomy, "
    "extra fingers, deformed hands, hand on face, backpack, hat, cap, jacket, coat, hoodie, "
    "scarf, pattern, stripes, plaid, print, multicolored clothes, layered clothes, crowd"
)


def old_recipe() -> list[tuple[str, str, tuple[int, int]]]:
    style = ("hand-painted 2D anime illustration, soft watercolor background, warm natural sunlight, "
             "gentle pastel palette, cozy whimsical atmosphere, clean line art")
    lan = recipes.character_phrase(LAN)
    minh = recipes.character_phrase(MINH)
    return [
        ("lan_portrait", f"{style}, {lan}, portrait, big happy smile", (1024, 1024)),
        ("minh_portrait", f"{style}, {minh}, portrait, calm friendly face", (1024, 1024)),
        ("duo_cafe", f"{style}, two Vietnamese people talking face to face, woman in plain yellow sweater "
                     f"on the left, man in plain light blue slim-fit shirt on the right, sitting at a table "
                     f"in a cozy cafe", (1344, 768)),
        ("duo_path", f"{style}, two Vietnamese people talking face to face, woman in plain yellow sweater "
                     f"on the left, man in plain light blue slim-fit shirt on the right, standing in a "
                     f"countryside path with wildflowers", (1344, 768)),
    ]


def new_recipe() -> list[tuple[str, str, tuple[int, int]]]:
    lan, minh = recipes.character_phrase(LAN), recipes.character_phrase(MINH)
    return [
        ("lan_portrait", recipes.sheet_prompt(LAN, "portrait_smile"), (1024, 1024)),
        ("minh_portrait", recipes.sheet_prompt(MINH, "portrait_calm"), (1024, 1024)),
        ("duo_cafe", recipes.duo_prompt(LAN, MINH, CAFE, "duo_wide"), (1344, 768)),
        ("duo_path", recipes.duo_prompt(LAN, MINH, PATH, "duo_wide"), (1344, 768)),
    ], lan, minh


ANIM_QUALITY = "masterpiece, high score, great score, absurdres"
ANIM_STYLE = "retro anime, 1990s \\(style\\), studio ghibli, cel shading, painted background, sunlight"
ANIM_NEGATIVE = ("lowres, bad anatomy, bad hands, text, error, missing finger, extra digits, fewer digits, "
                 "cropped, worst quality, low quality, low score, bad score, average score, signature, "
                 "watermark, username, blurry, watercolor, 3d, realistic")


def anim_recipe() -> list[tuple[str, str, tuple[int, int]]]:
    lan = "1girl, solo, vietnamese, long hair, black hair, brown eyes, yellow sweater, navy blue jeans"
    minh = "1boy, solo, vietnamese, short hair, black hair, brown eyes, light blue shirt, black pants"
    return [
        ("lan_portrait", f"{lan}, upper body, smile, open mouth, cafe, {ANIM_STYLE}, {ANIM_QUALITY}", (1024, 1024)),
        ("minh_portrait", f"{minh}, upper body, gentle smile, cafe, {ANIM_STYLE}, {ANIM_QUALITY}", (1024, 1024)),
        ("duo_cafe", "1girl, 1boy, vietnamese, black hair, girl yellow sweater, boy light blue shirt, "
                     f"sitting at table, cafe, looking at each other, smile, {ANIM_STYLE}, {ANIM_QUALITY}",
         (1344, 768)),
        ("duo_path", "1girl, 1boy, vietnamese, black hair, girl yellow sweater, boy light blue shirt, "
                     f"walking, countryside path, wildflowers, blue sky, cumulus clouds, {ANIM_STYLE}, "
                     f"{ANIM_QUALITY}", (1344, 768)),
    ]


def build(repo: str) -> StableDiffusionXLPipeline:
    vae = AutoencoderKL.from_pretrained(snapshot_download("madebyollin/sdxl-vae-fp16-fix",
                                        allow_patterns=["config.json", "diffusion_pytorch_model.safetensors"]),
                                        torch_dtype=torch.float16)
    if repo == "stabilityai/stable-diffusion-xl-base-1.0":
        path = snapshot_download(repo, allow_patterns=[
            "model_index.json", "scheduler/*", "tokenizer/*", "tokenizer_2/*", "text_encoder/config.json",
            "text_encoder/model.fp16.safetensors", "text_encoder_2/config.json",
            "text_encoder_2/model.fp16.safetensors", "unet/config.json",
            "unet/diffusion_pytorch_model.fp16.safetensors", "vae/config.json"])
        variant = "fp16"
    else:
        path = snapshot_download(repo, allow_patterns=[
            "model_index.json", "scheduler/*", "tokenizer/*", "tokenizer_2/*", "text_encoder/*",
            "text_encoder_2/*", "unet/*", "vae/config.json"])
        variant = None
    pipe = StableDiffusionXLPipeline.from_pretrained(path, vae=vae, torch_dtype=torch.float16, variant=variant,
                                                     use_safetensors=True, add_watermarker=False).to("cuda")
    pipe.scheduler = EulerAncestralDiscreteScheduler.from_config(pipe.scheduler.config)
    pipe.set_progress_bar_config(disable=True)
    return pipe


def run(pipe, label, items, negative, seeds, out: Path, log: list, steps=30, cfg=6.0) -> None:
    for name, prompt, (w, h) in items:
        tokens = len(pipe.tokenizer(prompt, truncation=False).input_ids)
        for seed in seeds:
            started = time.monotonic()
            image = pipe(prompt=prompt, negative_prompt=negative, width=w, height=h, num_inference_steps=steps,
                         guidance_scale=cfg, generator=torch.Generator("cpu").manual_seed(seed)).images[0]
            path = out / f"{name}_{label}_s{seed}.png"
            image.save(path)
            log.append({"variant": label, "item": name, "seed": seed, "tokens": tokens,
                        "truncated": tokens > 77, "sec": round(time.monotonic() - started, 1), "prompt": prompt})
            print(json.dumps(log[-1]), flush=True)


def sheet(out: Path, labels: list[str], seeds: list[int]) -> None:
    names = ["lan_portrait", "minh_portrait", "duo_cafe", "duo_path"]
    for seed in seeds:
        cell_w, cell_h = 448, 256
        canvas = Image.new("RGB", (cell_w * len(labels), cell_h * len(names)), "white")
        for col, label in enumerate(labels):
            for row, name in enumerate(names):
                path = out / f"{name}_{label}_s{seed}.png"
                if path.is_file():
                    with Image.open(path) as image:
                        image.thumbnail((cell_w, cell_h))
                        canvas.paste(image, (col * cell_w + (cell_w - image.width) // 2, row * cell_h))
        canvas.save(out / f"compare_s{seed}.png")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", default=str(ROOT / "owner-runs" / "style-ghibli"))
    parser.add_argument("--seeds", default="11,23")
    parser.add_argument("--variants", default="old,sdxl,lora,anim")
    parser.add_argument("--lora-weight", type=float, default=2.0)
    args = parser.parse_args()
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    seeds = [int(s) for s in args.seeds.split(",")]
    variants = args.variants.split(",")
    log: list = []
    items, _, _ = new_recipe()
    if {"old", "sdxl", "lora"} & set(variants):
        pipe = build("stabilityai/stable-diffusion-xl-base-1.0")
        if "old" in variants:
            run(pipe, "old", old_recipe(), OLD_NEGATIVE, seeds, out, log)
        if "sdxl" in variants:
            run(pipe, "sdxl", items, recipes.NEGATIVE, seeds, out, log)
        if "lora" in variants:
            pipe.load_lora_weights(hf_hub_download("ntc-ai/SDXL-LoRA-slider.Studio-Ghibli-style",
                                                   "Studio Ghibli style.safetensors"), adapter_name="ghibli")
            pipe.set_adapters(["ghibli"], adapter_weights=[args.lora_weight])
            run(pipe, "lora", items, recipes.NEGATIVE, seeds, out, log)
        del pipe
        gc.collect()
        torch.cuda.empty_cache()
    if "anim" in variants:
        pipe = build("cagliostrolab/animagine-xl-4.0")
        run(pipe, "anim", anim_recipe(), ANIM_NEGATIVE, seeds, out, log, steps=28, cfg=5.0)
    (out / "log.json").write_text(json.dumps(log, indent=1), encoding="utf-8")
    sheet(out, variants, seeds)
    return 0


if __name__ == "__main__":
    sys.exit(main())
