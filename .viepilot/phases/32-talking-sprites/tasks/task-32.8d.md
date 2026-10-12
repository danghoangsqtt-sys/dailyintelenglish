# Task 32.8d: Regenerate and re-render the Demo Episode for the re-gate

## Plan

1. Keep the current files for comparison: rename `video_remotion.mp4` to `video_gate_b22_r1.mp4` (the rejected render);
   `video_sprites_preview.mp4` stays as the baseline.
2. Regenerate the Demo Episode audio through the production API (32.8c re-synthesizes the old lines): word timings on all
   30 lines, duration and loudness within the usual tolerance of the previous mix.
3. Render `podcast_sprites` through the production API (Enhanced, no fallback).
4. Evidence in `data/video/b330d37f-a212-4cf7-a779-7a109098bd6c/phase32_evidence/r2/`: for each insert beat, frames before,
   mid and after showing both sprites in front of the activity picture; which picture was chosen (character or generic) and
   why; a caption frame showing the karaoke highlight.
5. Update `docs/operations/phase32-demo-cutaway-notes.md` with the new timeline and choices.

## Paths

- `docs/operations/phase32-demo-cutaway-notes.md`
- (runtime data under `data/`, not committed)

## Verification

ffprobe (1280x720, h264/aac, duration), full decode, `audio_jobs.word_timestamps_json` word counts, usage records name the
character pictures where they exist (Alex `exercise`/`working out` for the stretching line).
