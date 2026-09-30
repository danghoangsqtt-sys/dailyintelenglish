# Phase 21 Task 21.1b — StyleTTS 2 spike: install, measure, compare

- **Task:** 21.1b (Coder). Design record: `.viepilot/phases/21-tts-kokoro/tasks/task-21.1b.md`
  (D21.1b-a..g; design `a1727d3`; implementation `9b91d43`, plus the `torch.load` fix in
  `fb830cf`).
- **Run:** 2026-09-30 on the owner's PC by an executor agent, following
  `docs/operations/owner-runbook-2026-09-30-r2.md` pinned at `b67921d`. Evidence branch
  `owner-runs/20260930-r2` @ `5fd2929`. All numbers below are copied from that branch's JSON
  and text files.
- **Scope:** spike only. `data/app.db` was opened `mode=ro`.

## 1. Environment

- **GPU:** NVIDIA GeForce RTX 3060, 12288 MiB, driver 616.56.
- **`venv-styletts2`:** Python 3.11.9. `torch 2.11.0+cu128` (CUDA 12.8,
  `cuda.is_available() == True`, installed from the cu128 index).
  `styletts2==0.1.6`, `nltk==3.10.3`.
- **Reused venv:** `venv-styletts2` already existed from the earlier local 21.1b session. Two
  leftover processes running from it (PIDs 49908, 44024) had caused run 1's `Errno 13`; they
  were stopped under runbook B0, and the venv was reused.
- **Model:** `yl4579/StyleTTS2-LibriTTS` (`epochs_2nd_00020.pth`), plus the ASR, JDC and
  PL-BERT auxiliary checkpoints from the authors' GitHub. They are cached under
  `models/styletts2/`.

## 2. Install footprint (measured on the owner's machine)

| Component | Size |
|---|---|
| `venv-styletts2/` | 5.39 GB |
| `models/styletts2/` | 1.86 GB |

The models folder is larger than the ~0.87 GB of weights because it also holds the earlier
local session's cache (its WIP used `whisper-timestamped`). **Total ≈ 7.25 GB**, compared
with Kokoro's ~1.51 GB and Chrome Headless Shell's ~0.27 GB.

## 3. Python-compat approach

StyleTTS 2 runs in a subprocess-isolated Python 3.11 environment
(`scripts/styletts2_worker.py`), because `tokenizers==0.19.1` cannot build on 3.14
(D21.1b-a).

Two latent blockers were fixed **before** the owner-machine run, each reproduced first:
- the nltk `punkt_tab` lookup;
- the `torch>=2.6` `weights_only` default, which rejects the legacy checkpoints.

Neither occurred on the owner's machine: no errors, and both `.err` files are empty.

## 4. The three test lines (real, from `b330d37f…`)

The same lines as 21.1:
- **Line 0:** "Hey Maya, are you an early bird or a night owl?"
- **Line 24:** "Exactly. Small changes can help you wake up on the right side of the
  bed."
- **Line 29:** "I will! Wish me luck!"

**Voices, picked by measured median F0** from the upstream `reference_audio.zip`. Only
anonymous LibriTTS speakers were considered:

| Candidate clip | Median F0 | Picked as |
|---|---|---|
| `4077-13754-0000.wav` | 115.87 Hz | **male** |
| `908-157963-0027.wav` | 93.93 Hz | – |
| `5639-40744-0020.wav` | 134.26 Hz | – |
| `1221-135767-0014.wav` | 182.87 Hz | **female** |

## 5. StyleTTS 2 measurements (GPU)

| Line | Voice | Duration | Wall time | RTF |
|---|---|---|---|---|
| 0 | male | 4.048 s | 2.781 s | 0.687 (first request of the worker's life) |
| 0 | female | 3.923 s | 0.219 s | 0.056 |
| 24 | male | 5.248 s | 0.359 s | 0.068 |
| 24 | female | 5.748 s | 0.297 s | 0.052 |
| 29 | male | 2.198 s | 0.218 s | 0.099 |
| 29 | female | 2.023 s | 0.157 s | 0.078 |

- **Warm RTF: 0.05–0.10**, about 3–5× faster than Kokoro on CPU (~0.28).
- **Load:** import 7.9 s. `model_load_sec` 243.4 s on this first run includes downloading
  the weights; a warm load was not measured separately.
- **Worker RSS:** ~2.6 GB.
- **VRAM, from `nvidia-smi` snapshots:**

  | Snapshot | Used / free (MiB) |
  |---|---|
  | before the worker | 1104 / 11007 |
  | after model load | 1936 / 10175 |
  | after 6 clips | 2570 / 9541 |
  | after unload | 1214 / 10897 |

  **StyleTTS 2 needs ≈ 1.47 GB of VRAM at peak, not the 4–6 GB the design assumed.**
- **Word timing:** none is emitted (D21.1b-d, by design). 21.2 should use the model's own
  `pred_dur` (card finding 6).

## 6. Edge TTS baseline

Synthesized in the same run through 21.1's own helper: **6/6 ok**, with the same voices as
21.1 (Jenny / Guy). 21.1's timing table stays the reference (§4 of
`phase21-spike-kokoro.md`).

## 7. GPU-sharing behaviour (D21.1b-e)

| Run | qwen state | Free VRAM | Worker handshake |
|---|---|---|---|
| 1 | idle (`ollama ps` empty) | 11007 MiB | `ready`, `cuda` |
| 2 | loaded (`ollama run`, ctx 4096, 5.5 GB, 100% GPU) | 4677 MiB | **`unavailable` / `insufficient_vram`** |

The fail-safe policy worked exactly as designed. Run 2 falls back instead of risking an
OOM.

**The measurement also shows the 6144 MiB threshold is too conservative.** StyleTTS 2's
real peak (≈1.47 GB) would have fit in the 4677 MiB free alongside qwen.

- **Proposal for 21.2 (PM decision):** lower `DIE_GPU_MIN_FREE_MB_STYLETTS2` (and the
  worker's own default) to **2560 MiB**, which is the measured peak plus ~1 GB margin.
  StyleTTS 2 could then run **without evicting qwen** at all.
- Until then, the Task 20.1 lease will evict qwen whenever it is resident. That is
  correct, but it costs one qwen reload (≈12 s, measured in Task 20.2's run).

## 8. Side-by-side

| | Edge TTS | Kokoro (21.1, STOP) | StyleTTS 2 (this spike) |
|---|---|---|---|
| Runs on | cloud | CPU | GPU (~1.5 GB VRAM) |
| Warm RTF | network-bound | ~0.28 | **0.05–0.10** |
| Footprint | 0 | ~1.51 GB | ~7.25 GB |
| Licence | service | Apache-2.0 | MIT |
| Native word timing | yes | yes | no (`pred_dur` path for 21.2) |
| Owner listening | "không tự nhiên" (not natural) | STOP ("robot Star Wars") | **pending (§9)** |

## 9. Owner listening protocol

File: `owner-runs/20260930-r2/B/spike_comparison_styletts2.mp3` (1,191,884 bytes). The order
is the 6 StyleTTS 2 clips (line 0/24/29 × male/female), then the 6 Edge TTS clips, with 1
s of silence between clips.

**Question:** is StyleTTS 2 noticeably more natural and emotional than Edge TTS?

## 10. Decision proposal

- **Technical criteria: all pass.**
  - 12/12 clips were produced, with no OOM.
  - It is fast (RTF ≤ 0.10 warm).
  - It uses little VRAM (≈1.47 GB).
  - The fallback policy was verified live in both directions.
- **Costs to weigh:** the footprint is ~7.25 GB, and there is no native word timing.
- **PASS / SCOPE-CUT / STOP hinges on the owner's listening verdict (§9), which is
  deliberately not pre-decided:**
  - if the owner hears a clear improvement over Edge TTS → **PASS**, and 21.2 opens with
    the StyleTTS 2 provider;
  - if not → **STOP**.
