# Task 20.1 — Shared GPU model manager (load / free-VRAM check / unload)

> **Part 1: the PM card** (D37, commit `9b5c8f9`, 2026-09-29). Unchanged except for the
> Status line. Parts 2 and 3 follow below.

- **Status:** *(Coder update 2026-09-30; the PM's original text is kept below.)*
  **Implemented. Awaiting owner-machine verification and PM acceptance**, and PM
  decisions on the deviations listed in Part 3. It was started before the Phase 21 gate
  on the owner's explicit instruction of 2026-09-30 (Part 3, R0).
  PM original: "not started (doc-first card; **do not start until Phase 21's spike gate
  resolves** — Coder is single-session and Phase 21 has priority)"
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

---

# Part 2 — Coder design + implementation (2026-09-30, cloud session)

**How this card was assembled:** this Part 2 was written in the cloud session
*without* the Part 1 PM card. Commit `9b5c8f9` existed only on the owner's local `main`
and was recovered on 2026-09-30 through the backup branch `owner-local/backup-20260930`.
The design was committed as `b328fd3` and the implementation as `6b1e7f7`, both on
`claude/admiring-knuth-r1d8vc`. Part 2 uses its **own** decision ids (D20.1-a..g), which
**do not mean the same thing as Part 1's** D20.1-a..f. Commits `b328fd3`/`6b1e7f7` and the
code comments cite the Part 2 ids. Part 3 maps one set onto the other.

### Task statement (owner summary, 2026-09-30)

> Model manager solves a real problem. Measured with nvidia-smi: with Ollama qwen loaded,
> the card has only 3916 MiB free out of 12288. None of the three new jobs (StyleTTS 2,
> the image model, music) can run alongside it. But the pipeline is already sequential:
> each step needs only its own model and can then release it. What is missing is one
> place that does this load/release for everyone, instead of three phases writing it
> three different ways.

### What the real code does today (investigated, 2026-09-30)

1. **qwen stays resident for 5 minutes after every local call.** In
   `app/services/ai/ollama_provider.py:70` every `/api/generate` sends
   `"keep_alive": "5m"`. Once the cloud chain falls back to local, qwen holds its VRAM for
   5 minutes after the last call, with nothing in the app able to release it early.
2. **The 3916 MiB figure is optimistic for the real app.** It was measured with
   `ollama run qwen3.5:9b`, which ran at `CONTEXT 4096` (the `ollama ps` output in
   task-21.1b.md D21.1b-e). The app calls qwen with `num_ctx=16384`
   (`app/core/config.py:96`, `OLLAMA_NUM_CTX`), and a 4× context means a larger KV cache.
   Under the app's own settings, free VRAM with qwen loaded is therefore *below* 3916 MiB.
   This strengthens the case for the manager: waiting for qwen to "fit alongside" is not
   an option, so it has to be evicted. **To measure on the owner's machine** as part of
   implementation verification.
3. **The GPU consumers run concurrently today, not strictly in sequence.**
   - Script and learning jobs run in the background `AIWorker` loop
     (`app/services/ai_worker.py:93`, one job at a time).
   - Audio, video and thumbnail run inside HTTP request handlers (`app/api/audio.py:30`,
     `app/api/video.py:47`, `app/api/thumbnail.py:31`).

   So a qwen-fallback script job for one project can overlap with the owner pressing
   "Generate thumbnail" or (after 21.2) StyleTTS 2 audio for another. Each pipeline is
   sequential, but the app as a whole is not.
4. **Thumbnails collide with themselves.** `thumbnail_service` already calls the AI
   router for headline/palette text (`thumbnail_service.py:51`, `:113`). In fallback that
   loads qwen. With 20.3, the same request would then want the image model, while qwen
   still holds its 5-minute residency from a few seconds earlier. Without eviction, 20.3
   would fail (or OOM) exactly when the cloud chain is down.
5. **Existing GPU-adjacent code to reuse:**
   - `app/core/system_checks.py:25` `get_gpu_info()` already runs `nvidia-smi` through
     `asyncio.create_subprocess_exec` (no blocking call on the event loop, AR-05).
   - `validate_loopback_url` (`ollama_provider.py:21`) already guards the Ollama base URL
     (anti-SSRF).
   - `tts_service`'s `_omnivoice_semaphore` is the one earlier GPU guard. It is dead code
     since OmniVoice was dropped (Task 1.6); noted here, not touched.

### Design decisions (Coder)

#### D20.1-a: Shape: an arbiter with a lease, not a loader

The three consumers live in three different processes:
- Ollama is a separate server;
- StyleTTS 2 runs in `venv-styletts2/` through a subprocess worker (Task 21.1b);
- the image and music models will almost certainly need the same subprocess isolation
  (torch/diffusers pins vs. the project's Python 3.14, the same pattern as 21.1 and
  21.1b).

The app process cannot "load" them in one uniform way. What it *can* do uniformly is
decide who gets the GPU and free it. So the manager arbitrates; each consumer still owns
its own load and unload.

```python
# app/services/gpu_model_manager.py (proposed)
async with gpu_manager.lease("styletts2", min_free_mb=settings.GPU_MIN_FREE_MB_STYLETTS2) as lease:
    ...  # spawn/load the worker, synthesize, unload -- GPU is exclusively ours here
# on exit: lease released; the next waiter (e.g. a qwen fallback call) proceeds
```

`lease()` does the following:
1. Acquire one process-wide `asyncio.Lock`: one RTX 3060, one holder at a time.
2. Measure free VRAM (D20.1-d).
3. If free VRAM is below `min_free_mb`, evict Ollama's resident models (D20.1-b) and
   measure again.
4. If it is still short, release the lock and raise `GpuUnavailableError`. The caller
   takes its existing fallback: Edge TTS (Task 19.7's I36 pattern) or the template
   thumbnail (ENH-012's own acceptance criterion).

A `lease` is **not re-entrant**. Nesting (for example, a thumbnail lease wrapping a router
call that also wants a lease) raises immediately instead of deadlocking. The call sites
in 20.3 and 21.2 must take the lease *after* the text step, not around it.

#### D20.1-b: How Ollama gets evicted (documented API, to verify live)

Ollama's documented API:
- `GET /api/ps` lists resident models with `name` and `size_vram`;
- `POST /api/generate` with `{"model": <name>, "keep_alive": 0}` and no prompt unloads
  that model (Ollama FAQ, "How do I unload a model from memory?"; the CLI equivalent is
  `ollama stop <model>`).

Plan: add `list_resident_models()` and `unload(model)` to `OllamaProvider`, through the
same `validate_loopback_url` base URL, so there is no new network surface.

**Not verified in this session.** The design pass ran in a cloud container with no Ollama
and no GPU. Before acceptance, verification must show on the owner's machine that
`nvidia-smi` free VRAM actually goes up after `unload()`, and how long qwen takes to
reload afterwards. Unit tests use `httpx.MockTransport` for the API shape.

#### D20.1-c: Should Ollama calls take the lease too? (PM decision needed)

This is the one real trade-off in the design.

- **(i) Yes (recommended).** `OllamaProvider.generate` takes a lease (`min_free_mb=0`, so
  it never evicts anyone, it only waits its turn). The wait is bounded by the router's
  existing request deadline; on timeout it raises `ProviderTimeoutError`, which the router
  already handles. This makes it impossible for qwen to load while StyleTTS 2 or the image
  model is mid-inference. Cost: a local-fallback script call can wait for the duration of
  one TTS batch or one image (seconds to tens of seconds). This only happens when the
  cloud chain is already down.
- **(ii) No.** Ollama calls ignore the lease. Ollama does not OOM; it splits layers
  between GPU and CPU to fit whatever is free. But the PyTorch consumer that is already
  running can still OOM when its next allocation meets a freshly loaded qwen. That race is
  exactly what the manager exists to remove.

Recommend (i). In `cloud_first` mode (the default since D31), local calls are rare, and
correctness matters more than a few seconds of waiting on a path that is already
degraded.

`keep_alive: "5m"` stays as it is. Keeping qwen resident between the many calls of one
script job is a real speed-up, and eviction now covers the case where something else
needs the card.

#### D20.1-d: Measuring VRAM: `nvidia-smi`, no new dependency

`nvidia-smi --query-gpu=memory.used,memory.free,memory.total --format=csv,noheader,nounits`
goes through the existing `asyncio.create_subprocess_exec` pattern in `system_checks.py`,
as a new `get_gpu_memory()` next to `get_gpu_info()`.

- `pynvml` would add a dependency to the packaged .exe for no gain.
- torch is not in the main venv at all.
- `nvidia-smi` is already what every recorded measurement in Phases 19/21 used, so the
  thresholds and the runtime check use the same instrument.

With no NVIDIA GPU (a CI or cloud container, or a machine without a driver),
`get_gpu_memory()` returns `None` and `lease()` raises `GpuUnavailableError` straight
away. Every consumer then goes to its fallback. The whole suite can exercise that path
with no GPU.

#### D20.1-e: Thresholds and kill switch come from config, not constants

Consistent with CR-02 and the `DIE_` prefix:
- `DIE_GPU_MANAGER_ENABLED` (default `true`). When `false`, `lease()` is a pass-through:
  no lock, no eviction, today's behaviour exactly. This is the reversible kill switch in
  the spirit of invariant I36.
- `DIE_GPU_EVICT_OLLAMA` (default `true`). When `false`, a lease that finds too little
  VRAM fails over to the fallback instead of evicting qwen.
- `DIE_GPU_MIN_FREE_MB_STYLETTS2=6144`. This is the measured value from D21.1b-e, and
  matches `styletts2_worker.py`'s own default.
- The image model's and the music model's thresholds are **not guessed here**. Tasks 20.2
  and 22.x add them from their own spike measurements. A consumer with no configured
  threshold cannot take a lease: `lease()` requires the number.

#### D20.1-f: Observability

Every lease logs the following as one structured line (same `logger` style as the
router):
- consumer, wait time, free VRAM before and after, any models evicted, and outcome.

`/health` gains the current `get_gpu_memory()` numbers next to the existing
`get_gpu_info()`. This way a gate report can cite live numbers from the app itself.

#### D20.1-g: What 20.1 does NOT do

- No consumer is wired in except Ollama (D20.1-c). StyleTTS 2 is wired by 21.2 (if 21.1b
  passes), the image model by 20.3, music by Phase 22.
- No cross-process or multi-instance locking. The desktop app runs one FastAPI process.
  A second app instance is out of scope, and this is stated in the module docstring.
- The dead OmniVoice semaphore in `tts_service.py` is not touched: it is out of scope,
  and cleaning it up would be an unassigned change (AR-06).

### Proposed allowed files (for PM approval)

- **New** `app/services/gpu_model_manager.py`: lease, lock, eviction policy,
  `GpuUnavailableError`.
- `app/core/system_checks.py`: add `get_gpu_memory()`.
- `app/services/ai/ollama_provider.py`: `list_resident_models()`, `unload()`, and the
  lease around `generate` (if D20.1-c (i) is approved).
- `app/core/config.py` and `.env.example`: the settings from D20.1-e.
- `app/core/exceptions.py`: `GpuUnavailableError`.
- `app/main.py`: GPU memory in `/health` only.
- **New** `tests/test_gpu_model_manager.py`; `tests/test_ai_providers.py` (Ollama provider) and
  `tests/test_ai_health_api.py` (`/health`), which already cover these areas: extended, not duplicated.
- `CHANGELOG.md`: one bullet under `[Unreleased]`.

**Not touched:** `frontend/`, `video-renderer/`, `scripts/` (including 21.1b's worker),
`venv-*`, `data/app.db`.

### Risks

| Risk | Mitigation |
|---|---|
| Deadlock from a nested lease | Non-re-entrant lease with a task-local marker: nesting raises at once, and there is a test for it |
| A qwen call waits behind a long GPU batch | The wait is bounded by the router's existing deadline, and a timeout goes down the router's existing error path |
| Evicting qwen in the middle of a script job costs a reload | Only happens when another consumer actually needs the card. Measure the reload time on the owner's machine. `DIE_GPU_EVICT_OLLAMA=false` turns eviction off |
| `nvidia-smi` latency on Windows | Called once or twice per lease, not per token. Measure it and report the number |
| Ollama API shape differs from the docs | Parse defensively. On an unexpected shape, log it and treat it as "could not evict", so the consumer falls back instead of crashing. Verify live before acceptance |
| Behaviour change for current users | Only Ollama calls are wired in. On a machine where nothing else takes the lease, those calls acquire an uncontended lock, so behaviour does not change. The kill switch restores today's code path exactly |

### Tests to run

- New unit tests: lease exclusivity and ordering; eviction happens only when free VRAM is
  below the threshold; still short after eviction → `GpuUnavailableError`; no GPU →
  `GpuUnavailableError`; nested lease → error; kill switch → pass-through; a consumer with
  no threshold is refused; Ollama `/api/ps` and unload through `httpx.MockTransport`,
  including an unexpected response shape.
- Full suite (baseline **1205/1205** per the Phase 21 preflight), and `ruff check .`
  clean.
- **Owner-machine verification** (the implementation handover cannot claim these from a
  cloud session):
  - `nvidia-smi` free VRAM before and after a real qwen eviction;
  - qwen reload time;
  - one real lease cycle with qwen loaded at the app's `num_ctx=16384`, which also
    measures D20.1's finding 2.

### Definition of done

- The PM approves this design (or amends D20.1-c).
- Implementation stays inside the allowed files, and all tests pass.
- Owner-machine verification numbers are recorded in this card's evidence section.

### Implementation (2026-09-30, Coder)

**PM/owner approval:** the owner replied "có" (yes) to D20.1-c on 2026-09-30, meaning
Ollama calls take the lease too, per option (i). Implemented inside the approved allowed
files, with one deviation noted below.

#### What landed

- `app/services/gpu_model_manager.py`:
  - `GpuModelManager.lease(consumer, min_free_mb)`: exclusive, FIFO.
  - `min_free_mb=0` waits its turn only. `>0` measures free VRAM, evicts Ollama if short,
    polls up to 10 × 0.5 s while the driver releases memory, and otherwise raises
    `GpuUnavailableError`. `None` is refused (`no_measured_threshold`).
  - Not re-entrant: nesting raises `GpuLeaseNestingError`.
  - The lock is rebuilt per event loop.
  - Kill switch = pass-through.
  - Process-wide `get_gpu_manager()` / `set_gpu_manager()`.
- `app/core/system_checks.py`: `get_gpu_memory()` (`nvidia-smi` used/free/total MiB, or
  None).
- `app/services/ai/ollama_provider.py`:
  - `generate` runs inside `lease("ollama", min_free_mb=0)`. `latency_ms` is still the
    HTTP time only; the lease wait is logged by the manager.
  - New `list_resident_models()` (`GET /api/ps`, defensive parsing), `unload(model)`
    (`keep_alive: 0`, no prompt, no lease), and `unload_all_resident()`, which never
    raises.
- `app/core/exceptions.py`: `GpuUnavailableError` (503, with `reason`, `free_mb`,
  `min_free_mb`).
- `app/core/config.py` + `.env.example`: `GPU_MANAGER_ENABLED`, `GPU_EVICT_OLLAMA`,
  `GPU_MIN_FREE_MB_STYLETTS2=6144`.
- `app/main.py`: `/health` adds live `gpu_memory` and `gpu_manager_enabled`.
- Tests:
  - new `tests/test_gpu_model_manager.py` (24 tests);
  - `tests/test_ai_providers.py` +6 tests, including one where the router's own budget
    bounds a qwen call queued behind another consumer: `ProviderTimeoutError`, and the
    HTTP call never starts.
- `CHANGELOG.md`: one bullet.

**Deviation from the allowed list:** the `/health` test went into the new
`tests/test_gpu_model_manager.py`, not `tests/test_ai_health_api.py`. That file tests
`/api/ai/health`, not `/health`. The existing `/health` test lives in
`tests/test_projects_api.py`, which was left untouched.

#### Verification in this session (cloud container: Python 3.13, no GPU, no Ollama)

| Check | Result |
|---|---|
| New and extended tests | 30 new, all pass |
| Mutation check: rebuild the lock once only / remove the lease from `generate` / remove the post-eviction poll | each one makes the matching test(s) fail (1, 1, 2), so the tests do guard the behaviour |
| Full suite, excluding the 26 `*browser*` files (no Playwright here) | **1056 passed, 2 failed**. Clean-tree baseline in the same environment: **1026 passed, the same 2 failed**. **0 new failures** |
| The 2 pre-existing failures | `test_word_boundaries_match_real_edge_tts_output`: the cloud proxy breaks TLS to `speech.platform.bing.com` (environment). `test_concurrent_script_saves_do_not_interleave`: `Lock ... is bound to a different event loop` from the existing module-level `write_lock` in `app/db/transactions.py`, on Python 3.13 here. This is the same class of bug the manager's per-loop lock avoids. Not touched (out of scope) |
| `ruff check` on every changed file | clean. `ruff check .` shows 1 pre-existing F401 in `scripts/run_gate_b12.py`, also present on the clean tree; not touched |

The full suite with browser tests (owner-machine baseline 1205) was not run here.

#### Still owed: owner-machine verification (before PM acceptance)

1. With qwen loaded by the app itself (a local-mode script job, `num_ctx=16384`), record
   `/health` `gpu_memory.free_mb`. This measures finding 2 (is it below 3916 MiB?).
2. Run one real lease with room needed, with qwen still resident (within 5 min of step 1).
   Save these lines as `verify_lease.py` in the project root and run
   `venv\Scripts\python verify_lease.py`:
   ```python
   import asyncio, logging, time
   from app.services.gpu_model_manager import get_gpu_manager
   logging.basicConfig(level=logging.INFO)
   async def main():
       t = time.monotonic()
       async with get_gpu_manager().lease("verify", min_free_mb=6144) as lease:
           print(lease, f"{time.monotonic() - t:.2f}s")
   asyncio.run(main())
   ```
   Record the printed free VRAM before and after eviction, the evicted model list, and
   the time. Then delete the file.
3. Record qwen's reload time on the next script call after an eviction.
4. Run the full suite including browser tests (baseline 1205).


---

# Part 3 — Reconciliation with the PM card (for PM decision)

**R0. Sequencing.** Part 1 says not to start until the Phase 21 spike gate resolves. On
2026-09-30 the owner instructed, verbatim: *"tôi nghĩ nếu chưa chạy được test thử giọng thì
cứ làm các task tiếp theo"* ("I think that if the voice test can't be run yet, just go
ahead with the next tasks"), and then listed 20.1 next. The 21.1b spike still needs the
owner's GPU. Case D20.1-f therefore applies as "no GPU TTS consumer yet" (see R6).

| PM (Part 1) | Coder (Part 2) | Status |
|---|---|---|
| D20.1-a measurement method: recommends pynvml or torch, requires a 3-way real probe | D20.1-d: `nvidia-smi` | **Deviation, evidence owed** (R1) |
| D20.1-b API: acquire/release with a loader, fail fast, context manager, several models if they fit, refcount | D20.1-a: context-manager lease, arbiter not loader, **exclusive**, **waits its turn** for the lock, fails fast on VRAM | **Deviation** (R2) |
| D20.1-c unload + before/after evidence | Consumers unload in their own subprocess, and process exit frees everything; Ollama is evicted via its API (D20.1-b) | Evidence owed via the runbook (R3) |
| D20.1-d `DIE_GPU_ENABLED` + `DIE_GPU_VRAM_HEADROOM_MIB` | D20.1-e `DIE_GPU_MANAGER_ENABLED` / `DIE_GPU_EVICT_OLLAMA` / per-consumer thresholds | **Deviation: opposite switch semantics** (R4) |
| D20.1-e tests without a GPU | done: injected probe, 30 tests, mutation-checked | Matches, with R2's refcount difference |
| D20.1-f which consumer gets wired | Ollama (owner-approved, Part 2 D20.1-c); no GPU TTS consumer yet | Deviation from the allowed files (R6) |

**R1. The measurement method.** The Coder chose `nvidia-smi` because:
- torch is **not** a declared dependency of the app (it is not in `requirements.txt`; the
  `2.11.0+cu128` in the owner's venv is an OmniVoice leftover, per the 21.1 report §1);
- pynvml would add a new dependency to the packaged .exe;
- `nvidia-smi` reports whole-device memory, including Ollama's separate process.

The PM's 3-way probe was still **not done**, because it needs the owner's GPU. It is
added to the owner runbook: `scripts/probe_vram.py`, run in `venv-image` at idle and
with qwen loaded, printing the `nvidia-smi` / `torch.cuda.mem_get_info` / pynvml numbers
side by side. If the probe shows `nvidia-smi` disagreeing with pynvml, switching is a
one-function change in `system_checks.get_gpu_memory`.

**R2. Exclusive lease vs several models.** The consumers are separate processes whose
peak VRAM the manager cannot see in advance. Admitting two consumers on a free-VRAM
reading races: both measure before either allocates. Exclusivity removes that race, and
the pipeline is sequential anyway. Waiting for the lock is bounded for Ollama by the
router's deadline, but **unbounded for other consumers**, which is exactly the PM's
"stall a user-facing request" concern.
- **Proposed follow-up (PM to decide):** a `lock_wait_seconds` argument (default from
  config) that turns a long wait into `GpuUnavailableError("busy")`, so a request can fall
  back instead of stalling. It is small and additive.
- There is no loader callable because loading happens inside the consumer's own
  subprocess.
- There is no refcount because nesting is refused on purpose, to prevent deadlock.

**R3. Unload evidence.** The runbook's image spike records `gpu_snapshots` at lease
acquired and after worker exit, plus the worker's own `unload` stats (the gap between
"unloaded" and "process exited"). The `warm_qwen` run records Ollama's before/after
eviction numbers and qwen's reload time.

**R4. The master switch means opposite things (needs a PM decision).**
- PM `DIE_GPU_ENABLED=false`: make the whole app GPU-free, with every consumer falling
  back.
- Coder `DIE_GPU_MANAGER_ENABLED=false`: turn off *management*, restoring the exact
  pre-20.1 behaviour.

They are different levers, and both can exist. A proposed small follow-up: add
`DIE_GPU_ENABLED`, which, when false, makes every lease with `min_free_mb > 0` raise
`GpuUnavailableError("gpu_disabled")`. Ollama is unaffected, because it picks its own
device. Headroom is expressed per consumer (measured peak + stated margin, e.g.
`DIE_GPU_MIN_FREE_MB_STYLETTS2=6144`) instead of one global number, for the same
purpose.

**R5. Module path and allowed files.**
- The code is at `app/services/gpu_model_manager.py`, not `app/services/gpu/model_manager.py`.
- It also touched `system_checks.py`, `exceptions.py`, `main.py` (`/health`),
  `ollama_provider.py`, `.env.example` and `tests/test_ai_providers.py`, which are not in
  the Part 1 list.
- The Part 1 report `docs/operations/phase20-t1-model-manager.md` is **owed** after the
  owner-machine evidence arrives.
- Moving the module under `app/services/gpu/` is mechanical, if the PM wants it.

**R6. Consumers.** Ollama is wired (Part 2 D20.1-c, owner "có" = yes, 2026-09-30). No GPU
TTS consumer exists until 21.1b resolves. The 20.2 spike runner is the first real
non-Ollama lease user.

---

# Part 4 — Owner-machine evidence (run 1: `owner-runs/20260930` @ `f08d59d`, pinned `2008649`)

Executed by an agent on the owner's PC, following `docs/operations/owner-runbook-2026-09-30.md`
rev 3.

- **Full suite on the owner's machine (Python 3.14.7): `1235 passed, 2 warnings in 418.90s`.**
  That is the 1205 baseline + the 30 new Task 20.1 tests, with **0 failures**. The two
  failures seen in the cloud baseline do not occur here: Edge TTS has real network, and
  `write_lock` is fine on Python 3.14. The 2 warnings are third-party deprecations
  (starlette/anyio). `ruff`: only the pre-existing F401 in `scripts/run_gate_b12.py`.
- **PM D20.1-a three-way probe, now measured** (`scripts/probe_vram.py`, RTX 3060, driver
  616.56):

  | State | `nvidia-smi` free | pynvml free | `torch.cuda.mem_get_info` free |
  |---|---|---|---|
  | idle | 9748 MiB | 9747 MiB | **11250 MiB** |
  | qwen loaded (`ollama run`, ctx 4096) | 3379 MiB | 3378 MiB | **11250 MiB** |

  **R1 is resolved in favour of `nvidia-smi`.** It agrees with pynvml to within 1 MiB in
  both states. `torch.cuda.mem_get_info` reports the **same 11250 MiB with and without
  qwen**: on this Windows/WDDM machine it does not see memory held by other processes,
  including Ollama's. That is exactly the failure mode the PM card warned about, so
  option (ii) is disqualified by measurement.

  Two more observations:
  - pynvml's per-process `usedGpuMemory` is `None` for every process (WDDM does not
    expose it), so pynvml gives no extra per-process insight either.
  - Today's numbers are about 540 MiB lower than the 21.1b design measurement (10286 idle
    / 3916 with qwen), because desktop VRAM use varies. That is one more reason the
    thresholds are checked at runtime, not assumed.
- **Still owed:** the real Ollama eviction (VRAM before/after + release time) and the
  qwen reload time. The image run that produces them failed for an unrelated,
  now-fixed reason (task-20.2.md, run 1). They are re-requested by
  `docs/operations/owner-runbook-2026-09-30-r2.md` (run `warm_qwen2`).
