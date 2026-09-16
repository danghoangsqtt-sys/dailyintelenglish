# Phase 5 State — UI Polish Backlog

## Metadata
- **Phase:** 5
- **Slug:** 05-ui-polish-backlog
- **Status:** in_progress
- **Started:** 2026-09-16
- **Milestone Progress:** 1 / 3 tasks done. New phase, scoped in the 2026-09-16
  brainstorm session (`docs/brainstorm/session-2026-09-16.md`) after Phase 4 formally
  closed. Addresses the real, still-current P1/P2 findings from the 2026-09-16 Codex
  UI audit — PM re-verified each finding against the current codebase before scoping
  (2 of the original 9 findings turned out to already be fixed as side effects of Task
  4.2d/4.2e's shell redesign work, not carried forward). Progress cancellation and
  real LivePortrait lip-sync remain explicitly deferred, not part of this phase; Task
  4.3 (Vietnamese UI localization) was dropped by explicit user decision, not part of
  this phase either.
- **Test Suite Status:** 566/566 pass (2026-09-17, after Task 5.1) — see TRACKER.md

---

## Tasks Status & Acceptance Evidence

### Task 5.1: Dashboard scale (pagination) — ✅ DONE (2026-09-17)
- **Status:** done
- Client-side pagination for the Dashboard's project grid, no backend change (the
  measured problem is unbounded DOM rendering — 176 real project cards / 358 buttons
  in one `innerHTML` pass, ~17,000px page height — not the data fetch, which already
  returns the full list in one small payload). Fixed page size of 24. The clamp logic
  lives centrally inside `render()` itself (recomputed on every call), so the delete
  handler needed zero changes to satisfy "clamp after delete" — a cleaner design than
  the explicit post-delete clamp the task card anticipated. Filter/search changes
  reset to page 1; pagination controls hidden entirely for a single page; no
  `localStorage`/reload persistence (session-only, by design). Implemented by Codex,
  accepted by PM per AR-06. 4 new browser tests using an isolated
  `_pagination_projects()` fixture — confirmed the pre-existing shared `MOCK_PROJECTS`
  constant and its 6 existing consumers were left completely untouched, per PM's
  explicit plan-review requirement. **Zero real defects found on PM review** — PM
  independently re-ran every verification command and read the full diff. 566/566
  full suite passes (up from 562; 6 known Gemini-retry timing flakes seen on PM's
  independent run, all confirmed passing instantly in isolation — non-regressive,
  Task 5.1 touched zero backend code). See `tasks/task-5.1.md` for the full record.

### Task 5.2: Timeline polish (proportional width + keyboard resizer) — not started
- Timeline clip width made proportional to real clip duration (Script/TTS/Video); the
  shared shell's horizontal timeline resizer gets a keydown handler (currently only
  the vertical resizers do).

### Task 5.3: Small polish batch — not started
- Learning card semantic role/`tabindex`; Learning inspector defaults to the first
  item; Video's avatar section (not-yet-functional LivePortrait feature) collapsed by
  default.
