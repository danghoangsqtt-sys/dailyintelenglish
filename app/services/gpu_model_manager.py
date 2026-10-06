"""Task 20.1 -- one process-wide arbiter for the single RTX 3060 (D20.1-a..g).

The GPU consumers live in different processes: the Ollama server (qwen), the StyleTTS 2
subprocess worker (Task 21.1b), and the future image (Phase 20) and music (Phase 22)
workers. This process cannot load them all the same way, but it can decide who gets the
card and free it. So this is an **arbiter, not a loader**: a consumer takes an exclusive
lease, loads and unloads its own model inside it, and hands the card back on exit.

    async with get_gpu_manager().lease("image", min_free_mb=8192):
        ...  # spawn/load, synthesize, unload -- nobody else is on the GPU here

Why a lease is needed at all (real code, task-20.1.md "What the real code does today"):
- `OllamaProvider` sends `keep_alive: "5m"`, so qwen stays resident for 5 minutes after
  any local fallback call;
- with qwen loaded the card had only 3916 MiB free out of 12288, measured at context 4096
  (the app runs `num_ctx=16384`, so there is less than that in practice);
- script jobs (the AIWorker loop) and audio/video/thumbnail (request handlers) can
  overlap across projects, so the app is not sequential as a whole even though each
  pipeline is.

Lease semantics:
- **Exclusive, FIFO**: one `asyncio.Lock`. The lock is created per running event loop, so
  an old loop's lock is never reused (that is the real "bound to a different event loop"
  failure the existing `write_lock` shows under pytest).
- **Room check**: a lease with `min_free_mb > 0` measures free VRAM (`nvidia-smi`, D20.1-d),
  evicts Ollama's resident models if short (D20.1-b), and re-measures. If it is still
  short, it raises `GpuUnavailableError` so the caller takes its existing fallback (Edge
  TTS, template thumbnail). `min_free_mb=0` is the Ollama calls' own lease (D20.1-c): it
  waits its turn but never measures or evicts, because Ollama spills to CPU itself rather
  than OOM.
- **Not re-entrant**: taking a lease while already holding one raises at once instead of
  deadlocking. Call sites must take the lease after a text/AI step, not around it.
- **Kill switch** (`DIE_GPU_MANAGER_ENABLED=false`): `lease()` becomes a pass-through with
  no lock and no eviction. That is exactly the pre-20.1 behaviour.

Scope limits (D20.1-g): one FastAPI process. A second app instance on the same machine
is not coordinated with; this module does not pretend otherwise.
"""

from __future__ import annotations

import asyncio
import contextvars
import logging
import time
from collections.abc import AsyncIterator, Awaitable, Callable
from contextlib import asynccontextmanager
from dataclasses import dataclass, field

from app.core.exceptions import GpuUnavailableError

logger = logging.getLogger(__name__)

MemoryProbe = Callable[[], Awaitable["dict | None"]]
OllamaEvictor = Callable[[], Awaitable[list[str]]]

# Ollama's unload request can return a moment before the driver reports the memory as
# free, so a short poll is made after eviction instead of trusting a single re-read.
# 10 x 0.5 s bounds the wait at ~5 s. The real release latency on the owner's machine is
# part of this task's owner-machine verification (task-20.1.md).
POST_EVICTION_POLL_ATTEMPTS = 10
POST_EVICTION_POLL_INTERVAL_SECONDS = 0.5

_current_lease: contextvars.ContextVar[str | None] = contextvars.ContextVar("gpu_lease_holder", default=None)


class GpuLeaseNestingError(RuntimeError):
    """A lease was requested while this task already holds one (would deadlock).

    A programming error, not a GPU condition: callers must not catch it as a reason
    to fall back.
    """


@dataclass
class GpuLease:
    """What a lease holder can read (and what gets logged when the lease ends)."""

    consumer: str
    min_free_mb: int
    waited_seconds: float = 0.0
    free_mb_before: int | None = None
    free_mb_after_eviction: int | None = None
    evicted_models: list[str] = field(default_factory=list)
    managed: bool = True


class GpuModelManager:
    """Arbitrates the one GPU between consumers in different processes."""

    def __init__(
        self,
        *,
        enabled: bool,
        evict_ollama: bool,
        memory_probe: MemoryProbe,
        ollama_evictor: OllamaEvictor | None,
        sleep: Callable[[float], Awaitable[None]] = asyncio.sleep,
    ) -> None:
        """Args:
        enabled: `False` makes every lease a pass-through (the kill switch).
        evict_ollama: `False` means a short lease fails over instead of evicting qwen.
        memory_probe: Returns `{"free_mb": ...}` (see `system_checks.get_gpu_memory`),
            or None when there is no usable NVIDIA GPU.
        ollama_evictor: Unloads every resident Ollama model and returns their names.
            It must never raise (see `OllamaProvider.unload_all_resident`).
        sleep: Injected so the post-eviction poll is instant in tests.
        """
        self._enabled = enabled
        self._evict_ollama = evict_ollama
        self._memory_probe = memory_probe
        self._ollama_evictor = ollama_evictor
        self._sleep = sleep
        self._lock: asyncio.Lock | None = None
        self._lock_loop: asyncio.AbstractEventLoop | None = None

    @property
    def enabled(self) -> bool:
        return self._enabled

    def _lock_for_running_loop(self) -> asyncio.Lock:
        loop = asyncio.get_running_loop()
        if self._lock is None or self._lock_loop is not loop:
            self._lock = asyncio.Lock()
            self._lock_loop = loop
        return self._lock

    @asynccontextmanager
    async def lease(self, consumer: str, min_free_mb: int | None) -> AsyncIterator[GpuLease]:
        """Hold the GPU exclusively for the body of the `async with`.

        Args:
            consumer: Short name for logs, e.g. "ollama", "styletts2", "image".
            min_free_mb: Free VRAM this consumer needs before it loads. `0` means "only
                wait my turn" (Ollama). `None` means no measured threshold was
                configured, which is refused: thresholds come from real measurements
                (D20.1-e), never from a guess made at the call site.

        Raises:
            GpuUnavailableError: No usable GPU, no threshold, or not enough room even
                after evicting Ollama. The lock is not held when this is raised.
            GpuLeaseNestingError: This task already holds a lease.
        """
        holder = _current_lease.get()
        if holder is not None:
            raise GpuLeaseNestingError(
                f"{consumer!r} requested a GPU lease while {holder!r} already holds one in this task"
            )

        if not self._enabled:
            lease = GpuLease(consumer=consumer, min_free_mb=min_free_mb or 0, managed=False)
            token = _current_lease.set(consumer)
            try:
                yield lease
            finally:
                _current_lease.reset(token)
            return

        if min_free_mb is None:
            self._log_refusal(consumer, None, "no_measured_threshold", None)
            raise GpuUnavailableError(consumer, "no_measured_threshold")

        lease = GpuLease(consumer=consumer, min_free_mb=min_free_mb)
        wait_started = time.monotonic()
        async with self._lock_for_running_loop():
            lease.waited_seconds = round(time.monotonic() - wait_started, 3)
            if min_free_mb > 0:
                await self._ensure_room(lease)
            token = _current_lease.set(consumer)
            held_started = time.monotonic()
            try:
                yield lease
            finally:
                _current_lease.reset(token)
                logger.info(
                    "gpu_lease_released consumer=%s waited_s=%.3f held_s=%.3f free_before_mb=%s "
                    "free_after_eviction_mb=%s evicted=%s",
                    consumer, lease.waited_seconds, time.monotonic() - held_started,
                    lease.free_mb_before, lease.free_mb_after_eviction, ",".join(lease.evicted_models) or "-",
                )

    async def _ensure_room(self, lease: GpuLease) -> None:
        memory = await self._memory_probe()
        if memory is None:
            self._log_refusal(lease.consumer, lease.min_free_mb, "no_nvidia_gpu", None)
            raise GpuUnavailableError(lease.consumer, "no_nvidia_gpu")
        lease.free_mb_before = memory["free_mb"]
        if memory["free_mb"] >= lease.min_free_mb:
            return

        if not self._evict_ollama or self._ollama_evictor is None:
            self._log_refusal(lease.consumer, lease.min_free_mb, "insufficient_vram", memory["free_mb"])
            raise GpuUnavailableError(
                lease.consumer, "insufficient_vram", free_mb=memory["free_mb"], min_free_mb=lease.min_free_mb
            )

        lease.evicted_models = await self._ollama_evictor()
        free_mb = memory["free_mb"]
        if lease.evicted_models:
            for _ in range(POST_EVICTION_POLL_ATTEMPTS):
                memory = await self._memory_probe()
                free_mb = memory["free_mb"] if memory is not None else free_mb
                if free_mb >= lease.min_free_mb:
                    break
                await self._sleep(POST_EVICTION_POLL_INTERVAL_SECONDS)
        lease.free_mb_after_eviction = free_mb
        if free_mb >= lease.min_free_mb:
            return
        self._log_refusal(lease.consumer, lease.min_free_mb, "insufficient_vram_after_eviction", free_mb)
        raise GpuUnavailableError(
            lease.consumer, "insufficient_vram_after_eviction", free_mb=free_mb, min_free_mb=lease.min_free_mb
        )

    @staticmethod
    def _log_refusal(consumer: str, min_free_mb: int | None, reason: str, free_mb: int | None) -> None:
        logger.warning(
            "gpu_lease_refused consumer=%s reason=%s free_mb=%s min_free_mb=%s",
            consumer, reason, free_mb, min_free_mb,
        )


_manager: GpuModelManager | None = None


def build_gpu_manager_from_settings() -> GpuModelManager:
    """The app's real manager: `nvidia-smi` probe + the configured Ollama server."""
    from app.core.config import settings  # local import: avoids a config<->ai import cycle
    from app.core.system_checks import get_gpu_memory
    from app.services.ai.ollama_provider import OllamaProvider

    evictor = OllamaProvider(
        base_url=settings.OLLAMA_BASE_URL, model=settings.OLLAMA_MODEL, num_ctx=settings.OLLAMA_NUM_CTX
    ).unload_all_resident
    return GpuModelManager(
        enabled=settings.GPU_MANAGER_ENABLED,
        evict_ollama=settings.GPU_EVICT_OLLAMA,
        memory_probe=get_gpu_memory,
        ollama_evictor=evictor,
    )


def get_gpu_manager() -> GpuModelManager:
    """The process-wide manager, built from settings on first use."""
    global _manager
    if _manager is None:
        _manager = build_gpu_manager_from_settings()
    return _manager


def set_gpu_manager(manager: GpuModelManager | None) -> None:
    """Replace the process-wide manager (tests); `None` rebuilds it from settings on next use."""
    global _manager
    _manager = manager
