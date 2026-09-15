# Task 4.2a: UI Redesign Slice 2 — Learning page (`/step3`)

## Meta
- **ID**: 4.2a (first sub-task of Task 4.2 — UI Redesign Slice 2, split per-page per the
  2026-09-15 brainstorm session's explicit pacing decision)
- **Phase**: 4
- **Status**: done (2026-09-15)
- **Priority**: medium
- **Assignee**: PM (Claude Code)

## Doc-First Gate

Researched before writing this plan: `frontend/static/js/shell.js` (the shared
`WorkspaceShell.init()` — resizable sidebar/inspector, no timeline dependency),
`frontend/pages/step2_script.html` + `step2_script.js` (Task 2.4's reference
implementation — the only page currently using the shell), `frontend/static/css/style.css`
(confirmed `.stage-header`/`.stage-title`/`.page-badges`/`.save-status`/`.inspector-*`/
`.generate-panel`/`.spinner`/`#error-banner`/`.empty-state` are already shared, light-theme
tokens; `.tabs`/`.tab-btn`/`.tab-panel`/`.item-card`/`.field`/`.field-row`/`.ipa`/
`.examples-list`/`.options-list`/`.quiz-answer`/`.content-actions` are NOT shared — only
defined in `step3_learning.html`'s own local `<style>` block today), and the current
`step3_learning.html`/`step3_learning.js` (tabs + inline-contenteditable item cards +
coalesced-trailing-autosave — the exact BUG-012 state machine pattern also used by
Script/Thumbnail).

## Objective

Wrap Learning in the same 3-panel shell Task 2.4 built for Script — topbar with real
project name, `pane-sidebar` (StepNav) + `pane-main` (stage) + `pane-inspector` — **with
no timeline** (confirmed decision from the 2026-09-14 UI-redesign session: Learning has
no "sequential items" concept the way Script/TTS/Video's line-by-line audio does).

### Inspector design decision (PM call, disclosed here)

Learning has no per-item backend action to expose the way Script's inspector exposes
real Listen/Regenerate calls — there is no "regenerate one vocabulary word" endpoint,
only whole-pack regenerate (already a stage-level button). Building fake per-item
buttons would violate this project's own precedent ("building UI controls for a backend
path that always fails would be a fake feature" — Task 1.7c's rationale). Instead: the
inspector is a **read-only detail view of the selected item** — click any vocabulary/
idiom/grammar/quiz card to see it enlarged in the inspector. For Quiz specifically, the
inspector **always shows the correct answer + explanation** regardless of the main
list's show/hide toggle — genuinely useful (quick-reference while reviewing), not fake
(surfaces real, already-generated data). This is additive only: the existing inline
`contenteditable` fields in the main stage list keep working exactly as before (same
autosave state machine, same commit-on-blur/Enter/Escape behavior) — selection is a new,
independent read path, never a second write path for the same data.

## File-Level Plan

- **`frontend/pages/step3_learning.html`** — rewrite the `<body>` to the shell structure
  (topbar with `#project-name` in the header bar this time, not as the H1; `shell-flex` >
  `shell-row` > `pane-sidebar` + `#resizer-left` + `pane-main` [`pane-stage` only, no
  timeline/`#resizer-top`] + `#resizer-right` + `pane-inspector`). Move the existing
  generate-panel/tabs/tab-panels/content-actions into `pane-stage`, matching Script's
  `stage-header` (`<h1 class="stage-title">Learning</h1>` + `#project-badges`) pattern.
  Trim the local `<style>` block to only the Learning-specific component styles that
  aren't shared yet (tabs, item-card, field, examples/options/quiz-answer,
  content-actions) plus one new rule, `.item-card.selected` (mirrors the existing
  `.line-card.selected` pattern in `style.css`). Add `<script src="/static/js/shell.js">`
  before `step3_learning.js`.
- **`frontend/static/js/step3_learning.js`** — additive changes only:
  - Add `data-section`/`data-index` to each `*ItemHtml()` function's outer `.item-card`
    div (currently only present on the inner editable `.field` spans).
  - New `state.selectedItem = null` (`{section, index}` when set).
  - New `selectItem(section, index)` + `renderInspector()` (mirrors Script's pattern:
    empty state when nothing selected, else the item's fields in `.inspector-title`/
    `.inspector-meta`/`.inspector-copy`/`.callout`).
  - Click handler on the tab-panel content area: `closest('.item-card')` → `selectItem`
    (added alongside, not replacing, the existing focusout/keydown/click handlers for
    inline editing and the quiz answer-toggle button).
  - Clear `state.selectedItem` on tab switch (`switchTab`) and on a fresh
    generate/regenerate (`handleGenerate`) — a stale selection pointing at a
    now-different tab's index would show wrong data.
  - `WorkspaceShell.init({...})` call in the `DOMContentLoaded` handler (same call shape
    as `step2_script.js`, minus `timeline`/`resizerTop`).
- **New `tests/test_learning_shell_browser.py`** — real Playwright browser tests (first
  browser coverage this page has ever had — today only API/service-level tests exist):
  1. Shell resizes/collapses correctly (sidebar + inspector drag, collapse button) —
     mirrors `test_new_shell_resize_browser.py`'s pattern minus the timeline assertions.
  2. Selecting an item shows its detail in the inspector; switching tabs clears the
     inspector; selecting a quiz item shows the answer in the inspector even when the
     main list's answer is still hidden.
  3. Regression: inline-edit + autosave still fires the real `PUT .../learning` call
     with the expected payload shape, unchanged from before this task.

## Allowed files
- `frontend/pages/step3_learning.html`
- `frontend/static/js/step3_learning.js`
- `tests/test_learning_shell_browser.py` (new)
- `tests/test_step_nav_browser.py` (real, necessary fix found during verification — see
  Implementer Evidence)
- `.viepilot/ROADMAP.md`, `.viepilot/TRACKER.md`, `.viepilot/HANDOFF.json`,
  `.viepilot/phases/04-post-beta-polish/PHASE-STATE.md`, `CHANGELOG.md` (state tracking)
- No backend (`app/`) files touched — this is a pure frontend restructure, zero API
  contract change.

## Verification
- New Playwright suite passes (3 tests).
- Full suite (`pytest tests/ -q`) still green — no regression to the existing
  `test_learning_api.py`/`test_learning_service.py` coverage.
- `ruff check` clean (N/A for `.html`/`.js`, but re-run anyway for the touched Python
  test file); `node --check frontend/static/js/step3_learning.js` clean.
- Manual: a real Playwright screenshot at 1440×900 confirming the light-theme shell
  renders correctly (light background, readable contrast) — same bar Task 2.4 held
  itself to.

## Implementer Evidence (2026-09-15)

- New `tests/test_learning_shell_browser.py`: 3/3 pass — shell resize/collapse + tabs
  still switch correctly; item selection populates the inspector and clears on tab
  switch; quiz inspector always shows the answer independent of the main list's toggle;
  inline-edit + autosave still fires the real `PUT .../learning` call with the edited
  value.
- Real Playwright screenshots (1440×900, both empty and populated states) confirmed:
  light background, readable contrast, selected card highlighted with the accent border,
  inspector renders the selected vocabulary item's full detail cleanly. Deleted after
  review (not committed — same practice as Task 2.4).
- **Real regression found and fixed during full-suite verification** (not
  pre-anticipated in the plan above): `tests/test_step_nav_browser.py`'s
  `test_each_page_renders_and_navigates_shared_step_nav[3]` failed —
  its `if current_step == 2` branch assumed only Script uses the 3-panel shell (StepNav
  lives inside `#pane-sidebar` with the `.step-nav-workflow` variant), so Step 3 fell
  into the `else` branch expecting the old flat `<header>` → `<main class="main">`
  structure. Fixed the test's branching to `if current_step in (2, 3)`. Root cause on
  the implementation side: `step3_learning.js`'s new `StepNav.render()` call was missing
  `variant: "workflow"` (present on `step2_script.js`'s call) — without it, `step_nav.js`
  renders the flat pill list instead of the workflow-with-dots variant the sidebar
  expects. Fixed both (test assertion + missing `variant` option) rather than only the
  test, since the missing `variant` was the real bug and just weakening the test would
  have masked it.
- Full suite re-run after both fixes: `test_step_nav_browser.py` 15/15 pass;
  `test_ui_async_browser.py` + `test_save_indicator_browser.py` +
  `test_responsive_layout_browser.py` (the other files referencing `/step3`) all pass
  unmodified — confirming no other test assumed the old flat structure. Full suite:
  **536/536 pass** (up from 533 — 3 new tests, zero flakes this run).
- `ruff check tests/test_learning_shell_browser.py` clean; `node --check
  frontend/static/js/step3_learning.js` clean.

## PM Acceptance

**Accepted 2026-09-15** — real browser coverage (first this page has ever had),
real screenshots taken and reviewed, one real regression found by running the actual
suite (not assumed away) and fixed at its root cause rather than papered over. Existing
inline-edit/autosave/tabs/generate/regenerate behavior verified unchanged. Closes Task
4.2a.
