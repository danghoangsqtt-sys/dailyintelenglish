# Task 28.3: Recipes and checks for the semi-realistic look (RealVisXL in the app)

## Objective

The app generates pictures in the approved look: crisp editorial photographs from **RealVisXL V5.0**,
with **single-colour outfits** (the woman all white, the man all black). The shot checks keep working
on photographs. The library data (the new Lan and Minh, the 55 plates) is Task 28.4, not this one.

## Facts found in the code (2026-10-06)

- The app loads the worker with `mode: "base"` (`app/services/visuals/engine.py:124`) and 30 steps,
  CFG 6.0 (`pipelines.py`). The worker already accepts a custom `base_repo` (mode base only), but its
  fine-tune patterns fetch `unet/*`, i.e. also the 10 GB fp32 shards RealVisXL keeps; only the fp16
  files (about 6.8 GB) are on disk.
- Style words: `recipes.STYLE_CEL_ANIME`, `NEGATIVE`, `PLATE_NEGATIVE` (cel-anime wording, "watercolor,
  pastel" etc. in the negatives). `tests/test_visuals_colour_check.py:65` pins the style constant.
- Outfit rule: `app/models/visuals.py:69-70` rejects a character whose top and bottom colours are equal;
  `tests/test_visuals_library_api.py:51` expects that error.
- Colour check (`colour_check.py`): HSV rules per colour name, calibrated on cel-shaded images (for
  example white = s < 0.2 and v > 0.72). Photographs have shaded whites and lit blacks.

## Paths

- `app/services/visuals/recipes.py`
- `app/models/visuals.py`
- `app/services/visuals/colour_check.py`
- `app/services/visuals/engine.py`
- `app/core/config.py`
- `scripts/image_worker.py`
- `tests/test_visuals_foundation.py`
- `tests/test_visuals_beat_recipes.py`
- `tests/test_visuals_colour_check.py`
- `tests/test_visuals_library_api.py`
- `tests/test_ai_worker.py`
- `docs/operations/phase28-t3-smoke.md` (new, the smoke report)

## File-Level Plan

1. **Calibrate first** (read-only): measure the median HSV of the white and black garments on the owner's
   approved sheets (`docs/operations/phase28-characters/`) and on the 28.1 spike images, to set the
   `white` and `black` rules from data, not by guess.
2. **`recipes.py`:**
   - `STYLE_CEL_ANIME` becomes `STYLE_EDITORIAL` = "editorial photograph, soft natural light, crisp sharp
     focus, high resolution" (from the spike); every `_styled` call uses it; `NEGATIVE` and
     `PLATE_NEGATIVE` get the photographic guards (blurry, bokeh, cartoon, anime, 3d render, plastic
     skin) and lose the watercolor/pastel words; the outfit-lock words stay.
   - One `outfit_phrase(character)`: when the top and bottom colours are the same, "plain white blouse and
     trousers" (one colour word), otherwise as today; `character_phrase`, `compact_phrase` and
     `garment_refine_prompt` use it, which also saves tokens.
   - `BEAT_TOKEN_BUDGET` stays 72 (re-checked against the real CLIP tokenizer in the tests).
3. **`models/visuals.py`:** drop the "top and bottom colours must differ" rule (single-colour outfits are now
   the design). Colour names must still come from `COLORS`.
4. **`colour_check.py`:** re-tune `white` and `black` for photographs from step 1 (same function
   signatures); the other colour rules stay.
5. **`engine.py`, `config.py`, `image_worker.py`:**
   - setting `IMAGE_BASE_REPO` (default `SG161222/RealVisXL_V5.0`), sent as `base_repo` with
     `scheduler: "euler_a"` in the `load` request (the sampler the spike used); the fake engine ignores it;
   - the worker's fine-tune download prefers the fp16 files when the repo has them (fp16-only patterns
     first, the full patterns as the fallback), so it never fetches the 10 GB fp32 shards;
   - the worker's licence list names RealVisXL V5.0 (`openrail++`).
6. **Tests:** update the pinned strings; new tests: the outfit phrase (same / different colour), the token
   budget for the two new characters' prompts with the real tokenizer (skipped when no tokenizer is
   cached, like today), the single-colour character is accepted and a bad colour name is still
   rejected, the load request carries `base_repo` and `scheduler`, the fp16 pattern choice.
7. **Smoke (GPU, real worker):** through `WorkerImageEngine`, load RealVisXL and render, with the app's own
   `recipes` prompts, a close-up of a white-outfit woman and a black-outfit man plus one duo; run the
   colour check on them; write `docs/operations/phase28-t3-smoke.md` (seconds per image, VRAM, the check
   results, the images).

## Verification

- `pytest tests/test_visuals_*.py tests/test_ai_worker.py tests/test_storyboard_shots.py -q` green, then
  the full suite green (about 15 minutes) before the task is marked done.
- The smoke report shows the colour check passing on the photographs.
- No change to the data of the user's real database or to the library (Task 28.4).

## Out of scope

The library redo (28.4), the shot-level IP-Adapter tuning with the new faces (28.4 checks it), the
duo placement of two outfit colours beyond what the existing per-person refine already does.

## Calibration result (step 1, 2026-10-06)

Measured with the app's own `colour_check.measure` / `matches` on 33 woman and 21 man full-body images
(the approved sheets and every candidate): **white** garments measure v 0.82-0.97 and s <= 0.07 and all 33
pass the current rule. **Black** garments on the approved Minh sheet measure v 0.24-0.37 (pass); the
"failures" are the rejected white-shirt candidates and boxes that touch skin or background in my crude
fixed region. **Decision: step 4 changes no rule.** The photographic white and black pass the cel-calibrated
rules; a regression test pins the measured values instead.

## Implementation notes (2026-10-06)

- Done in code: `STYLE_EDITORIAL` and the photographic negatives (real CLIP counts 72 and 44), `outfit_phrase`,
  the "colours must differ" rule removed, `IMAGE_BASE_REPO` / `IMAGE_SCHEDULER` settings and the `load`
  request, the worker's fp16-first download, the API `style_id` = `editorial_photo`.
- New tests: `tests/test_visuals_phase28.py` (9, including a real-tokenizer budget check); four old
  tests were updated where they pinned the cel-anime strings or the "must differ" rule.
- **Found for Task 28.4:** the character form allows at most 4 hair words, so Lan's hair is written
  "long straight black hair" in the library (not "very long ...").

## Smoke result (2026-10-06)

`docs/operations/phase28-t3-smoke.md`: 8 images through the app's engine, 34 s each. The smoke found a real
bug (black garments measured on the hand, because the cel outline filter removed the shirt); fixed with
`include_dark` for black, 2 new tests. The duo's colour swap is a single-pass effect that the app's refine
and retry repair; it is verified with the real library in Task 28.4.
