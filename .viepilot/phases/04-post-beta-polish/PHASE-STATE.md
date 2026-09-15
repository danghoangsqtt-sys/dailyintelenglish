# Phase 4 State — Post-v1.0.0-beta Polish

## Metadata
- **Phase:** 4
- **Slug:** 04-post-beta-polish
- **Status:** in_progress
- **Started:** 2026-09-15
- **Milestone Progress:** 1 / 2 tasks done — 4.1 CEFR `news` prompt tuning done
  2026-09-15 (partial, honestly-reported improvement — see `tasks/task-4.1.md`); 4.2 UI
  Redesign Slice 2 (7 pages) not started. New phase, scoped in the 2026-09-15 brainstorm
  session (`docs/brainstorm/session-2026-09-15.md`), not part of the original
  21-day/3-phase plan. Progress cancellation and real LivePortrait lip-sync remain
  explicitly deferred, not part of this phase.
- **Test Suite Status:** carried over from Phase 3 close-out (533/533) — see TRACKER.md

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
- **Status:** in_progress (1/7 pages done)
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
- Remaining: TTS, Video, Thumbnail, YouTube, Music Library, Step1-Config — not started.
