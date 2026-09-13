# Task 2.3c: UX Polish — Error Toasts (close the one real gap)

## Meta
- **ID**: 2.3c (third independent slice of ROADMAP.md Phase 2 "UX Polish" — covers item 5,
  "Error toasts: user-friendly error messages (not stack traces)")
- **Phase**: 2
- **Status**: done (2026-09-13)
- **Priority**: low
- **Assignee**: PM (Claude, autonomous continuation via `/vp-auto`, "tiếp tục")

## Context (read before planning)

Audited the actual current state before scoping, same discipline as `task-2.3b.md`:

- All 7 step pages already show friendly-only errors via a consistent `#error-banner`
  element (never raw backend text — this has been CR-05 since Task 1.3).
- `frontend/static/js/music_library.js` already has a fully working friendly-error system
  (`setMessage("error", ...)` toggling `#error-message`/`#status-message`) — a naive grep
  for the literal string `error-banner` missed this because it uses different element ids,
  not because the functionality is missing. **Not a gap.**
- `frontend/static/js/dashboard.js` (`/`, the entry point every session starts from) has
  two real, confirmed gaps:
  1. `loadProjects()`'s `catch` block (line ~74) only does `console.error(...)` and
     silently sets `allProjects = []` — a failed load then renders the exact same
     "No projects yet. Create your first AI-powered podcast episode." empty-state copy
     as a genuinely empty account. A real API failure is indistinguishable from "you have
     no projects" from the user's point of view — worse than no message at all, because
     it's actively misleading.
  2. The delete-project handler's `catch` block (line ~120) does
     `alert(\`Failed to delete project: ${err.message}\`)` — a native browser `alert()`
     showing the raw backend error string. This is the one place in the entire app that
     still violates CR-05 ("raw API errors are logged to console, never shown to the
     user" — every other page already gets this right).

So the actual, narrow scope of "Error toasts" is: bring `dashboard.js`/`dashboard.html`
in line with the pattern already proven everywhere else in this app. Nothing else needs
touching.

## Objective

Add the same `#error-banner` pattern already used on all 7 step pages to the Dashboard,
and use it for both of `dashboard.js`'s two real gaps instead of silent failure / `alert()`.

## Paths (`allowed_files` — do not touch anything outside this list)

- `frontend/pages/dashboard.html`
- `frontend/static/js/dashboard.js`
- `tests/test_dashboard_browser.py`
- `.viepilot/phases/02-testing-polish/tasks/task-2.3c.md` (this file)

## Acceptance Criteria

- [x] `dashboard.html` gets a `<div id="error-banner" role="alert" hidden></div>` inside
  `<main>`, placed before `#project-grid` (same position convention as every step page),
  plus the same `#error-banner` CSS block already used on every step page (copy verbatim
  — do not invent a new visual style for the same concept).
- [x] `dashboard.js` gets `showError(message)`/`clearError()` helpers, same shape as every
  step page's own copy of these two functions (this codebase intentionally keeps this
  tiny helper duplicated per page rather than factored into a shared module — matches the
  existing convention, confirmed by reading `step1_config.js`'s copy).
- [x] `loadProjects()`'s catch path calls `showError(...)` with a friendly message, and a
  new `loadFailed` flag suppresses the misleading "No projects yet" empty-state copy when
  the failure is real (a failed load must never look identical to a genuinely empty
  account).
- [x] The delete handler's `catch` block calls `showError(...)` instead of `alert(...)` —
  the raw `err.message` is only ever logged via `console.error`, never shown to the user.
- [x] New/updated Playwright tests: a failed `GET /api/projects` shows the error banner
  and does NOT show the "No projects yet" empty-state copy; a failed
  `DELETE /api/projects/{id}` shows the error banner (not a native `alert()` — assert no
  `dialog` event fires) and leaves the card in place.

## Forbidden Scope

- No changes to `music_library.js` — its existing `#error-message`/`#status-message`
  system already satisfies this ROADMAP item; duplicating `#error-banner` there would be
  a redundant second error-display mechanism on the same page, not an improvement.
- No changes to any step page — already done.
- No new shared "toast" component/library — this app's established pattern is a
  per-page banner, not a floating toast stack; introducing a second UI paradigm for the
  same concept would be inconsistent, not an improvement.
- No changes to any of the other remaining "UX Polish" items (auto-save indicator,
  responsive layout) — separate task cards. "Empty states" was also audited this session
  and found already satisfied everywhere it matters (step1 is a pure form with nothing to
  be "empty," step7's `#generate-panel` already serves as its own empty/call-to-action
  state) — no code change needed for that item either.

## Verification Commands

- `venv\Scripts\python -m pytest tests/test_dashboard_browser.py -q`
- `venv\Scripts\python -m pytest tests/ -q` (must still show 480+ passed, 0 new failures)
- `venv\Scripts\python -m ruff check app/ tests/`
- `node --check frontend/static/js/dashboard.js`
- `git diff --check`

## Result (2026-09-13) — DONE

Delivered exactly the plan above. `dashboard.html`: `#error-banner` markup (before
`#project-grid`) + its CSS block, copied verbatim from `step1_config.html`. `dashboard.js`:
`showError`/`clearError` helpers (same shape as every step page's own copy), a `loadFailed`
flag consulted first in `render()` so a failed load shows neither the project grid nor the
"No projects yet" copy, `loadProjects()`'s catch now calls `showError(...)` (and clears it
on a subsequent successful load), and the delete handler's `catch` now calls `showError(...)`
instead of `alert(err.message)` — the raw message is still logged via `console.error`,
never shown to the user.

2 new Playwright tests: a failed `GET /api/projects` shows the banner with a friendly
message, contains no raw backend text, and shows neither the empty-state nor any project
cards; a failed `DELETE` shows the banner (friendly text, no raw backend text), leaves the
card in place, and — checked explicitly — only the one expected `confirm()` dialog ever
fires (no second native `alert()`).

**One real bug caught in the test itself while writing it, not the product code**: the
delete-failure test's dialog handler was originally `page.on("dialog", lambda dialog:
(dialog_messages.append(dialog.message), dialog.accept()))` — Playwright's Python API
schedules a dialog handler's returned coroutine as a fire-and-forget task only when the
callback returns the coroutine directly; wrapping it in a tuple (to also record the
message) hid it, so `dialog.accept()` was constructed but never awaited/scheduled,
deadlocking the `confirm()` dialog and timing out the test's `click()`. Fixed by using a
small named function that returns `dialog.accept()` as its last statement, keeping the
side-effect (recording the message) and the coroutine return separate.

Took a real Playwright screenshot of the load-failure state to visually confirm the
banner renders correctly and no misleading empty-state text appears.

### Verification output

`venv\Scripts\python -m pytest tests/test_dashboard_browser.py -q` (exit 0):
```
9 passed in 21.32s
```

`venv\Scripts\python -m ruff check app/ tests/` (exit 0): `All checks passed!`

`node --check frontend/static/js/dashboard.js` (exit 0).

`git diff --check` (exit 0): only pre-existing CRLF-on-touch notices, no real errors.
