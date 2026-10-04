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
