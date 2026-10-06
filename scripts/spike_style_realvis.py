"""Task 28.1 round 4: the round 3b portraits (same prompts, negatives, seeds, sampler) on RealVisXL V5.0,
side by side with SDXL base 1.0 (the round 3b images). Not shipped. No face is copied.

    venv-image\Scripts\python scripts\spike_style_realvis.py --out data\tmp\style-realvis
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
sys.path.insert(0, str(Path(__file__).resolve().parent))
import spike_style_semireal3b as r3b  # noqa: E402
import torch  # noqa: E402
from diffusers import AutoencoderKL, EulerAncestralDiscreteScheduler, StableDiffusionXLPipeline  # noqa: E402
from huggingface_hub import snapshot_download  # noqa: E402
from PIL import Image, ImageDraw  # noqa: E402

REPO = "SG161222/RealVisXL_V5.0"


def build() -> StableDiffusionXLPipeline:
    vae = AutoencoderKL.from_pretrained(snapshot_download("madebyollin/sdxl-vae-fp16-fix",
                                        allow_patterns=["config.json", "diffusion_pytorch_model.safetensors"]),
                                        torch_dtype=torch.float16)
    # Only the fp16 files were downloaded, so the cached snapshot is partial: read its folder directly
    # (snapshot_download(local_files_only=True) insists on every file of the repository).
    path = next((ROOT / "models" / "image" / "hub" / "models--SG161222--RealVisXL_V5.0" / "snapshots").iterdir())
    pipe = StableDiffusionXLPipeline.from_pretrained(path, vae=vae, torch_dtype=torch.float16, variant="fp16",
                                                     use_safetensors=True, add_watermarker=False).to("cuda")
    pipe.scheduler = EulerAncestralDiscreteScheduler.from_config(pipe.scheduler.config)
    pipe.vae.enable_tiling()
    pipe.set_progress_bar_config(disable=True)
    return pipe


def compare_sheet(out: Path, base_dir: Path, item: str, style: str) -> None:
    """Row 1 SDXL base (round 3b), row 2 RealVisXL; one column per seed."""
    width = 480
    sheet = Image.new("RGB", (width * len(r3b.SEEDS), (width + 26) * 2), "white")
    draw = ImageDraw.Draw(sheet)
    for row, (label, folder) in enumerate((("SDXL base 1.0", base_dir), ("RealVisXL V5.0", out))):
        for column, seed in enumerate(r3b.SEEDS):
            image = Image.open(folder / f"{item}_{style}_s{seed}.png").resize((width, width))
            sheet.paste(image, (column * width, row * (width + 26) + 26))
        draw.text((8, row * (width + 26) + 6), f"{label}  {style}  (seeds {', '.join(map(str, r3b.SEEDS))})",
                  fill="black")
    sheet.save(out / f"compare_{item}_{style}.png")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", default="data/tmp/style-realvis")
    parser.add_argument("--base-dir", default="data/tmp/style-semireal3b")
    args = parser.parse_args()
    out, base_dir = Path(args.out), Path(args.base_dir)
    out.mkdir(parents=True, exist_ok=True)
    pipe = build()
    log = []
    for item, (subject, neg) in r3b.ITEMS.items():
        negative = f"{r3b.COMMON_NEG}, {neg}"
        for style, words in r3b.STYLES.items():
            prompt = f"{words}, {subject}"
            for seed in r3b.SEEDS:
                started = time.monotonic()
                image = pipe(prompt=prompt, negative_prompt=negative, width=r3b.SIZE[0], height=r3b.SIZE[1],
                             num_inference_steps=35, guidance_scale=6.5,
                             generator=torch.Generator("cpu").manual_seed(seed)).images[0]
                image.save(out / f"{item}_{style}_s{seed}.png")
                log.append({"item": item, "style": style, "seed": seed, "sec": round(time.monotonic() - started, 1)})
                print(json.dumps(log[-1]), flush=True)
            compare_sheet(out, base_dir, item, style)
    (out / "log.json").write_text(json.dumps(log, indent=1), encoding="utf-8")
    print("done", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
