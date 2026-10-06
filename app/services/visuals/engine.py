"""Image worker protocol and deterministic, GPU-free test engine."""

from __future__ import annotations

import asyncio
import json
import os
import subprocess
import uuid
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any, Protocol

from PIL import Image

from app.core.config import settings
from app.core.exceptions import ConflictError
from app.core.paths import get_project_root
from app.services.gpu_model_manager import get_gpu_manager
from app.services.visuals.recipes import token_count

ROOT = get_project_root()
IMAGE_PYTHON = ROOT / "venv-image" / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
IMAGE_WORKER = ROOT / "scripts" / "image_worker.py"


def generation_available() -> bool:
    return settings.AI_VISUALS_ENABLED and (settings.IMAGE_ENGINE == "fake" or IMAGE_PYTHON.is_file())


def require_generation() -> None:
    if not settings.AI_VISUALS_ENABLED:
        raise ConflictError("AI visuals generation is disabled")
    if settings.IMAGE_ENGINE == "worker" and not IMAGE_PYTHON.is_file():
        raise ConflictError("Image environment is missing (venv-image)")


class ImageSession(Protocol):
    async def request(self, payload: dict[str, Any]) -> dict[str, Any]: ...


class ImageEngine(Protocol):
    def session(
        self, pipeline: str = "text2img", encoders: bool = True,
        ip: str = "none", consumer: str = "visuals", scene: bool = False,
    ) -> Any: ...


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

    def request(self, payload: dict[str, Any]) -> dict[str, Any]:
        assert self.process.stdin is not None
        self.process.stdin.write(json.dumps(payload) + "\n")
        self.process.stdin.flush()
        response = self._read_line()
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


class WorkerImageEngine:
    """Leased subprocess engine; it never imports the image model stack."""

    def __init__(self) -> None:
        self._encoded_tokens: dict[str, list[dict[str, Any]]] = {}

    @asynccontextmanager
    async def session(
        self, pipeline: str = "text2img", encoders: bool = True,
        ip: str = "none", consumer: str = "visuals", scene: bool = False,
    ) -> AsyncIterator[WorkerImageEngine]:
        require_generation()
        async with get_gpu_manager().lease(consumer, min_free_mb=8192):
            worker = await asyncio.to_thread(_WorkerProcess)
            self._worker = worker
            try:
                # Task 23.2 probe: the 1344x768 VAE decode is the VRAM peak. Without tiling the L2
                # render reserved 13.2 GB (14.1 GB with the scene adapter) on the 12 GB card and
                # spilled into shared memory (2.7x slower shots); tiled: 10.9 GB, same image.
                load = {"command": "load", "mode": "base", "pipeline": pipeline, "encoders": encoders,
                        "vae_tiling": True}
                if settings.IMAGE_BASE_REPO:
                    load.update(base_repo=settings.IMAGE_BASE_REPO, scheduler=settings.IMAGE_SCHEDULER)
                await self.request(load)
                if ip != "none":
                    adapter = {"command": "load_ip_adapter"}
                    if scene:  # Task 23.2: + the scene-plate adapter
                        adapter["scene"] = True
                    if ip == "layers_only":
                        adapter["image_encoder_folder"] = None
                    await self.request(adapter)
                yield self
            finally:
                await asyncio.to_thread(worker.close)
                self._worker = None

    async def request(self, payload: dict[str, Any]) -> dict[str, Any]:
        response = await asyncio.to_thread(self._worker.request, payload)
        if payload["command"] == "encode":
            self._encoded_tokens[str(payload["output_path"])] = response["item_tokens"]
        elif payload["command"] == "generate" and payload.get("embeds_path"):
            tokens = self._encoded_tokens[str(payload["embeds_path"])][int(payload.get("embeds_index", 0))]
            response = {**response, **tokens}
        return response


class FakeImageEngine:
    """Deterministic solid-colour PNGs with the worker's JSON response shape."""

    def __init__(self) -> None:
        self._encoded_tokens: dict[str, list[dict[str, Any]]] = {}

    @asynccontextmanager
    async def session(
        self, pipeline: str = "text2img", encoders: bool = True,
        ip: str = "none", consumer: str = "visuals", scene: bool = False,
    ) -> AsyncIterator[FakeImageEngine]:
        require_generation()
        yield self

    async def request(self, payload: dict[str, Any]) -> dict[str, Any]:
        command = payload["command"]
        if command == "encode":
            tokens = [
                {"prompt_tokens": token_count(item["prompt"]),
                 "prompt_truncated": token_count(item["prompt"]) > 75}
                for item in payload["items"]
            ]
            self._encoded_tokens[str(payload["output_path"])] = tokens
            await asyncio.to_thread(_touch, Path(payload["output_path"]))
            return {"status": "ok", "items": len(tokens), "do_cfg": True,
                    "with_ip": bool(payload.get("ip_adapter_image") or payload.get("ip_adapter_images")),
                    "ip_faces": len(payload.get("ip_adapter_images") or []) or int(bool(payload.get("ip_adapter_image"))),
                    "output_path": str(payload["output_path"]), "wall_time_sec": 0.0, "item_tokens": tokens}
        if command == "generate":
            width, height = int(payload.get("width", 1344)), int(payload.get("height", 768))
            seed = int(payload["seed"])
            await asyncio.to_thread(_solid_png, Path(payload["output_path"]), (width, height), seed)
            if payload.get("embeds_path"):
                tokens = self._encoded_tokens[str(payload["embeds_path"])][int(payload.get("embeds_index", 0))]
            else:
                count = token_count(payload["prompt"])
                tokens = {"prompt_tokens": count, "prompt_truncated": count > 75}
            return {"status": "ok", "wall_time_sec": 0.0, "steps": int(payload.get("steps", 30)),
                    "guidance_scale": float(payload.get("guidance_scale", 6.0)),
                    "pipeline": "fake", "from_embeds": bool(payload.get("embeds_path")),
                    "negative_prompt_applied": bool(payload.get("negative_prompt")),
                    "native_size": [width, height], "output_path": str(payload["output_path"]),
                    "fitted_path": None, **tokens}
        if command == "remove_background":
            # No foreground anywhere: the extra-person check sees an empty gap.
            await asyncio.to_thread(_transparent_png, Path(payload["input_path"]), Path(payload["output_path"]))
            return {"status": "ok", "output_path": str(payload["output_path"]), "wall_time_sec": 0.0,
                    "foreground_fraction": 0.0, "soft_edge_fraction": 0.0}
        raise ValueError(f"unsupported fake image command: {command}")


def _touch(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.touch()


def _solid_png(path: Path, size: tuple[int, int], seed: int) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    color = ((seed * 73) % 256, (seed * 151) % 256, (seed * 199) % 256)
    Image.new("RGB", size, color).save(path, format="PNG")


def _transparent_png(source: Path, path: Path) -> None:
    with Image.open(source) as image:
        size = image.size
    path.parent.mkdir(parents=True, exist_ok=True)
    Image.new("RGBA", size, (0, 0, 0, 0)).save(path, format="PNG")


def get_image_engine() -> ImageEngine:
    return FakeImageEngine() if settings.IMAGE_ENGINE == "fake" else WorkerImageEngine()
