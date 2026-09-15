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
- **Status:** not_started
- Split into per-page sub-tasks, written doc-first individually as each is picked up.
