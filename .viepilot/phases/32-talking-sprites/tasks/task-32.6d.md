# Task 32.6d — Full-screen cutaway renderer

## Objective

Render selected activity images as full-frame inserts in `podcast_sprites`, preserving the audio and overlays.

## Paths

- `app/services/video_renderer_remotion.py` — copy selected assets and send insert-cutaway props.
- `video-renderer/src/types.ts` — validated cutaway prop schema.
- `video-renderer/src/Sprites.tsx` — image cutaway layer above sprites and below overlays.
- `video-renderer/src/spriteTimeline.ts` — pure cutaway timing/crossfade calculations.
- `video-renderer/src/spriteTimeline.test.ts` — timing tests.
- `tests/test_activity_video_props.py` — server prop-copy and fallback tests.

## File-Level Plan

1. Cutaway starts at insert beat start, ends at beat end or six seconds, whichever is earlier; remaining long-beat audio restores sprites.
2. Use 0.3-second in/out opacity crossfades, rounded from FPS, bounded so short beats never produce invalid timing.
3. Fit images with cover crop; retain subtitles, speaker chips, vocabulary cards, chapter bar and audio exactly as in the sprite path.
4. Do not alter the non-sprite renderers or change line timestamps.

## Verification

`venv\Scripts\python.exe -m pytest tests/test_activity_video_props.py -q`

`npm run test -- --run` and `npx tsc --noEmit` in `video-renderer/`.

## Acceptance Criteria

- [ ] Insert image is fullscreen for no more than 6 seconds.
- [ ] Crossfade is 0.3 seconds at 30 fps when duration permits.
- [ ] Audio/subtitles remain continuous; missing image leaves the sprite stage visible.
