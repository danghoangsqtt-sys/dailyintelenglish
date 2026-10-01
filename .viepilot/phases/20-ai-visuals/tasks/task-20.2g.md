# Task 20.2g — Spike v5: quality tuning (hand repair, male redesign, pose-placed one-pass scenes, outfit lock)

- **Status:** implemented (Coder, 2026-10-01). Design commit `743a32f`; see "Implementation
  notes" at the end. **The real run needs the owner's GPU.**
  It goes through the runbook `docs/operations/owner-runbook-2026-10-01-r7.md`.
- **Owner:** Coder
- **Authorization:** owner *"okey chốt phương án của bạn"* ("okay, lock in your plan"),
  2026-10-01, to the 20.2g proposal.
- **Depends on:** 20.2f (the accepted direction), 20.2b (ControlNet + the encode→render
  split), 20.2c (scene-space poses), and 20.2d (captions).

## Accepted baseline (20.2f, owner verdict 2026-10-01)

The baseline the owner accepted:
- SDXL base;
- the r3 watercolor preset family (`r3_watercolor`, `r3_bright`, both kept as
  user-selectable channel styles);
- prompts within 77 CLIP tokens;
- one-pass character + scene with IP-Adapter;
- 20.2d outline captions.

The owner's remaining points:
- the female student's **hands** have many errors;
- the male student is **not attractive, with little emotion**;
- actions and placement were only partly followed (Coder reading, r6);
- outfit extras drift.

## Design decisions

- **D20.2g-a: male redesign.**
  - Prompt: *"handsome young Vietnamese man student, short black hair, brown eyes, bright
    friendly smile, expressive face, bright teal hoodie, dark jeans"*.
  - **4 candidates** per style, for the owner to choose from (the runner uses #1).
  - Expressions: calm friendly / big laughing smile / surprised.
- **D20.2g-b: clean references.**
  - The candidate prompts say "arms down"; the negative adds "hand on face, hand on
    cheek". In 20.2f a hand-to-cheek pose leaked from the reference into the sheet.
  - Female: 2 new candidates per style, with the same character text as 20.2f.
- **D20.2g-c: outfit lock.** The negative adds "backpack, hat, cap, jacket, coat,
  scarf".
- **D20.2g-d: pose-placed one-pass scenes.**
  - Text2img **ControlNet OpenPose** + IP-Adapter, through the proven encode→render split
    (SDXL + IP + ControlNet ≈ 13.6 GB does not fit 12 GB at once).
    - P2 encodes the scene prompts + reference.
    - P3 renders with UNet + ControlNet + IP layers only, at strict scale 1.0 (the owner's
      20.2c choice).
  - **The scene is still painted in the same pass**, so the character cannot sink
    (20.2e verdict 4).
  - **Medium-shot geometry:**
    - head height 0.16 of the frame, nose at y 0.30;
    - hips ≈ 0.78, knees just below the frame;
    - centred at x 0.30, which keeps the vocab-card corner (top-right) clear.
  - **Actions:**
    - female: waving (library), reading a book held in both hands (café);
    - male: pointing to the side (classroom), talking with open hands (café).
  - **2 seeds per shot** (16 renders), so a bad-hands render has an alternative.
- **D20.2g-e: hand repair pass (P4).** We drew the pose, so we know where every wrist is.
  - For each in-frame wrist:
    - centre a square crop on wrist + 0.35 × (wrist − elbow) (the hand extends past the
      wrist), with side 2.2 head-units;
    - upscale it to 768²;
    - inpaint with SDXL base (pipeline `inpaint`, strength 0.5, the style + "detailed
      hand, five fingers" prompt, a negative against extra/fused fingers);
    - downscale and paste back through a feathered circular mask.
  - Both the **raw** and the **fixed** renders are kept, so the owner can judge the
    repair.
  - **Stated plainly:** hands are a known SDXL weakness. This reduces errors; it cannot
    guarantee perfect hands.
- **D20.2g-f: frames.** 16 frames (from the fixed renders) with the 20.2d outline
  captions.
- **D20.2g-g: run shape — 3 worker lifetimes + Pillow.**

  | Phase | Worker | Produces |
  |---|---|---|
  | P1 | base text2img | per style: female ×2 + male ×4 candidates |
  | P2 | base + IP (with encoder) | per style × character: 3 expression portraits; encode 2 scene prompts each |
  | P3 | base ControlNet text2img, no encoders, IP layers | 2 styles × 2 characters × 2 scenes × 2 seeds = 16 renders |
  | P4 | base inpaint (with encoders) | hand repair on every render |
  | P5 | Pillow | 16 frames, 4 sheets |

  The estimate is ~25 minutes; no download (everything is cached).

## Allowed files

- **New** `scripts/spike_character_v5.py` (reuses the 20.2b/20.2c/20.2f helpers).
- **New** `docs/operations/owner-runbook-2026-10-01-r7.md`, this card, and PHASE-STATE.

**Not touched:** `scripts/image_worker.py` (every pipeline kind needed already exists),
`app/`, `tests/`, `frontend/`, `video-renderer/`, requirements, and the DB.

## Verification here (cloud, no GPU, no Hub)

- The runner end to end on the tiny SDXL with `--allow-cpu --skip-ip`.
- Pure-helper unit checks:
  - the pose geometry (placement, frame bounds);
  - the hand boxes (centred past the wrist, clamped to the frame, skipped when off-frame);
  - the paste-back changes pixels only inside the feathered hand circle.
- Every prompt is counted with OpenAI's CLIP BPE: ≤ 75 tokens.

## Owner questions the run answers

1. Which male candidate (1–4)? Is he attractive and expressive now?
2. Hands: raw vs repaired — better?
3. Do the actions and the left-side placement now match the intent?
4. Is the outfit stable?

## Implementation notes (Coder, 2026-10-01)

- **Framing changed after a visual check.**
  - The design said head height 0.16 (hips ≈ 0.78). Laid over the r6 scenes, that read
    clearly smaller than the r6 composition the owner praised.
  - The implementation uses **0.20** (waist-up):
    - head top ≈ 0.14, below the chip row;
    - hips ≈ 0.90;
    - knees below the frame;
    - every in-frame joint at x ≤ 0.57 of the width, left of the vocab card at 0.64.
- **CLIP token counts** (OpenAI BPE):
  - every positive prompt is 32–70 tokens;
  - the negative is 54 and the hand negative 17;
  - all ≤ 75.
- **Verification (cloud, tiny random SDXL, CPU, `--allow-cpu --skip-ip`).** All 5 phases
  ok:
  - 12 candidates;
  - 12 expressions;
  - 4 CFG encodes;
  - 16 ControlNet one-pass renders from embeds (no encoders, negatives applied);
  - 32 hand repairs (inpaint);
  - 16 frames;
  - 4 sheets.
  - Each repaired render differs from its raw in 12–20% of pixels; only the hand discs
    changed.
- **Pure-helper checks for all 4 actions:**
  - head below the chip row; medium framing; joints left of the vocab card;
  - square hand crops inside the frame, centred past the wrist;
  - the paste-back changes pixels only around the hands.

