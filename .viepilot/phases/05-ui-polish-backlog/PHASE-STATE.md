# Phase 5 State — UI Polish Backlog

## Metadata
- **Phase:** 5
- **Slug:** 05-ui-polish-backlog
- **Status:** in_progress
- **Started:** 2026-09-16
- **Milestone Progress:** 0 / 3 tasks done. New phase, scoped in the 2026-09-16
  brainstorm session (`docs/brainstorm/session-2026-09-16.md`) after Phase 4 formally
  closed. Addresses the real, still-current P1/P2 findings from the 2026-09-16 Codex
  UI audit — PM re-verified each finding against the current codebase before scoping
  (2 of the original 9 findings turned out to already be fixed as side effects of Task
  4.2d/4.2e's shell redesign work, not carried forward). Progress cancellation and
  real LivePortrait lip-sync remain explicitly deferred, not part of this phase; Task
  4.3 (Vietnamese UI localization) was dropped by explicit user decision, not part of
  this phase either.
- **Test Suite Status:** 562/562 pass (2026-09-16, end of Phase 4) — see TRACKER.md

---

## Tasks Status & Acceptance Evidence

### Task 5.1: Dashboard scale (pagination) — 🔄 IN PROGRESS
- **Status:** in_progress (2026-09-16)
- Client-side pagination for the Dashboard's project grid, no backend change (the
  measured problem is unbounded DOM rendering — 176 real project cards / 358 buttons
  in one `innerHTML` pass, ~17,000px page height — not the data fetch, which already
  returns the full list in one small payload). Fixed-size pagination (Prev/Next),
  filter/search resets to page 1, delete clamps back from an emptied last page. Handed
  to Codex as Implementer per AR-06. See `tasks/task-5.1.md` for the full plan.

### Task 5.2: Timeline polish (proportional width + keyboard resizer) — not started
- Timeline clip width made proportional to real clip duration (Script/TTS/Video); the
  shared shell's horizontal timeline resizer gets a keydown handler (currently only
  the vertical resizers do).

### Task 5.3: Small polish batch — not started
- Learning card semantic role/`tabindex`; Learning inspector defaults to the first
  item; Video's avatar section (not-yet-functional LivePortrait feature) collapsed by
  default.
