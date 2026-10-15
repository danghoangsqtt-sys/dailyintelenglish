"""Image worker protocol (Qwen batches) and the deterministic, GPU-free test engine."""

from __future__ import annotations

import asyncio
import json
import os
import subprocess
import uuid
from pathlib import Path
from typing import Any, Protocol

from PIL import Image

from backend.core.config import settings
from backend.core.exceptions import ConflictError
from backend.core.paths import IMAGE_VENV_DIR, RUNTIME_ROOT
from backend.ai.image.gpu_model_manager import get_gpu_manager

ROOT = RUNTIME_ROOT
IMAGE_PYTHON = IMAGE_VENV_DIR / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
IMAGE_WORKER = ROOT / "backend/ai/image/image_worker.py"


def generation_available() -> bool:
    return settings.AI_VISUALS_ENABLED and (settings.IMAGE_ENGINE == "fake" or IMAGE_PYTHON.is_file())


def require_generation() -> None:
    if not settings.AI_VISUALS_ENABLED:
        raise ConflictError("AI visuals generation is disabled")
    if settings.IMAGE_ENGINE == "worker" and not IMAGE_PYTHON.is_file():
        raise ConflictError("Image environment is missing (.venv-image)")


class ImageEngine(Protocol):
    async def qwen_batch(self, model: str, items: list[dict[str, Any]], consumer: str,
                         detect_faces: bool = False) -> dict[str, Any]: ...


class _WorkerProcess:
    """Owns one line-delimited worker process and its stderr log."""

    def __init__(self) -> None:
        log_dir = settings.DATA_DIR / "visuals" / "logs"
        log_dir.mkdir(parents=True, exist_ok=True)
        self.stderr_file = (log_dir / f"image_worker_{uuid.uuid4().hex}.log").open("w", encoding="utf-8")
        self.process = subprocess.Popen(
            [str(IMAGE_PYTHON), str(IMAGE_WORKER)], cwd=ROOT, stdin=subprocess.PIPE,
            stdout=subprocess.PIPE, stderr=self.stderr_file, text=True, encoding="utf-8", bufsize=1,
        )
        try:
            self.handshake = self._read_line()
        except Exception:
            self.close(kill=True)
            raise
        if self.handshake.get("status") != "ready":
            self.close(kill=True)
            raise RuntimeError(f"image worker unavailable: {self.handshake.get('reason', 'unknown')}")

    def _read_line(self) -> dict[str, Any]:
        assert self.process.stdout is not None
        line = self.process.stdout.readline()
        if not line:
            raise RuntimeError(f"image worker exited unexpectedly; see {self.stderr_file.name}")
        return json.loads(line)

    def request(self, payload: dict[str, Any], *, allow_unavailable: bool = False) -> dict[str, Any]:
        assert self.process.stdin is not None
        self.process.stdin.write(json.dumps(payload) + "\n")
        self.process.stdin.flush()
        response = self._read_line()
        if allow_unavailable and response.get("status") == "unavailable":
            return response
        if response.get("status") != "ok":
            raise RuntimeError(response.get("message", "image worker request failed"))
        return response

    def close(self, kill: bool = False) -> None:
        """Let the worker exit on stdin EOF; a worker that hangs (or failed its handshake) is
        killed, so it can never keep VRAM after its GPU lease ends (review r1 F3)."""
        try:
            if self.process.stdin and not self.process.stdin.closed:
                self.process.stdin.close()
        except OSError:
            pass
        try:
            if kill:
                self.process.kill()
            self.process.wait(timeout=120)
        except subprocess.TimeoutExpired:
            self.process.kill()
            self.process.wait()
        finally:
            self.stderr_file.close()


class QwenUnavailable(RuntimeError):
    """The Qwen model is not installed (or there is no GPU). Phase 44 (D123): callers report it; there is no fallback."""


def qwen_request(model: str, items: list[dict[str, Any]], detect_faces: bool = False) -> dict[str, Any]:
    request = {"command": "qwen_generate", "model": model, "items": items}
    if detect_faces:  # Phase 43: each result item also gets the faces found on it
        request["detect_faces"] = True
    return request


class WorkerImageEngine:
    """Leased subprocess engine; it never imports the image model stack."""

    async def qwen_batch(self, model: str, items: list[dict[str, Any]], consumer: str,
                         detect_faces: bool = False) -> dict[str, Any]:
        """Phase 39 (D118): one worker, one GPU lease, a batch of Qwen pictures (`qwen21` or `qwen_edit`). Raises
        `QwenUnavailable` when the model is missing (no fallback since D123). Phase 43: with
        `detect_faces` every result item carries the faces found on the drawn picture."""
        require_generation()
        async with get_gpu_manager().lease(consumer, min_free_mb=8192):
            worker = await asyncio.to_thread(_WorkerProcess)
            try:
                response = await asyncio.to_thread(worker.request, qwen_request(model, items, detect_faces),
                                                   allow_unavailable=True)
            finally:
                await asyncio.to_thread(worker.close)
        if response.get("status") == "unavailable":
            raise QwenUnavailable(f"{model}: {response.get('reason')} {response.get('missing') or ''}".strip())
        return response

class FakeImageEngine:
    """Deterministic solid-colour PNGs with the worker's JSON response shape."""

    qwen_available = True  # tests flip it to exercise the "model missing" message
    qwen_calls: list[dict[str, Any]] = []
    qwen_faces: list[list[float]] = [[560, 79, 818, 397, 1.0], [901, 180, 1134, 468, 1.0]]  # Phase 43 detect_faces

    async def qwen_batch(self, model: str, items: list[dict[str, Any]], consumer: str,
                         detect_faces: bool = False) -> dict[str, Any]:
        require_generation()
        FakeImageEngine.qwen_calls.append(qwen_request(model, items, detect_faces))
        if not FakeImageEngine.qwen_available:
            raise QwenUnavailable(f"{model}: model_missing")
        for item in items:
            await asyncio.to_thread(_solid_png, Path(item["output_path"]), (int(item["width"]), int(item["height"])),
                                    int(item["seed"]))
        results = [{"output_path": item["output_path"], "seconds": 0.0} for item in items]
        if detect_faces:  # the faces of the real 2026-10-14 draw (a pair right of centre); tests may script others
            for entry in results:
                entry["faces"] = [list(face) for face in FakeImageEngine.qwen_faces]
        return {"status": "ok", "model": model, "items": results}

def _solid_png(path: Path, size: tuple[int, int], seed: int) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    color = ((seed * 73) % 256, (seed * 151) % 256, (seed * 199) % 256)
    Image.new("RGB", size, color).save(path, format="PNG")


def get_image_engine() -> ImageEngine:
    return FakeImageEngine() if settings.IMAGE_ENGINE == "fake" else WorkerImageEngine()
