# Expanded vertical motion — 2026-10-15

Owner request: add more motion effects to the current lively vertical episode. This extends the existing scene drift, ambient background and yellow karaoke highlight.

## Added motion groups

1. **Activity reveal/settle:** approved activity images reveal from alternating sides over 420 ms, with at most 16 px translation and 2.5% temporary extra zoom. The reveal settles before the insert's hold period.
2. **Transition light sweep:** a faint warm sweep crosses the image during its first 700 ms. The scene and insert are still composited before the shared scene mask, preventing sustained double exposure in the lower image.
3. **Speaker spotlight:** a soft background glow follows the active character slot, easing in and out around the actual dialogue line. The original character images and their proportions are preserved.
4. **Speaking indicators:** three animated bars and a small badge glow indicate the active speaker. This is a speaking-status animation, not an audio-amplitude measurement.
5. **Vocabulary motion:** cards slide, rotate slightly and pop into place at their learning-slot boundary, with a slim brand accent and one brief light sweep. They leave within the same slot.
6. **Caption/word motion:** caption pages alternate entrance directions while remaining within their column; active words cycle between pop, lift and glow accents. A thin progress line follows the original word interval of each page.
7. **Ambient bokeh:** eight low-opacity light motes move through the decorative side gutters, behind all text and characters.

All animation is deterministic from frame, fps and the existing content timings. No added audio, model/API dependency, encoder policy or horizontal visual change.

## Technical verification

- TypeScript clean; **83 Vitest tests passed**. New tests verify caption transform bounds, insert settling, particle placement/determinism, speaking/card envelopes, reading progress and word timing.
- Actual `Episode` DOM scanned at **757 sampled frames**, including word midpoints and 30/100/180/320 ms entrance/exit samples around dialogue boundaries. There are **755 visible caption measurements** covering **88 pages**; maximum caption height **235.563 px** within 250 px. Vocabulary maximum height **321 px** within 400 px. **Zero overflow failures**. The offscreen initialization sample is excluded; another sampled frame contains no caption because its dialogue line has ended.
- Inspected insert entrance/hold and vocabulary entrance stills. The **22-second motion preview** uses the actual episode soundtrack and covers an activity insert, a speaker handoff and a learning card: `data/tmp/vertical-motion-library/motion-preview.mp4`.

## Full episode

Before regeneration, the project SQLite DB and original MP4/SRT outputs were snapshotted under `data/backups/vertical-motion-20261015-104954/`.

The normal source API successfully rendered the complete vertical episode in **424.081 seconds** and exported it into `D:\Example-videos\Local Market\Ep 02 - Shopping at the Market\video_vertical.mp4`. Source application remains at http://127.0.0.1:8001.

- Final media: **1080x1920 H.264/AAC**, **249.514667 seconds**, **470,564,946 bytes**; audio/video duration difference **0.048 seconds**.
- AAC audio bitstream hash matches the previous version exactly. Horizontal MP4 and SRT hashes remain unchanged.
- Source/export MP4 hashes match and the export API reports no error.
- Finished-video frames at 108 and 121 seconds were inspected, including the activity hold without sustained scene ghosting and the settled vocabulary card.
- Effects are integrated into the vertical renderer for subsequent renders; this task does not add a preset selector to the UI.

Evidence and disposable QA tooling: `data/tmp/vertical-motion-library/`. Formal owner gate acceptance, commits and release remain pending; no EXE is rebuilt by this work.
