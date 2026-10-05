# Task 23.2 — Scene model v2 + scene plate as an IP reference in shots (doc-first card)

**Authority:** owner pick 2026-10-05 after spike 23.1: **variant b, plate IP reference ~0.4**.

## Data (migration `009_scenes_v2.sql`, additive)

`scenes` gains `category TEXT NOT NULL DEFAULT 'other'`, `time_of_day TEXT NOT NULL DEFAULT 'day'`,
`seed INTEGER` (filled for existing rows at startup). The existing `preview_path` **is the plate**:
an empty-scene render at 1344×768.

- `category` ∈ home, school, work, city, nature, food, travel, other;
  `time_of_day` ∈ morning, day, sunset, night (`app/models/visuals.py`).
- Create/edit accept both; editing `place`, `time_of_day` or `staging`... only `place` and
  `time_of_day` change the plate, so they clear `preview_path` (stale plate) — staging does not.
- The preview job renders with the scene's own `seed` (reproducible) and a prompt that adds
  the time of day (`recipes.scene_preview_prompt`, measured ≤ 77 tokens).

## Shots (`pipelines._generate_set`)

- **L0 (only when needed):** project scenes without a plate get one (text2img, no IP), stored
  as their preview — so a first project run needs no manual preview step.
- **L1 encode:** with a plate and `VISUALS_SCENE_REFERENCE_SCALE` > 0 the worker loads two
  adapters (face plus-face + `ip-adapter-plus_sdxl_vit-h`) and encodes `[faces, plate]`.
- **L2 render:** both adapters' layers; masks per adapter: faces (halves for duos, full frame for
  singles) and the scene mask = inverse of the dilated person silhouettes; scales
  `[0.45, VISUALS_SCENE_REFERENCE_SCALE]` (default 0.4).
- **L3** (refine, colour retry, hands) unchanged: face adapter only.
- Scale 0 or no plate → exactly today's path (backward compatible).

## Worker protocol (additive)

`load_ip_adapter {"scene": true}` loads both adapters; `encode`/`generate` accept
`ip_adapter_scene_image`, `ip_adapter_scene_mask`, `ip_adapter_scene_scale`; responses report
`ip_adapters`. The fake engine mirrors the shape.

## Verification

Tests (fake engine): migration + backfilled seeds; enum validation; stale-plate clearing; L0
generates missing plates once; payloads carry the scene image/mask/scale only when enabled.
Real GPU smoke on the owner's machine: 8 shots, **peak VRAM of L2 without offload ≤ 12 GB**
(the risk from 23.1), background CLIP similarity per scene vs the 23.1 numbers.

## Results (2026-10-05, owner's RTX 3060)

- **VRAM finding (affects every shot, not only 23.2):** probe of one L2 render (UNet +
  ControlNet + IP layers, no text encoders, no offload): peak reserved **13.2 GB without** the
  scene adapter and **14.1 GB with** it, on a 12 GB card -> Windows spills into shared memory.
  The first 23.2 smoke took **2395 s** for 8 shots, with 803 s spent at >=12 GB. The peak is
  the 1344x768 VAE decode: with **VAE tiling** the same render reserves **10.9 GB** (46.9 s vs
  53.8 s), and the image shows no seams (A/B checked). `engine.py` now loads every worker with
  `vae_tiling: true`. `PYTORCH_CUDA_ALLOC_CONF=expandable_segments` had no effect on Windows.
- **Real smoke after the fix** (seed 20261001; sheet
  `docs/operations/phase23-t2-scene-reference-smoke.png`, plate | 4 shots per scene):
  8/8 shots in **967 s** (20.11 without the scene reference: 898 s), nvidia-smi peak
  **11.4 GB**, plates generated in L0.
- **Background CLIP similarity** (same characters and seeds, persons masked):
  Cafe 0.791 -> **0.853**, Classroom 0.757 -> **0.813**. By eye the shots share the plate's
  teal awnings and wooden storefronts, and the classroom's whiteboard and windows.
- **Open for the owner / follow-ups:**
  - Classroom single Minh has an extra head behind him. The extra-person check covers only
    duos.
  - The palette is warmer (sepia) because the plates are warm; owner to judge at Gate B-15.
  - The colour misses carried over from 20.11 (layered jacket) still appear and are reported.
