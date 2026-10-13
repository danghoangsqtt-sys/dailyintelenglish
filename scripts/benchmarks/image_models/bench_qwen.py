"""Phase 39 benchmark, Qwen side (run with `.venv-qwen`: diffusers 0.41 + gguf + bitsandbytes).

    .venv-qwen\\Scripts\\python scripts\\benchmarks\\image_models\\bench_qwen.py --engine qwen2512 [--only A1] [--tasks activity]
    engines: qwen2512 (Qwen-Image-2512, Apache 2.0), qwen-edit-2511 (character inserts, Apache 2.0),
             qwen21-turbo (Qwen-Image-2.1-Turbo, research licence: evaluation only, D111)

A 20B model does not fit a 12 GB card with its 7B text encoder, so each run has two phases, like the app's SDXL
"encoders=false" path: (1) the text encoder in 4-bit on the GPU encodes every prompt, then is freed; (2) the GGUF
transformer (block-level group offload when it does not fit) + VAE renders from the saved embeddings.
"""

from __future__ import annotations

import argparse
import gc
import json
import math
import sqlite3
import time
from pathlib import Path

from common import OUT, ROOT, VramPeak, bench_set, qwen_prompt, record

HUB = ROOT / "backend" / "ai" / "models" / "image" / "hub"
if not HUB.is_dir():  # before Phase 38.4 moves the folder
    HUB = ROOT / "models" / "image" / "hub"

ENGINES = {
    "qwen2512": {"repo": "Qwen/Qwen-Image-2512", "gguf": ("unsloth/Qwen-Image-2512-GGUF", "qwen-image-2512-Q4_K_S.gguf"),
                 "lora": ("lightx2v/Qwen-Image-2512-Lightning", "Qwen-Image-2512-Lightning-8steps-V1.0-bf16.safetensors"),
                 "steps": 8, "tasks": ("activity", "plate", "thumbnail")},
    "qwen-edit-2511": {"repo": "Qwen/Qwen-Image-Edit-2511", "text_repo": "Qwen/Qwen-Image-2512",
                       "gguf": ("unsloth/Qwen-Image-Edit-2511-GGUF", "qwen-image-edit-2511-Q4_K_S.gguf"),
                       "lora": ("lightx2v/Qwen-Image-Edit-2511-Lightning",
                                "Qwen-Image-Edit-2511-Lightning-8steps-V1.0-bf16.safetensors"),
                       "steps": 8, "tasks": ("character",)},
    "qwen21-turbo": {"repo": "Qwen/Qwen-Image-2.1-Turbo",
                     "gguf": ("unsloth/Qwen-Image-2.1-Turbo-GGUF", "qwen-image-2.1-turbo-Q8_0.gguf"),
                     "lora": None, "steps": 8, "tasks": ("activity", "plate", "thumbnail")},
}
LIGHTNING_SCHEDULER = {  # ModelTC/Qwen-Image-Lightning generate_with_diffusers.py (shift 3 used in distillation)
    "base_image_seq_len": 256, "base_shift": math.log(3), "invert_sigmas": False, "max_image_seq_len": 8192,
    "max_shift": math.log(3), "num_train_timesteps": 1000, "shift": 1.0, "shift_terminal": None,
    "stochastic_sampling": False, "time_shift_type": "exponential", "use_beta_sigmas": False,
    "use_dynamic_shifting": True, "use_exponential_sigmas": False, "use_karras_sigmas": False,
}


def snapshot(repo: str) -> Path:
    folder = HUB / f"models--{repo.replace('/', '--')}" / "snapshots"
    return next(folder.iterdir())


def hub_file(repo: str, name: str) -> Path:
    return snapshot(repo) / name


def characters() -> dict[str, dict]:
    connection = sqlite3.connect(f"file:{ROOT / 'data' / 'app.db'}?mode=ro", uri=True)
    connection.row_factory = sqlite3.Row
    found = {}
    for row in connection.execute("SELECT * FROM characters WHERE name IN ('Alex', 'Lina', 'Jack')"):
        character = dict(row)
        face = connection.execute("SELECT path FROM character_assets WHERE character_id = ? AND kind = 'face'",
                                  (character["id"],)).fetchone()
        character["face_path"] = str((ROOT / face["path"]).resolve()) if face else None
        found[character["name"]] = character
    return found


def pipeline_class(name: str, spec: dict):
    import diffusers

    if name == "qwen-edit-2511":
        return diffusers.QwenImageEditPlusPipeline
    if name == "qwen21-turbo":
        for candidate in ("QwenImage21Pipeline", "QwenImage2Pipeline"):
            if hasattr(diffusers, candidate):
                return getattr(diffusers, candidate)
        raise SystemExit("this diffusers has no Qwen-Image-2.1 pipeline (needs a newer diffusers)")
    return diffusers.QwenImagePipeline


def encode_all(name: str, spec: dict, jobs: list[dict], cast: dict) -> dict[str, tuple]:
    """Phase 1: the text encoder in 4-bit NF4 on the GPU; returns {id: (embeds, mask)} on the CPU."""
    import torch
    from diffusers import BitsAndBytesConfig as DiffusersBnb  # noqa: F401  (import check)
    from transformers import AutoModelForImageTextToText, BitsAndBytesConfig

    text_repo = snapshot(spec.get("text_repo", spec["repo"]))
    started = time.monotonic()
    text_encoder = AutoModelForImageTextToText.from_pretrained(
        text_repo / "text_encoder", quantization_config=BitsAndBytesConfig(
            load_in_4bit=True, bnb_4bit_quant_type="nf4", bnb_4bit_compute_dtype=torch.bfloat16),
        torch_dtype=torch.bfloat16, device_map="cuda")
    pipe = pipeline_class(name, spec).from_pretrained(snapshot(spec["repo"]), transformer=None, vae=None,
                                                      text_encoder=text_encoder, torch_dtype=torch.bfloat16)
    record(name, {"event": "text_encoder_ready", "load_s": round(time.monotonic() - started, 1)})
    embeds = {}
    for job in jobs:
        kwargs = {"prompt": job["prompt"], "device": "cuda"}
        if job.get("image") is not None:
            kwargs["image"] = [job["image"]]
        with VramPeak() as vram:
            tick = time.monotonic()
            with torch.no_grad():
                prompt_embeds, mask = pipe.encode_prompt(**kwargs)[:2]
            seconds = time.monotonic() - tick
        embeds[job["id"]] = (prompt_embeds.cpu(), None if mask is None else mask.cpu())
        record(name, {"event": "encode", "id": job["id"], "seconds": round(seconds, 2), "vram_peak_mib": vram.peak})
    del pipe, text_encoder
    gc.collect()
    torch.cuda.empty_cache()
    return embeds


def render_all(name: str, spec: dict, jobs: list[dict], embeds: dict, seeds: list[int], size: list[int]) -> None:
    import diffusers
    import torch
    from diffusers import FlowMatchEulerDiscreteScheduler, GGUFQuantizationConfig

    started = time.monotonic()
    model_class = diffusers.QwenImage21Transformer2DModel if name == "qwen21-turbo" else diffusers.QwenImageTransformer2DModel
    transformer = model_class.from_single_file(
        str(hub_file(*spec["gguf"])), quantization_config=GGUFQuantizationConfig(compute_dtype=torch.bfloat16),
        torch_dtype=torch.bfloat16, config=str(snapshot(spec["repo"])) if (snapshot(spec["repo"]) / "transformer").is_dir()
        else spec["repo"], subfolder="transformer")
    extra = {}
    if spec["lora"]:
        extra["scheduler"] = FlowMatchEulerDiscreteScheduler.from_config(LIGHTNING_SCHEDULER)
    pipe = pipeline_class(name, spec).from_pretrained(snapshot(spec["repo"]), transformer=transformer, text_encoder=None,
                                                      tokenizer=None, torch_dtype=torch.bfloat16, **extra)
    if spec["lora"]:
        pipe.load_lora_weights(str(hub_file(*spec["lora"])))
    free = torch.cuda.mem_get_info()[0] / 2**30
    weights = hub_file(*spec["gguf"]).stat().st_size / 2**30
    if weights + 2.5 < free:
        pipe.to("cuda")
        placement = "gpu"
    else:  # stream the transformer blocks from RAM; VAE stays on the GPU
        pipe.transformer.enable_group_offload(onload_device=torch.device("cuda"), offload_device=torch.device("cpu"),
                                              offload_type="block_level", num_blocks_per_group=2, use_stream=True,
                                              low_cpu_mem_usage=True)
        pipe.vae.to("cuda")
        placement = "group_offload"
    pipe.vae.enable_tiling()
    record(name, {"event": "transformer_ready", "placement": placement, "load_s": round(time.monotonic() - started, 1),
                  "gguf_gb": round(weights, 1)})
    for job in jobs:
        prompt_embeds, mask = embeds[job["id"]]
        for seed in seeds:
            path = OUT / name / f"{job['id']}_s{seed}.png"
            path.parent.mkdir(parents=True, exist_ok=True)
            kwargs = {"prompt_embeds": prompt_embeds.to("cuda"), "num_inference_steps": spec["steps"],
                      "generator": torch.Generator("cuda").manual_seed(seed)}
            if mask is not None:
                kwargs["prompt_embeds_mask"] = mask.to("cuda")
            if job.get("image") is not None:
                kwargs["image"] = [job["image"]]
            else:
                kwargs.update(width=size[0], height=size[1])
            if spec["lora"]:
                kwargs["true_cfg_scale"] = 1.0
            with VramPeak() as vram:
                tick = time.monotonic()
                with torch.no_grad():
                    image = pipe(**kwargs).images[0]
                seconds = time.monotonic() - tick
            if image.size != tuple(size):
                image = image.resize(tuple(size))
            image.save(path)
            record(name, {"id": job["id"], "task": job["task"], "seed": seed, "seconds": round(seconds, 1),
                          "vram_peak_mib": vram.peak, "prompt": job["prompt"], "path": str(path), "placement": placement})


def edit_all(name: str, spec: dict, jobs: list[dict], seeds: list[int], size: list[int]) -> None:
    """Edit-2511 (character inserts): the prompt encoding needs the pipeline's own preprocessing of the reference
    picture, so it runs in one phase: 4-bit text encoder resident on the GPU, transformer streamed from RAM."""
    import torch
    from diffusers import FlowMatchEulerDiscreteScheduler, GGUFQuantizationConfig, QwenImageTransformer2DModel
    from transformers import AutoModelForImageTextToText, BitsAndBytesConfig

    started = time.monotonic()
    text_encoder = AutoModelForImageTextToText.from_pretrained(
        snapshot(spec["text_repo"]) / "text_encoder", quantization_config=BitsAndBytesConfig(
            load_in_4bit=True, bnb_4bit_quant_type="nf4", bnb_4bit_compute_dtype=torch.bfloat16),
        torch_dtype=torch.bfloat16, device_map="cuda")
    transformer = QwenImageTransformer2DModel.from_single_file(
        str(hub_file(*spec["gguf"])), quantization_config=GGUFQuantizationConfig(compute_dtype=torch.bfloat16),
        torch_dtype=torch.bfloat16, config=spec["repo"], subfolder="transformer")
    pipe = pipeline_class(name, spec).from_pretrained(
        snapshot(spec["repo"]), transformer=transformer, text_encoder=text_encoder,
        tokenizer=snapshot(spec["text_repo"]) / "tokenizer" if not (snapshot(spec["repo"]) / "tokenizer").is_dir() else None,
        scheduler=FlowMatchEulerDiscreteScheduler.from_config(LIGHTNING_SCHEDULER), torch_dtype=torch.bfloat16)
    pipe.load_lora_weights(str(hub_file(*spec["lora"])))
    pipe.transformer.enable_group_offload(onload_device=torch.device("cuda"), offload_device=torch.device("cpu"),
                                          offload_type="block_level", num_blocks_per_group=2, use_stream=True,
                                              low_cpu_mem_usage=True)
    pipe.vae.to("cuda")
    pipe.vae.enable_tiling()
    record(name, {"event": "pipeline_ready", "placement": "te_4bit_gpu+group_offload",
                  "load_s": round(time.monotonic() - started, 1)})
    for job in jobs:
        for seed in seeds:
            path = OUT / name / f"{job['id']}_s{seed}.png"
            path.parent.mkdir(parents=True, exist_ok=True)
            with VramPeak() as vram:
                tick = time.monotonic()
                with torch.no_grad():
                    image = pipe(image=[job["image"]], prompt=job["prompt"], num_inference_steps=spec["steps"],
                                 true_cfg_scale=1.0, width=size[0], height=size[1],
                                 generator=torch.Generator("cuda").manual_seed(seed)).images[0]
                seconds = time.monotonic() - tick
            if image.size != tuple(size):
                image = image.resize(tuple(size))
            image.save(path)
            record(name, {"id": job["id"], "task": job["task"], "seed": seed, "seconds": round(seconds, 1),
                          "vram_peak_mib": vram.peak, "prompt": job["prompt"], "path": str(path)})


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--engine", choices=sorted(ENGINES), required=True)
    parser.add_argument("--only", default="")
    parser.add_argument("--tasks", default="")
    args = parser.parse_args()
    spec = ENGINES[args.engine]
    data = bench_set()
    items = [item for item in data["items"] if item["task"] in spec["tasks"]]
    if args.only:
        items = [item for item in items if item["id"] in args.only.split(",")]
    if args.tasks:
        items = [item for item in items if item["task"] in args.tasks.split(",")]
    cast = characters()
    from PIL import Image

    jobs = []
    for item in items:
        character = cast.get(item.get("character", ""))
        job = {"id": item["id"], "task": item["task"], "prompt": qwen_prompt(item, character)}
        if character:
            job["image"] = Image.open(character["face_path"]).convert("RGB")
        jobs.append(job)
    record(args.engine, {"event": "start", "items": [job["id"] for job in jobs]})
    if args.engine == "qwen-edit-2511":
        edit_all(args.engine, spec, jobs, data["seeds"], data["size"])
    else:
        embeds = encode_all(args.engine, spec, jobs, cast)
        render_all(args.engine, spec, jobs, embeds, data["seeds"], data["size"])
    (OUT / args.engine / "prompts.json").write_text(json.dumps({job["id"]: job["prompt"] for job in jobs}, indent=1),
                                                     encoding="utf-8")


if __name__ == "__main__":
    main()
