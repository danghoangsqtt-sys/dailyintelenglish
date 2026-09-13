# Phase 2 State — Testing & Polish

## Metadata
- **Phase:** 2
- **Slug:** 02-testing-polish
- **Status:** in_progress
- **Started:** 2026-09-13
- **Target Completion:** 2026-09-20 (per ROADMAP.md's Day 8-14 target, adjusted forward
  since Phase 1 finished on Day 3 instead of Day 7)
- **Milestone Progress:** 0 / 3 major tasks fully done (2.1 Quality Testing, 2.2 Bug Fixes
  & Performance not started; 2.3 UX Polish has 2 of 7 items done)
- **Test Suite Status:** 480 passed, ruff clean, all `node --check` clean

---

## Tasks Status & Acceptance Evidence

### Task 2.1: Quality Testing
- **Status:** ⏳ Planned — no task card yet

### Task 2.2: Bug Fixes & Performance
- **Status:** ⏳ Planned — no task card yet

### Task 2.3: UX Polish
- **Status:** 🔄 In Progress (2 of 7 ROADMAP items done)
- **Details:** ROADMAP.md's "UX Polish" bullet has 7 items; `task-2.3.md` covers the
  first 2 (step progress indicator, breadcrumb navigation), `task-2.3b.md` covers item 3
  (keyboard shortcuts). The other 4 (auto-save indicator, empty states, error toasts,
  responsive layout) are not yet assigned to a task card.
  - **Step progress indicator + breadcrumb navigation — DONE (2026-09-13, by Codex,
    PM-accepted):** new `frontend/static/js/step_nav.js` — `StepNav.render(containerId,
    { projectId, currentStep })`, a pure synchronous DOM component (no network/async
    state) rendering "Step X of 7" plus 7 clickable pills, mounted identically on all 7
    step pages (`<div id="step-nav"></div>` right after `</header>`, one integration line
    per page's own `DOMContentLoaded` handler, each page parsing its own
    `location.search` independently). Missing `project_id` degrades to clean bare URLs,
    never `null`/`undefined`. No existing business logic, state machine, or
    `beforeunload` guard touched — confirmed via a full line-by-line diff review, not
    just the test suite. 15 new Playwright tests (parametrized across all 7 pages), 452
    total tests pass. Codex's session ended mid-verification on a usage limit (after
    finishing implementation, its own targeted test run, and lint/syntax checks, but
    before writing up evidence) — PM independently re-verified every command from
    scratch and took its own screenshot before accepting; see `tasks/task-2.3.md` for
    the full record.
  - **Keyboard shortcuts — DONE (2026-09-13, Task 2.3b, PM as Implementer via `/vp-auto`
    continuation):** new `frontend/static/js/keyboard_shortcuts.js` —
    `KeyboardShortcuts.init({ primaryButtonId })`, mounted on all 7 step pages, triggers
    the page's real primary button (`submit-btn` on `/step1`, `generate-btn` elsewhere) on
    `Ctrl+Enter`/`Cmd+Enter` — only when it's genuinely visible and not disabled, so it
    never fires "Generate" when an existing script/package hides that button. `Esc` to
    cancel needed no new code (native `confirm()` dialogs + `/step2`/`/step3`'s existing
    inline-edit revert handlers already cover it). Caught and fixed a real bug in the
    module itself before shipping (top-level `const` doesn't attach to `window` in a
    classic script — fixed to match `StepNav`'s explicit `window.X = ...` pattern) plus
    two test-fixture mistakes while writing the Playwright suite (a wrong 404-vs-null
    contract for `GET .../youtube`, and a missing `/tts/preview` mock that silently hit
    the real backend). 6 new Playwright tests, 480 total pass. See `tasks/task-2.3b.md`
    for the full record.
