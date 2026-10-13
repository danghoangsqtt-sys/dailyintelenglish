"""Phase 39 (D118): Qwen image models inside the image worker (runs in `.venv-image`; the app never imports it).

- `qwen21` — Qwen-Image-2.1-Turbo text-to-image (activity illustrations, topic pictures, scene plates). Two phases, the
  benchmark's proven path on the 12 GB card: the 4-bit text encoder encodes every prompt and is freed, then the Q8 GGUF
  transformer renders on the GPU (~31 s per 1344x768 picture).
- `qwen_edit` — Qwen-Image-Edit-2511 with the 4-step Lightning LoRA (character inserts from a face reference). One phase:
  4-bit text encoder on the GPU, the transformer streamed from RAM block by block (~56 s per picture).

Weights are read from the local Hugging Face cache only (`local_files_only`); a missing model raises `ModelMissing` so the
app falls back to RealVisXL instead of downloading tens of GB. Evidence: docs/operations/phase39-image-benchmark.md.
"""

from __future__ import annotations

import gc
import math
import time
from pathlib import Path
from typing import Any, Callable

MODELS = {
    "qwen21": {"repo": "Qwen/Qwen-Image-2.1-Turbo",
               "gguf": ("unsloth/Qwen-Image-2.1-Turbo-GGUF", "qwen-image-2.1-turbo-Q8_0.gguf")},
    "qwen_edit": {"repo": "Qwen/Qwen-Image-Edit-2511", "text_repo": "Qwen/Qwen-Image-2512",
                  "gguf": ("unsloth/Qwen-Image-Edit-2511-GGUF", "qwen-image-edit-2511-Q4_K_S.gguf"),
                  "lora": ("lightx2v/Qwen-Image-Edit-2511-Lightning",
                           "Qwen-Image-Edit-2511-Lightning-4steps-V1.0-bf16.safetensors"),
                  "steps": 4},
}
LIGHTNING_SCHEDULER = {  # ModelTC/Qwen-Image-Lightning (shift 3 used in distillation)
    "base_image_seq_len": 256, "base_shift": math.log(3), "invert_sigmas": False, "max_image_seq_len": 8192,
    "max_shift": math.log(3), "num_train_timesteps": 1000, "shift": 1.0, "shift_terminal": None,
    "stochastic_sampling": False, "time_shift_type": "exponential", "use_beta_sigmas": False,
    "use_dynamic_shifting": True, "use_exponential_sigmas": False, "use_karras_sigmas": False,
}


class ModelMissing(RuntimeError):
    """A Qwen model file is not in the local cache."""


def _snapshot(repo: str) -> Path:
    """The cached snapshot folder. Only the needed parts were downloaded (no transformer weights of the full repo, no
    assets), so `snapshot_download(local_files_only=True)` calls it incomplete; its `model_index.json` locates it."""
    from huggingface_hub import try_to_load_from_cache

    found = try_to_load_from_cache(repo, "model_index.json")
    if not isinstance(found, str):
        raise ModelMissing(f"{repo} is not installed")
    return Path(found).parent


def _file(repo: str, name: str) -> Path:
    from huggingface_hub import hf_hub_download

    try:
        return Path(hf_hub_download(repo, name, local_files_only=True))
    except Exception as exc:  # noqa: BLE001
        raise ModelMissing(f"{repo}/{name} is not installed") from exc


def installed(model: str) -> list[str]:
    """The missing pieces of `model` (empty when it can run)."""
    spec = MODELS[model]
    missing = []
    checks: list[Callable[[], Any]] = [lambda: _snapshot(spec["repo"]), lambda: _file(*spec["gguf"])]
    if "text_repo" in spec:
        checks.append(lambda: _snapshot(spec["text_repo"]))
    if "lora" in spec:
        checks.append(lambda: _file(*spec["lora"]))
    for check in checks:
        try:
            check()
        except ModelMissing as exc:
            missing.append(str(exc))
    if not missing and not (_snapshot(spec.get("text_repo", spec["repo"])) / "text_encoder").is_dir():
        missing.append(f"{spec.get('text_repo', spec['repo'])} text_encoder is not installed")
    return missing


def _text_encoder(torch: Any, folder: Path) -> Any:
    from transformers import AutoModelForImageTextToText, BitsAndBytesConfig

    return AutoModelForImageTextToText.from_pretrained(
        folder / "text_encoder", quantization_config=BitsAndBytesConfig(
            load_in_4bit=True, bnb_4bit_quant_type="nf4", bnb_4bit_compute_dtype=torch.bfloat16),
        dtype=torch.bfloat16, device_map="cuda")


def _dequantize_non_linear(model: Any) -> None:
    """diffusers 0.41 keeps GGUF BF16 tensors as raw bytes; GGUFLinear dequantizes its own weight, other modules read the
    bytes (Qwen-Image-2.1's text_norm: 8192 bytes for 4096 values). Dequantize those."""
    import torch
    from diffusers.quantizers.gguf.utils import GGUFLinear, GGUFParameter, dequantize_gguf_tensor

    for module in model.modules():
        if isinstance(module, GGUFLinear):
            continue
        for key, param in list(module.named_parameters(recurse=False)):
            if isinstance(param, GGUFParameter):
                setattr(module, key, torch.nn.Parameter(dequantize_gguf_tensor(param).to(torch.bfloat16),
                                                        requires_grad=False))


def _transformer(model: str, repo_folder: Path) -> Any:
    import diffusers
    import torch

    spec = MODELS[model]
    cls = diffusers.QwenImage21Transformer2DModel if model == "qwen21" else diffusers.QwenImageTransformer2DModel
    transformer = cls.from_single_file(
        str(_file(*spec["gguf"])), quantization_config=diffusers.GGUFQuantizationConfig(compute_dtype=torch.bfloat16),
        torch_dtype=torch.bfloat16, config=str(repo_folder), subfolder="transformer", local_files_only=True)
    if model == "qwen21":
        _dequantize_non_linear(transformer)
    return transformer


def _free(torch: Any) -> None:
    gc.collect()
    torch.cuda.empty_cache()


def generate_qwen21(torch: Any, items: list[dict[str, Any]], progress: Callable[[str], None]) -> dict[str, Any]:
    import diffusers

    folder = _snapshot(MODELS["qwen21"]["repo"])
    started = time.monotonic()
    text_encoder = _text_encoder(torch, folder)
    pipe = diffusers.QwenImage21Pipeline.from_pretrained(folder, transformer=None, vae=None, text_encoder=text_encoder,
                                                         torch_dtype=torch.bfloat16, local_files_only=True)
    embeds = []
    with torch.no_grad():
        for item in items:
            prompt_embeds, mask = pipe.encode_prompt(prompt=item["prompt"], device="cuda")[:2]
            embeds.append((prompt_embeds.cpu(), None if mask is None else mask.cpu()))
    del pipe, text_encoder
    _free(torch)
    encode_sec = time.monotonic() - started
    progress(f"encoded {len(items)} prompts")

    transformer = _transformer("qwen21", folder)
    pipe = diffusers.QwenImage21Pipeline.from_pretrained(folder, transformer=transformer, text_encoder=None,
                                                         tokenizer=None, torch_dtype=torch.bfloat16, local_files_only=True)
    pipe.to("cuda")
    pipe.vae.enable_tiling()
    load_sec = time.monotonic() - started - encode_sec
    results = []
    for index, (item, (prompt_embeds, mask)) in enumerate(zip(items, embeds, strict=True), start=1):
        tick = time.monotonic()
        kwargs = {"prompt_embeds": prompt_embeds.to("cuda"), "width": int(item["width"]), "height": int(item["height"]),
                  "generator": torch.Generator("cuda").manual_seed(int(item["seed"]))}
        if mask is not None:
            kwargs["prompt_embeds_mask"] = mask.to("cuda")
        with torch.no_grad():
            image = pipe(**kwargs).images[0]
        _save(image, item)
        results.append({"output_path": item["output_path"], "seconds": round(time.monotonic() - tick, 1)})
        progress(f"picture {index}/{len(items)}")
    del pipe, transformer
    _free(torch)
    return {"encode_sec": round(encode_sec, 1), "load_sec": round(load_sec, 1), "items": results}


def generate_qwen_edit(torch: Any, items: list[dict[str, Any]], progress: Callable[[str], None]) -> dict[str, Any]:
    import diffusers
    from PIL import Image

    spec = MODELS["qwen_edit"]
    folder, text_folder = _snapshot(spec["repo"]), _snapshot(spec["text_repo"])
    started = time.monotonic()
    extra = {}
    if not (folder / "tokenizer").is_dir():
        extra["tokenizer"] = text_folder / "tokenizer"
    pipe = diffusers.QwenImageEditPlusPipeline.from_pretrained(
        folder, transformer=_transformer("qwen_edit", folder), text_encoder=_text_encoder(torch, text_folder),
        scheduler=diffusers.FlowMatchEulerDiscreteScheduler.from_config(LIGHTNING_SCHEDULER), torch_dtype=torch.bfloat16,
        local_files_only=True, **extra)
    pipe.load_lora_weights(str(_file(*spec["lora"])))
    pipe.transformer.enable_group_offload(onload_device=torch.device("cuda"), offload_device=torch.device("cpu"),
                                          offload_type="block_level", num_blocks_per_group=1, use_stream=True,
                                          low_cpu_mem_usage=True)
    pipe.vae.to("cuda")
    pipe.vae.enable_tiling()
    load_sec = time.monotonic() - started
    results = []
    for index, item in enumerate(items, start=1):
        tick = time.monotonic()
        with Image.open(item["reference"]) as reference:
            reference_rgb = reference.convert("RGB")
        with torch.no_grad():
            image = pipe(image=[reference_rgb], prompt=item["prompt"], num_inference_steps=spec["steps"],
                         true_cfg_scale=1.0, width=int(item["width"]), height=int(item["height"]),
                         generator=torch.Generator("cuda").manual_seed(int(item["seed"]))).images[0]
        _save(image, item)
        results.append({"output_path": item["output_path"], "seconds": round(time.monotonic() - tick, 1)})
        progress(f"picture {index}/{len(items)}")
    del pipe
    _free(torch)
    return {"load_sec": round(load_sec, 1), "items": results}


def _save(image: Any, item: dict[str, Any]) -> None:
    size = (int(item["width"]), int(item["height"]))
    if image.size != size:
        image = image.resize(size)
    path = Path(item["output_path"])
    path.parent.mkdir(parents=True, exist_ok=True)
    image.save(path)


def validate(request: dict[str, Any]) -> tuple[str, list[dict[str, Any]]]:
    """Check a `qwen_generate` request without a GPU (unit-tested)."""
    model = request.get("model")
    if model not in MODELS:
        raise ValueError(f"model must be one of {sorted(MODELS)}")
    items = request.get("items")
    if not isinstance(items, list) or not items:
        raise ValueError("items must be a non-empty list")
    for item in items:
        for key in ("prompt", "seed", "width", "height", "output_path"):
            if key not in item:
                raise ValueError(f"item is missing {key!r}")
        if int(item["width"]) % 16 or int(item["height"]) % 16:
            raise ValueError("width and height must be multiples of 16")
        if model == "qwen_edit" and not item.get("reference"):
            raise ValueError("qwen_edit items need a reference picture")
    return model, items
