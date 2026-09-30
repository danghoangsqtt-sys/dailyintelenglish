# Phase 20 Task 20.2 — Image model spike: SDXL base vs SDXL-Lightning + IP-Adapter

- **Task:** 20.2 (Coder). Card: `.viepilot/phases/20-ai-visuals/tasks/task-20.2.md`.
  - Design `d787325`, then Amendment A `fe1584c` (owner's Q1/Q2), then implementation
    `518fed8`.
  - Fixes after run 1: threshold `4c0d1fb`, and meta-init plus partial results
    `b67921d`.
- **Run:** 2026-09-30 on the owner's PC by an executor agent, following
  `docs/operations/owner-runbook-2026-09-30-r2.md` pinned at `b67921d`. Evidence branch
  `owner-runs/20260930-r2` @ `5fd2929` (runs `idle2` and `warm_qwen2`).
- **Run 1** (`owner-runs/20260930` @ `f08d59d`) failed on a Coder bug: the UNet was
  materialised in fp32, causing os error 1455. It is fixed and root-caused in the card.

## 1. Candidates (per the owner's constraints: free, commercial, no registration, no watermark)

| Id | Model | Licence |
|---|---|---|
| base | `stabilityai/stable-diffusion-xl-base-1.0` fp16 + `madebyollin/sdxl-vae-fp16-fix`, 30 steps, CFG 6 | OpenRAIL++-M / MIT |
| lightning | the same base + `ByteDance/SDXL-Lightning` 4-step **UNet**, CFG 0, trailing scheduler | OpenRAIL++ |
| IP | `h94/IP-Adapter` `ip-adapter-plus-face_sdxl_vit-h` + ViT-H encoder, on both | Apache-2.0 |

- SDXL-Turbo and FLUX.1-schnell were dropped by the owner (see the card).
- **The watermark was checked live:** `watermark_active: false` in all 4 worker loads.

## 2. Environment and footprint

- **GPU:** RTX 3060 12 GB, driver 616.56.
- **`venv-image`:** Python 3.14.7, `torch 2.11.0+cu128`, `diffusers 0.40.0`.
- **Disk:** `venv-image` 4.84 GB; `models/image` **15.62 GB**, matching the 15.6 GB spike
  set computed from Hub sizes in advance. Production keeps only the winning UNet, so about
  10.5 GB.
- **RAM (preflight):** 33.3 GB visible, 13.6 GB free physical, 8.5 GB free virtual
  (commit).

## 3. Measurements, 1344×768 native, cover-fit to 1280×720 (`idle2` run)

| | base (30 steps) | lightning (4 steps) |
|---|---|---|
| Model load | 11.9 s | 13.3 s |
| Per image (5 episodes) | **21.3–22.1 s** | **2.07–2.54 s** (first 2.54) |
| Peak VRAM allocated / reserved | 9131.6 / 11524 MB | 9111.5 / 11338 MB |
| Worker RSS | ~1.7 GB | ~1.77 GB |
| IP-Adapter load | +2016 MB VRAM, 7.4 s | +2016 MB VRAM, 7.6 s |
| Per IP scene | 26.9–27.4 s | 7.3–7.6 s |
| Peak VRAM allocated with IP | **11149 MB** | **11128 MB** |

- **Lightning is ~10× faster per image** for the same VRAM.
- **With the IP-Adapter, both need ~11.1 GB allocated, which is nearly the whole card.**
  That is the key constraint for 20.4/20.5:
  - IP images must run with nothing else on the GPU (the Task 20.1 lease guarantees
    that);
  - desktop VRAM use can vary. In run 1, before the app was closed, idle free was
    9748 MiB against 11836 in run 2. So 20.4 should plan the mitigation (VAE tiling or
    a lower native size) as a fallback, not a default.

## 4. GPU sharing (Task 20.1 lease, real)

**`idle2`:**
- `base` free before 11049 MiB and `lightning` 11837 MiB, both above the provisional
  8192.
- No eviction was needed, and no waiting.

**`warm_qwen2`:** qwen was first loaded by the app's own `OllamaProvider` (`num_ctx=16384`):

| Snapshot | Used / free (MiB) |
|---|---|
| start | 275 / 11836 |
| after warm qwen | 7147 / 4964 |
| base lease acquired (**qwen evicted**) | 275 / 11836 |
| base worker exited | 269 / 11842 |
| lightning worker exited | 275 / 11836 |
| after qwen reload | 7147 / 4964 |

- The `base` lease had `free_mb_before` **4964**. It evicted `qwen3.5:9b`, giving
  `free_mb_after_eviction` **11836**. It did not wait.
- VRAM returns to its baseline after each worker exits, to within ±6 MiB: **process exit
  frees everything**.
- **qwen reload after eviction: 12.1 s** (the first warm call took 12.7 s).

**Proposed thresholds, measured peak + margin (PM decision; to be added in 20.3/20.4):**
- `DIE_GPU_MIN_FREE_MB_IMAGE` = **9728** (9.5 GiB), for backgrounds without IP-Adapter
  (peak 9.1 GB allocated).
- `DIE_GPU_MIN_FREE_MB_IMAGE_IP` = **11264** (11 GiB), for character images with
  IP-Adapter (peak 11.15 GB allocated). This effectively needs an idle card; the lease
  evicts qwen to get there.

## 5. Outputs for the owner

In `owner-runs/20260930-r2/C/`:
- `sheet_ep1.png` … `sheet_ep5.png`: today's template | base | lightning, for 5 real
  episodes;
- `sheet_ip_adapter.png`: a generated reference portrait, then 3 scenes × IP scale 0.5/0.8,
  for base and for lightning.

The Coder's own look at the sheets (the owner's judgement is what counts):
- No text, logos or watermarks appear in the backgrounds.
- Both candidates give a polished modern-3D look.
- Lightning tends to add an invented mascot character in the scene, while base often
  shows just the room.
- In the IP sheet, the same character (glasses, face shape and, for base, a moustache) is
  recognisable across all 3 scenes at both scales.
- Episode 3 has no template thumbnail in the database, so its first tile is a grey
  placeholder.

## 6. Decision proposal (the owner judges; not pre-decided)

- **Technical PASS for both candidates:** 10/10 backgrounds and 12/12 IP scenes, no OOM, no
  watermark, and the lease and eviction were verified live.
- **Lightning is the natural production default *if* the owner finds its quality
  acceptable**: 2 s against 21 s per image.
- **For the owner:**
  1. which look is better for thumbnails: base, lightning, or today's template?
  2. does the character stay recognisable across the IP scenes? If yes, IP-Adapter is
     confirmed for 20.4/20.5.

## 7. Owner verdict (2026-09-30): **PASS, SDXL-Lightning**

> "cả base và lightning đều tốt nhưng lightning cho kết quả nhanh hơn và tôi nghĩ có thể cải thiện bằng cách tối ưu hóa prompt và luồng tạo nhân vật …"

In English: both base and Lightning are good, but Lightning is faster, and prompts and the
character-creation flow can be improved. The full quote is in
`.viepilot/phases/20-ai-visuals/proposal-amendment-b-asset-library.md` §1.

- **Model: SDXL-Lightning 4-step** (base + Lightning UNet + fp16-fix VAE, with
  IP-Adapter plus-face ViT-H for characters).
- **New direction:** a pre-built **Character Library** (views × expressions,
  owner-approved) and **Scene Library** (named, reusable), composed per episode. This
  replaces free per-episode prompting. The design is proposed as **Amendment B** (link
  above), awaiting owner/PM approval.
- **Q3** (was the IP-Adapter character recognisably the same?) was not answered as a
  yes/no. The owner's library direction builds on that approach, and the proposed 20.2b
  spike re-tests identity across profile, full-body and expression views, which 20.2 did
  not cover.
