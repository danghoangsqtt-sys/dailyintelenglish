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
