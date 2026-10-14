"""The local image worker process (runs INSIDE `.venv-image/`).

Phase 44 (D123): RealVisXL/SDXL, IP-Adapter, ControlNet, inpaint and the anime cut-out are gone. The worker draws with
Qwen (`qwen_runner.py`: Qwen-Image-2.1-Turbo for illustrations, plates and topic pictures; Qwen-Image-Edit-2511 for the
AI-scene thumbnails) and finds faces (UltraFace ONNX, MIT). It is a separate venv and a subprocess: torch stays out of
the app's `requirements.txt` and of the packaged .exe, and a worker that exits returns all of its VRAM, which is what
the GPU lease relies on.

Protocol: line-delimited JSON over stdin/stdout. The first line is a handshake (`ready` / `unavailable`), then one
response per request; a failed request never kills the worker.

    {"command": "qwen_generate", "model": "qwen21" | "qwen_edit", "items": [...], "detect_faces": true}
    {"command": "qwen_installed"}
    {"command": "count_faces", "input_path": ".../picture.png"}
    {"command": "stats"}
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path
from typing import Any

# Same stdout isolation as styletts2_worker.py (and the removed Kokoro worker). huggingface_hub
# download progress, diffusers deprecation notices and transformers' torchvision fallback
# notice all print. Only `_write_protocol_line` may touch the real stdout.
_PROTOCOL_STDOUT = sys.stdout
sys.stdout = sys.stderr

PROJECT_ROOT = Path(__file__).resolve().parents[3]  # backend/ai/image/image_worker.py -> project root
MODEL_CACHE_DIR = PROJECT_ROOT / "backend" / "ai" / "models" / "image"
# Weights land in backend/ai/models/image/ (gitignored by the `backend/ai/models/*` rule), never the
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
# Phase 28: RealVisXL V5.0 keeps fp32 shards (about 10 GB) next to the fp16 files the app uses (about 6.8 GB),
# so a fine-tune is fetched fp16-only first and falls back to FINETUNE_PATTERNS when the repo has no fp16 UNet.
FINETUNE_FP16_PATTERNS = [
    "model_index.json",
    "scheduler/*",
    "tokenizer/*",
    "tokenizer_2/*",
    "text_encoder/config.json",
    "text_encoder/model.fp16.safetensors",
    "text_encoder_2/config.json",
    "text_encoder_2/model.fp16.safetensors",
    "unet/config.json",
    "unet/diffusion_pytorch_model.fp16.safetensors",
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
# Task 23.2: the scene plate as a second, background-masked reference (spike 23.1 variant b).
# Same repo and ViT-H encoder, Apache-2.0; 847,517,512 B.
SCENE_IP_ADAPTER_WEIGHT = "ip-adapter-plus_sdxl_vit-h.safetensors"

# Task 20.2b (Apache-2.0, checked on the Hub 2026-09-30). 2,502,139,104-byte fp16 weights.
CONTROLNET_OPENPOSE_REPO = "xinsir/controlnet-openpose-sdxl-1.0"
# Task 20.2b: anime-oriented background removal (Apache-2.0), run as ONNX via onnxruntime,
# so no downloaded code executes (unlike BiRefNet's trust_remote_code loader).
ANIME_SEG_REPO = "skytnt/anime-seg"
ANIME_SEG_ONNX = "isnetis.onnx"  # 176,069,933 B
ANIME_SEG_SIZE = 1024

# Task 28.5: counting the people of a shot on photographs. A small face detector does it. UltraFace "version-RFB-320": MIT licence, 1,270,727 bytes, pinned to a commit
# and checked by SHA-256. Input 320 x 240, (pixel - 127) / 128; outputs `scores` (softmax, column 1 = face) and `boxes`
# (normalised corners). It runs on the CPU (onnxruntime).
FACE_MODEL_COMMIT = "0f9ca4a9fc80170fd505168fd1132b837141f7df"
FACE_MODEL_URL = (
    "https://raw.githubusercontent.com/Linzaer/Ultra-Light-Fast-Generic-Face-Detector-1MB/"
    f"{FACE_MODEL_COMMIT}/models/onnx/version-RFB-320.onnx"
)
FACE_MODEL_BYTES = 1_270_727
FACE_MODEL_SHA256 = "34cd7e60aeff28744c657de7a3dc64e872d506741de66987f3426f2b79f88017"
FACE_MODEL_PATH = MODEL_CACHE_DIR / "face" / "ultraface-rfb-320.onnx"
_FACE_SESSION: Any = None


def _face_model_ok(path: Path) -> bool:
    import hashlib

    return (path.is_file() and path.stat().st_size == FACE_MODEL_BYTES
            and hashlib.sha256(path.read_bytes()).hexdigest() == FACE_MODEL_SHA256)


def ensure_face_model(path: Path = FACE_MODEL_PATH) -> Path:
    """The pinned face model, downloaded once when it is missing (size and SHA-256 checked)."""
    if _face_model_ok(path):
        return path
    import urllib.request

    path.parent.mkdir(parents=True, exist_ok=True)
    partial = path.with_suffix(".part")
    with urllib.request.urlopen(FACE_MODEL_URL, timeout=60) as response:  # noqa: S310  (a pinned https URL)
        partial.write_bytes(response.read())
    if not _face_model_ok(partial):
        partial.unlink(missing_ok=True)
        raise RuntimeError("the face model download failed its size or SHA-256 check")
    partial.replace(path)
    return path


def detect_faces(image_path: str | Path, threshold: float = 0.7, iou: float = 0.3) -> list[list[float]]:
    """Faces of a picture as `[x1, y1, x2, y2, score]` in pixels (confidence cut, then greedy NMS)."""
    global _FACE_SESSION
    import numpy as np
    from PIL import Image

    if _FACE_SESSION is None:
        import onnxruntime

        options = onnxruntime.SessionOptions()
        options.log_severity_level = 3  # the model's initialisers trigger harmless warnings
        _FACE_SESSION = onnxruntime.InferenceSession(str(ensure_face_model()), options,
                                                     providers=["CPUExecutionProvider"])
    with Image.open(image_path) as source:
        rgb = source.convert("RGB")
    width, height = rgb.size
    net_input = ((np.asarray(rgb.resize((320, 240)), dtype=np.float32) - 127.0) / 128.0).transpose(2, 0, 1)[None]
    scores, boxes = _FACE_SESSION.run(None, {_FACE_SESSION.get_inputs()[0].name: net_input})
    confidence, corners = scores[0][:, 1], boxes[0]
    keep = confidence > threshold
    confidence, corners = confidence[keep], corners[keep]
    kept: list[list[float]] = []
    for index in np.argsort(-confidence):
        box = corners[index]
        overlaps = False
        for other in kept:
            x1, y1 = max(box[0], other[0]), max(box[1], other[1])
            x2, y2 = min(box[2], other[2]), min(box[3], other[3])
            inter = max(0.0, x2 - x1) * max(0.0, y2 - y1)
            union = (box[2] - box[0]) * (box[3] - box[1]) + (other[2] - other[0]) * (other[3] - other[1]) - inter
            if union > 0 and inter / union >= iou:
                overlaps = True
                break
        if not overlaps:
            kept.append([float(box[0]), float(box[1]), float(box[2]), float(box[3]), float(confidence[index])])
    return [[round(x1 * width, 1), round(y1 * height, 1), round(x2 * width, 1), round(y2 * height, 1), round(score, 3)]
            for x1, y1, x2, y2, score in kept]
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

    def count_faces(self, request: dict[str, Any]) -> dict[str, Any]:
        """Task 28.5: the faces a picture shows (Phase 43 frames the AI-scene thumbnails on them)."""
        started = time.monotonic()
        boxes = detect_faces(request["input_path"], float(request.get("threshold", 0.7)),
                             float(request.get("iou", 0.3)))
        return {"status": "ok", "faces": len(boxes), "boxes": boxes,
                "wall_time_sec": round(time.monotonic() - started, 3)}

    def stats(self) -> dict[str, Any]:
        torch = self.torch
        return {
            "status": "ok",
            "device": self.device,
            "vram_allocated_mb": _mb(torch.cuda.memory_allocated()) if self.device == "cuda" else None,
            "vram_reserved_mb": _mb(torch.cuda.memory_reserved()) if self.device == "cuda" else None,
            "rss_mb": _rss_mb(),
        }

    def qwen_generate(self, request: dict[str, Any]) -> dict[str, Any]:
        """Phase 39 (D118): a batch of Qwen pictures (`model` qwen21 | qwen_edit); the worker exits afterwards to return
        all VRAM."""
        import qwen_runner  # sibling module; only this worker (in .venv-image) imports it

        model, items = qwen_runner.validate(request)
        missing = qwen_runner.installed(model)
        if missing:
            return {"status": "unavailable", "reason": "model_missing", "model": model, "missing": missing}
        if self.device != "cuda":
            return {"status": "unavailable", "reason": "needs_gpu", "model": model}
        torch = self.torch
        torch.cuda.reset_peak_memory_stats()
        started = time.monotonic()
        run = qwen_runner.generate_qwen21 if model == "qwen21" else qwen_runner.generate_qwen_edit
        result = run(torch, items, lambda message: _log(f"qwen {model}: {message}"))
        if request.get("detect_faces"):  # Phase 43 (D122): the AI-scene thumbnail frames itself on the drawn faces
            for entry in result["items"]:
                entry["faces"] = detect_faces(entry["output_path"])
        return {"status": "ok", "model": model, **result, "wall_time_sec": round(time.monotonic() - started, 1),
                "vram_peak_mb": _mb(torch.cuda.max_memory_reserved())}

    def qwen_installed(self, request: dict[str, Any]) -> dict[str, Any]:
        import qwen_runner

        return {"status": "ok", "models": {model: qwen_runner.installed(model) for model in qwen_runner.MODELS}}


def _handle(worker: ImageWorker, request: dict[str, Any]) -> dict[str, Any]:
    command = request.get("command")
    handlers = {
        "count_faces": worker.count_faces,
        "qwen_generate": worker.qwen_generate,
        "qwen_installed": worker.qwen_installed,
    }
    if command in handlers:
        return handlers[command](request)
    if command == "stats":
        return worker.stats()
    raise ValueError(f"unknown command: {command!r}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Local image worker: Qwen pictures and face detection")
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
