# Task 20.2e — Spike v3: anime-specialised SDXL (Animagine XL 4.0), two styles, render-then-cut M2

- **Status:** implemented (Coder, 2026-09-30). Design commit `d29cfe6`; see "Implementation
  notes" at the end. **The real run needs the owner's GPU.**
  It goes through the runbook `docs/operations/owner-runbook-2026-09-30-r5.md`.
- **Owner:** Coder
- **Authorization:** owner *"okey tôi đồng ý"* ("okay, I agree"), 2026-09-30, to the
  proposal:
  - Animagine XL 4.0;
  - style A (modern action-webtoon look) + style B (bright anime);
  - render-then-cut;
  - a face-crop reference;
  - a tag-based "thinking" pose.
- **Depends on:** 20.1 (the lease), 20.2b/20.2c (the worker + runner machinery), 20.2d
  (captions).

## Why (owner verdicts, `docs/operations/phase20-spike-character-v2.md`)

1. **Style rejected twice on SDXL base 1.0** (20.2b "Ghibli-like" and 20.2c "cel
   animation"). The owner wants a polished anime look, like the Korean action webtoon/anime
   they named.
2. **The character is "not OK".**
3. **Strict pose; the owner confirmed the edge halo.**
4. **The captions and frame layout are accepted.**

## Design decisions

- **D20.2e-a: model — `cagliostrolab/animagine-xl-4.0`.**
  - **Licence:** CreativeML Open RAIL++-M, "without any modifications or additional
    restrictions". It permits commercial use (read on the Hub 2026-09-30); this is the same
    licence as the SDXL base already accepted.
  - **Architecture:** SDXL, so the fp16-fix VAE, IP-Adapter plus-face, ControlNet
    OpenPose, the lease and the encode→render split all carry over unchanged.
  - **Download** (diffusers folders only, never the two 6.9 GB single-file checkpoints at
    the repo root):
    - UNet 5,135,149,760 B;
    - text encoders 246,144,152 + 1,389,382,176 B.
    - It lands in `models/image/` on the repo drive, not C:.
  - **Rejected:**
    - Illustrious-XL and NoobAI-XL: licence "other"; NoobAI is tagged
      not-for-all-audiences.
    - Any franchise LoRA.
- **D20.2e-b: worker changes.**
  - `load` takes `base_repo` (default: SDXL base, unchanged) and `scheduler`
    (`"euler_a"` → `EulerAncestralDiscreteScheduler`, the model card's recommended
    sampler).
  - A non-default repo is fetched with folder patterns (config + tokenizers + text
    encoders + UNet), never the root checkpoints.
  - fp16 weights without a `.fp16` suffix are already detected (`variant=None`).
- **D20.2e-c: two style presets, both generic.**
  - Both use tag syntax (the model is tag-trained), `safe` + `original` (Danbooru's tag
    for original characters) in every prompt, and the model card's quality/negative tags.
  - **Never** a franchise, character or artist name (Amendment B §5.1; the owner's "no
    copyright entanglement").
  - **A `action_webtoon`:** "dramatic lighting, rim lighting, cinematic lighting, high
    contrast, sharp lineart, cel shading, detailed eyes, cool color palette, blue and
    purple lighting, year 2024".
  - **B `bright_anime`:** "anime screencap, soft lighting, bright colors, clean lineart,
    detailed eyes, sunlight, vibrant, year 2024".
- **D20.2e-d: character (invented, one per run, tag-described).**
  - *"1girl, solo, original, mature female, short black hair, bob cut, blunt bangs, blue
    eyes, white collared shirt, black jacket"*.
  - **Reference:** a close-up portrait candidate on "simple background, white background"
    (Animagine obeys these tags), so the reference is face-dominant with no scene.
  - **IP scale 0.4.** In 20.2c, 0.5 with a scene reference copied the whole layout.
- **D20.2e-e: identity set, small and tag-driven.**
  - Four assets:
    - front neutral (`expressionless`);
    - front smile (`smile, open mouth`);
    - side look surprised (`looking to the side, surprised, open mouth`);
    - an upper-body outfit shot (`cowboy shot`).
  - Each uses a **different seed**; 20.2c used one seed for all, which amplified the
    copying.
- **D20.2e-f: render-then-cut M2 (fixes the halo the owner saw).**
  - P3 renders exactly as 20.2c: strict pose 1.0, silhouette mask, presenter framing,
    base-style CFG through saved embeddings, IP layers only.
  - Then the **same worker** runs `remove_background` (anime-seg, CPU) on the raw render.
  - The runner composites the render onto the untouched scene with
    `alpha = anime_seg_alpha × hard(silhouette mask)`, lightly feathered (1 px). Only the
    character's own pixels are pasted; the model's re-painted background inside the
    silhouette is dropped.
  - **Both** composites are saved (`blend` = the 20.2c method, `cut` = new), so the owner
    sees the difference. The frames use `cut`.
- **D20.2e-g: tag-friendly actions.**
  - waving (`waving, smile`);
  - pointing up (`pointing up`);
  - explaining (`open hands, talking`);
  - thinking (`hand on own chin, thinking`, the tag the model knows).
  - The same scene-space OpenPose skeletons as 20.2c.
- **D20.2e-h: run shape — 3 worker lifetimes, both styles in each.**

  | Phase | Worker | Produces |
  |---|---|---|
  | P1 | Animagine text2img | per style: 2 scenes (`no humans, scenery`) + 2 face-reference candidates |
  | P2 | Animagine + IP (with encoder) | per style: 4 identity assets; encode 4 M2 prompts + reference |
  | P3 | Animagine ControlNet-inpaint, no encoders, IP layers + anime-seg | per style: 4 M2 renders → blend + cut |
  | P4 | no GPU | per style: 4 video frames (cut) with the 20.2d outline captions |

  Settings: 28 steps, CFG 5, Euler a, sizes from the model card's list (1344×768 scenes,
  1024² portraits, 832×1216 outfit shot). The estimate is ~15 minutes plus the first
  download.

## Allowed files

- `scripts/image_worker.py`: `base_repo` and `scheduler` on `load`.
- **New** `scripts/spike_character_v3.py` (reuses the 20.2c helpers).
- **New** `docs/operations/owner-runbook-2026-09-30-r5.md`, this card, and PHASE-STATE.

**Not touched:** `app/`, `tests/`, `frontend/`, `video-renderer/`, requirements (no new
package), and the DB.

## Verification here (cloud, no GPU, no Hub)

- The worker's `base_repo` pattern selection and the `euler_a` scheduler swap, on the
  tiny random SDXL.
- The runner end to end with `--allow-cpu --skip-ip`, with a tiny fake anime-seg ONNX
  (the 20.2b fixture), so render-then-cut runs, covering:
  - counts;
  - the scene stays pixel-identical outside the silhouette in both composites;
  - the cut alpha is 0 wherever the segmenter says background.
- The IP-Adapter and the real anime-seg run only on the owner's machine.

## Owner questions the run answers

1. Style A or B — does either look like the anime you want?
2. Is the character OK now (design + identity across the 4 assets and 4 actions)?
3. Is the halo gone (blend vs cut)?
4. Do the frames work?

## Implementation notes (Coder, 2026-09-30)

- **Worker** (`scripts/image_worker.py`).
  - `load` takes `base_repo`: any non-default repo is fetched with `FINETUNE_PATTERNS`,
    and only in mode `base`.
  - `load` takes `scheduler`: `default` | `euler_a`. Lightning refuses anything but its
    own trailing Euler.
  - The response now reports `base_repo` (`local:<path>` when a local mirror is used).
- **Runner** `scripts/spike_character_v3.py`. It reuses:
  - the 20.2c scene poses, silhouette mask, frame mockup and captions;
  - the 20.2b lease/worker plumbing.
- **Verification (cloud, tiny random-weight SDXL on CPU, a fake anime-seg ONNX).**
  - The runner end to end with `--allow-cpu --skip-ip`: all 4 phases ok.
    - 4 scenes, 4 candidates and 8 assets.
    - Both styles encoded with `do_cfg: true`.
    - 8 M2 renders at CFG 5 with negatives, each followed by anime-seg.
    - 8 frames and 4 sheets.
    - The scheduler is `EulerAncestralDiscreteScheduler`.
  - **Render-then-cut, all 8 renders:**
    - the scene is untouched beyond the 1 px blur margin of the hard silhouette;
    - every cut pixel is a scene/render mix;
    - on pixels the segmenter labels background inside the silhouette, the cut differs
      from the scene by 15–16 (mean |Δ|), against 84–88 for the 20.2c blend. That is the
      halo removed.
  - **Worker repo selection** (a stubbed `snapshot_download`):
    - the Animagine patterns exclude both 6.9 GB root checkpoints and the repo VAE, and
      include the UNet, both text encoders, the tokenizers and `model_index.json`;
    - the default SDXL-base pattern list is unchanged;
    - Lightning with a custom repo is refused, as are an unknown scheduler and Lightning
      with `euler_a`.

