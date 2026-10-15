# Task 46.6: Add a richer vertical motion vocabulary

Owner follow-up: add more motion effects to the current lively 9:16 design. Continue the authorized video improvement.

## Plan and allowed_files
- renderer/src/verticalMotion.ts and verticalMotion.test.ts: bounded deterministic helpers for caption direction/progress, word accents, vocabulary entrance, activity reveal, speaking indicators and decorative particles.
- renderer/src/MotionAccents.tsx: ambient bokeh and a soft spotlight following the speaking character, behind the original sprite pictures.
- renderer/src/Sprites.tsx: activity reveal/settle and a brief light sweep, using the existing composited scene mask; integrate stage accents.
- renderer/src/Episode.tsx: vertical speaker meters, vocabulary entrance/accent, alternating caption entrance, reading progress and varied active-word motion.
- This task card and docs/operations/vertical-motion-library.md.
- Disposable preview props, frames, clips and QA under data/tmp/vertical-motion-library/.
- Back up current project DB/media under data/backups/ before normal vertical API regeneration and the configured episode export hook.

## Design and risk
Keep the established center alignment, character pictures/proportions, safe zones, transcript and word timing. Motion follows actual speech/insert/card boundaries; decoration stays behind content. Use green/yellow accents. Add seven complementary effects: activity reveal and settle; transition light sweep; speaker spotlight; speaking meter; vocabulary pop/slide; varied caption/word entrances plus reading progress; ambient bokeh. Avoid continuous camera shake, random frame state and added sound effects. Horizontal rendering retains its existing branches. Do not change encoder policy or external dependencies.

Risks: motion may move cards outside reserved regions or increase render time/file size. Bound all transforms, measure actual text/card rectangles, and inspect speech/learning/insert frames before rendering the full episode. Preserve the prior output for comparison/rollback.

## Verification
- TypeScript and renderer Vitest, including bounds/determinism/timing tests for the new helpers.
- Reuse the actual Episode DOM scan for all Ep. 2 caption pages and vocabulary slots, including entrance/exit samples; inspect representative stills and motion samples.
- Render corrected final Ep. 2 vertical output through the normal source API; verify dimensions, duration, identical audio bitstream, unchanged horizontal/SRT, and source/export hash equality.
- No EXE build, release, commit/push or self-acceptance of owner gates.

## Result: implemented_verified_pending_pm

- Seven motion groups added, using the actual speaker, word, learning-slot and activity-insert timings; horizontal branches and character proportions retained.
- TypeScript clean; 83 Vitest tests passed. Expanded real Episode DOM scan: 757 sampled frames, 755 visible caption measurements, 88 pages, no overflow failures. Maximum caption/vocabulary heights: 235.563/321 px in 250/400 px regions.
- Actual 22-second preview and entrance/settled stills inspected before full regeneration. Final vertical rendered in 424.081 s: 1080x1920 H.264/AAC, 249.514667 s, 470,564,946 bytes, A/V difference 0.048 s.
- AAC bitstream identical to the previous video; horizontal MP4 and SRT unchanged. Exported video hash matches source; export reports no error. Finished-video insert and learning frames inspected.
- Snapshot retained at data/backups/vertical-motion-20261015-104954/. Evidence and preview: data/tmp/vertical-motion-library/. Report: docs/operations/vertical-motion-library.md.
- No formal owner acceptance, phase completion, EXE release or commit/push declared.
