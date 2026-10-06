# Phase 28 spike: semi-realistic picture style (Task 28.1)

**Date:** 2026-10-06. **Model:** SDXL base 1.0, fp16-fix VAE, 30 steps, CFG 6, Euler-a, no LoRA, no
download (the models were already on disk). **Script:** `scripts/spike_style_semireal.py`.
**Sheets:** `docs/operations/phase28-spike/sheet_*.png` (rows A, B, C; columns seed 7 and 21).

| Recipe | Wording |
|---|---|
| **A photo** | photorealistic photo, natural soft window light, shallow depth of field, 85mm lens, warm beige tones, detailed skin |
| **B editorial** | cinematic editorial photograph, warm color grading, soft key light, film grain, natural skin texture |
| **C painted** | semi-realistic digital painting, soft natural light, warm tones, believable faces, fine detail, painterly |

- 24 images, **~24 s each** on the RTX 3060; every prompt is **under 77 CLIP tokens**.

## What the images show

- **Presenter:** all three recipes make the banner's woman: round glasses, long wavy brown hair, beige
  blouse, warm room.
  - A is the closest to the banner's photo look.
  - B is warmer and more cinematic.
  - C looks drawn, with the softest skin.
- **Student:** see `sheet_student.png`.
- **Empty cafe plate:** good in all three, with no people. A is bright and clean, B is moodier, C is the
  warmest and most painted.
- **Duo (the hard case):** two people are rendered reliably, but three known problems appear:
  1. **glasses leak onto the man** in most images: the prompt gave glasses to the woman only;
  2. **the two outfit colours blend** (cream and light blue appear on both people);
  3. **left/right swap** between seeds.
  The existing machinery should handle these in Task 28.2: the per-person colour check and re-refine,
  IP-Adapter identity references, and a "no glasses" word for the man.

## Claude's reading

- Base SDXL is **enough**: no fine-tune download is needed, so there is no licence question.
- Recommendation: **A (photo)** for the people, because it is the closest to the banner. The **plates**
  can use A or B. C is the choice if the owner prefers a "drawn" feel.

## Owner decision needed

Pick **A, B or C** (or a mix, for example A for people and C for places), or say what to change.

## Round 2 (owner feedback: beautiful faces, crisp editorial, no blur)

**Sheets:** `docs/operations/phase28-spike/r2_sheet_*.png`. **Script:** `scripts/spike_style_semireal2.py`.
16 images, ~27 s each (35 steps).

| Recipe | Wording |
|---|---|
| **E1 bright** | editorial fashion photograph, bright airy natural light, crisp sharp focus, clean fine details, high resolution, soft warm tones |
| **E2 warm** | cinematic editorial photograph, warm golden glow, crisp sharp focus, rich fine details, high resolution, luminous skin |

Both add: beautiful, flawless clear skin, delicate features, large bright eyes (handsome, sharp features
for the man). The negative adds blur, bokeh, haze, noise, grain, skin flaws.

- **Faces are clearly more beautiful** than round 1, and **sharp**: no film grain, no soft focus.
- **The presenter keeps her glasses** without losing beauty (compare the two presenter sheets).
- **The male student** is very good: clear skin, defined features, a crisp shirt.
- **Background:** deep enough to read as a real place; E2 keeps a gentle blur on far lamps only.
- **Found:** the cream blouse falls open at the neck. The product prompt will say a buttoned collar.
- **Still open: glasses leak to the man in the duo** (4 of 4 images), because "no glasses" does not work
  in CLIP. The fix belongs to the pipeline: the glasses are an attribute of the presenter only, so
  they are written into her single/refine prompts and never into the shared duo prompt; the per-person
  refine then paints her with them and him without. Checked in Task 28.2.
- Words used for attractiveness describe a polished editorial look; no reference photo's face is copied.
