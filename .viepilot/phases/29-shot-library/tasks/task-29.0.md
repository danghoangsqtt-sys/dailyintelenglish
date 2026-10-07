# Task 29.0: Cleaner cuts between shots

## Owner feedback (2026-10-07)

"The change between pictures makes the ghost effect a bit too much."

## Facts

- `video-renderer/src/visuals.ts`: `CROSSFADE_FRAMES = 10` (0.33 s at 30 fps) and `INSERT_CROSSFADE_FRAMES = 18` (0.6 s).
  `visualBackgroundForFrame` shows the previous picture under the new one until the fade ends.
- A dialogue changes speaker line by line, so a single of the first speaker dissolves into a single of the second many
  times a minute: two faces overlap for a third of a second each time (the frame at 12 s of the Gate B-20 video).

## Plan

- `CROSSFADE_FRAMES = 4` (0.13 s) and `INSERT_CROSSFADE_FRAMES = 9` (0.3 s): near-hard cuts that still hide a one-frame pop.
- `crossfadeFrames` stays the one function that decides the length, so the tests and the composition agree.

## Paths

- `video-renderer/src/visuals.ts`
- `video-renderer/src/visuals.test.ts`
- `docs/operations/phase29-cuts.md` (the real-render check)

## Verification

- vitest: the two constants, that `crossfadeFrames` returns them, that the previous picture is gone after 4 frames (and
  after 9 for an insert), and that the new picture is at full opacity then.
- A real render of a speaker change (frames around a cut) shows no overlap after the fade; sheet saved.

## Task 29.0 closed (2026-10-07)

Done as planned; report `docs/operations/phase29-cuts.md`. vitest 47 passed, `tsc` clean, a real render checked. The change is
TypeScript only (no Python file changed), so the Python suite is run with the next task.
