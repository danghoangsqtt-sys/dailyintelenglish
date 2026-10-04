# Task 23.1 — Spike: can shots of one scene look like the same place? (doc-first card)

**Why:** a story scene reuses one place across its framing set (wide, duo close, singles) and,
in Phase 24, across beats. Today every shot is generated independently from the same one-line
place text, so the café in the wide shot and in the close-up are different cafés.

## Variants (same characters, same pose geometry, same seeds)

- **a — text only (today):** ControlNet OpenPose + face IP-Adapter (plus-face, 0.45), the
  place text only.
- **b — scene reference:** a, plus a second IP-Adapter (`ip-adapter-plus_sdxl_vit-h`,
  Apache-2.0, h94/IP-Adapter; shares the cached ViT-H image encoder) fed the scene **plate**
  (an empty-scene render), masked to the background (inverse of the person silhouettes).
  Scales 0.3 and 0.5.
- **c — plate + inpaint:** the plate is the init image (cropped to the shot's framing for
  close kinds), the characters are painted into dilated silhouette masks with ControlNet
  inpaint + face IP. The background outside the masks is the plate itself.

Shots per scene: single Lan, single Minh, duo_close, duo_wide (seated); scenes Cafe (indoor)
and Park (outdoor). Standalone diffusers script `scripts/spike_scene_consistency.py` in
venv-image with model CPU offload (not the product worker, so nothing ships from the spike).

## Measures

1. **Background consistency:** persons masked to grey, ViT-H CLIP image embedding, mean
   pairwise cosine similarity across the 4 shots of a scene (higher = same place).
2. **Character quality** (owner's eye): faces/outfits, "pasted-on" look, lighting match.
3. **Cost:** seconds per shot, peak VRAM (12 GB card; b adds ~0.85 GB of adapter weights).

**Decision (owner, with PM recommendation):** which variant Phase 23.2 builds on.
