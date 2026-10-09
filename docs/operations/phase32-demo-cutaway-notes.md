# Phase 32 Demo Episode cutaway notes

Date: 2026-10-09
Project: `Demo Episode` (`b330d37f-a212-4cf7-a779-7a109098bd6c`)

## Timeline

The narration timeline starts after the 7.62-second branded intro. The final video timing
below includes that offset.

| Beat | Activity | Narration time | Final video time | Length | Visual result |
|---|---|---:|---:|---:|---|
| 1 | morning routine | 20.288–26.240 | 27.908–33.860 | 5.952 s | Person waking and avoiding the phone; relevant to Alex's line |
| 2 | exercise | 45.304–50.152 | 52.924–57.772 | 4.848 s | Group stretching; directly supports “stretch for ten minutes” |
| 3 | cooking breakfast | 126.368–132.368 | 133.988–139.988 | 6.000 s | Kitchen food preparation; demonstrates the 6-second cap |

All three matches are approved, generic assets. The third requested action
`cooking breakfast` correctly resolves to the broader `cooking` activity.

## Transition evidence

Evidence directory:
`data/video/b330d37f-a212-4cf7-a779-7a109098bd6c/phase32_evidence/`

For each beat:

- `beatN_before.png`: 0.15 seconds before cutaway start; talking sprites are visible.
- `beatN_fadein.png`: 0.15 seconds after start; the expected 0.3-second blend is visible.
- `beatN_mid.png`: full-screen activity image is visible.
- `beatN_fadeout.png`: 0.15 seconds before end; the reverse blend is visible.
- `beatN_after.png`: 0.15 seconds after end; talking sprites are restored.
- `beatN_transition_sheet.png`: the five frames above in left-to-right order.

Visual inspection result:

- No stretched or letterboxed cutaway; each image fills 1280×720 with cover cropping.
- The 0.3-second fade is visible at both boundaries for all three inserts.
- The speaker chip and active-speaker state remain visible.
- Subtitles remain readable and synchronized at all three midpoints.
- Vocabulary cards continue to appear over beats 1 and 3.
- The underlying talking-sprite scene returns without a layout jump.

## Audio continuity

The candidate decodes cleanly. Its AAC stream is continuous from 0.000 to 192.256 seconds:
9,012 packets, no gap over 1 ms, and a maximum measured positive packet gap of one
microsecond. The cutaway layer therefore does not interrupt or replace the soundtrack.

## Gate B-22 files

- Baseline: `data/video/b330d37f-a212-4cf7-a779-7a109098bd6c/video_sprites_preview.mp4`
- Candidate: `data/video/b330d37f-a212-4cf7-a779-7a109098bd6c/video_remotion.mp4`

The owner should compare image relevance, transition quality, subtitle/audio continuity
and whether three cutaways add useful visual variety without distracting from the lesson.
