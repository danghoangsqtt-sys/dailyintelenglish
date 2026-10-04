r"""Task 23.1 spike: can the shots of one scene look like the same place? Not shipped.

Runs in venv-image (diffusers directly, model CPU offload; not the product worker):

    venv-image\Scripts\python scripts\spike_scene_consistency.py --part ab --out <dir>
    venv-image\Scripts\python scripts\spike_scene_consistency.py --part c  --out <dir>
    venv-image\Scripts\python scripts\spike_scene_consistency.py --part score --out <dir>

Variants (card .viepilot/phases/23-scene-library/tasks/task-23.1.md):
  a   ControlNet OpenPose + face IP (0.45), place text only (today)
  b3  a + scene-plate IP (ip-adapter-plus_sdxl_vit-h) at 0.3, masked to the background
  b5  the same at 0.5
  c   plate as init image (cropped for close kinds) + characters inpainted in their masks
"""

from __future__ import annotations

import argparse
import gc
import json
import os
import sqlite3
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
os.environ.setdefault("HF_HOME", str(ROOT / "models" / "image"))
sys.path.insert(0, str(ROOT))

import torch  # noqa: E402
from PIL import Image, ImageChops, ImageFilter  # noqa: E402

from app.services.visuals import geometry, recipes  # noqa: E402

SIZE = (1344, 768)
STEPS, CFG = 30, 6.0
FACE_W = "ip-adapter-plus-face_sdxl_vit-h.safetensors"
SCENE_W = "ip-adapter-plus_sdxl_vit-h.safetensors"
SCENES = [
    {"name": "Cafe", "place": "a cozy Vietnamese street cafe", "staging": "seated"},
    {"name": "Park", "place": "a green city park", "staging": "standing"},
]
SHOTS = [("single", 0, 101), ("single", 1, 102), ("duo_close", None, 103), ("duo_wide", None, 104)]
# Close kinds see a tighter part of the plate (c): (x0, y0, x1, y1) as fractions of the plate.
CROPS = {"single": (0.12, 0.18, 0.72, 0.86), "duo_close": (0.1, 0.15, 0.9, 0.9), "duo_wide": (0, 0, 1, 1)}


def characters() -> tuple[list[dict], list[Image.Image]]:
    db = sqlite3.connect(ROOT / "data" / "app.db")
    db.row_factory = sqlite3.Row
    people, faces = [], []
    for name in ("Lan", "Minh"):
        row = dict(db.execute("SELECT * FROM characters WHERE name = ?", (name,)).fetchone())
        people.append(row)
        path = db.execute("SELECT path FROM character_assets WHERE character_id = ? AND kind = 'face'",
                          (row["id"],)).fetchone()[0]
        faces.append(Image.open(ROOT / path).convert("RGB"))
    return people, faces


def shot_people(kind: str, scene: dict) -> list[dict]:
    return geometry.shot_people(kind, scene["staging"], SIZE)


def prompt_for(kind: str, who: int | None, people: list[dict], scene: dict) -> str:
    if kind == "single":
        return recipes.single_prompt(people[who], scene)
    return recipes.duo_prompt(people[0], people[1], scene, kind)


def person_mask(persons: list[dict], grow: int = 0) -> Image.Image:
    mask = Image.new("L", SIZE, 0)
    for person in persons:
        mask = ImageChops.lighter(mask, geometry.silhouette_mask(person["points"], SIZE, person["head_h"]))
    if grow:
        mask = mask.filter(ImageFilter.MaxFilter(grow | 1))
    return mask.point(lambda value: 255 if value > 20 else 0)


def base_parts():
    from diffusers import AutoencoderKL, ControlNetModel
    from huggingface_hub import snapshot_download

    base = snapshot_download("stabilityai/stable-diffusion-xl-base-1.0", allow_patterns=[
        "model_index.json", "scheduler/*", "tokenizer/*", "tokenizer_2/*", "text_encoder/config.json",
        "text_encoder/model.fp16.safetensors", "text_encoder_2/config.json", "text_encoder_2/model.fp16.safetensors",
        "unet/config.json", "unet/diffusion_pytorch_model.fp16.safetensors", "vae/config.json"])
    vae = AutoencoderKL.from_pretrained(snapshot_download(
        "madebyollin/sdxl-vae-fp16-fix", allow_patterns=["config.json", "diffusion_pytorch_model.safetensors"]),
        torch_dtype=torch.float16)
    controlnet = ControlNetModel.from_pretrained("xinsir/controlnet-openpose-sdxl-1.0", torch_dtype=torch.float16)
    return base, vae, controlnet


def load_adapters(pipe) -> None:
    pipe.load_ip_adapter(["h94/IP-Adapter", "h94/IP-Adapter"], subfolder=["sdxl_models", "sdxl_models"],
                         weight_name=[FACE_W, SCENE_W], image_encoder_folder="models/image_encoder")


def ip_args(kind: str, who: int | None, faces: list[Image.Image], plate: Image.Image, persons: list[dict],
            face_scale: float, scene_scale: float) -> dict:
    from diffusers.image_processor import IPAdapterMaskProcessor

    processor = IPAdapterMaskProcessor()
    if kind == "single":
        face_images, face_masks = [faces[who]], [Image.new("L", SIZE, 255)]
    else:
        left, right = geometry.half_masks(SIZE)
        face_images, face_masks = [faces[0], faces[1]], [left, right]
    background = ImageChops.invert(person_mask(persons, grow=31))
    face_tensor = processor.preprocess(face_masks, height=SIZE[1], width=SIZE[0])
    scene_tensor = processor.preprocess([background], height=SIZE[1], width=SIZE[0])
    return {
        "ip_adapter_image": [face_images, plate],
        "cross_attention_kwargs": {"ip_adapter_masks": [
            face_tensor.reshape(1, face_tensor.shape[0], SIZE[1], SIZE[0]),
            scene_tensor.reshape(1, 1, SIZE[1], SIZE[0])]},
        "scales": [face_scale, scene_scale],
    }


def part_ab(out: Path) -> None:
    from diffusers import EulerDiscreteScheduler, StableDiffusionXLControlNetPipeline

    people, faces = characters()
    base, vae, controlnet = base_parts()
    pipe = StableDiffusionXLControlNetPipeline.from_pretrained(
        base, vae=vae, controlnet=controlnet, torch_dtype=torch.float16, variant="fp16", add_watermarker=False)
    pipe.scheduler = EulerDiscreteScheduler.from_config(pipe.scheduler.config)
    pipe.set_progress_bar_config(disable=True)
    load_adapters(pipe)  # before the offload hooks, or the image encoder stays on the CPU
    pipe.enable_model_cpu_offload()
    black = Image.new("RGB", SIZE, "black")
    log = []
    for scene in SCENES:  # plates first: ControlNet off (scale 0, black pose), IP scales 0
        path = out / f"plate_{scene['name']}.png"
        if not path.exists():
            started = time.monotonic()
            pipe.set_ip_adapter_scale([0.0, 0.0])
            pipe(prompt=recipes.scene_preview_prompt(scene), negative_prompt=recipes.NEGATIVE, image=black,
                 ip_adapter_image=[[faces[0]], black],
                 controlnet_conditioning_scale=0.0, width=SIZE[0], height=SIZE[1], num_inference_steps=STEPS,
                 guidance_scale=CFG, generator=torch.Generator("cpu").manual_seed(7)).images[0].save(path)
            print("plate", scene["name"], round(time.monotonic() - started, 1), flush=True)
    for scene in SCENES:
        plate = Image.open(out / f"plate_{scene['name']}.png").convert("RGB")
        for kind, who, seed in SHOTS:
            persons = shot_people(kind, scene)
            pose = geometry.draw_people(persons, SIZE)
            for variant, scene_scale in (("a", 0.0), ("b3", 0.3), ("b5", 0.5)):
                path = out / f"{scene['name']}_{kind}_{who}_{variant}.png"
                if path.exists():
                    continue
                args = ip_args(kind, who, faces, plate, persons, 0.45, scene_scale)
                pipe.set_ip_adapter_scale(args.pop("scales"))
                torch.cuda.reset_peak_memory_stats()
                started = time.monotonic()
                pipe(prompt=prompt_for(kind, who, people, scene), negative_prompt=recipes.NEGATIVE, image=pose,
                     controlnet_conditioning_scale=1.0, width=SIZE[0], height=SIZE[1], num_inference_steps=STEPS,
                     guidance_scale=CFG, generator=torch.Generator("cpu").manual_seed(seed), **args).images[0].save(path)
                log.append({"file": path.name, "sec": round(time.monotonic() - started, 1),
                            "peak_vram_mb": round(torch.cuda.max_memory_allocated() / 2**20)})
                print(json.dumps(log[-1]), flush=True)
    (out / "log_ab.json").write_text(json.dumps(log, indent=1), encoding="utf-8")


def part_c(out: Path) -> None:
    from diffusers import EulerDiscreteScheduler, StableDiffusionXLControlNetInpaintPipeline

    people, faces = characters()
    base, vae, controlnet = base_parts()
    pipe = StableDiffusionXLControlNetInpaintPipeline.from_pretrained(
        base, vae=vae, controlnet=controlnet, torch_dtype=torch.float16, variant="fp16", add_watermarker=False)
    pipe.scheduler = EulerDiscreteScheduler.from_config(pipe.scheduler.config)
    pipe.set_progress_bar_config(disable=True)
    load_adapters(pipe)
    pipe.enable_model_cpu_offload()
    log = []
    for scene in SCENES:
        plate = Image.open(out / f"plate_{scene['name']}.png").convert("RGB")
        for kind, who, seed in SHOTS:
            path = out / f"{scene['name']}_{kind}_{who}_c.png"
            if path.exists():
                continue
            x0, y0, x1, y1 = CROPS[kind]
            init = plate.crop((round(x0 * SIZE[0]), round(y0 * SIZE[1]), round(x1 * SIZE[0]), round(y1 * SIZE[1])))
            init = init.resize(SIZE, Image.Resampling.LANCZOS)
            persons = shot_people(kind, scene)
            mask = person_mask(persons, grow=41)
            args = ip_args(kind, who, faces, plate, persons, 0.45, 0.0)
            pipe.set_ip_adapter_scale(args.pop("scales"))
            started = time.monotonic()
            image = pipe(prompt=prompt_for(kind, who, people, scene), negative_prompt=recipes.NEGATIVE, image=init,
                         mask_image=mask, control_image=geometry.draw_people(persons, SIZE), strength=1.0,
                         controlnet_conditioning_scale=1.0, width=SIZE[0], height=SIZE[1],
                         num_inference_steps=STEPS, guidance_scale=CFG,
                         generator=torch.Generator("cpu").manual_seed(seed), **args).images[0]
            feather = mask.filter(ImageFilter.GaussianBlur(6))
            Image.composite(image.resize(SIZE), init, feather).save(path)
            log.append({"file": path.name, "sec": round(time.monotonic() - started, 1)})
            print(json.dumps(log[-1]), flush=True)
    (out / "log_c.json").write_text(json.dumps(log, indent=1), encoding="utf-8")


def part_score(out: Path) -> None:
    """Background consistency: persons greyed out, ViT-H CLIP embeddings, mean pairwise cosine."""
    from huggingface_hub import snapshot_download
    from transformers import CLIPImageProcessor, CLIPVisionModelWithProjection

    folder = Path(snapshot_download("h94/IP-Adapter", allow_patterns=["models/image_encoder/*"])) / "models" / "image_encoder"
    model = CLIPVisionModelWithProjection.from_pretrained(folder, torch_dtype=torch.float16).to("cuda")
    processor = CLIPImageProcessor()
    results, sheet_rows = {}, []
    for scene in SCENES:
        for variant in ("a", "b3", "b5", "c"):
            embeds, row = [], []
            for kind, who, _ in SHOTS:
                path = out / f"{scene['name']}_{kind}_{who}_{variant}.png"
                if not path.exists():
                    continue
                image = Image.open(path).convert("RGB")
                row.append(image)
                grey = Image.new("RGB", SIZE, (128, 128, 128))
                masked = Image.composite(grey, image, person_mask(shot_people(kind, scene), grow=41))
                inputs = processor(images=masked, return_tensors="pt").to("cuda", torch.float16)
                with torch.no_grad():
                    embed = model(**inputs).image_embeds[0].float()
                embeds.append(embed / embed.norm())
            pairs = [float(embeds[i] @ embeds[j]) for i in range(len(embeds)) for j in range(i + 1, len(embeds))]
            results[f"{scene['name']}_{variant}"] = round(sum(pairs) / len(pairs), 4) if pairs else None
            sheet_rows.append((f"{scene['name']} {variant}  bg-sim {results[f'{scene['name']}_{variant}']}", row))
    (out / "scores.json").write_text(json.dumps(results, indent=1), encoding="utf-8")
    print(json.dumps(results, indent=1))
    from PIL import ImageDraw

    cw, chh, cap = 336, 192, 16
    sheet = Image.new("RGB", (cw * 5, (chh + cap) * len(sheet_rows)), "white")
    draw = ImageDraw.Draw(sheet)
    for r, (label, row) in enumerate(sheet_rows):
        scene_name = label.split()[0]
        plate = Image.open(out / f"plate_{scene_name}.png").convert("RGB").resize((cw, chh))
        sheet.paste(plate, (0, r * (chh + cap) + cap))
        for c, image in enumerate(row):
            sheet.paste(image.resize((cw, chh)), ((c + 1) * cw, r * (chh + cap) + cap))
        draw.text((4, r * (chh + cap) + 2), f"plate | {label}", fill="black")
    sheet.save(out / "contact.png")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--part", choices=["ab", "c", "score"], required=True)
    parser.add_argument("--out", required=True)
    args = parser.parse_args()
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    {"ab": part_ab, "c": part_c, "score": part_score}[args.part](out)
    gc.collect()
    return 0


if __name__ == "__main__":
    sys.exit(main())
