# Task 24.6 — Remotion motion polish for storyboard videos (doc-first card)

## Objective

With few pictures per episode (owner E4), motion carries the life between cuts. Today every shot
does the same 1.00 → 1.04 zoom-in with a 10-frame crossfade. This task varies the motion per shot
while keeping it subtle (O8: "not stiff", no dizzying moves), and gives inserts (the story's
illustrations) a softer, longer entrance.

## Paths

- `video-renderer/src/visuals.ts` (motion + crossfade)
- `video-renderer/src/Episode.tsx` (apply the transform)
- `video-renderer/src/visuals.test.ts` (vitest)

## File-Level Plan

- **visuals.ts:**
  - `shotMotion(id)`: a deterministic choice (string hash) of zoom-in, zoom-out, pan-left or
    pan-right. The same shot always moves the same way, so renders are reproducible.
  - `motionTransform(motion, progress)` → `{scale, x, y}`:
    - zoom-in 1.00 → 1.05;
    - zoom-out 1.05 → 1.00;
    - pan at a fixed scale 1.06, x from +2.5% to −2.5% (or reverse).

    |x| always stays ≤ (scale − 1) / 2, so the image never shows an edge.
  - Crossfade: 10 frames between shots of a place; **18 frames** when either side of the cut is
    an insert (a change of picture world).
  - `visualBackgroundForFrame` returns `transform` (a CSS string) next to the existing fields.
    `scale` is kept for compatibility.
- **Episode.tsx:** the current-shot `<Img>` uses `background.transform` instead of
  `scale(${background.scale})`.

## Best practices

Pure, deterministic functions (no `Math.random`, so Remotion frames are reproducible); vitest
covers bounds; no layout change.

## Verification

vitest:
- the motion is deterministic per id and all 4 motions occur over a sample of ids;
- edges stay hidden at progress 0, 0.5 and 1 for every motion;
- an insert crossfade lasts 18 frames, a regular one 10;
- the transform string is well formed.

`npx tsc --noEmit` clean; Python suite unaffected (props unchanged).
