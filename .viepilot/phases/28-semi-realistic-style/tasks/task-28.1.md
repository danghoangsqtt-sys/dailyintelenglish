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

## Owner feedback on round 1 (2026-10-06)

- The characters are **not beautiful enough**: the faces must be beautiful (the owner sent 3
  idol-style reference photos with bright, flawless skin, large eyes and delicate features, in warm
  or airy light).
- Use the **editorial** look (recipe B), but **not blurred**: the shallow depth of field and the soft
  focus of round 1 looked hazy and unpleasant.
- References are used for light, polish and attractiveness only. No face is copied.

## Round 2 plan

- Editorial recipes with **crisp sharp focus and deep focus** (no bokeh, no film grain), plus
  attractiveness words (clear skin, delicate features, large bright eyes).
- Two lightings, E1 (bright airy, like the cherry-blossom reference) and E2 (warm glow, like the
  warm references).
- Items: the presenter **with glasses**, the presenter **without** glasses (to see whether the
  glasses cost beauty), the male student, and the cafe duo (the man with no glasses).
- 35 steps, CFG 6.5; the negative adds blur, bokeh, haze, noise, grain and skin flaws.
- Script: `scripts/spike_style_semireal2.py`.

## Owner feedback on round 2 (2026-10-06): 6 reference photos

- **Female** (3 photos of Vietnamese women, photographic): very long **straight black hair**, fair
  luminous skin, soft delicate face, a white shirt. No glasses, no brown hair.
- **Male** (3 manhwa-style illustrations): **messy layered black hair** with bangs over the eyes, pale
  clear skin, sharp jaw, narrow cool eyes, black clothes.
- **Outfits are single colour:** the woman all **white**, the man all **black**.
- The female photos are photographic and the male photos are illustrated, so one frame could mix
  two styles. Round 3 renders the man **both ways** for the owner to compare.
- References are used for the look only; no face is copied.

## Round 3 plan (`scripts/spike_style_semireal3.py`)

- The presenter: long straight black hair, fair skin, plain white shirt (E1 bright, E2 warm).
- The male student: messy layered black hair, pale skin, sharp features, plain black shirt, in the
  same two editorial recipes, **plus** a semi-realistic illustrated version (manhwa-like) as a third
  row.
- The duo: the woman in white and the man in black (a strong contrast, which also helps keep the two
  outfit colours apart).
- 3 seeds for portraits, 2 for the duo.
- **Product consequence to check in Task 28.2:** the library today requires a different top and
  bottom colour; a single-colour outfit needs that rule relaxed and the colour check adapted.

## Owner correction before round 3 ran (2026-10-06)

- The male references are replaced by **4 photographs**: thick glossy black hair with a soft fringe to
  the brows, fair clear skin, a sharp jaw, calm almond eyes, black clothes.
- **Editorial only**: no illustrated version. Focus on making **both** characters as good as possible.
- Round 3 therefore drops the illustrated row. It runs 4 seeds per portrait (so one face can be
  picked and locked), plus the duo at 2 seeds.
- Every prompt is counted with the real CLIP tokenizer first (`--tokens-only`): 55–57 tokens, and the
  negative is 76. Round 2's duo prompt (81) had been truncated.

## Rounds 3 / 3b result (2026-10-06)

- See `docs/operations/phase28-spike-style.md`: 3b is closer to the references, but base SDXL tops out
  below the "idol" faces.
- **Waiting for the owner:** approval to download RealVisXL V5.0 (openrail++, ~7 GB) for a side-by-side.

## Owner decision (2026-10-06): RealVisXL V5.0 approved, Ghibli models removed

- Download approved: `SG161222/RealVisXL_V5.0` (openrail++), fp16 diffusers files only (~6.8 GB). The
  fp32 file and its own VAE are skipped; the fp16-fix VAE is reused.
- Removed from `models/image` (6.8 GB freed), because they were used only by the old style spike:
  - `cagliostrolab/animagine-xl-4.0`;
  - `ntc-ai/SDXL-LoRA-slider.Studio-Ghibli-style`.
- **Kept**, because the app uses them today: SDXL base 1.0, SDXL-Lightning, IP-Adapter, ControlNet
  openpose, anime-seg, the fp16-fix VAE. SDXL base can go only after RealVisXL is wired in and proven
  (Task 28.2).
- **Round 4** (`scripts/spike_style_realvis.py`): the round 3b prompts, negatives, seeds and sampler on
  RealVisXL. The compare sheets put SDXL base above RealVisXL.

## Round 4 result (2026-10-06)

RealVisXL V5.0 beats SDXL base on all four checks: outfits, face quality, background clarity and
sharpness (`docs/operations/phase28-spike-style.md`, round 4). **Waiting for the owner to pick the look
and one face per character** (seeds 7, 21, 42, 99 in the sheets). Task 28.1 closes on that answer.

## Owner feedback on round 4 (2026-10-06)

- RealVisXL V5.0 is "very strong": no face errors and no outfit errors.
- **The woman is approved** (keep the round 4 look; a face is picked from the 4 seeds later).
- **The man's face is not handsome enough**: redo the male character only.
- The 4 male reference photos show: straight dark eyebrows, narrow sharp eyes with an intense
  gaze, defined lips, a V-shaped jaw and slim face, fair luminous skin, thick voluminous tousled
  black hair with a swept fringe, studio editorial light.
- Method: text description only. The reference photos of real people are NOT fed to the model as
  face references (no likeness copying).

## Round 5 plan (`scripts/spike_style_realvis_male.py`)

- 3 prompt variants of the man x 4 seeds on RealVisXL, a plain soft studio background so the face is
  judged alone; the black shirt stays; a negative against the boyish look ("baby face, round face,
  soft jaw, thin eyebrows"); prompts counted with the real tokenizer.

## Rounds 5 / 6 (2026-10-06)

Round 5 overshot (harsh, older, tanned). Round 6 is fair, young and refined: 12 images,
`docs/operations/phase28-spike/r6_sheet_male_refined.png`. **Waiting for the owner's pick** of one man
(variant + seed) and one woman (round 4 seed).
