"""Task 20.2 (Phase 20 spike) -- local SDXL image worker process.

Runs INSIDE `venv-image/` (Python 3.14). Unlike Kokoro (21.1) and StyleTTS 2 (21.1b), the
image stack installs on this project's own interpreter, verified with a real install
(task-20.2.md F3). It is still a separate venv and a subprocess:
- torch is not in `requirements.txt`;
- the ~5.5 GB venv must stay out of the packaged .exe;
- a worker that exits returns 100% of its VRAM, which is what the Task 20.1 GPU lease
  relies on.
The parent (`scripts/spike_images.py`) holds that lease while this process is alive.

Protocol: the same line-delimited JSON over stdin/stdout as `styletts2_worker.py`. The
first line is a handshake (`ready` / `unavailable`), then there is one response per
request. A per-request failure never kills the worker.

    {"command": "load", "mode": "base" | "lightning", "lightning_steps": 4}
    {"command": "generate", "prompt": "...", "seed": 7, "width": 1344, "height": 768,
     "output_path": ".../ep1_base.png", "target_size": [1280, 720]}
    {"command": "load_ip_adapter"}
    {"command": "generate", ..., "ip_adapter_image": ".../ref.png", "ip_adapter_scale": 0.8}
    {"command": "stats"}
    {"command": "unload"}

Licence and watermark constraints (owner, 2026-09-30: free, commercial-safe with no
registration, no vendor watermark; task-20.2.md Amendment A). Every model fetched here is
`openrail++`, `mit` or `apache-2.0`:
- `stabilityai/stable-diffusion-xl-base-1.0`: `openrail++`;
- `madebyollin/sdxl-vae-fp16-fix`: `mit`;
- `ByteDance/SDXL-Lightning`: `openrail++`;
- `h94/IP-Adapter`: `apache-2.0`.

The SDXL pipeline is built with `add_watermarker=False`. diffusers 0.40.0 would otherwise
add an invisible watermark whenever the optional `invisible-watermark` package happens to be
installed (`pipeline_stable_diffusion_xl.py:276`). Every `load` response reports
`watermark_active` from the live pipeline object, so the report can show "false" rather
than assert it.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path
from typing import Any

# Same stdout isolation as kokoro_worker.py / styletts2_worker.py. huggingface_hub
# download progress, diffusers deprecation notices and transformers' torchvision fallback
# notice all print. Only `_write_protocol_line` may touch the real stdout.
_PROTOCOL_STDOUT = sys.stdout
sys.stdout = sys.stderr

PROJECT_ROOT = Path(__file__).resolve().parent.parent
MODEL_CACHE_DIR = PROJECT_ROOT / "models" / "image"
# Weights land in models/image/ (gitignored by the existing `models/*` rule), never the
# user's global HF cache. It must be set before huggingface_hub is imported.
os.environ.setdefault("HF_HOME", str(MODEL_CACHE_DIR))

BASE_REPO = "stabilityai/stable-diffusion-xl-base-1.0"
VAE_REPO = "madebyollin/sdxl-vae-fp16-fix"
LIGHTNING_REPO = "ByteDance/SDXL-Lightning"
IP_ADAPTER_REPO = "h94/IP-Adapter"

# Exact file lists, so only the fp16 PyTorch weights are fetched. The base repo also
# carries flax/onnx/openvino copies of every component (each 10+ GB for the UNet), and a
# plain snapshot would pull all of them. Sizes were checked on the Hub on 2026-09-30
# (task-20.2.md F2): UNet 5,135,149,760 + text encoders 246,144,152 + 1,389,382,176 bytes.
# The base VAE weights are skipped: the fp16-fix VAE replaces them.
BASE_CONFIG_FILES = [
    "model_index.json",
    "scheduler/*",
    "tokenizer/*",
    "tokenizer_2/*",
    "text_encoder/config.json",
    "text_encoder/model.fp16.safetensors",
    "text_encoder_2/config.json",
    "text_encoder_2/model.fp16.safetensors",
    "unet/config.json",
    "vae/config.json",
]
BASE_UNET_WEIGHTS = "unet/diffusion_pytorch_model.fp16.safetensors"
VAE_FILES = ["config.json", "diffusion_pytorch_model.safetensors"]  # 334,643,238 B
# Task 20.2e: any other SDXL fine-tune (e.g. cagliostrolab/animagine-xl-4.0) is fetched by
# folder, never the multi-GB single-file checkpoints such repos also keep at their root.
# Its VAE weights are skipped too: the fp16-fix VAE replaces them.
FINETUNE_PATTERNS = [
    "model_index.json",
    "scheduler/*",
    "tokenizer/*",
    "tokenizer_2/*",
    "text_encoder/*",
    "text_encoder_2/*",
    "unet/*",
    "vae/config.json",
]
SCHEDULERS = ("default", "euler_a")

# SDXL-Lightning's own README: "Use LoRA only if you are using non-SDXL base models.
# Otherwise use our UNet checkpoint for better quality." So the full UNet
# (5,135,149,736 B) is used, not the 394 MB LoRA. It also avoids diffusers' LoRA path,
# which needs `peft>=0.17.0` (diffusers/utils/constants.py MIN_PEFT_VERSION) as an extra
# dependency. The README also requires "trailing" timesteps, the same step count as the
# checkpoint, and CFG 0.
LIGHTNING_STEPS_ALLOWED = (2, 4, 8)

IP_ADAPTER_SUBFOLDER = "sdxl_models"
IP_ADAPTER_WEIGHT = "ip-adapter-plus-face_sdxl_vit-h.safetensors"  # 847,517,512 B
# The vit-h adapters use the ViT-H encoder at the repo ROOT's models/image_encoder
# (2,528,373,448 B), not sdxl_models/image_encoder (the bigG one). diffusers treats a value
# containing "/" as a repo-root path (loaders/ip_adapter.py:203-206).
IP_ADAPTER_IMAGE_ENCODER = "models/image_encoder"

# Task 20.2b (Apache-2.0, checked on the Hub 2026-09-30). 2,502,139,104-byte fp16 weights.
CONTROLNET_OPENPOSE_REPO = "xinsir/controlnet-openpose-sdxl-1.0"
# Task 20.2b: anime-oriented background removal (Apache-2.0), run as ONNX via onnxruntime,
# so no downloaded code executes (unlike BiRefNet's trust_remote_code loader).
ANIME_SEG_REPO = "skytnt/anime-seg"
ANIME_SEG_ONNX = "isnetis.onnx"  # 176,069,933 B
ANIME_SEG_SIZE = 1024
# Task 20.2c: "controlnet_inpaint" = pose-controlled M2 (a character painted into a scene).
PIPELINE_KINDS = ("text2img", "controlnet", "inpaint", "controlnet_inpaint")

BASE_DEFAULT_STEPS = 30
BASE_DEFAULT_GUIDANCE = 6.0


def _log(message: str) -> None:
    print(message, file=sys.stderr, flush=True)


def _write_protocol_line(payload: dict[str, Any]) -> None:
    _PROTOCOL_STDOUT.write(json.dumps(payload) + "\n")
    _PROTOCOL_STDOUT.flush()


def _rss_mb() -> float | None:
    try:
        import psutil
    except ImportError:
        return None
    return round(psutil.Process().memory_info().rss / (1024 * 1024), 1)


def _mb(num_bytes: int) -> float:
    return round(num_bytes / (1024 * 1024), 1)


class ImageWorker:
    def __init__(self, device: str) -> None:
        import torch

        self.torch = torch
        self.device = device
        # fp16 on the GPU (what the weights are and what fits 12 GB); fp32 on CPU, where
        # fp16 kernels are missing or slow. A CPU run exists only to exercise the plumbing.
        self.dtype = torch.float16 if device == "cuda" else torch.float32
        self.pipe: Any | None = None
        self.mode: str | None = None
        self.lightning_steps: int | None = None
        self.ip_adapter_loaded = False
        self.kind: str | None = None
        self.encoders = True
        self._embeds_cache: dict[str, Any] = {}
        self._anime_seg_session: Any | None = None
        self._last_size: tuple[int, int] | None = None

    # -- sources -----------------------------------------------------------------------

    @staticmethod
    def _resolve_base(mode: str, override: str | None, repo: str = BASE_REPO) -> Path:
        if override:
            return Path(override)
        from huggingface_hub import snapshot_download

        if repo != BASE_REPO:
            if mode != "base":
                raise ValueError("a custom base_repo supports mode 'base' only (Lightning is an SDXL-base UNet)")
            return Path(snapshot_download(repo, allow_patterns=FINETUNE_PATTERNS))
        patterns = list(BASE_CONFIG_FILES)
        if mode == "base":
            patterns.append(BASE_UNET_WEIGHTS)  # lightning brings its own UNet
        return Path(snapshot_download(BASE_REPO, allow_patterns=patterns))

    @staticmethod
    def _resolve_vae(override: str | None) -> Path:
        if override:
            return Path(override)
        from huggingface_hub import snapshot_download

        return Path(snapshot_download(VAE_REPO, allow_patterns=VAE_FILES))

    @staticmethod
    def _resolve_lightning_unet(steps: int, override: str | None) -> Path:
        if override:
            return Path(override)
        from huggingface_hub import hf_hub_download

        return Path(hf_hub_download(LIGHTNING_REPO, f"sdxl_lightning_{steps}step_unet.safetensors"))

    # -- commands ----------------------------------------------------------------------

    def load(self, request: dict[str, Any]) -> dict[str, Any]:
        if self.pipe is not None:
            raise RuntimeError(f"already loaded (mode={self.mode}); one mode per worker -- spawn another")
        mode = request.get("mode", "base")
        if mode not in ("base", "lightning"):
            raise ValueError(f"unknown mode {mode!r}")
        steps = int(request.get("lightning_steps", 4))
        if mode == "lightning" and steps not in LIGHTNING_STEPS_ALLOWED:
            raise ValueError(f"lightning_steps must be one of {LIGHTNING_STEPS_ALLOWED}")
        sources = request.get("sources") or {}
        kind = request.get("pipeline", "text2img")
        if kind not in PIPELINE_KINDS:
            raise ValueError(f"pipeline must be one of {PIPELINE_KINDS}")
        # Task 20.2b D20.2b-b: `encoders=false` builds the pipeline WITHOUT the two text
        # encoders (they are optional components). Renders then come from embeddings
        # saved earlier by `encode`, which is how UNet + ControlNet + IP layers fit the 12
        # GB card: SDXL 9.1 + IP 2.0 + ControlNet 2.5 GB would not.
        encoders = bool(request.get("encoders", True))
        base_repo = request.get("base_repo") or BASE_REPO
        scheduler_name = request.get("scheduler", "default")
        if scheduler_name not in SCHEDULERS:
            raise ValueError(f"scheduler must be one of {SCHEDULERS}")
        if mode == "lightning" and scheduler_name != "default":
            raise ValueError("Lightning needs its own trailing Euler scheduler")

        from diffusers import (
            AutoencoderKL,
            ControlNetModel,
            EulerAncestralDiscreteScheduler,
            EulerDiscreteScheduler,
            StableDiffusionXLControlNetInpaintPipeline,
            StableDiffusionXLControlNetPipeline,
            StableDiffusionXLInpaintPipeline,
            StableDiffusionXLPipeline,
            UNet2DConditionModel,
        )
        from safetensors.torch import load_file

        torch = self.torch
        started = time.monotonic()
        base_dir = self._resolve_base(mode, sources.get("base_dir"), base_repo)
        vae_dir = self._resolve_vae(sources.get("vae_dir"))
        download_seconds = time.monotonic() - started

        load_started = time.monotonic()
        # `variant="fp16"` only when the fp16 files exist. The Hub snapshot has them; a
        # local test pipeline saved without a variant does not.
        variant = "fp16" if (base_dir / "text_encoder" / "model.fp16.safetensors").is_file() else None
        vae = AutoencoderKL.from_pretrained(vae_dir, torch_dtype=self.dtype)
        components: dict[str, Any] = {"vae": vae}
        if mode == "lightning":
            unet_path = self._resolve_lightning_unet(steps, sources.get("lightning_unet"))
            # Owner-machine run 2026-09-30 (owner-runs/20260930): the original
            # `from_config(...).to(device, dtype)` first built the whole 2.57B-param UNet
            # with random **fp32** weights in CPU RAM (≈10.3 GB, the size of the fp32
            # UNet file), and failed with "The paging file is too small for this
            # operation to complete (os error 1455)". Measured here on a 0.9B-param
            # SDXL-shaped UNet: peak RSS 4186 MB the old way vs 745 MB this way. The
            # UNet is created on the meta device (no memory), then the fp16 Lightning
            # tensors are *assigned* straight from the safetensors file on the target
            # device.
            from accelerate import init_empty_weights

            with init_empty_weights():
                unet = UNet2DConditionModel.from_config(base_dir, subfolder="unet")
            unet.load_state_dict(load_file(str(unet_path), device=self.device), assign=True)
            unet = unet.to(self.device, self.dtype)
            components["unet"] = unet
        if kind in ("controlnet", "controlnet_inpaint"):
            components["controlnet"] = ControlNetModel.from_pretrained(
                sources.get("controlnet_dir") or request.get("controlnet_repo", CONTROLNET_OPENPOSE_REPO),
                torch_dtype=self.dtype,
            )
        if not encoders:
            components.update(text_encoder=None, text_encoder_2=None)
        pipeline_cls = {
            "text2img": StableDiffusionXLPipeline,
            "controlnet": StableDiffusionXLControlNetPipeline,
            "inpaint": StableDiffusionXLInpaintPipeline,
            "controlnet_inpaint": StableDiffusionXLControlNetInpaintPipeline,
        }[kind]
        pipe = pipeline_cls.from_pretrained(
            base_dir,
            torch_dtype=self.dtype,
            variant=variant,
            use_safetensors=True,
            add_watermarker=False,
            **components,
        ).to(self.device)
        if mode == "lightning":
            pipe.scheduler = EulerDiscreteScheduler.from_config(pipe.scheduler.config, timestep_spacing="trailing")
        elif scheduler_name == "euler_a":
            # Task 20.2e: the Animagine XL 4.0 model card's recommended sampler.
            pipe.scheduler = EulerAncestralDiscreteScheduler.from_config(pipe.scheduler.config)
        pipe.set_progress_bar_config(disable=True)
        if request.get("vae_tiling"):
            # Risk-table mitigation (task-20.2.md): the VAE decode at 1344x768 is a VRAM
            # spike; tiling trades a little speed for a much lower peak. Off by default so
            # the report shows whether it was actually needed.
            pipe.vae.enable_tiling()

        self.pipe, self.mode, self.lightning_steps = pipe, mode, steps if mode == "lightning" else None
        self.kind, self.encoders = kind, encoders
        return {
            "status": "ok",
            "mode": mode,
            "base_repo": base_repo if not sources.get("base_dir") else f"local:{sources['base_dir']}",
            "pipeline": kind,
            "encoders": encoders,
            "lightning_steps": self.lightning_steps,
            "download_or_cache_sec": round(download_seconds, 3),
            "load_sec": round(time.monotonic() - load_started, 3),
            "device": self.device,
            "dtype": str(self.dtype),
            "watermark_active": getattr(pipe, "watermark", None) is not None,
            "scheduler": type(pipe.scheduler).__name__,
            "timestep_spacing": pipe.scheduler.config.get("timestep_spacing"),
            "vram_allocated_mb": _mb(torch.cuda.memory_allocated()) if self.device == "cuda" else None,
            "rss_mb": _rss_mb(),
        }

    def load_ip_adapter(self, request: dict[str, Any]) -> dict[str, Any]:
        pipe = self._require_pipe()
        before = self.torch.cuda.memory_allocated() if self.device == "cuda" else 0
        started = time.monotonic()
        pipe.load_ip_adapter(
            request.get("repo", IP_ADAPTER_REPO),
            subfolder=request.get("subfolder", IP_ADAPTER_SUBFOLDER),
            weight_name=request.get("weight_name", IP_ADAPTER_WEIGHT),
            image_encoder_folder=request.get("image_encoder_folder", IP_ADAPTER_IMAGE_ENCODER),
        )
        self.ip_adapter_loaded = True
        after = self.torch.cuda.memory_allocated() if self.device == "cuda" else 0
        return {
            "status": "ok",
            "load_sec": round(time.monotonic() - started, 3),
            "vram_added_mb": _mb(after - before) if self.device == "cuda" else None,
            "rss_mb": _rss_mb(),
        }

    def generate(self, request: dict[str, Any]) -> dict[str, Any]:
        from PIL import Image, ImageOps

        pipe = self._require_pipe()
        torch = self.torch
        output_path = Path(request["output_path"])
        width, height = int(request.get("width", 1344)), int(request.get("height", 768))

        if self.mode == "lightning":
            # Lightning is distilled for exactly N steps at CFG 0 (README). Honouring a
            # different request would quietly measure a configuration nobody would ship.
            steps, guidance = self.lightning_steps, 0.0
        else:
            steps = int(request.get("steps", BASE_DEFAULT_STEPS))
            guidance = float(request.get("guidance_scale", BASE_DEFAULT_GUIDANCE))

        call: dict[str, Any] = {
            "width": width,
            "height": height,
            "num_inference_steps": steps,
            "guidance_scale": guidance,
            # A CPU generator makes the starting noise identical on every device, so a
            # CPU plumbing run and the owner's GPU run share seeds meaningfully.
            "generator": torch.Generator("cpu").manual_seed(int(request["seed"])),
        }
        ip_from_embeds = False
        if request.get("embeds_path"):
            # Task 20.2b: a render from embeddings saved by `encode` (no text encoders
            # needed in this process).
            embeds = self._embeds(request["embeds_path"])
            item = embeds["items"][int(request.get("embeds_index", 0))]
            for key in ("prompt_embeds", "pooled_prompt_embeds", "negative_prompt_embeds",
                        "negative_pooled_prompt_embeds"):
                if item.get(key) is not None and (embeds["do_cfg"] or not key.startswith("negative")):
                    call[key] = item[key].to(self.device, self.dtype)
            if embeds.get("ip_adapter_image_embeds") is not None:
                if not self.ip_adapter_loaded:
                    raise RuntimeError("embeds carry IP-Adapter image embeds but no IP-Adapter is loaded")
                pipe.set_ip_adapter_scale(float(request.get("ip_adapter_scale", 0.6)))
                call["ip_adapter_image_embeds"] = [e.to(self.device, self.dtype) for e in embeds["ip_adapter_image_embeds"]]
                ip_from_embeds = True
            negative_applied = bool(embeds["do_cfg"] and item.get("negative_prompt_embeds") is not None)
        else:
            if not self.encoders:
                raise RuntimeError("this pipeline was loaded with encoders=false; generate needs embeds_path")
            call["prompt"] = request["prompt"]
            # With CFG 0 (Lightning) diffusers never runs the unconditional branch, so a
            # negative prompt has NO effect. It is only passed when it can act, and the
            # response says whether it was applied (task-20.2.md: the "no text/logos"
            # rule must live in the positive prompt too).
            negative_applied = bool(request.get("negative_prompt")) and guidance > 1.0
            if negative_applied:
                call["negative_prompt"] = request["negative_prompt"]

        references = self._ip_references(request)
        if references is not None:
            if not self.ip_adapter_loaded:
                raise RuntimeError("ip_adapter_image(s) given but no IP-Adapter loaded -- send load_ip_adapter first")
            pipe.set_ip_adapter_scale(float(request.get("ip_adapter_scale", 0.6)))
            call["ip_adapter_image"] = references
        elif self.ip_adapter_loaded and not ip_from_embeds:
            raise RuntimeError("IP-Adapter is loaded; every generate call must pass ip_adapter_image")
        if request.get("ip_adapter_masks"):
            # Task 20.2h: one mask per face (white = where that face's identity applies), in
            # the order of `ip_adapter_images`, preprocessed as diffusers' IP-Adapter masking
            # expects: one tensor [1, n_faces, h, w] for the single loaded adapter.
            from diffusers.image_processor import IPAdapterMaskProcessor

            masks = []
            for mask_path in request["ip_adapter_masks"]:
                with Image.open(mask_path) as mask_image:
                    masks.append(mask_image.convert("L"))
            processed = IPAdapterMaskProcessor().preprocess(masks, height=height, width=width)
            call["cross_attention_kwargs"] = {
                "ip_adapter_masks": [processed.reshape(1, processed.shape[0], processed.shape[2], processed.shape[3])]
            }

        if self.kind == "controlnet":
            if not request.get("control_image"):
                raise RuntimeError("controlnet pipeline needs control_image")
            with Image.open(request["control_image"]) as control:
                call["image"] = control.convert("RGB")
            call["controlnet_conditioning_scale"] = float(request.get("controlnet_conditioning_scale", 1.0))
        elif self.kind in ("inpaint", "controlnet_inpaint"):
            if not (request.get("init_image") and request.get("mask_image")):
                raise RuntimeError(f"{self.kind} pipeline needs init_image and mask_image")
            with Image.open(request["init_image"]) as init, Image.open(request["mask_image"]) as mask:
                call["image"] = init.convert("RGB")
                call["mask_image"] = mask.convert("L")
            call["strength"] = float(request.get("strength", 0.99))
            if self.kind == "controlnet_inpaint":
                if not request.get("control_image"):
                    raise RuntimeError("controlnet_inpaint pipeline needs control_image")
                with Image.open(request["control_image"]) as control:
                    call["control_image"] = control.convert("RGB")
                call["controlnet_conditioning_scale"] = float(request.get("controlnet_conditioning_scale", 1.0))

        if self.device == "cuda":
            if self._last_size is not None and self._last_size != (width, height):
                # Task 20.2b finding F1 (owner run r3): a size switch in one worker grew the
                # allocator's reserve from 11.3 to 13.1 GB on the 12 GB card (Windows spilled
                # into shared memory, 2-3x slower). Hand the cached blocks back first.
                torch.cuda.empty_cache()
            torch.cuda.reset_peak_memory_stats()
        self._last_size = (width, height)
        started = time.monotonic()
        image = pipe(**call).images[0]
        wall_seconds = time.monotonic() - started

        output_path.parent.mkdir(parents=True, exist_ok=True)
        image.save(output_path, format="PNG")
        fitted_path = None
        if request.get("target_size"):
            target = (int(request["target_size"][0]), int(request["target_size"][1]))
            # "Cover" fit: SDXL's nearest 16:9 bucket is 1344x768 (1.75), and the
            # thumbnail is 1280x720 (1.78), so scale to cover, then centre-crop the
            # sliver. The same helper the app's template renderer uses (ImageOps.fit).
            fitted = ImageOps.fit(image, target, method=Image.Resampling.LANCZOS)
            fitted_path = output_path.with_name(f"{output_path.stem}_{target[0]}x{target[1]}.png")
            fitted.save(fitted_path, format="PNG")

        return {
            "status": "ok",
            "wall_time_sec": round(wall_seconds, 3),
            "steps": steps,
            "guidance_scale": guidance,
            "pipeline": self.kind,
            "from_embeds": bool(request.get("embeds_path")),
            "negative_prompt_applied": negative_applied,
            **self._prompt_tokens(call.get("prompt")),
            "native_size": list(image.size),
            "output_path": str(output_path),
            "fitted_path": str(fitted_path) if fitted_path else None,
            "peak_vram_allocated_mb": _mb(torch.cuda.max_memory_allocated()) if self.device == "cuda" else None,
            "peak_vram_reserved_mb": _mb(torch.cuda.max_memory_reserved()) if self.device == "cuda" else None,
            "rss_mb": _rss_mb(),
        }

    @staticmethod
    def _ip_references(request: dict[str, Any]) -> Any | None:
        """`ip_adapter_image` (one face, as before) or `ip_adapter_images` (Task 20.2h:
        several faces for the one loaded adapter -> diffusers' nested [[a, b]] form)."""
        from PIL import Image

        if request.get("ip_adapter_images"):
            images = []
            for path in request["ip_adapter_images"]:
                with Image.open(path) as image:
                    images.append(image.convert("RGB"))
            return [images]
        if request.get("ip_adapter_image"):
            with Image.open(request["ip_adapter_image"]) as image:
                return image.convert("RGB")
        return None

    def _prompt_tokens(self, prompt: str | None) -> dict[str, Any]:
        """Task 20.2f finding: CLIP reads 77 tokens and silently drops the rest (20.2c/20.2e
        prompts ran 87-105 tokens, losing expressions and style tags). Report it."""
        tokenizer = getattr(self.pipe, "tokenizer", None)
        if not prompt or tokenizer is None:
            return {}
        count = len(tokenizer(prompt, truncation=False).input_ids)
        return {"prompt_tokens": count, "prompt_truncated": count > tokenizer.model_max_length}

    def _embeds(self, path: str) -> dict[str, Any]:
        if path not in self._embeds_cache:
            # Written by this same worker script's `encode` in an earlier process of the
            # same spike run: a local, trusted file, hence weights_only=False.
            self._embeds_cache[path] = self.torch.load(path, map_location="cpu", weights_only=False)
        return self._embeds_cache[path]

    def encode(self, request: dict[str, Any]) -> dict[str, Any]:
        """Task 20.2b D20.2b-b: text (+ optional IP reference) -> embeddings on disk, so a
        later process can render with UNet + ControlNet only."""
        pipe = self._require_pipe()
        if not self.encoders:
            raise RuntimeError("encode needs a pipeline loaded with encoders=true")
        torch = self.torch
        do_cfg = self.mode != "lightning" and float(request.get("guidance_scale", BASE_DEFAULT_GUIDANCE)) > 1.0
        started = time.monotonic()
        ip_embeds = None
        with torch.no_grad():
            references = self._ip_references(request)
            if references is not None:
                if not self.ip_adapter_loaded:
                    raise RuntimeError("ip_adapter_image(s) given but no IP-Adapter loaded")
                # Task 20.2h: several faces for ONE adapter ([[a, b]]) -> embeds shaped
                # (batch, n_faces, tokens, dim); each face is later confined to its own
                # region by `ip_adapter_masks` at render time.
                ip_embeds = pipe.prepare_ip_adapter_image_embeds(references, None, self.device, 1, do_cfg)
            items = []
            for item in request["items"]:
                prompt_embeds, negative_embeds, pooled, negative_pooled = pipe.encode_prompt(
                    prompt=item["prompt"],
                    device=self.device,
                    num_images_per_prompt=1,
                    do_classifier_free_guidance=do_cfg,
                    negative_prompt=item.get("negative_prompt") if do_cfg else None,
                )
                items.append({
                    "prompt": item["prompt"],
                    **self._prompt_tokens(item["prompt"]),
                    "prompt_embeds": prompt_embeds.cpu(),
                    "pooled_prompt_embeds": pooled.cpu(),
                    "negative_prompt_embeds": negative_embeds.cpu() if do_cfg and negative_embeds is not None else None,
                    "negative_pooled_prompt_embeds": (
                        negative_pooled.cpu() if do_cfg and negative_pooled is not None else None
                    ),
                })
        payload = {"mode": self.mode, "do_cfg": do_cfg, "items": items,
                   "ip_adapter_image_embeds": [e.cpu() for e in ip_embeds] if ip_embeds is not None else None}
        output_path = Path(request["output_path"])
        output_path.parent.mkdir(parents=True, exist_ok=True)
        torch.save(payload, output_path)
        return {"status": "ok", "items": len(items), "do_cfg": do_cfg, "with_ip": ip_embeds is not None,
                "ip_faces": len(request.get("ip_adapter_images") or []) or (1 if request.get("ip_adapter_image") else 0),
                "output_path": str(output_path), "wall_time_sec": round(time.monotonic() - started, 3)}

    def remove_background(self, request: dict[str, Any]) -> dict[str, Any]:
        """Task 20.2b: transparent cut-out via skytnt/anime-seg (ONNX, CPU onnxruntime).

        Pre/post-processing follows the model author's own demo: letterbox to a
        1024 square, RGB/255 float32 NCHW in, a 0..1 mask out, then crop the letterbox
        back off and resize to the original size."""
        import numpy as np
        from PIL import Image

        if self._anime_seg_session is None:
            import onnxruntime

            model_path = request.get("model_path")
            if not model_path:
                from huggingface_hub import hf_hub_download

                model_path = hf_hub_download(ANIME_SEG_REPO, ANIME_SEG_ONNX)
            self._anime_seg_session = onnxruntime.InferenceSession(str(model_path), providers=["CPUExecutionProvider"])
        session = self._anime_seg_session
        started = time.monotonic()
        with Image.open(request["input_path"]) as source:
            rgb = source.convert("RGB")
        w0, h0 = rgb.size
        size = ANIME_SEG_SIZE
        if h0 > w0:
            h, w = size, max(1, int(size * w0 / h0))
        else:
            h, w = max(1, int(size * h0 / w0)), size
        ph, pw = size - h, size - w
        canvas = np.zeros((size, size, 3), dtype=np.float32)
        canvas[ph // 2:ph // 2 + h, pw // 2:pw // 2 + w] = (
            np.asarray(rgb.resize((w, h), Image.Resampling.LANCZOS), dtype=np.float32) / 255.0
        )
        net_input = canvas.transpose(2, 0, 1)[np.newaxis, :]
        mask = session.run(None, {session.get_inputs()[0].name: net_input})[0][0]
        mask = mask[0] if mask.ndim == 3 else mask
        mask = np.clip(mask[ph // 2:ph // 2 + h, pw // 2:pw // 2 + w], 0.0, 1.0)
        alpha = Image.fromarray((mask * 255).astype(np.uint8)).resize((w0, h0), Image.Resampling.LANCZOS)
        cutout = rgb.copy()
        cutout.putalpha(alpha)
        output_path = Path(request["output_path"])
        output_path.parent.mkdir(parents=True, exist_ok=True)
        cutout.save(output_path, format="PNG")
        alpha_arr = np.asarray(alpha)
        return {"status": "ok", "output_path": str(output_path), "wall_time_sec": round(time.monotonic() - started, 3),
                "foreground_fraction": round(float((alpha_arr > 127).mean()), 4),
                "soft_edge_fraction": round(float(((alpha_arr > 10) & (alpha_arr < 245)).mean()), 4)}

    def stats(self) -> dict[str, Any]:
        torch = self.torch
        return {
            "status": "ok",
            "loaded": self.pipe is not None,
            "mode": self.mode,
            "ip_adapter_loaded": self.ip_adapter_loaded,
            "device": self.device,
            "vram_allocated_mb": _mb(torch.cuda.memory_allocated()) if self.device == "cuda" else None,
            "vram_reserved_mb": _mb(torch.cuda.memory_reserved()) if self.device == "cuda" else None,
            "rss_mb": _rss_mb(),
        }

    def unload(self) -> dict[str, Any]:
        import gc

        was_loaded = self.pipe is not None
        self.pipe, self.mode, self.lightning_steps, self.ip_adapter_loaded = None, None, None, False
        self.kind, self.encoders, self._last_size = None, True, None
        self._embeds_cache.clear()
        gc.collect()
        if self.device == "cuda":
            self.torch.cuda.empty_cache()
        # The real release is the process exit; this is reported so the gap between
        # "unloaded" and "exited" is visible in the evidence.
        return {"status": "ok", "was_loaded": was_loaded, **{k: v for k, v in self.stats().items() if k != "status"}}

    def _require_pipe(self) -> Any:
        if self.pipe is None:
            raise RuntimeError("no model loaded -- send load first")
        return self.pipe


def _handle(worker: ImageWorker, request: dict[str, Any]) -> dict[str, Any]:
    command = request.get("command")
    handlers = {
        "load": worker.load,
        "load_ip_adapter": worker.load_ip_adapter,
        "generate": worker.generate,
        "encode": worker.encode,
        "remove_background": worker.remove_background,
    }
    if command in handlers:
        return handlers[command](request)
    if command == "stats":
        return worker.stats()
    if command == "unload":
        return worker.unload()
    raise ValueError(f"unknown command: {command!r}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="SDXL image worker (Task 20.2 spike)")
    parser.add_argument("--device", choices=["auto", "cuda", "cpu"], default="auto")
    parser.add_argument("--allow-cpu", action="store_true",
                        help="run on CPU instead of reporting unavailable (plumbing checks only; minutes per image)")
    args = parser.parse_args(argv)

    import torch

    cuda_ok = torch.cuda.is_available()
    base = {"torch": torch.__version__, "torch_cuda_build": torch.version.cuda, "cuda_available": cuda_ok}
    if args.device == "cpu" or (not cuda_ok and args.allow_cpu):
        device = "cpu"
    elif cuda_ok and args.device in ("auto", "cuda"):
        device = "cuda"
    else:
        # Covers a CPU-only torch build on Windows too (plain PyPI resolved `+cpu` for
        # venv-kokoro, per 21.1), so the spike can never measure CPU while claiming GPU.
        reason = "cpu_only_torch_build" if torch.version.cuda is None else "no_cuda_device"
        _write_protocol_line({"status": "unavailable", "reason": reason, **base})
        return 0

    worker = ImageWorker(device)
    _write_protocol_line({
        "status": "ready",
        "device": device,
        "gpu_name": torch.cuda.get_device_name(0) if device == "cuda" else None,
        "rss_mb": _rss_mb(),
        **base,
    })
    _log(f"image_worker: ready on {device}")

    for raw_line in sys.stdin:
        line = raw_line.strip()
        if not line:
            continue
        try:
            response = _handle(worker, json.loads(line))
        except Exception as exc:  # noqa: BLE001 -- a bad request must not kill the worker
            response = {"status": "error", "message": f"{type(exc).__name__}: {exc}"}
        _write_protocol_line(response)

    _log("image_worker: stdin closed, exiting")
    return 0


if __name__ == "__main__":
    sys.exit(main())
