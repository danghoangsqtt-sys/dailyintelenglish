# Task 20.1 — Shared VRAM model manager (foundation for Phases 20, 21, 22)

- **Status:** design committed (Coder, doc-first), **awaiting PM approval before any code**
  (AR-06). No `app/` or `tests/` file has been changed.
- **Owner:** Coder
- **Priority:** P0 for Phase 20. It is also used by 21.2 if 21.1b passes, and by Phase 22.
- **Dependency:** none. It is useful whatever Phase 21 decides (owner, 2026-09-30).
- **Card source:** the owner's Phase 20 summary (2026-09-30). The PM has not written a
  card for it in the repo, so this card combines the task statement (taken from that
  summary) with Coder's design answers. The PM should edit the task statement if it does
  not match the PM plan.

## Task statement (owner summary, 2026-09-30)

> Model manager solves a real problem. Measured with nvidia-smi: with Ollama qwen loaded,
> the card has only 3916 MiB free out of 12288. None of the three new jobs (StyleTTS 2,
> the image model, music) can run alongside it. But the pipeline is already sequential:
> each step needs only its own model and can then release it. What is missing is one
> place that does this load/release for everyone, instead of three phases writing it
> three different ways.

## What the real code does today (investigated, 2026-09-30)

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

## Design decisions (Coder)

### D20.1-a: Shape: an arbiter with a lease, not a loader

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

### D20.1-b: How Ollama gets evicted (documented API, to verify live)

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

### D20.1-c: Should Ollama calls take the lease too? (PM decision needed)

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

### D20.1-d: Measuring VRAM: `nvidia-smi`, no new dependency

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

### D20.1-e: Thresholds and kill switch come from config, not constants

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

### D20.1-f: Observability

Every lease logs the following as one structured line (same `logger` style as the
router):
- consumer, wait time, free VRAM before and after, any models evicted, and outcome.

`/health` gains the current `get_gpu_memory()` numbers next to the existing
`get_gpu_info()`. This way a gate report can cite live numbers from the app itself.

### D20.1-g: What 20.1 does NOT do

- No consumer is wired in except Ollama (D20.1-c). StyleTTS 2 is wired by 21.2 (if 21.1b
  passes), the image model by 20.3, music by Phase 22.
- No cross-process or multi-instance locking. The desktop app runs one FastAPI process.
  A second app instance is out of scope, and this is stated in the module docstring.
- The dead OmniVoice semaphore in `tts_service.py` is not touched: it is out of scope,
  and cleaning it up would be an unassigned change (AR-06).

## Proposed allowed files (for PM approval)

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

## Risks

| Risk | Mitigation |
|---|---|
| Deadlock from a nested lease | Non-re-entrant lease with a task-local marker: nesting raises at once, and there is a test for it |
| A qwen call waits behind a long GPU batch | The wait is bounded by the router's existing deadline, and a timeout goes down the router's existing error path |
| Evicting qwen in the middle of a script job costs a reload | Only happens when another consumer actually needs the card. Measure the reload time on the owner's machine. `DIE_GPU_EVICT_OLLAMA=false` turns eviction off |
| `nvidia-smi` latency on Windows | Called once or twice per lease, not per token. Measure it and report the number |
| Ollama API shape differs from the docs | Parse defensively. On an unexpected shape, log it and treat it as "could not evict", so the consumer falls back instead of crashing. Verify live before acceptance |
| Behaviour change for current users | Only Ollama calls are wired in. On a machine where nothing else takes the lease, those calls acquire an uncontended lock, so behaviour does not change. The kill switch restores today's code path exactly |

## Tests to run

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

## Definition of done

- The PM approves this design (or amends D20.1-c).
- Implementation stays inside the allowed files, and all tests pass.
- Owner-machine verification numbers are recorded in this card's evidence section.
