# Phase 20 Task 20.1 — Shared GPU model manager: report

- **Task:** 20.1 (Coder). Card: `.viepilot/phases/20-ai-visuals/tasks/task-20.1.md`.
  - Part 1: PM card.
  - Part 2: Coder design `b328fd3` and implementation `6b1e7f7`.
  - Part 3: reconciliation R0–R6.
  - Part 4: owner-machine evidence.
- **Evidence branches:** `owner-runs/20260930` @ `f08d59d` (tests + probe) and
  `owner-runs/20260930-r2` @ `5fd2929` (live lease + eviction).

## 1. Design rationale (short)

The GPU consumers live in different processes:
- the Ollama server;
- the StyleTTS 2 worker;
- the SDXL image worker;
- later, a music worker.

So `app/services/gpu_model_manager.py` is an **arbiter, not a loader**. A consumer takes an
exclusive, FIFO, non-re-entrant `lease(consumer, min_free_mb)`. For a lease with
`min_free_mb > 0`, the manager:
- measures free VRAM with `nvidia-smi`;
- evicts Ollama's resident models (`/api/ps`, then `keep_alive: 0`) if there is not
  enough;
- polls up to ~5 s while the driver releases the memory;
- otherwise raises `GpuUnavailableError`, so the caller takes its existing fallback.

Ollama calls themselves take a `min_free_mb=0` lease (owner decision D20.1-c), so qwen
cannot load mid-inference of another model. The kill switch is
`DIE_GPU_MANAGER_ENABLED=false`, which makes the lease a pass-through.

## 2. Real VRAM probe evidence (PM card D20.1-a)

`scripts/probe_vram.py` on the RTX 3060 (driver 616.56):

| State | `nvidia-smi` free | pynvml free | `torch.cuda.mem_get_info` free |
|---|---|---|---|
| idle | 9748 MiB | 9747 MiB | 11250 MiB |
| qwen loaded | 3379 MiB | 3378 MiB | 11250 MiB |

**`nvidia-smi` is confirmed.** It matches pynvml to within 1 MiB. torch does not see memory
held by other processes on this WDDM machine, so it is disqualified (its reading stays at
11250 with and without qwen).

## 3. Real lease and eviction evidence (PM card D20.1-c)

This comes from the Task 20.2 `warm_qwen2` run, with qwen loaded by the app's own
`OllamaProvider` at `num_ctx=16384`:

| Point | Used / free (MiB) |
|---|---|
| start | 275 / 11836 |
| after warm qwen | 7147 / 4964 |
| lease acquired (`min_free_mb` 8192) | 275 / 11836 |
| image worker exited | 269 / 11842 |

- **The lease evicted `qwen3.5:9b`**: free went from 4964 to **11836 MiB**, and the lease
  returned without waiting on the lock (`waited_seconds 0.0`).
- **Unload is real:** after each worker process exits, VRAM is back at its baseline to
  within ±6 MiB. Process exit frees everything, including the CUDA context.
- **The cost of an eviction:** the next local qwen call reloads in **12.1 s** (the first
  load took 12.7 s).
- **qwen's own footprint at the app's `num_ctx=16384`:** 6872 MiB (7147 − 275). At
  `ollama run`'s ctx 4096 it was 6369 MiB (8732 − 2363). The larger context costs about
  **+0.5 GB**, which confirms Part 2 finding 2.
- **Negative path, also live (Task 21.1b run 2):** with qwen resident and 4677 MiB free,
  the StyleTTS 2 worker's own threshold refused to load (`insufficient_vram`) and fell
  back as designed.

## 4. Test coverage

- **30 new tests:** `tests/test_gpu_model_manager.py` (24) and `tests/test_ai_providers.py`
  (+6).
- **Mutation-checked:** a lock that is not rebuilt per loop, removing the lease from
  `generate`, and removing the eviction poll each make their tests fail.
- **Full suite on the owner's machine: `1235 passed, 2 warnings`**, with 0 failures. The 2
  warnings are third-party deprecations.

## 5. Which D20.1-f case applied

**Case 2 plus Ollama.** Phase 21 has not finished its gate (the 21.1b owner listening is
pending), so no GPU TTS consumer is wired yet. Ollama is wired (owner-approved). The 20.2
spike runner is the first real non-Ollama lease user, and it was verified live (§3).

## 6. Open items for the PM (from card Part 3)

- **R2:** exclusive lease vs several models; an optional lock-wait timeout.
- **R4:** the master-switch semantics. PM's `DIE_GPU_ENABLED` and the Coder's
  `DIE_GPU_MANAGER_ENABLED` mean opposite things.
- **R5:** the module path (`app/services/gpu_model_manager.py` vs
  `app/services/gpu/model_manager.py`).
- **New measured thresholds proposed:**
  - StyleTTS 2 **2560 MiB** (measured peak ≈1.47 GB, so it could coexist with qwen
    without eviction);
  - image backgrounds **9728 MiB**;
  - image with IP-Adapter **11264 MiB**.

  Sources: `phase21-spike-styletts2.md` §7 and `phase20-spike-images.md` §4.
