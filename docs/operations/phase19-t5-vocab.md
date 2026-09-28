# Phase 19 Task 19.5 — Vocabulary/idiom pop-up cards

- **Task:** 19.5 (Coder). Design record: `.viepilot/phases/19-remotion/tasks/task-19.5.md`
  (D19.5-a..f, PM-approved 2026-09-29).
- **Run date:** 2026-09-29. **Code HEAD at task start:** Task 19.4 accepted (`693fba7`,
  PM task-level).
- **Scope:** composition change only. `app/services/video_service.py` untouched (confirmed
  below, §5). No `VideoService` wire-up (that's 19.7).

## 1. Real finding before writing any composition code: no `line_id` field exists

The card's proposed `attachItemsToLines(vocab, idioms, lines) -> Array<{line_id, items}>`
assumes lines carry a `line_id`, but `episodeLineSchema` (unchanged since 19.1) has no
line-level id at all -- only `startSec`/`endSec`/`speaker`/`speakerId`/`text`/`words`.
`speakerId` is the *speaker's* id, not the line's. Resolved (PM-approved) by using the line's
own array index instead -- the same positional convention every other composition function
(`activeLine`, `activeSpeakerId`, `buildKaraokeTokens`) already uses against the same `lines`
array. `attachItemsToLines` returns `Array<{lineIndex: number, items: LearningItem[]}>`.

## 2. Real match numbers (checked before writing composition code, reconfirmed at implementation time)

Ran both matching strategies against the real 5-vocab + 4-idiom pack and the real 30-line
script for `b330d37f-a212-4cf7-a779-7a109098bd6c` -- **100% match rate on both, unchanged
between the design-time check and this render's own `.props.json`:**

| Vocab word | Matched line | Idiom phrase | Matched line(s) → attached to |
|---|---|---|---|
| struggle | 1 | early bird | 0 |
| avoid | 4 | night owl | 0, 1 → **0** (first-match tie-break) |
| routine | 2 | piece of cake | 22, 23 → **22** (first-match tie-break) |
| clever | 17 | wake up on the right side of the bed | 24 |
| skip | 19 | | |

**5/5 vocab, 4/4 idioms** -- no design-finding-level failure (the card's own 0-or-1 escalation
trigger does not apply). Line 0 genuinely exercises the time-slicing math for real (matches
both "early bird" and "night owl" simultaneously) -- confirmed visually in §4 below.

## 3. Real project-selection change found and handled mid-implementation

The very first render picked a **different** real project
(`c08ce057-792a-44db-be5d-2585e6600f4b`, "Demo Episode", 5:00) instead of `b330d37f...` --
investigated rather than accepted silently: a new real B1 project with a completed audio mix
appeared in the real DB during the T6 report-prep window (closer to the runner's 8-minute
target than `b330d37f...`'s 2:56), so `_select_project`'s existing "closest to target" logic
correctly, automatically switched to it. This is not a bug in that logic -- it did exactly
what it was designed to do. It would, however, have made this task's wall-time comparison
against 19.3/19.4's baseline meaningless (a 5-minute episode renders slower than a 2:56 one
for reasons that have nothing to do with this task's own composition cost). **Fixed by
pinning `scripts/run_remotion_spike.py` to the same specific episode every prior Phase 19
task rendered**, with a fallback to the general search if that project is ever gone (e.g. a
fresh checkout). Re-ran after the fix: `b330d37f...` selected again, 5/5 vocab + 4/4 idioms
match confirmed unchanged.

## 4. Verification frames (real data, one coherent run)

Episode: `b330d37f-a212-4cf7-a779-7a109098bd6c` (same as every prior Phase 19 task). Evidence
under `data/tmp/phase19_spike/` (gitignored scratch): the rendered video, this run's
`.props.json`, and the 3 frames below.

| # | Timestamp | Expected card | Frame file | Observed |
|---|---|---|---|---|
| 1 | t=0.5s | idiom "early bird" (line 0, slot 1 of 2: 0.0-1.8s) | `t5_frame1_earlybird.png` | Correct word/definition/example, Alex chip active, caption band unaffected -- match |
| 2 | t=2.5s | idiom "night owl" (line 0, slot 2 of 2: 1.8-3.6s) | `t5_frame2_nightowl.png` | Card correctly switched mid-line via the time-slicing math -- match |
| 3 | t=12.5s | vocab "routine" (line 2) -- **also the combined-features frame** | `t5_frame3_combined.png` | Vocab card (word, part-of-speech, IPA, EN/VI definitions, example) **+** karaoke word "recently" highlighted **+** Alex chip active, all three Phase 19 features rendering correctly in the same frame -- match, proves 19.3/19.4 didn't regress |

All 3/3 correct.

## 5. Re-verification of Task 19.1/19.3/19.4 invariants (D19.5-f)

- `git log fe06405..HEAD -- app/services/video_service.py`: **empty.** Untouched -- this was
  explicitly the last task before 19.7 touches it.
- Python full suite: **1189/1189 passed**, unchanged (no Python files touched beyond the
  runner script, and this task adds no Python tests). `ruff check .`: clean.
- `tests/test_video_studio_browser.py`: **10/10 passed**, unchanged.
- Frame 3 above (§4) is the direct proof 19.3's karaoke and 19.4's speaker chip both still
  render correctly alongside the new vocab card.

## 6. Render measurement

Two full re-renders of the same pinned episode:

| Run | Wall time |
|---|---|
| 1 | 61.621 s |
| 2 | 60.601 s |

Compared to 19.4's ~90-97s baseline: **at or below it**, not just "near-flat" as predicted --
the vocab card overlay (a handful of `<div>`s, same category of cost as the speaker chips) adds
no measurable render-time cost on top of the karaoke + chip composition. (The first,
mis-selected run against the 5-minute "Demo Episode" measured 154.056s -- included here only
to explain why the project pin in §3 was necessary, not as this task's own baseline number.)

## 7. Full checks

- `tsc --noEmit` on `video-renderer/src/`: **clean.**
- `npm run test` (vitest): **21/21 passed** (6 karaoke + 4 speaker + 11 vocab). Revert-and-
  confirm-failure done: reverted `attachItemsToLines` to always return `[]` -- 3/21 tests
  failed with real assertion mismatches (not crashes); restored, 21/21 green again.
- Python full suite: **1189/1189 passed**, unchanged. `ruff check .`: **clean.**
- `tests/test_video_studio_browser.py`: **10/10 passed**, unchanged.
- `git log fe06405..HEAD -- app/services/video_service.py`: **empty.**

## 8. Carry-over conditions (acknowledged, not acted on)

1. **8-min B1 episode:** still does not exist in `data/app.db` -- confirmed again during this
   task's own project-selection investigation (§3): the closest real candidate found was a
   5-minute episode, not 8. This task deliberately rendered the same `b330d37f...` (2:56
   actual) as every prior Phase 19 task, not the newer 5-minute one, for wall-time
   comparability -- not invented, not silently switched.
2. **Chrome ~270 MB hard floor:** still 19.7's problem. No `video-renderer/` packaging change
   in this task.
