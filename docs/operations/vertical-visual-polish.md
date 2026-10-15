# Vertical episode visual polish — 2026-10-15

The owner reported that the safe layout looked left-heavy and the upper photograph did not blend with the character stage. The owner selected a more lively style with clearer transitions and word emphasis.

## Changes

- Move the character pair from centers 270/640 (average 455) to 355/725 (average 540), matching the 1080-pixel frame center. Caption, vocabulary, speaker and hook columns also center on x=540.
- Keep the existing platform exclusion limits. Speech labels, vocabulary, captions, hooks and the face envelopes additionally fit the supplied ads reference: x=48..888 and y=288..1248. Bodies and decorative imagery may extend outside that rectangle. Intro/outro retain their existing layout.
- Carry the scene's colors into a blurred, dark green ambient backdrop across the full frame. A continuous image alpha mask blends the upper photograph into it; soft stage light sits behind the figures. Full-bleed imagery is preserved.
- Apply that mask once to the composited scene/insert group. An intermediate render masked each image separately, which revealed the previous scene through the lower part of an opaque insert; visual review caught and corrected that ghosting before delivery.
- Add deterministic lateral drift (up to 12 px), vertical drift (up to 6 px), and slow zoom (1.025..1.055). Scene and activity-insert cross-fades continue to use their existing timing.
- Add a short caption-page entrance and a yellow active-word pill with a brief scale pulse (up to 1.07) using the existing word timings. The speaker name sits on its own row.
- Bound narrow caption pages by 10 words and 54 characters. This preserves every token and its timing while avoiding overflow from long English words. Existing callers that omit the character limit retain the previous word-only behavior.
- Use explicit border-box widths for the centered vocabulary cards to prevent padding from extending outside the safe region.

## Verification

- TypeScript check clean; **79 renderer tests passed**, including centering, both reference regions, motion limits, and the two long-caption regressions.
- A disposable composition wraps the actual `Episode` component and measures its real DOM at 620 sampled frames from the episode's word timings. Of these, 619 provide visible caption measurements covering 88 pages. The first effect ran during Remotion's offscreen initialization and is excluded; subsequent words measure that same initial page normally.
- Final scan: **zero overflow failures**. Caption maximum height: **235.563 px** in a 250-pixel region. Vocabulary maximum height: **319 px** in a 400-pixel region, with 176 measurements and no clipped cards.
- The initial scan caught two real long-caption pages (292.75 px) before the character budget was added; the repeated scan verifies the correction.
- Inspected real speech and vocabulary stills. A 13-second motion sample covers page/word changes and an activity-picture entrance/exit, with the existing episode soundtrack. Sample: `data/tmp/vertical-visual-polish/motion-preview.mp4`.

## Application to the real episode

Before regeneration, SQLite and both original media formats were snapshotted at `data/backups/vertical-polish-20261015-100335/`. A full first pass rendered in 413.613 seconds; visual inspection then caught the insert compositing issue described above.

The corrected full episode rendered successfully through the normal source API in **419.607 seconds** and was automatically exported to `D:\Example-videos\Local Market\Ep 02 - Shopping at the Market\video_vertical.mp4`.

- Final MP4: **1080x1920, H.264/AAC, 249.514667 seconds**. Audio/video duration difference: **0.048 seconds**.
- Audio AAC bitstream hash is identical to the previous vertical version. Existing horizontal MP4 and SRT hashes are unchanged.
- Exported MP4 SHA-256 matches the generated source. Export reports no error. Corrected output frames at 24 and 108 seconds were inspected, including the fully visible activity insert with no previous-scene ghosting.
- The 13-second preview was replaced with a cut of the corrected finished video.
- The animated version is approximately **470 MB** versus the previous **141 MB**, using the existing renderer quality setting. Full-frame scene motion increases encoding size and render time; no encoder-quality policy was changed.

Evidence scripts, measurements, preview props and images live under `data/tmp/vertical-visual-polish/`. No EXE build, release, commit or owner gate acceptance is declared by this work.
