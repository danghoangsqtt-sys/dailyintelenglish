# Phase 19 Task 19.4 — Active-speaker indicator (name chip + optional avatar)

- **Task:** 19.4 (Coder). Design record: `.viepilot/phases/19-remotion/tasks/task-19.4.md`
  (D19.4-a..f, PM-approved 2026-09-28).
- **Run date:** 2026-09-28. **Code HEAD at task start:** Task 19.3 accepted (`c48037d`, PM
  task-level).
- **Scope:** composition change only. `app/services/video_service.py` untouched (confirmed
  below, §5). No `VideoService` wire-up (that's Task 19.7).

## 1. Real findings (checked before writing code)

- **Real palette, not guessed:** `frontend/static/css/style.css` defines
  `--speaker-a`/`--speaker-b` custom properties, already used app-wide via an identical
  `speakerIndex % 2 === 0 ? "speaker-a" : ""` pattern repeated in `step2_script.js:267`,
  `step4_tts.js:293`, and `step5_video.js:124`. Two theme variants exist: light
  (`#9a4a00`/`#0757a8`) and dark (`#F59E0B`/`#58A6FF`). **Chosen: the dark-theme pair** --
  the composition's background is the fixed near-black `#0E0F15`, and the light-theme values
  were contrast-calibrated for a white surface (would read muddy here).
- **Real missing-avatar precedent:** `frontend/static/js/step5_video.js:239-242` (Task
  1.7c's own avatar upload UI) shows the app's actual placeholder for a missing avatar is a
  plain text box reading **"No image"** -- no initials-in-a-circle pattern exists anywhere in
  this codebase. The chip's absent-avatar design follows this real, simpler precedent:
  name-only, no substitute shape.
- **Card correction:** `frontend/static/css/step4_tts.css` (cited in the card) does not
  exist -- Step 4's styles are inline in `frontend/pages/step4_tts.html`; the real palette
  lives in `style.css`.

## 2. Demo episode's avatar status

Both of `b330d37f...`'s speakers (Alex, male; Maya, female) have `avatar_image_path = NULL`
(confirmed by the PM's read-only preflight, unchanged). **This task's real render exercises
only the name-only chip path.** The avatar path (circular image + name layout, and the
`_copy_avatar_into_public` copy-not-symlink logic) is exercised exclusively by
`scripts/run_remotion_spike.py`'s own code path (never invoked this run, since both
`avatar_image_path` values are NULL) and is otherwise **not covered by an automated test** --
`speakers.test.ts` covers `activeSpeakerId` only (the avatar rendering itself lives in
`Episode.tsx`'s `SpeakerChip` JSX, which has no vitest coverage in this task, same as
`CaptionBand`'s JSX in 19.3). This is disclosed plainly rather than implied covered: if a
future project uploads a real avatar, the first real signal that the copy-and-render path
works will be that project's own render, not a pre-existing test.

## 3. Chip design (as implemented)

- **Position:** top-left (`top: 5%, left: 5%`), horizontal flex row, `flexWrap: "wrap"`.
  Opposite the bottom-anchored `<CaptionBand>` -- no collision risk even when a caption wraps
  to two lines (confirmed visually, see §6).
- **Active state:** solid color fill (`#F59E0B` or `#58A6FF`, alternating by speaker index)
  + `transform: scale(1.08)`; text switches to `#0E0F15` (matching the background) for
  contrast against the now-bright chip.
- **Inactive state:** persistent (never fades out), `rgba(255,255,255,0.08)` background,
  white text at **0.6 opacity** (within the PM-recommended 0.5-0.65 range) -- legible enough
  to still read the name, dim enough the active chip clearly wins the eye.
- **Avatar (when present):** 56px circular image (`object-fit: cover`) to the left of the
  name.
- **Multi-speaker scaling:** `flexWrap: "wrap"` -- untested beyond the demo's 2 speakers in
  this task, but requires no different code path at 5-6 speakers (wraps to a second row
  instead of overflowing).

## 4. `activeSpeakerId` semantics (D19.4-d)

`src/speakers.ts`: `startSec` inclusive, `endSec` exclusive (identical tie rule to 19.3's
`activeTokenIndex`); `null` in gaps (before line 0, between lines, after the last line).
6/6 real vitest cases pass, including the exact-boundary case
(`activeSpeakerId(3.6, LINES)` → `null`, `activeSpeakerId(4.1, LINES)` → the next line's
speaker). Revert-and-confirm-failure: reverted the function to always return `null` -- 2/10
vitest tests failed with real assertion mismatches (`expected "alex", received null`), not
crashes; restored, 10/10 green again.

## 5. Re-verification of Task 19.1/19.3 invariants (D19.4-f)

- `git log fe06405..HEAD -- app/services/video_service.py`: **empty.** Untouched.
- Python full suite: **1178/1178 passed**, unchanged (no Python files touched). `ruff check
  .`: clean.
- `tests/test_video_studio_browser.py`: **10/10 passed**, unchanged.
- 19.3's karaoke band still renders correctly alongside the new chip -- confirmed directly:
  spot-check frame 1 (§6) shows both the karaoke-highlighted word "or" **and** the active
  Alex chip in the same frame, proving `<SpeakerChips>` is a true sibling addition, not a
  regression of `<CaptionBand>`.

## 6. Verification frames (real data, one coherent run)

Episode: `b330d37f-a212-4cf7-a779-7a109098bd6c` (same as 19.1-19.3). Evidence under
`data/tmp/phase19_spike/` (gitignored scratch): the rendered video, this run's
`.props.json`, and the 3 frames below.

| # | Timestamp | Expected active speaker | Frame file | Observed |
|---|---|---|---|---|
| 1 | t=2.0s | Alex (line 0, "...are you an early bird **or** a night owl") | `t4_frame1_alex.png` | Alex chip amber/filled/scaled, Maya chip dim -- match. **Also proves 19.3's karaoke ("or" highlighted) still renders alongside the chip in the same frame.** |
| 2 | t=6.5s | Maya (mid-line 1, proving the chip *stays* highlighted through a whole line, not just at its boundary) | `t4_frame2_maya.png` | Maya chip blue/filled/scaled, Alex chip dim -- match |
| 3 | t=12.0s | Alex (line 2, after the Maya→Alex transition at t=10.312s completes) | `t4_frame3_alex_combined.png` | Alex chip amber/filled/scaled, Maya chip dim -- match |

All 3/3 correct. The Alex↔Maya alternation (frames 1→2→3) demonstrates both transition
directions plus persistence through a line's full duration.

## 7. Render measurement -- an investigated anomaly, not a shrug

Two full end-to-end pipeline runs (spike runner, including 30 real Edge TTS re-synthesis
calls before the timed render step) initially measured **141.8s** and **131.0s** -- both
~40-50% above 19.3's ~95-97s baseline, well outside the card's ±10% expectation. **Investigated
rather than reported as-is:** ran a controlled A/B comparison isolating just the render step,
same real `.props.json` from an actual run, back-to-back on the same machine:

| Composition | Render-only wall time |
|---|---|
| Pre-19.4 (`c48037d`'s `Episode.tsx`, no chips) | 97.37 s |
| Post-19.4 (with `<SpeakerChips>`) | 105.08 s (**+7.9%**) |

The controlled delta (+7.9%) is squarely inside the ±10% expectation and matches the design
doc's prediction that chip rendering (a handful of `<div>`s) adds negligible per-frame cost.
A third full pipeline run afterward measured **90.5s** -- at or below the 19.3 baseline. The
two elevated full-pipeline readings (131-142s) are attributed to transient system load on
this shared, multi-session development machine (the same machine has run several concurrent
Claude Code sessions throughout Phase 19), not to this task's code -- the isolated, same-props
A/B test is the reliable signal, and it confirms the design doc's prediction held.

## 8. Visual quality signal

Stepping through the three spot-check frames and the frames immediately surrounding each
speaker transition: the chip switch (color fill + scale) lands cleanly on the same frame the
new speaker's line begins, no visible flicker, no intermediate half-state. Reads as crisp,
not laggy.

## 9. Full checks

- `tsc --noEmit` on `video-renderer/src/`: **clean.**
- `npm run test` (vitest): **10/10 passed** (6 karaoke + 4 speaker).
- Python full suite: **1178/1178 passed**, unchanged. `ruff check .`: **clean.**
- `tests/test_video_studio_browser.py`: **10/10 passed**, unchanged.
- `git log fe06405..HEAD -- app/services/video_service.py`: **empty.**

## 10. Carry-over conditions (acknowledged, not acted on)

1. **8-min B1 episode:** still does not exist in `data/app.db`. This task rendered the same
   `b330d37f...` (2:56 actual) as every prior Phase 19 task -- not invented.
2. **Chrome ~270 MB hard floor:** still 19.7's problem. No `video-renderer/` packaging change
   in this task.
