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

## Round 3 and 3b (owner references: 3 female photos, 4 male photos; white / black single-colour outfits)

**Sheets:** `docs/operations/phase28-spike/r3_sheet_*.png`, `r3b_sheet_*.png` (4 seeds per portrait).
**Scripts:** `scripts/spike_style_semireal3.py`, `scripts/spike_style_semireal3b.py`. Every prompt and negative
was counted with the real CLIP tokenizer (all ≤ 77).

- **Round 3** (the round 2 wording + the new hair and colours):
  - The woman had straight black hair and a white shirt, but a tanned "model" face.
  - The man had an undercut/pompadour instead of the fringe, an older face, and one white shirt.
  - The backgrounds were blurred again.
  - **The duo failed:** swapped colours, extra people, long hair on the man.
- **Round 3b** (youthful idol-like faces, fair porcelain skin, "deep focus", a two-block fringe, and a
  negative per character):
  - **clearly closer to the references:** both are fair and young, she has very long straight black
    hair and a white shirt, he has a thick fringe covering the forehead;
  - **the base model's limit:** the faces are pleasant but not "idol" level, and the photos are flat;
  - **his outfit still drifts** (a jacket, and a grey shirt in 1 of 4).
  - E1 and E2 now look almost the same.
- **Duo:** prompt wording alone cannot place two people with locked colours. Task 28.2 must render
  each person through the existing per-person path (identity reference + regional refine).

## Recommendation: a photoreal SDXL fine-tune (owner approval needed for the download)

- **RealVisXL V5.0** (`SG161222/RealVisXL_V5.0`):
  - **licence `openrail++`, the same licence as the SDXL base 1.0 already in use**;
  - diffusers format, drop-in for the current pipeline and IP-Adapter;
  - about 7 GB (fp16).
- It is trained for photographic people, the gap seen in round 3b.
- Plan if approved: the same round 3b prompts, seeds and sheets on RealVisXL, side by side with base.
- Not recommended: Juggernaut XL (its commercial terms are less clear).

## Round 4: RealVisXL V5.0 vs SDXL base 1.0 (owner approved the download)

**Sheets:** `docs/operations/phase28-spike/r4_compare_*.png` (top row SDXL base, bottom row RealVisXL; the same
prompts, negatives, seeds, 35 steps, CFG 6.5, Euler-a). **Script:** `scripts/spike_style_realvis.py`.
16 images, ~27 s each. RealVisXL V5.0 fp16 (openrail++), the same fp16-fix VAE.

- **Outfits now hold:** the man wears a black shirt in 4 of 4 (base: a jacket in 2 of 4, grey in 1);
  the woman wears a plain white buttoned shirt in 4 of 4, with no open collar.
- **Faces:** cleaner, brighter, younger and sweeter, closer to the owner's references than the base.
- **Backgrounds:** crisp and believable (windows, plants, chairs) instead of the base's blur and blinds.
- **Remaining limit:** this is a polished everyday-photo look, not the heavy retouched "idol" look of
  the references. Raising it further belongs to Task 28.2 (prompt tuning on RealVisXL, IP-Adapter
  face reference after the owner locks one face).
- **Duo:** not yet re-tested on RealVisXL; Task 28.2.
- **Cache note:** the new huggingface_hub keeps the real weights in the shared `models/image/hub/blobs`
  folder, and the model folder holds only links. The spike script reads the partial snapshot folder
  directly, because `snapshot_download(local_files_only=True)` demands every file of the repository.
