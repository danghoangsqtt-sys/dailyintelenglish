# Phase 28 Task 28.4b: the app's own shot pipeline with Lan and Minh (2026-10-06)

**Method:** a throw-away copy of the data folder (`scripts/make_smoke_copy.py`) and a second app instance
(`DIE_DATA_DIR`, port 8001); `POST /api/projects/<Demo Episode>/visuals/shots`: the real storyboard job with the
face references, the duo refine, the hand repair, the colour retry and the extra-person check. **12 shots** (2
singles, 1 close duo, 6 wide duos, 3 inserts), about 62 job steps, about 45 minutes. Sheet:
`docs/operations/phase28-shots-real-pipeline.png`. The real data was not touched.

## What works

- All 12 shots complete; no prompt is cut (65-67 estimated tokens for the duos).
- The look is the photographic editorial look, sharp, in the 55 new plates' cafe; **Lan and Minh are
  recognisable** in singles and duos (the fringe and the black shirt; the long straight hair and the white blouse).
- Lan in a white blouse is right in most shots; Minh alone is truly black (measured value 0.08).

## What does not work yet (found here)

1. **Minh's shirt is dark navy, not black, in the duos** (7 of 7 duo shots): measured hue 225-234 degrees,
   saturation 0.32-0.42, value 0.12-0.32. The black rule (`v < 0.35`) accepts it, so the colour retry never
   fires.
2. **An extra person is not detected:** shot 12 shows three people (an extra man in a white shirt). The
   extra-person check uses the anime cut-out, which is unreliable on photographs (it already said 0.0 on a market
   full of vendors in Task 28.4a).
3. **Lan drifts in a few shots:** a white or navy blazer over the blouse (2 and 6) and blue jeans (8). The
   checks look at the chest only; a seated duo has no trouser check.
4. Insert shot 7 (a person stretching) draws a stranger: inserts are "no characters" by design, and the model
   shows a person when the subject names one. Not a regression.

## Decision

- Fix (1) in the colour rule and the prompts: calibrated on these measurements.
- (2) needs a person or face detector that works on photographs; that is a download and is asked of the owner.
- (3) is a prompt and negative question: tried after (1), measured again.

## Fixes made and measured again (2026-10-06)

- **Colour rule for black** (`colour_check.py`): `(v < 0.35 and v * s < 0.055) or (s < 0.25 and v < 0.42)`. The 7
  navy duo shirts (v * s 0.07-0.12) now fail it, so the colour retry fires; every measured black (v * s up to
  0.046, or low saturation) still passes.
- **`recipes.negative_for(*characters)`**, used by the duo refine, the colour retry and the shot encode: a black
  outfit swaps "multicolored clothes" for "navy blue clothes"; a white outfit adds "blazer" and (unless someone
  wears jeans) "blue jeans". A navy outfit is never fought. Always within 77 real CLIP tokens (tested for every
  combination).
- **Re-run of shots 6, 8 and 12** with the new code (`docs/operations/phase28-shots-after-fixes.png`):
  - shot 6: **fixed**: Minh's shirt is black, Lan has no blazer;
  - shot 8: **mostly fixed**: black shirt, no blue jeans; the trousers still differ (grey on Minh, black on Lan),
    because a seated duo gets no trouser check (the table hides the legs);
  - shot 12: **no third person this time, but the two swapped outfits** (Minh in white, Lan in a white dress);
    the colour retry ran out (2 attempts) and the shot stayed wrong with no warning to the user.

## Still open, and what each needs

1. **Detecting a third person on photographs** needs a face or person detector that works on photos. The small
   ONNX face detectors (about 1-2 MB, MIT licence, run with the onnxruntime that is already installed) are the
   cheap answer; it is a download, so the owner decides.
2. **A shot that still fails its colour check after the retries** is accepted silently. Either more retries
   (each about 2 minutes), or render two candidates and keep the one that passes, or mark the shot "colour
   mismatch" in Step 5 so the owner can regenerate it. The mark is cheap; the other two cost time.
3. **Trouser colour in seated duos** is unchecked.

## Task 28.5: face counting and the "check this shot" mark, run on the real job (2026-10-06)

- **Model:** UltraFace RFB-320 (MIT, 1.27 MB, pinned commit, SHA-256 checked), on the CPU with the onnxruntime already
  in `venv-image`. Measured on this project's shots: singles 1 face, duos 2, inserts 0, the fixed shot 12 = 2, and the
  original three-person shot 12 = **3** (the anime cut-out said 0.0). It is a test fixture
  (`tests/fixtures/three_people_cafe.png`) with 0 / 1 / 2 / 3 face checks on the real model.
- **Real run (shots 12 and 6 regenerated with the new code):** shot 12 now has 2 faces and passes both colour checks, no
  note. Shot 6 finished with the note **"Minh's top ... not black"** produced by the pipeline itself: the colour was
  still outside the black rule after the two retries. Step 5 shows it as an amber line with Regenerate as the primary
  button (`docs/operations/ui-audit/step5-check-this-shot.png`).
- **That note was a false alarm** (Minh's shirt is black in the picture): it measured value 0.157, saturation 0.37,
  just past the threshold set the day before. The data separates the two better by value: real blacks read <= 0.16,
  the navy shirts >= 0.18. The black rule became `v < 0.16 or (s < 0.25 and v < 0.42)` (the real black is a test
  sample now) and shots 6 and 12 pass.
- **A limit that stays:** a *lit* black shirt (value 0.27, saturation 0.32, shot 8) is not separable from navy by HSV.
  So the note says "may not be black" and never asserts it; the cost of a false alarm is one look and one click.
  Re-measured with the new rule, the four older navy duo shots (3, 4, 9, 10) are flagged, as they should be.
