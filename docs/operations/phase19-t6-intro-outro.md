# Phase 19 Task 19.6 — Intro + outro + chapter/progress bar + Remotion thumbnail still

- **Task:** 19.6 (Coder). Design record: `.viepilot/phases/19-remotion/tasks/task-19.6.md`
  (D19.6-a..h, PM-approved 2026-09-29, sha `b120cbd`).
- **Run date:** 2026-09-29. **Code HEAD at task start:** Task 19.5 accepted (`4548653`,
  PM task-level).
- **Scope:** composition change only. `app/services/video_service.py` untouched (confirmed
  below, §6). No `VideoService` wire-up (that's 19.7).

## 1. Real finding: `<Sequence>` already remaps `useCurrentFrame()` (D19.6-a)

Read `video-renderer/node_modules/remotion/dist/cjs/Sequence.js:379` directly:
`const content = frameInParent - from < -boundaryTolerance`. A `<Sequence from={N}>` genuinely
remaps `useCurrentFrame()` for its children to `frameInParent - from` -- frame 0 *inside* the
Sequence is already that Sequence's own start. Practical consequence: wrapping the existing
karaoke/speaker-chip/vocab-card tree in `<Sequence from={introFrames}>` required zero changes
to their internal `currentTimeSec = frame / fps` math -- it already lines up with
`line.startSec`/`endSec` (both audio-relative) with no manual offset subtraction anywhere in
`Episode.tsx`. This is the one real risk Option B (extend) carried; it turned out not to
apply. Implementation: `Episode.tsx` now renders three `<Sequence>`s (`Intro`, `Audio`,
`Outro`); `<Audio startFrom={0}>` moved inside the audio-window Sequence.

## 2. Real finding: chapters data source returns text, not structured data (D19.6-e)

`app/services/youtube_service.py:85-105`'s `real_chapters_from_timestamps` returns a single
newline-joined **string** (`"00:00 Introduction\n00:20 Label\n..."`), not the
`Array<{title, startSec}>` the card's `types.ts` schema needs. Confirmed with a real call
against the pinned episode's actual timestamps:

```
00:00 Introduction
00:20 Well, the first thing I do…
00:45 I drink a big glass of…
01:09 Just ten minutes of fresh air…
01:33 If you put your alarm clock…
01:56 If you don't eat anything, you…
02:20 Exactly. Small changes can help you…
02:47 Anytime! Let me know if you…
```

Resolved with a small runner-side parser, `_parse_chapters_text` (`scripts/run_remotion_spike.py`):
splits on `"\n"`, then per line on the first space into `"MM:SS"` and the rest as `title`,
converting `"MM:SS"` to `startSec`. Real parser output for the block above (first 3 lines
shown as the auditable sample):

```json
[
  { "title": "Introduction", "startSec": 0 },
  { "title": "Well, the first thing I do…", "startSec": 20 },
  { "title": "I drink a big glass of…", "startSec": 45 }
]
```

This only reformats fields `real_chapters_from_timestamps` already computed
(`cue["start_sec"]` rounded, `cue["text"]` truncated via `_chapter_label`) -- it does not
decide which lines become chapters or how labels are built. That heuristic
(`YOUTUBE_CHAPTER_MIN_LINES`, `_chapter_label`) stays entirely inside the Python function, per
D19.6-e's single-source-of-truth rule. Empty timestamps -> `""` -> `[]` is handled (not an
error; the progress bar renders with no tick marks).

## 3. Real finding: `remotion still`'s frame selection is a CLI flag (D19.6-f)

Ran `npx remotion still --help` for real. Confirmed usage:
`remotion still <serve-url|entry-point>? [<composition-id>] [<output-location>]`, with a real
`--frame <value>` override option alongside `--props`. The 50%-of-audio-duration still
timestamp (owner decision) is therefore a **runner-side computation passed via `--frame`**,
not something `StillFrame`'s own `calculateMetadata` can express (`calculateMetadata` controls
`durationInFrames`/`fps`/dimensions, not which single frame gets captured). Implementation:
`StillFrame.tsx`'s `calculateMetadata` computes duration from `audioSec * fps` only (no
"50%" anywhere in JS); the runner computes
`still_frame = round(0.5 * audio_job["duration_seconds"] * RENDER_FPS)` and invokes
`npx remotion still src/index.ts StillFrame <output.png> --props=<file> --frame=<still_frame>`,
mirroring `_run_render`'s existing invocation shape exactly. `StillFrame` reuses the exact same
`AudioWindowContent` component `Episode.tsx` uses for its own audio window (exported from
`Episode.tsx`), so the still's visuals are guaranteed identical to the video at that instant --
no separate implementation to drift out of sync.

## 4. Real render (pinned episode `b330d37f-a212-4cf7-a779-7a109098bd6c`)

| Measurement | Value |
|---|---|
| Real chapters computed | **8** (via `real_chapters_from_timestamps`, parsed) |
| Audio duration | 176.02 s |
| Total video duration (intro 2.5s + audio + outro 5.0s) | 183.53 s |
| Video output frames (ffprobe `nb_frames`) | 5506 (== `ceil(183.533 × 30)`, exact) |
| Video file size | 9,958,283 bytes |
| Still PNG frame (== `round(0.5 × 176.02 × 30)`) | 2640, exact |
| Still PNG dimensions (ffprobe) | 1280×720 |
| Still PNG file size | 60,570 bytes |

## 5. Verification frames (real data, one coherent run)

Evidence under `data/tmp/phase19_spike/` (gitignored scratch): the rendered video, this run's
`.props.json`, the still PNG, and the 5 frames below (`t6_frames/`).

| # | Timestamp (absolute, video) | Expected | Frame file | Observed |
|---|---|---|---|---|
| 1 | t=1.0s (intro window) | Title slide: project name, speaker names, `[CEFR] topic` | `t6_intro.png` | "Demo Episode" / "Alex & Maya" (amber) / "[B1] The best way to start your morning" -- match |
| 2 | t=15.0s (= 12.5s into audio, same instant as 19.5's own combined frame, shifted by `introSec`) | Combined-features frame: karaoke + active chip + vocab card + chapter bar all visible, no regression from 19.3/19.4/19.5 | `t6_combined.png` | Alex chip active (amber), Maya dimmed, vocab card "routine" (correct definition/example), karaoke word "recently" highlighted, chapter bar with tick marks visible at top -- match, proves all four features render together |
| 3 | t=20.0s (audio window) | Chapter bar: early progress | `t6_chapterbar_early.png` | Thin played-portion strip near the left edge, tick marks visible | 
| 4 | t=170.0s (audio window) | Chapter bar: late progress, visibly wider than #3 | `t6_chapterbar_late.png` | Played portion visibly extends much further right than #3 -- bar genuinely progresses across the audio window |
| 5 | t=180.5s (outro window) | Owner-approved CTA text, centered | `t6_outro.png` | "Thanks for watching · Subscribe for more · See you next episode!" exact string, centered -- match |

All 5/5 correct.

**Still PNG** (`b330d37f-a212-4cf7-a779-7a109098bd6c.png`, frame 2640 = 88.0s into the audio
window, the owner's fixed 50%-of-real-audio-duration decision): shows Maya's chip active, her
real caption line, and the chapter progress bar at ~50%. **Disclosed rather than smoothed
over:** this exact real timestamp does not happen to have a vocab/idiom card active (no
learning item's line covers t=88.0s) -- a real content coincidence, not a bug. The "all four
features in one frame" proof required by the Verification checklist is satisfied by frame #2
above (a video frame, not the still) instead, since the still's timestamp is an owner decision
(task-19.6.md header) this task must not override to chase a more photogenic frame.

## 6. Re-verification of Task 19.1/19.3/19.4/19.5 invariants (D19.6-h)

- `git log fe06405..HEAD -- app/services/video_service.py`: **empty.** Untouched -- still the
  last task before 19.7 touches it.
- Python full suite: **1189/1189 passed**, unchanged (no Python test files touched; the
  runner-script change is code, not tests). `ruff check .`: clean.
- `tests/test_video_studio_browser.py`: **10/10 passed**, unchanged.
- Frame #2 above (§5) is the direct proof 19.3's karaoke, 19.4's speaker chip, and 19.5's
  vocab card all still render correctly alongside this task's new chapter bar.

## 7. Wall-time investigation (not shrugged off)

| Run | Context | Wall time |
|---|---|---|
| 1 (via `run_remotion_spike.py`, cold, real DB/TTS pipeline ahead of it) | first real end-to-end run | **85.07 s** |
| 2 (repeat, same saved `.props.json`, `npx remotion render` direct) | isolates render-only cost | **63 s** |
| 3 (repeat, same saved `.props.json`, `npx remotion render` direct) | isolates render-only cost | **63 s** |

The card's own D19.6-g guidance expected roughly +8-15% over 19.5's 60-61s baseline (~65-70s).
Run 1's 85.07s was well above that. Investigated rather than accepted: at the time of run 1,
`tasklist` showed **17 concurrent Chrome processes** on this shared machine -- consistent with
the same "transient shared-machine load" cause identified in Task 19.4's own wall-time
anomaly. Two repeat renders against the exact same real props (bypassing the DB read + 30-line
Edge TTS resynthesis that run 1 also paid for) landed at 63s and 63s, back-to-back -- this
isolates the genuine per-frame cost of the new Sequences/Intro/Outro/chapter-bar composition.
63s matches the proportional expectation from the added intro+outro frames almost exactly:
`61s × (183.53 / 176.02) ≈ 63.6s`. **Conclusion: the new composition adds no measurable
per-frame cost beyond the extra intro/outro frames themselves; run 1's 85.07s was real but
attributable to shared-machine load, not this task's code.**

The still render itself took **3.261 s** (single frame, negligible, as expected).

## 8. Full checks

- `tsc --noEmit` on `video-renderer/src/`: **clean.**
- `npm run test` (vitest): **28/28 passed** (6 karaoke + 4 speaker + 11 vocab + 7 chapters).
  Revert-and-confirm-failure done: reverted `computeProgressForFrame` to always return
  `{overallPct: 0, currentChapter: null, chapters: []}` -- 4/7 chapters tests failed with real
  assertion mismatches (not crashes); restored, 28/28 green again.
- Python full suite: **1189/1189 passed**, unchanged. `ruff check .`: **clean.**
- `tests/test_video_studio_browser.py`: **10/10 passed**, unchanged.
- `git log fe06405..HEAD -- app/services/video_service.py`: **empty.**

## 9. Carry-over conditions (acknowledged, not acted on)

1. **8-min B1 episode:** still does not exist in `data/app.db`. This task deliberately
   rendered the same `b330d37f...` (2:56 actual audio) as every prior Phase 19 task, for
   wall-time comparability -- not invented, not silently switched.
2. **Chrome ~270 MB hard floor:** still 19.7's problem. No `video-renderer/` packaging change
   in this task.
