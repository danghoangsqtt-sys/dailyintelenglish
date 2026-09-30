"""Tests for the Task 20.1 GPU model manager (no GPU, no Ollama: probe + evictor are fakes)."""

from __future__ import annotations

import asyncio

import pytest

from app.core.exceptions import GpuUnavailableError
from app.services import gpu_model_manager as gpu_module
from app.services.gpu_model_manager import GpuLeaseNestingError, GpuModelManager


class FakeGpu:
    """A scripted `nvidia-smi` probe plus an Ollama evictor that frees VRAM when called."""

    def __init__(self, free_mb: int | None, resident: list[str] | None = None, freed_by_eviction_mb: int = 0,
                 eviction_release_reads: int = 0) -> None:
        self.free_mb = free_mb
        self.resident = list(resident or [])
        self.freed_by_eviction_mb = freed_by_eviction_mb
        # How many post-eviction probe reads still report the old number (driver lag).
        self.eviction_release_reads = eviction_release_reads
        self.probe_calls = 0
        self.evict_calls = 0
        self._pending_release = 0

    async def probe(self) -> dict | None:
        self.probe_calls += 1
        if self.free_mb is None:
            return None
        if self._pending_release:
            if self.eviction_release_reads > 0:
                self.eviction_release_reads -= 1
            else:
                self.free_mb += self._pending_release
                self._pending_release = 0
        return {"used_mb": 12288 - self.free_mb, "free_mb": self.free_mb, "total_mb": 12288}

    async def evict(self) -> list[str]:
        self.evict_calls += 1
        evicted, self.resident = self.resident, []
        if evicted:
            self._pending_release = self.freed_by_eviction_mb
        return evicted


class RecordingSleep:
    def __init__(self) -> None:
        self.calls: list[float] = []

    async def __call__(self, seconds: float) -> None:
        self.calls.append(seconds)


def _manager(gpu: FakeGpu, *, enabled: bool = True, evict_ollama: bool = True, sleep=None) -> GpuModelManager:
    return GpuModelManager(
        enabled=enabled,
        evict_ollama=evict_ollama,
        memory_probe=gpu.probe,
        ollama_evictor=gpu.evict,
        sleep=sleep or RecordingSleep(),
    )


# --- room check ---------------------------------------------------------------------


async def test_enough_free_vram_needs_no_eviction():
    gpu = FakeGpu(free_mb=10286, resident=["qwen3.5:9b"])
    async with _manager(gpu).lease("styletts2", min_free_mb=6144) as lease:
        assert lease.free_mb_before == 10286
        assert lease.evicted_models == []
    assert gpu.evict_calls == 0


async def test_short_vram_evicts_ollama_then_proceeds():
    # The real D21.1b-e numbers: 3916 MiB free with qwen loaded, 10286 MiB at idle.
    gpu = FakeGpu(free_mb=3916, resident=["qwen3.5:9b"], freed_by_eviction_mb=10286 - 3916)
    async with _manager(gpu).lease("styletts2", min_free_mb=6144) as lease:
        assert lease.evicted_models == ["qwen3.5:9b"]
        assert lease.free_mb_before == 3916
        assert lease.free_mb_after_eviction == 10286


async def test_post_eviction_poll_waits_for_the_driver_to_report_the_release():
    gpu = FakeGpu(free_mb=3916, resident=["qwen3.5:9b"], freed_by_eviction_mb=6370, eviction_release_reads=3)
    sleep = RecordingSleep()
    async with _manager(gpu, sleep=sleep).lease("styletts2", min_free_mb=6144) as lease:
        assert lease.free_mb_after_eviction == 10286
    assert len(sleep.calls) == 3  # three stale reads, then the fourth sees the room


async def test_still_short_after_eviction_raises_and_bounds_the_poll():
    gpu = FakeGpu(free_mb=3916, resident=["qwen3.5:9b"], freed_by_eviction_mb=1000)
    sleep = RecordingSleep()
    with pytest.raises(GpuUnavailableError) as excinfo:
        async with _manager(gpu, sleep=sleep).lease("image", min_free_mb=6144):
            pytest.fail("body must not run")
    assert excinfo.value.reason == "insufficient_vram_after_eviction"
    assert excinfo.value.free_mb == 4916
    assert len(sleep.calls) == gpu_module.POST_EVICTION_POLL_ATTEMPTS


async def test_nothing_resident_to_evict_fails_without_polling():
    gpu = FakeGpu(free_mb=3000, resident=[])
    sleep = RecordingSleep()
    with pytest.raises(GpuUnavailableError) as excinfo:
        async with _manager(gpu, sleep=sleep).lease("image", min_free_mb=6144):
            pass
    assert excinfo.value.reason == "insufficient_vram_after_eviction"
    assert gpu.evict_calls == 1
    assert sleep.calls == []


async def test_eviction_disabled_falls_back_instead_of_unloading_qwen():
    gpu = FakeGpu(free_mb=3916, resident=["qwen3.5:9b"], freed_by_eviction_mb=6370)
    with pytest.raises(GpuUnavailableError) as excinfo:
        async with _manager(gpu, evict_ollama=False).lease("styletts2", min_free_mb=6144):
            pass
    assert excinfo.value.reason == "insufficient_vram"
    assert gpu.evict_calls == 0
    assert gpu.resident == ["qwen3.5:9b"]


async def test_no_nvidia_gpu_raises_for_a_consumer_that_needs_room():
    gpu = FakeGpu(free_mb=None)
    with pytest.raises(GpuUnavailableError) as excinfo:
        async with _manager(gpu).lease("styletts2", min_free_mb=6144):
            pass
    assert excinfo.value.reason == "no_nvidia_gpu"


async def test_missing_threshold_is_refused_not_guessed():
    gpu = FakeGpu(free_mb=10286)
    with pytest.raises(GpuUnavailableError) as excinfo:
        async with _manager(gpu).lease("image", min_free_mb=None):
            pass
    assert excinfo.value.reason == "no_measured_threshold"
    assert gpu.probe_calls == 0


async def test_zero_threshold_only_waits_its_turn_even_without_a_gpu():
    # The Ollama calls' own lease: never measures, never evicts, works on a GPU-less box.
    gpu = FakeGpu(free_mb=None, resident=["qwen3.5:9b"])
    async with _manager(gpu).lease("ollama", min_free_mb=0) as lease:
        assert lease.managed is True
    assert gpu.probe_calls == 0
    assert gpu.evict_calls == 0


async def test_refusal_does_not_leave_the_lock_held():
    gpu = FakeGpu(free_mb=None)
    manager = _manager(gpu)
    with pytest.raises(GpuUnavailableError):
        async with manager.lease("styletts2", min_free_mb=6144):
            pass
    async with asyncio.timeout(1):
        async with manager.lease("ollama", min_free_mb=0):
            pass


# --- exclusivity --------------------------------------------------------------------


async def test_leases_are_exclusive_and_first_come_first_served():
    manager = _manager(FakeGpu(free_mb=10286))
    events: list[str] = []
    first_entered = asyncio.Event()
    release_first = asyncio.Event()

    async def holder(name: str, wait_for: asyncio.Event | None) -> None:
        async with manager.lease(name, min_free_mb=0):
            events.append(f"enter:{name}")
            if name == "styletts2":
                first_entered.set()
            if wait_for is not None:
                await wait_for.wait()
            events.append(f"exit:{name}")

    first = asyncio.create_task(holder("styletts2", release_first))
    await first_entered.wait()
    second = asyncio.create_task(holder("ollama", None))
    third = asyncio.create_task(holder("image", None))
    await asyncio.sleep(0.05)
    assert events == ["enter:styletts2"]  # nobody else got in while it was held
    release_first.set()
    await asyncio.gather(first, second, third)
    assert events == [
        "enter:styletts2", "exit:styletts2",
        "enter:ollama", "exit:ollama",
        "enter:image", "exit:image",
    ]


async def test_waiting_for_the_lease_is_cancellable_by_a_caller_deadline():
    # The router bounds an Ollama call with `asyncio.wait_for`; a caller cancelled while
    # queued must not end up holding the lock.
    manager = _manager(FakeGpu(free_mb=10286))
    release = asyncio.Event()
    entered = asyncio.Event()

    async def long_holder() -> None:
        async with manager.lease("image", min_free_mb=0):
            entered.set()
            await release.wait()

    async def queued_ollama_call() -> None:
        async with manager.lease("ollama", min_free_mb=0):
            pytest.fail("must not get the GPU while image holds it")

    holder_task = asyncio.create_task(long_holder())
    await entered.wait()
    with pytest.raises(TimeoutError):
        await asyncio.wait_for(queued_ollama_call(), timeout=0.05)
    release.set()
    await holder_task
    async with asyncio.timeout(1):
        async with manager.lease("ollama", min_free_mb=0):
            pass


async def test_lease_is_released_when_the_body_raises():
    manager = _manager(FakeGpu(free_mb=10286))
    with pytest.raises(RuntimeError, match="synthesis blew up"):
        async with manager.lease("styletts2", min_free_mb=6144):
            raise RuntimeError("synthesis blew up")
    async with asyncio.timeout(1):
        async with manager.lease("ollama", min_free_mb=0):
            pass


async def test_nested_lease_raises_instead_of_deadlocking():
    manager = _manager(FakeGpu(free_mb=10286))
    async with asyncio.timeout(1):
        async with manager.lease("thumbnail", min_free_mb=0):
            with pytest.raises(GpuLeaseNestingError):
                async with manager.lease("ollama", min_free_mb=0):
                    pass
    # The outer lease was still released normally.
    async with asyncio.timeout(1):
        async with manager.lease("ollama", min_free_mb=0):
            pass


def test_lock_is_rebuilt_per_event_loop():
    # A module-level asyncio.Lock reused across loops is the real "bound to a different
    # event loop" failure; the manager outlives many loops (pytest, app restarts).
    manager = _manager(FakeGpu(free_mb=10286))

    async def contended_round() -> None:
        release = asyncio.Event()

        async def holder() -> None:
            async with manager.lease("image", min_free_mb=0):
                await release.wait()

        task = asyncio.create_task(holder())
        await asyncio.sleep(0)
        waiter = asyncio.create_task(_enter_and_exit(manager))
        await asyncio.sleep(0.01)
        release.set()
        await asyncio.gather(task, waiter)

    asyncio.run(contended_round())
    asyncio.run(contended_round())


async def _enter_and_exit(manager: GpuModelManager) -> None:
    async with manager.lease("ollama", min_free_mb=0):
        pass


# --- kill switch --------------------------------------------------------------------


async def test_kill_switch_is_a_pass_through():
    gpu = FakeGpu(free_mb=None, resident=["qwen3.5:9b"])
    manager = _manager(gpu, enabled=False)
    both_inside = asyncio.Event()
    inside = 0

    async def holder(name: str) -> None:
        nonlocal inside
        async with manager.lease(name, min_free_mb=6144) as lease:
            assert lease.managed is False
            inside += 1
            if inside == 2:
                both_inside.set()
            async with asyncio.timeout(1):
                await both_inside.wait()  # would time out if the lease serialized them

    await asyncio.gather(holder("styletts2"), holder("image"))
    assert gpu.probe_calls == 0
    assert gpu.evict_calls == 0


async def test_kill_switch_still_refuses_nesting():
    manager = _manager(FakeGpu(free_mb=10286), enabled=False)
    async with manager.lease("thumbnail", min_free_mb=0):
        with pytest.raises(GpuLeaseNestingError):
            async with manager.lease("ollama", min_free_mb=0):
                pass


# --- settings wiring ----------------------------------------------------------------


def test_manager_is_built_from_settings(monkeypatch):
    from app.core.config import settings

    monkeypatch.setattr(settings, "GPU_MANAGER_ENABLED", False)
    monkeypatch.setattr(settings, "GPU_EVICT_OLLAMA", False)
    gpu_module.set_gpu_manager(None)
    try:
        manager = gpu_module.get_gpu_manager()
        assert manager.enabled is False
        assert manager._evict_ollama is False
        assert gpu_module.get_gpu_manager() is manager  # one per process
    finally:
        gpu_module.set_gpu_manager(None)


def test_styletts2_threshold_default_is_the_measured_number():
    from app.core.config import Settings

    assert Settings().GPU_MIN_FREE_MB_STYLETTS2 == 6144


# --- /health (D20.1-f) --------------------------------------------------------------


def test_health_reports_live_gpu_memory_and_manager_state(tmp_path, monkeypatch):
    from fastapi.testclient import TestClient

    from app import main as main_module
    from app.core.config import settings

    async def fake_gpu_memory() -> dict:
        return {"used_mb": 8195, "free_mb": 3916, "total_mb": 12288}

    monkeypatch.setattr(settings, "DATA_DIR", tmp_path)
    monkeypatch.setattr(main_module, "get_gpu_memory", fake_gpu_memory)
    with TestClient(main_module.app) as client:
        body = client.get("/health").json()
    assert body["data"]["gpu_memory"] == {"used_mb": 8195, "free_mb": 3916, "total_mb": 12288}
    assert body["data"]["gpu_manager_enabled"] is True


async def test_get_gpu_memory_is_none_without_nvidia_smi(monkeypatch):
    from app.core import system_checks

    monkeypatch.setattr(system_checks.shutil, "which", lambda name: None)
    assert await system_checks.get_gpu_memory() is None


async def test_get_gpu_memory_parses_nvidia_smi_csv(monkeypatch):
    from app.core import system_checks

    class FakeProcess:
        returncode = 0

        async def communicate(self):
            return b"8195, 3916, 12288\n", b""

    async def fake_exec(*args, **kwargs):
        assert "--query-gpu=memory.used,memory.free,memory.total" in args
        return FakeProcess()

    monkeypatch.setattr(system_checks.shutil, "which", lambda name: "/usr/bin/nvidia-smi")
    monkeypatch.setattr(system_checks.asyncio, "create_subprocess_exec", fake_exec)
    assert await system_checks.get_gpu_memory() == {"used_mb": 8195, "free_mb": 3916, "total_mb": 12288}
