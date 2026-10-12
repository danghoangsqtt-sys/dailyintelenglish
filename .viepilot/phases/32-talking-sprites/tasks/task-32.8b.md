# Task 32.8b: Activity pictures behind the talking characters (ENH-028, D75)

## Why

Gate B-22 (2026-10-12): the activity picture is drawn after the sprites in `SpriteStage`, so it covers Alex and Lina. The
owner wants it **behind** both characters, who stay visible and animated in front — also when the picture shows the speaking
character (D75: intentional, artistic and teaching choice; no hiding).

## Plan

- `video-renderer/src/Sprites.tsx` `SpriteStage`: draw the activity layer right after the scene background(s) and before the
  sprites; give it the same slow `zoom` transform as the background so the switch does not jump. Top/bottom shades, captions,
  chips, vocabulary cards and chapters stay above, unchanged.
- Fades unchanged: `activityCutawayAt` opacity (0.3 s in/out) now blends background → activity → background.
- Timing unchanged: the 6-second cap and beat window in `video_renderer_remotion.py` stay (the owner did not ask to change the
  length; revisit at the re-gate if wanted).
- Rename nothing in the props contract (`cutaways` stays) so stored renders and tests keep working; update comments and the
  CHANGELOG wording from "full-screen cutaway" to "background".

## Paths

- `video-renderer/src/Sprites.tsx`
- `video-renderer/src/spriteTimeline.ts`
- `video-renderer/src/spriteTimeline.test.ts`

## Verification

Vitest: a layer-order test (activity layer index between background and sprites) plus the existing cutaway timing tests;
`npx tsc --noEmit`; a still frame at a beat midpoint shows both sprites over the activity picture.
