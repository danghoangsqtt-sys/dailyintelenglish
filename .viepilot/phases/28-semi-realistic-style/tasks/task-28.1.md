# Task 28.1: Spike: semi-realistic picture style on SDXL base (doc-first card)

## Owner answers (2026-10-06)

- No "New videos every Wed & Sat" line: it is not about the video.
- Order: Phase 28 first, then Phase 27.

## Objective

Give the owner side-by-side images, so they can pick a semi-realistic look like `channels4_banner.jpg`.
No product code changes.

## Paths

- `scripts/spike_style_semireal.py` (new; not shipped)
- `docs/operations/phase28-spike-style.md` (new report)

## File-Level Plan

1. **Items** (the cases that matter for episodes):
   - the presenter: a young Vietnamese woman, long wavy brown hair, round black glasses, cream blouse;
   - a male student: light-blue shirt, short black hair;
   - an empty cafe plate (a scene);
   - the duo in the cafe (the hardest case: two faces, two outfit colours).
2. **Recipes**, all on SDXL base 1.0 with the fp16-fix VAE, 30 steps, CFG 6, Euler-a, at 2 seeds:
   - **A photo:** photographic wording (natural window light, shallow depth of field, 85 mm lens, warm
     beige tones);
   - **B editorial:** cinematic editorial photo, warm colour grade, soft key light;
   - **C painted:** semi-realistic digital painting, soft natural light, warm tones, believable faces.
   - A shared negative: cartoon, anime, illustration, 3d render, plastic skin, text, deformed hands,
     extra person.
3. **Report:**
   - a contact sheet per item (recipe × seed);
   - the CLIP token counts (limit 77);
   - the seconds per image;
   - Claude's own reading.
4. **Owner:** picks A, B or C (or says what to change).

## Verification

- 24 images are made (4 items × 3 recipes × 2 seeds) and checked by eye.
- The owner decides the look.
