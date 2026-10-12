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

## Round 2 (Task 32.8d, 2026-10-12) — after Gate B-22 FAIL

Fixes: 32.8a (BUG-029, speaking character's pictures), 32.8b (ENH-028, pictures behind both characters),
32.8c (BUG-030, word timings restored). The rejected render is kept as `video_gate_b22_r1.mp4`; the previous mix as
`data/audio/<project>/mix_before_r2.*`; database backup `data/backups/app-before-phase32-r2-20261012-140347.db`.

Audio (production API, 113 s): 30/30 lines re-synthesized from the pre-19.2 cache, 413 words, `lines_without_words` 0,
176.02 s, -16.0 LUFS. Render (production API, Enhanced, 176.6 s): 192.256 s, H.264 1280x720 + AAC, full decode clean.

| Beat | Line | Speaker | Final video time | Picture chosen |
|---|---|---|---:|---|
| morning routine | 4 | Alex | 27.91–33.86 | Alex `morning routine` (character) |
| exercise | 8 | Alex | 52.92–57.77 | Alex `exercise` (character) |
| cooking breakfast | 22–23 | Alex | 133.99–139.99 | Alex `cooking` (character) |

Frames in `data/video/b330d37f-a212-4cf7-a779-7a109098bd6c/phase32_evidence/r2/`: at every beat midpoint both
sprites stand in front of the activity picture; `karaoke_a.png` / `karaoke_b.png` and the beat frames show the active
word highlighted. Seen in passing (not part of B-22): the speaker chip reads "Maya", the project's speaker name for
the Lina cast slot; the vocabulary card can sit over the background picture's person.
