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
