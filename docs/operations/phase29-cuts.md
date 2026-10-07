# Phase 29 Task 29.0: cleaner cuts (2026-10-07)

**Frames:** `docs/operations/phase29-cuts-frames.png`: the first speaker change of the Gate B-20 episode (11.72 s) at -2, 0, +1,
+2, +3, +4, +5 and +8 frames, rendered by the app's own Remotion job with the new constants.

- Before: a 10-frame (0.33 s) dissolve at every change of speaker, 18 frames around inserts; two faces on top of each other
  for a third of a second (the frame at 12 s of the first video).
- Now: `CROSSFADE_FRAMES = 4` (0.13 s) and `INSERT_CROSSFADE_FRAMES = 9` (0.3 s). In the render the overlap is visible on
  frames +1 to +3 only and the new shot is clean from +4.
- Tests: vitest 47 passed (the cut tests now pin 4 and 9 frames, and that the previous picture is gone after them), `tsc` clean.
- Not changed: the slow zoom or pan inside a shot, the intro and outro morph.
