# Task 20.1 — Shared GPU model manager (load / free-VRAM check / unload)

- **Status:** not started (doc-first card; **do not start until Phase 21's spike gate
  resolves** — Coder is single-session and Phase 21 has priority)
- **Owner:** Coder
- **Priority:** P0 (foundation for Phase 20 images and Phase 22 music; also refactors
  Phase 21's TTS VRAM handling into one place if StyleTTS 2 ships)
- **Dependency:** Phase 21 spike gate reached (PASS, SCOPE-CUT, or STOP — any outcome
  unblocks this task; it is useful regardless)
- **Controlling detail:** `docs/implementation/phase-20-ai-visuals.md` §3 "20.1";
  invariant 48 (VRAM is shared, never assumed)

## Goal

One component that owns GPU model lifecycle for the whole app: check free VRAM before
loading, load a model, hand it to the caller, unload it when the caller is done, and
degrade honestly when there is not enough memory.

Today nothing does this. Ollama manages its own model outside the app's control. Task
21.1b proposed a `nvidia-smi` free-memory check for StyleTTS 2 specifically. Phase 20's
image model and Phase 22's music model will each need the same thing. Writing it three
times means three subtly different behaviors and a hard-to-diagnose failure the first time
two of them overlap in a real run.

**This task builds the shared piece and nothing else.** No image model, no music model —
those are 20.2 and Phase 22. The only consumer wired up in this task is whatever TTS engine
Phase 21 leaves behind (if any), as a real integration test of the manager.

## Real numbers this task is designed around

Measured by Coder in Task 21.1b D21.1b-e with real `nvidia-smi` on the owner's RTX 3060:

| State | Free VRAM |
|---|---|
| Idle | 10286 MiB of 12288 |
| Ollama qwen3.5:9b loaded | **3916 MiB** |

Estimated needs (20.2 and Phase 22 will measure the real values):
- StyleTTS 2: 4–6 GB
- SDXL + IP-Adapter: 8–9 GB
- ACE-Step: 10–11 GB

The manager's job is to make "not enough free VRAM right now" a normal, handled outcome
rather than a CUDA OOM crash.

## Allowed files

- **New** `app/services/gpu/model_manager.py` — the manager itself.
- **New** `app/services/gpu/__init__.py`.
- **Modify** `app/core/config.py` — settings for the manager (see D20.1-d).
- **Modify** `app/core/constants.py` — VRAM thresholds if they belong there rather than
  config.
- **New** `tests/test_gpu_model_manager.py` — unit tests with a faked VRAM probe (the
  manager must be testable without a GPU present, since CI and a fresh checkout have none).
- **Modify** whichever TTS file Phase 21 leaves behind (`app/services/tts_service.py` or a
  new provider module) — **only if Phase 21 shipped a GPU-based engine**. If Phase 21 ended
  in STOP and Edge TTS remains the only engine, there is no GPU consumer to wire and this
  task ships the manager with tests only. Say which case applies in the design commit.
- `CHANGELOG.md` — one bullet under `[Unreleased]`.
- `.viepilot/phases/20-ai-visuals/PHASE-STATE.md` — flip 20.1 to done, evidence entry.
- **New** `docs/operations/phase20-t1-model-manager.md` — short task report (this one is
  mostly code, so the report can be brief: design rationale, real VRAM probe evidence,
  test coverage summary).

**Not allowed:** any file under `frontend/`, `video-renderer/`, `venv-kokoro/`,
`venv-styletts2/`, prior phase reports. No image or music model work — that is 20.2 and
Phase 22. `data/app.db` is `mode=ro`.

## Design decisions (Coder, doc-first — commit under `docs(review)` before code)

### D20.1-a: How free VRAM is measured

Options:
- **(i) `nvidia-smi` subprocess** — what you proposed in Task 21.1b. Works without extra
  deps, already proven on this machine. Cost: a subprocess spawn (~50–200 ms) per check.
- **(ii) `torch.cuda.mem_get_info()`** — no subprocess, returns `(free, total)` in bytes
  directly from the CUDA driver. torch is already installed (2.11.0+cu128). Faster and
  more precise, but reports only the current process's visible device state.
- **(iii) `pynvml` / `nvidia-ml-py`** — the library `nvidia-smi` itself wraps. New
  dependency, but no subprocess and gives whole-device truth including other processes
  (which is what matters here, since Ollama is a separate process).

Recommend **(iii) or (ii)**, not (i) — but verify with a real probe: does
`torch.cuda.mem_get_info()` see memory held by the **separate Ollama process**, or only
this process's own allocations? That distinction decides the answer. Run the real test
(load qwen via `ollama run`, then call each method from Python, compare against
`nvidia-smi`) and cite the three numbers side by side.

If (ii) turns out to only see the local process, it is the wrong tool here and (iii) or (i)
wins.

### D20.1-b: The manager's public shape

Sketch the API in the design commit. A rough starting point, not binding:

```python
class GpuModelManager:
    async def acquire(self, model_key: str, required_mib: int, loader: Callable) -> Any: ...
    async def release(self, model_key: str) -> None: ...
    def free_vram_mib(self) -> int: ...
    def loaded_models(self) -> list[str]: ...
```

Questions to answer:
- Does `acquire` block and wait when VRAM is short, or fail fast so the caller can
  degrade? **Recommend fail fast** — it matches every fallback pattern the project already
  uses (Phase 18 cloud→local, Task 19.7 Remotion→ffmpeg, Phase 21 GPU-TTS→Edge TTS). A
  blocking wait would stall a user-facing request for an unbounded time.
- Is it a context manager (`async with manager.acquire(...) as model:`) so release is
  automatic even on exception? Recommend yes.
- One model at a time, or several if they fit? Recommend allowing several while free VRAM
  permits — the manager's job is bookkeeping, not an artificial single-slot rule.
- What happens on double-acquire of the same key? Recommend refcount, release on last
  release.

### D20.1-c: What "unload" actually does

Unloading a torch model is not just `del model`. Document what the manager really does:
`del` the references, `gc.collect()`, `torch.cuda.empty_cache()`, and verify with a real
before/after VRAM probe that memory actually returned. Include that real measurement in
the report — "we called empty_cache" is not evidence that memory was freed.

### D20.1-d: Configuration

- `DIE_GPU_ENABLED: bool = True` — master switch; when false, `acquire` always fails fast
  and every caller degrades to its CPU path. Gives owner one lever to make the whole app
  GPU-free.
- `DIE_GPU_VRAM_HEADROOM_MIB: int` — reserve that is never allocated (recommend 512–1024
  MiB, justify the number). Prevents the manager from filling the card to the last byte and
  triggering an OOM inside a model that allocates a little extra mid-inference.
- Whether to add `DIE_GPU_MAX_CONCURRENT_MODELS` — probably not needed if free-VRAM
  accounting is honest, but say why.

### D20.1-e: Testability without a GPU

The unit tests must run on a machine with no CUDA (CI, fresh checkout, the packaged `.exe`
test path). Inject the VRAM probe so tests can fake "10 GB free" or "200 MiB free" and
assert the manager's decisions. No test should require a real GPU.

Include at least: enough-VRAM acquires successfully, not-enough-VRAM fails fast with a
clear error, release actually frees the bookkeeping slot, double-acquire refcounts
correctly, `DIE_GPU_ENABLED=false` short-circuits everything.

### D20.1-f: Which consumer gets wired in this task

Depends on how Phase 21 ended:
- **Phase 21 shipped a GPU TTS engine** → wire it through the manager, and its existing
  ad-hoc VRAM check gets removed in favor of the shared one. Real integration test.
- **Phase 21 ended STOP** → no GPU consumer exists yet. Ship the manager with unit tests
  only, and say so plainly in the report. 20.2 will be its first real consumer.

State which case applies, with the Phase 21 gate outcome cited.

## Verification

- Full suite green (1205 baseline + the new tests; state the real number).
- `ruff check .` clean.
- Real VRAM probe evidence: the three-way comparison from D20.1-a, and the before/after
  unload measurement from D20.1-c.
- **Revert-and-confirm-failure** on the free-VRAM guard: make `free_vram_mib()` always
  return a huge number, confirm the not-enough-VRAM test fails for the right reason,
  restore.
- If a real GPU consumer was wired (D20.1-f case 1): one real end-to-end synthesis through
  the manager, with a VRAM probe before / during / after.

## Evidence (handover)

- Two shas (design + implementation).
- Full-suite line, ruff line.
- The D20.1-a three-way probe numbers (nvidia-smi vs torch vs pynvml, with Ollama loaded).
- The D20.1-c before/after unload numbers.
- Which D20.1-f case applied.
- Any deviation from the recommended API shape, with reasoning.

## Definition of done

- Two commits, design before implementation.
- Manager exists, is unit-tested without a GPU, and has real VRAM probe evidence behind
  its choice of measurement method.
- `DIE_GPU_ENABLED=false` verified to make the whole thing inert.
- Report on disk.
- Handover per the Evidence checklist.
