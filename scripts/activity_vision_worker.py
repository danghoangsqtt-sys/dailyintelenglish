"""Isolated local vision worker for Activity Library metadata suggestions.

The main FastAPI process intentionally does not import torch or transformers. This
worker loads one Hugging Face vision model for a complete upload batch, writes raw
model responses to a JSON file, and exits so CUDA memory is returned to the system.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
_MAX_BATCH = 20


def _read_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError("request must be a JSON object")
    return value


def _validated_request(value: dict[str, Any]) -> tuple[str, str, int, list[dict[str, str]]]:
    model = value.get("model")
    prompt = value.get("prompt")
    max_new_tokens = value.get("max_new_tokens")
    items = value.get("items")
    if not isinstance(model, str) or not model.strip():
        raise ValueError("model is required")
    if not isinstance(prompt, str) or not prompt.strip():
        raise ValueError("prompt is required")
    if not isinstance(max_new_tokens, int) or not 32 <= max_new_tokens <= 512:
        raise ValueError("max_new_tokens must be between 32 and 512")
    if not isinstance(items, list) or not 1 <= len(items) <= _MAX_BATCH:
        raise ValueError(f"items must contain between 1 and {_MAX_BATCH} images")

    normalized: list[dict[str, str]] = []
    for item in items:
        if not isinstance(item, dict) or not isinstance(item.get("id"), str):
            raise ValueError("each item must have a string id")
        image_path = Path(str(item.get("path", ""))).resolve()
        if not image_path.is_file():
            raise ValueError(f"image does not exist for item {item['id']}")
        normalized.append({"id": item["id"], "path": str(image_path)})
    return model.strip(), prompt, max_new_tokens, normalized


def _self_check() -> int:
    import torch
    import transformers

    payload = {
        "ok": bool(torch.cuda.is_available() and hasattr(transformers, "Qwen3VLForConditionalGeneration")),
        "cuda": torch.cuda.is_available(),
        "torch": torch.__version__,
        "transformers": transformers.__version__,
        "qwen3_vl_native": hasattr(transformers, "Qwen3VLForConditionalGeneration"),
    }
    print(json.dumps(payload), flush=True)
    return 0 if payload["ok"] else 1


def _analyze(request_path: Path, output_path: Path, cache_dir: Path) -> None:
    cache_dir.mkdir(parents=True, exist_ok=True)
    os.environ.setdefault("HF_HOME", str(cache_dir))
    os.environ.setdefault("HF_HUB_DISABLE_TELEMETRY", "1")
    # Xet's multi-stream CDN repeatedly timed out on the target Windows machine.
    # The Hub's standard HTTP downloader is slower but resumable and reliable.
    os.environ.setdefault("HF_HUB_DISABLE_XET", "1")
    os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")

    import torch
    from PIL import Image
    from transformers import AutoModelForMultimodalLM, AutoProcessor

    if not torch.cuda.is_available():
        raise RuntimeError("Activity Vision requires a CUDA-enabled torch build and NVIDIA GPU")

    model_name, prompt, max_new_tokens, items = _validated_request(_read_json(request_path))
    processor = AutoProcessor.from_pretrained(model_name, cache_dir=cache_dir)
    model = AutoModelForMultimodalLM.from_pretrained(
        model_name,
        cache_dir=cache_dir,
        device_map="auto",
        dtype=torch.bfloat16,
        attn_implementation="sdpa",
        trust_remote_code=False,
    )
    model.eval()
    torch.set_grad_enabled(False)
    torch.backends.cuda.matmul.allow_tf32 = True

    results: list[dict[str, str]] = []
    for index, item in enumerate(items, start=1):
        print(f"activity_vision item={index}/{len(items)}", flush=True)
        with Image.open(item["path"]) as source:
            image = source.convert("RGB")
        messages = [{
            "role": "user",
            "content": [{"type": "image"}, {"type": "text", "text": prompt}],
        }]
        chat = processor.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
        inputs = processor(text=[chat], images=[image], return_tensors="pt")
        inputs = inputs.to(model.device)
        generated = model.generate(
            **inputs,
            max_new_tokens=max_new_tokens,
            do_sample=False,
            use_cache=True,
        )
        prompt_tokens = inputs["input_ids"].shape[1]
        text = processor.decode(generated[0, prompt_tokens:], skip_special_tokens=True).strip()
        results.append({"id": item["id"], "text": text})
        del inputs, generated, image

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps({"items": results}, ensure_ascii=False), encoding="utf-8")


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Analyze Activity Library images with local Qwen3-VL")
    parser.add_argument("--request", type=Path)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--cache-dir", type=Path, default=ROOT / "models" / "activity-vision")
    parser.add_argument("--self-check", action="store_true")
    return parser


def main() -> int:
    args = _parser().parse_args()
    if args.self_check:
        return _self_check()
    if args.request is None or args.output is None:
        raise SystemExit("--request and --output are required")
    _analyze(args.request.resolve(), args.output.resolve(), args.cache_dir.resolve())
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:  # worker boundary: main process converts failure to safe fallback
        print(f"activity_vision_worker_failed: {type(exc).__name__}: {exc}", file=sys.stderr, flush=True)
        raise SystemExit(1) from exc
