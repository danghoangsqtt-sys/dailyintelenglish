# Phase 4 State — Post-v1.0.0-beta Polish

## Metadata
- **Phase:** 4
- **Slug:** 04-post-beta-polish
- **Status:** in_progress
- **Started:** 2026-09-15
- **Milestone Progress:** 1 / 2 tasks done — 4.1 CEFR `news` prompt tuning done
  2026-09-15 (partial, honestly-reported improvement — see `tasks/task-4.1.md`); 4.2 UI
  Redesign Slice 2 (7 pages) in progress, 2/7 pages done (Learning, TTS). New phase,
  scoped in the 2026-09-15 brainstorm session (`docs/brainstorm/session-2026-09-15.md`),
  not part of the original 21-day/3-phase plan. Progress cancellation and real
  LivePortrait lip-sync remain explicitly deferred, not part of this phase. A new
  Task 4.3 (Vietnamese UI localization) is scoped and queued to start once Task 4.2's
  remaining 5 pages are done — see `docs/brainstorm/session-2026-09-15.md`'s
  2026-09-15 update.
- **Test Suite Status:** 541/541 pass (2026-09-16, after Task 4.2b) — see TRACKER.md

---

## Tasks Status & Acceptance Evidence

### Task 4.1: CEFR `news`-genre prompt tuning — ✅ DONE (2026-09-15), partial improvement
- **Status:** done
- Added register-vs-complexity guidance to `prompts/script/news.txt`. Re-tested A2/B1/B2
  × `news` (3 real Gemini calls) against Task 2.1b's exact rubric: one specific failure
  pattern (A2's indefinite-pronoun+modal) didn't recur, but Future Simple usage persists
  at A2, the exact flagged idiom ("a breath of fresh air") recurred verbatim at B1, and
  B2's grammar still borders C1 (Past Perfect Continuous) though idiom choice improved.
  Honestly reported as partial/mixed, not a full fix — consistent with tuning a
  probabilistic model. See `tasks/task-4.1.md` for the full evidence.

### Task 4.2: UI Redesign Slice 2 (7 remaining pages)
- **Status:** in_progress (2/7 pages done)
- Split into per-page sub-tasks, written doc-first individually as each is picked up.
- **4.2a — Learning (`/step3`)**: ✅ DONE (2026-09-15). Wrapped in the same 3-panel
  shell as Script (Task 2.4), no timeline (confirmed decision — Learning has no
  sequential-items concept). New read-only item inspector (click a vocabulary/idiom/
  grammar/quiz card to see its full detail; quiz inspector always shows the answer,
  independent of the main list's toggle) — no fake per-item actions invented, since no
  backend supports regenerating a single item. Existing inline-edit/autosave/tabs
  behavior unchanged. First browser test coverage this page has ever had (3 new tests).
  Found and fixed a real regression during verification: `test_step_nav_browser.py`
  assumed only Script used the shell layout, and `step3_learning.js`'s `StepNav.render()`
  call was missing `variant: "workflow"` — both fixed at the root cause. 536/536 full
  suite passes (up from 533). See `tasks/task-4.2a.md` for the full record.
- **4.2b — TTS Audio Studio (`/step4`)**: ✅ DONE (2026-09-16), implemented by Codex,
  accepted by PM (Claude Code) per AR-06 — first task delegated to Codex since its quota
  was restored. Shell + 3-track timeline (Script/Voice/Music); read-only inspector shows
  the selected line, an honest session-only preview-state badge (Not previewed/
  Synthesizing/Preview ready — never guesses persisted cache state), a real Listen
  action reusing the existing preview endpoint, and a real scroll-to-speaker-card "Voice
  settings" affordance (no new write path). Existing per-speaker autosave debounce and
  the sequential Generate-All request order are unchanged. 5 new browser tests.
  **2 real review rounds**: (1) Codex correctly flagged and PM pre-authorized a narrow
  fix to `test_step_nav_browser.py` (same `variant:"workflow"` class of issue as 4.2a,
  now covering `current_step == 4` too) before writing any other code; (2) PM's
  independent screenshot review (not the test suite) caught a real bug — `renderTimeline()`
  cleared the Script/Voice lanes on every re-render but never the Music lane, so it
  accumulated duplicate clips — sent back to Codex with the exact fix, which PM then
  re-verified independently (including a 5-interaction stress-test screenshot) before
  accepting. 541/541 full suite passes. See `tasks/task-4.2b.md` for the full record.
- **4.2c — Video Studio (`/step5`)**: in_progress, assigned to Codex (Implementer),
  PM (Claude Code) writes/accepts per AR-06. Doc-first task card written 2026-09-16 —
  see `tasks/task-4.2c.md`. Not yet implemented; awaiting Codex.
- Remaining after 4.2c: Thumbnail, YouTube, Music Library, Step1-Config — not started.
