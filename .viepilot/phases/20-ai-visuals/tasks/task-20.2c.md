# Task 20.2c — Spike: SDXL base + simple character + pose-controlled M2 → real video frames

- **Status:** implemented (Coder, 2026-09-30). Design commit `099d8bb`; see "Implementation
  notes" at the end. **The real run needs the owner's GPU.**
  It goes through the runbook `docs/operations/owner-runbook-2026-09-30-r4.md`.
- **Owner:** Coder
- **Authorization:** owner said *"okey làm đi"* ("okay, go ahead") to the 20.2c plan,
  2026-09-30.
- **Depends on:**
  - 20.1 (the lease);
  - 20.2b (the worker's encode→render split, IP-layers-only loading, ControlNet);
  - 20.2d (the caption styles; the frames use the default `outline`).

## Why (the owner's 20.2b verdicts, `docs/operations/phase20-spike-character-library.md`)

1. **SDXL base, not Lightning.** Base is "much prettier, with more soul"; Lightning makes
   too many defective images. The style is also "not very Ghibli-like yet".
2. **Simplify the character.** Complex expressions and outfits are error-prone.
3. **M2 (inpaint into the scene) is far more natural; M1 (collage) is rejected.** But the
   M2 render had four problems:
   - a rectangular seam;
   - identity drift;
   - the action was ignored;
   - the model, not us, chose the scale.
4. **Full-bleed video frames with film-style captions** (the owner rejected the framed
   layout, and 20.2d added the caption styles).

## Design decisions

- **D20.2c-a: SDXL base everywhere** (30 steps, CFG 6.0), in three worker lifetimes. Each
  runs under its own Task 20.1 lease and exits, freeing all of its VRAM.

  | Phase | Worker | Produces |
  |---|---|---|
  | P1 | base text2img | 2 scenes (style v2, calm lower third) + 3 **plain-background** character candidates |
  | P2 | base text2img + IP-Adapter plus-face (with image encoder) | 6 identity assets (2 views × 3 expressions) + 1 full body; then **encodes** the 4 M2 prompts (with negatives, CFG) + the reference to an embeddings file |
  | P3 | base **ControlNet-inpaint** (new `pipeline: "controlnet_inpaint"`), **no text/image encoders**, IP projection layers only | 4 M2 renders × 2 variants (full-frame vs mask-crop) |
  | P4 | no GPU | 1280×720 video-frame mockups of the real Remotion layout with `outline` captions |

- **D20.2c-b: style preset v2**, descriptive only, never a studio, person or franchise name
  (Amendment B §5.1 rule):
  - *"hand-drawn 2D animation film still, 1990s cel animation look, flat cel shading,
    soft painted gouache background, simple clean character design, natural soft
    daylight, muted warm earthy palette, gentle nostalgic atmosphere"*;
  - a negative prompt that now acts (base has CFG): *"3d render, photorealistic, glossy,
    detailed rendering, cluttered, text, logo, watermark, extra fingers, deformed"*.
- **D20.2c-c: a simple character** (the owner's verdict 2), with few, flat, high-contrast
  identity features and no accessories:
  - *"a young woman teacher with a short dark brown bob haircut with straight bangs,
    wearing a plain mustard-yellow long-sleeve dress"*;
  - 3 expressions only (neutral, happy, surprised);
  - 2 views (front, three-quarter);
  - one full body.
- **D20.2c-d: a clean IP reference.**
  - The reference is a candidate portrait on a **plain light background, neutral pose**.
    In 20.2b the reference's pose and background leaked into every asset.
  - IP scale drops from 0.7 to **0.5**, to let expressions and views through.
  - The runner uses candidate #1; in the real library the owner picks.
- **D20.2c-e: pose-controlled M2 with presenter framing.** This fixes three of the four
  M2 problems.
  - **Action honoured:** ControlNet OpenPose drives the body.
  - **Scale and placement ours:** the pose is drawn in **scene coordinates**. The
    character is waist-up, head below the speaker-chip row, on the side away from the
    vocab card (standard presenter framing). The waist-up choice removes the 20.2b
    "feet on the furniture" failure entirely.
  - **Poses:** 4 new upper-body poses (waving, explaining with open hands, pointing up
    toward the vocab-card corner, hand to chin), 2 per scene.
- **D20.2c-f: fix the seam.**
  - The inpaint mask is the **pose silhouette** (thick limbs, torso, and a head ellipse
    enlarged for hair), dilated and feathered, not a rectangle.
  - The composite back onto the untouched scene uses that same feathered mask.
  - **Variant B** also passes `padding_mask_crop`: diffusers inpaints an upscaled crop
    around the mask (more pixels for the character), then pastes it back.
  - The owner compares full-frame vs crop.
- **D20.2c-g: a memory plan (measured basis, 20.2b r3).**
  - P3 holds the base UNet + VAE + ControlNet + IP layers, with no encoders. By the
    measured components that is ≈ 9.2–10.5 GB allocated, with CFG batch 2 at 1344×768.
    The 13.6 GB all-in-one configuration still would not fit.
  - The worker now calls `torch.cuda.empty_cache()` whenever the output size changes
    (20.2b finding F1: 11.3 → 13.1 GB reserved on a size switch caused spillover and a
    2–3× slowdown).
- **D20.2c-h: frames, not videos.**
  - P4 composites each M2 render into a 1280×720 frame with the real Step-5 overlays:
    - speaker chips top-left;
    - the vocab card top-right (85% dark);
    - a karaoke caption in the 20.2d `outline` style.
  - Pillow draws it using the same geometry as `Episode.tsx`, and it is labelled a
    mockup.
  - The Remotion composition has no background-image prop yet. Adding one is the real
    in-video task, after the owner approves the look.

## Allowed files

- `scripts/image_worker.py`: `pipeline: "controlnet_inpaint"` (init + mask + control
  image, optional `padding_mask_crop`), and `empty_cache` on a size change.
- **New** `scripts/spike_character_v2.py` (the runner; reuses the helpers in
  `spike_images.py` and `spike_character_library.py`).
- **New** `docs/operations/owner-runbook-2026-09-30-r4.md`, this card, and PHASE-STATE.

**Not touched:**
- `app/`, `tests/`, `frontend/`, `video-renderer/`;
- `requirements-image.txt` (no new dependency; the ControlNet weights are already in the
  owner's HF cache from r3);
- the DB.

## Verification here (cloud, no GPU, no Hub)

- Tiny random-weight SDXL components (the 20.2b test fixtures), covering:
  - the `controlnet_inpaint` path from embeds, with and without `padding_mask_crop`;
  - the scene outside the mask stays pixel-identical after the composite;
  - clean errors when inputs are missing.
- The runner end to end with `--allow-cpu --skip-ip`.
- Unit checks of the scene-space pose drawing, the silhouette mask (it covers every
  keypoint and stays inside the frame) and the frame mockup geometry.
- The IP-Adapter paths run only on the owner's machine (no weights here).

## Owner questions the run answers

1. Is style v2 on base closer to the look you want?
2. Is the simple character recognisable across views, expressions and the 4 actions?
3. Is M2 with pose control natural, with no seam? Full-frame or crop?
4. Do the frames, with captions, look like a professional video?

## Implementation notes (Coder, 2026-09-30)

- **D20.2c-f variant B changed, found in verification.**
  - `padding_mask_crop` cannot upscale a presenter-framed character at 16:9.
  - diffusers' `get_crop_region` expands the crop to the target aspect ratio. For the
    real 1344×768 "thinking" silhouette it returns `(0, 41, 1272, 768)`, so the "crop" is
    almost the whole frame and gains no pixels.
  - Variant B is therefore **pose strength**: strict (`controlnet_conditioning_scale`
    1.0) vs loose (0.7). This answers the owner's "not stiff" concern directly.
  - The worker's `padding_mask_crop` pass-through was removed again, so there is no dead
    option.
- **Pose proportions reworked after a visual check** on the real r3 scenes.
  - The first keypoint set had a tiny head and a long torso. The keypoints are now in
    head-height units with ordinary adult proportions, using medium close-up presenter
    framing: head height 0.24 of the frame, head top ≈ 0.17, hips at the bottom edge.
- **Verification (cloud, tiny random-weight SDXL, CPU).**
  - The runner end to end with `--allow-cpu --skip-ip`: all 4 phases ok. Counts:
    - 2 scenes and 3 candidates;
    - 7 assets and 1 encode with `do_cfg: true`;
    - 8 M2 renders;
    - 8 frames;
    - 4 sheets.
  - Every M2 render applied the encoded negative prompt.
  - The scene stays pixel-identical outside the mask in all 4 scene/action pairs.
  - Strict vs loose renders differ inside the mask. This needed a tiny ControlNet with
    non-zero output convs: the fixture's ControlNet, built from the UNet, has
    zero-initialised output convs, so any scale gave identical output.
  - Clean worker errors: missing `control_image`, missing init/mask, and a prompt
    without embeds on an encoders-free pipeline.
  - Broken model sources: every GPU phase records its error, frames report `missing`,
    and the run exits 0.
  - Pure-helper checks, all 4 actions:
    - 14 upper-body joints, knees/ankles omitted;
    - the mask top is below the chip row;
    - the mask stays clear of the vocab card;
    - the mask covers every in-frame joint and 23–27% of the frame;
    - the torso reaches the bottom edge;
    - frame geometry: 1280×720, chapter bar, dark vocab card, white outlined caption,
      yellow active word.

