# Phase 28 Task 28.3 smoke: RealVisXL through the app's own engine

**Date:** 2026-10-06. **Script:** `scripts/smoke_phase28_t3.py` (the project venv; the image worker runs in
`venv-image`). **Sheet:** `docs/operations/phase28-t3-smoke-sheet.png` (rows: Lan alone in a cafe, Minh alone in a
park, the duo in the cafe wide, the duo close; columns: seeds 7 and 21).

- Path: `WorkerImageEngine.session("controlnet")` -> the `load` request with `base_repo` =
  `SG161222/RealVisXL_V5.0` and `scheduler` = `euler_a` -> one-pass renders with the app's own `recipes`
  prompts (46-53 estimated tokens), the app's skeletons (`geometry.shot_people`) and `recipes.NEGATIVE`.
- **8 images in 295 s: about 34 s each** at 1344 x 768, 30 steps, CFG 6. The model downloaded nothing
  new: the worker found the cached fp16 files.
- **What it shows:**
  - the editorial look is in the app: crisp, natural light, readable cafe and park, no blur;
  - Lan in a white blouse and Minh in a black shirt, in single shots, in 4 of 4 images;
  - the colour check: **single shots 4 of 4 pass**; in the duo it flags 2 of 4 correctly (the man in a white
    shirt); 1 of 4 is a false pass (both people in black, the woman's region unmeasurable).
- **Bug found and fixed by this smoke:** `colour_check.measure` dropped every pixel darker than v 0.22 as a
  cel outline, which on a photograph removed the whole black shirt and measured the hand or a button (Minh
  failed 2 of 2). A black garment is now measured on all its pixels (`include_dark`, black only).
- **Limits, stated plainly:**
  - this is a single pass without the library's face references (the characters do not exist in the library
    yet: Task 28.4), so the faces here are not the approved Lan and Minh, and the duo has the known
    colour-swap that the app's per-person refine and colour retry (`VISUALS_COLOUR_RETRIES`) repair;
  - those repair steps, the extra-person check and the scene plates are verified with the real library in
    Task 28.4 and the Gate.
