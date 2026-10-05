"""Music worker protocol and a deterministic, GPU-free test engine (Task 22.2)."""

from __future__ import annotations

import asyncio
import json
import math
import os
import struct
import subprocess
import uuid
import wave
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any, Protocol

from app.core.config import settings
from app.core.exceptions import ConflictError
from app.core.paths import get_project_root
from app.services.gpu_model_manager import get_gpu_manager

ROOT = get_project_root()
MUSIC_PYTHON = ROOT / "venv-music" / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
MUSIC_WORKER = ROOT / "scripts" / "music_worker.py"
MODEL_LICENCE = "MIT"  # ACE-Step 1.5 code and weights, checked 2026-10-05 (Task 22.1)


def unavailable_reason() -> str | None:
    if not settings.AI_MUSIC_ENABLED:
        return "AI music generation is disabled"
    if settings.MUSIC_ENGINE == "worker" and not MUSIC_PYTHON.is_file():
        return "Music environment is missing (venv-music)"
    return None


def generation_available() -> bool:
    return unavailable_reason() is None


def require_generation() -> None:
    reason = unavailable_reason()
    if reason is not None:
        raise ConflictError(reason)


class MusicEngine(Protocol):
    def session(self, consumer: str = "music") -> Any: ...


class _WorkerProcess:
    """Owns one line-delimited music worker process and its stderr log."""

    def __init__(self) -> None:
        log_dir = settings.DATA_DIR / "music_library" / ".logs"
        log_dir.mkdir(parents=True, exist_ok=True)
        self.stderr_file = (log_dir / f"music_worker_{uuid.uuid4().hex}.log").open("w", encoding="utf-8")
        self.process = subprocess.Popen(
            [str(MUSIC_PYTHON), str(MUSIC_WORKER)], cwd=ROOT, stdin=subprocess.PIPE,
            stdout=subprocess.PIPE, stderr=self.stderr_file, text=True, encoding="utf-8", bufsize=1,
        )
        try:
            self.handshake = self._read_line()
        except Exception:
            self.close(kill=True)
            raise
        if self.handshake.get("status") != "ready":
            self.close(kill=True)
            raise RuntimeError(f"music worker unavailable: {self.handshake.get('reason', 'unknown')}")

    def _read_line(self) -> dict[str, Any]:
        assert self.process.stdout is not None
        line = self.process.stdout.readline()
        if not line:
            raise RuntimeError(f"music worker exited unexpectedly; see {self.stderr_file.name}")
        return json.loads(line)

    def request(self, payload: dict[str, Any]) -> dict[str, Any]:
        assert self.process.stdin is not None
        self.process.stdin.write(json.dumps(payload) + "\n")
        self.process.stdin.flush()
        response = self._read_line()
        if response.get("status") != "ok":
            raise RuntimeError(response.get("message", "music worker request failed"))
        return response

    def close(self, kill: bool = False) -> None:
        """Let the worker exit on stdin EOF; a hung worker is killed so it never keeps VRAM
        after its GPU lease ends (same rule as the image worker)."""
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


class WorkerMusicEngine:
    """Leased subprocess engine; it never imports the music model stack."""

    @asynccontextmanager
    async def session(self, consumer: str = "music") -> AsyncIterator[WorkerMusicEngine]:
        require_generation()
        async with get_gpu_manager().lease(consumer, min_free_mb=settings.GPU_MIN_FREE_MB_MUSIC):
            worker = await asyncio.to_thread(_WorkerProcess)
            self._worker = worker
            try:
                await self.request({"command": "load", "lm": settings.MUSIC_LM})
                yield self
            finally:
                await asyncio.to_thread(worker.close)
                self._worker = None

    async def request(self, payload: dict[str, Any]) -> dict[str, Any]:
        return await asyncio.to_thread(self._worker.request, payload)


FAKE_MODEL = "fake music engine"
FAKE_SAMPLE_RATE = 8000
FAKE_SECONDS = 1.0


class FakeMusicEngine:
    """A short deterministic sine WAV with the worker's response shape (tests only)."""

    @asynccontextmanager
    async def session(self, consumer: str = "music") -> AsyncIterator[FakeMusicEngine]:
        require_generation()
        yield self

    async def request(self, payload: dict[str, Any]) -> dict[str, Any]:
        command = payload["command"]
        if command != "generate":
            raise ValueError(f"unsupported fake music command: {command}")
        duration_s, strategy = float(payload["duration_s"]), payload.get("strategy", "full")
        looped = strategy == "loop" or duration_s > 600
        await asyncio.to_thread(_sine_wav, Path(payload["output_path"]), int(payload["seed"]))
        return {"status": "ok", "output_path": str(payload["output_path"]), "model": FAKE_MODEL,
                "lm": settings.MUSIC_LM, "strategy": "loop" if looped else "full",
                "piece_s": min(150.0, duration_s) if looped else duration_s, "duration_s": duration_s,
                "sample_rate": FAKE_SAMPLE_RATE, "wall_time_sec": 0.0, "vram_peak_mb": None}


def _sine_wav(path: Path, seed: int) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    frequency = 220 + seed % 440
    frames = b"".join(
        struct.pack("<h", int(8000 * math.sin(2 * math.pi * frequency * index / FAKE_SAMPLE_RATE)))
        for index in range(int(FAKE_SAMPLE_RATE * FAKE_SECONDS))
    )
    with wave.open(str(path), "wb") as output:
        output.setnchannels(1)
        output.setsampwidth(2)
        output.setframerate(FAKE_SAMPLE_RATE)
        output.writeframes(frames)


def get_music_engine() -> MusicEngine:
    return FakeMusicEngine() if settings.MUSIC_ENGINE == "fake" else WorkerMusicEngine()
