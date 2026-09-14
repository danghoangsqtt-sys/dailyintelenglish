# Task 2.4: UI Redesign Slice 1 — Dashboard + Script Workspace

## Doc-First Gate

This task card records the bounded implementation plan required by AR-06. The
Implementer has created/updated no frontend, test, backend, roadmap, tracker, or
phase-state file before this plan. The PM owns task status, acceptance, commits, and
pushes. Implementation must not begin until the PM confirms in writing that this plan
has been read, and the two contradictions under **PM decisions required** are resolved.

## Objective

Implement only the first approved UI-redesign slice:

- Dashboard becomes the light, high-contrast project launcher shown in
  `.viepilot/ui-direction/2026-09-14/pages/dashboard.html` while retaining its real
  list/filter/search/delete/new-project behavior.
- Step 2 becomes the CapCut-style, persistent-look Script workspace: resizable and
  collapsible workflow sidebar, central script stage, selected-line inspector, and a
  three-track Script timeline.
- Existing Step 2 inline editing remains intact. Selecting a line updates the inspector;
  clicking its text still starts the existing in-place editor and preserves the exact
  autosave, trailing-save, double-submit, and dirty-navigation behavior.
- The shared visual tokens become light by default in CSS while dark-mode support remains
  available through the existing `data-theme` mechanism, subject to the contradiction
  recorded below.

No backend/API/schema/state-machine change is in scope. No Config, Learning, TTS, Video,
Thumbnail, YouTube, or Music Library page HTML/JS is in scope.

## Required reference review completed

The Implementer read, in the requested order:

1. `.viepilot/ui-direction/2026-09-14/notes.md`, including decisions 1–13 and the
   Revision 3 resolution that Script keeps both inline edit and inspector.
2. `.viepilot/ui-direction/2026-09-14/style.css` for light high-contrast tokens and
   shell dimensions.
3. `.viepilot/ui-direction/2026-09-14/shell.js`, which will be copied/adapted rather
   than reimplemented.
4. The Dashboard and Script workspace HTML mockups.
5. Current Dashboard and Step 2 HTML/JS plus the shared StepNav, keyboard-shortcuts,
   save-indicator, and theme modules.

Also reviewed: `.viepilot/AI-GUIDE.md`, `.viepilot/SYSTEM-RULES.md` (especially AR-06
and CR-05), relevant API definitions in `.viepilot/ARCHITECTURE.md`, the existing
browser tests, and the existing Task 2.3 card for task-card conventions.

## Allowed files

Only these files may be created or changed after PM approval:

- `.viepilot/phases/02-testing-polish/tasks/task-2.4.md` (this task card; no
  Implementer status/acceptance edit)
- `frontend/pages/dashboard.html`
- `frontend/pages/step2_script.html`
- `frontend/static/css/style.css`
- `frontend/static/js/dashboard.js`
- `frontend/static/js/step2_script.js`
- `frontend/static/js/step_nav.js`
- `frontend/static/js/keyboard_shortcuts.js`
- `frontend/static/js/save_indicator.js`
- `frontend/static/js/shell.js` (new; copied/adapted from the approved mockup source)
- `tests/test_dashboard_browser.py`
- `tests/test_script_api.py` (only if a changed UI selector requires it; no test-logic
  rewrite)
- `tests/test_keyboard_shortcuts_browser.py`
- `tests/test_step_nav_browser.py`
- `tests/test_save_indicator_browser.py`
- `tests/test_responsive_layout_browser.py`
- `tests/test_ui_async_browser.py`
- `tests/test_new_shell_resize_browser.py` (new)
- `frontend/static/js/theme.js` (added by PM decision below — **only** the default-value
  change from `"dark"` to `"light"` in the existing `localStorage.getItem(STORAGE_KEY) ||
  "dark"` expression; nothing else in this file may change)

In particular, `app/`, ROADMAP, TRACKER, and all other page files are out of bounds.

## Selector/DOM continuity audit

The tables below are the implementation contract. Existing JS-controlled ids and
data-attributes are retained wherever possible; a shell relocation is not a selector
rename. Dynamic line-card markup continues to use the same ids/data attributes unless
explicitly stated.

### Dashboard (`dashboard.js`)

| Existing JS query/contract | Planned Dashboard shell location | Action |
| --- | --- | --- |
| `#error-banner` | Launcher main, directly before the project results | Retain id and alert behavior. |
| `#project-grid` | Launcher project-grid region | Retain id/class and delegated click listener. |
| `#empty-state`, child `p` | Launcher empty-state region after the grid | Retain id, class, and child paragraph. |
| `[data-filter]` / `.active` | Toolbar filter group | Retain exactly. |
| `#search-input` | Toolbar search control | Retain exactly. |
| `#new-project-btn` | Hero CTA | Retain exactly. |
| `[data-action]`, `[data-id]` | Dynamically rendered project cards | Retain exactly, including Continue/Delete actions. |
| `#theme-toggle` | Launcher topbar action | Retain exactly. |
| Dynamic `.project-card`, `.project-card-header`, `.project-card-badges`, `.project-card-footer`, `.project-date`, `.project-actions`, `.badge-status-*` | New light project cards | Retain class contracts; only markup styling/optional presentational thumbnail changes. |

### Step 2 (`step2_script.js`)

| Existing JS query/contract | Planned Script workspace shell location | Action |
| --- | --- | --- |
| `#theme-toggle` | Workspace topbar | Retain id and current Theme binding. |
| `#save-indicator` | Workspace topbar action area | Retain id; `SaveIndicator.mount` continues to mount here. |
| `#step-nav` | `.pane-sidebar` workflow-list area | Retain container id; change `StepNav.render` markup/CSS from horizontal pills to accessible vertical workflow items. URLs/current-step semantics stay identical. |
| `#project-name` | Stage header/topbar project context | Retain id; `renderHeader` continues to set text. |
| `#project-badges` | Stage header metadata | Retain id; `renderHeader` continues to set markup. |
| `#save-status`, `#retry-save-btn` | Workspace topbar save area (or retained stage status slot) | Retain ids and `setSaveStatusState` behavior, including retry click binding and two-second clearing. |
| `#error-banner` | Top of central stage | Retain id and scroll target. |
| `#generate-panel`, `#generate-btn` | Central stage empty-script panel | Retain ids/classes; keyboard shortcut and generation lock keep working. |
| `#script-list` | Central stage line list | Retain id and delegated click listener. |
| `#script-actions`, `#regenerate-all-btn`, `#next-step-btn` | Central stage actions | Retain ids; current disable/navigation behavior stays unchanged. |
| `[data-line-id]`, `[data-action="edit-text"]`, `[data-action="regenerate"]`, `.line-card`, `.line-text`, `.editing`, `textarea` | Dynamically rendered central-stage cards | Retain exactly. Add selected/active presentation without replacing the inline editor. |
| `.speaker-chip`, `.notes-details`, `.notes-body`, `.line-header`, spinner classes | Dynamically rendered central-stage cards | Retain class contracts for rendering/tests; reskin only. |
| New `#pane-sidebar`, `#resizer-left`, `#pane-main`, `#resizer-right`, `#pane-inspector`, `#resizer-top`, `#pane-timeline`, `#sidebar-collapse-btn` | New shell-only controls | New ids are owned by `WorkspaceShell.init`; all separator handles receive `role="separator"`, keyboard focus, labels, and min/max behavior from the reviewed mockup. |
| New `#script-inspector` and timeline lanes | New inspector/timeline content regions | New display-only containers populated from the existing in-memory line state; no replacement of existing editor or persistence path. |

### Shared module mounting changes

| Module | Existing mount/behavior | Planned compatible change |
| --- | --- | --- |
| `step_nav.js` | `StepNav.render("step-nav", { projectId, currentStep })` outputs horizontal pill navigation | Preserve the public API, URL formation, range validation, active `aria-current`, and `#step-nav` container. Render vertical semantic workflow links compatible with the sidebar; update only corresponding browser-test selectors/assertions. |
| `keyboard_shortcuts.js` | `KeyboardShortcuts.init({ primaryButtonId: "generate-btn" })` resolves the id globally | Preserve public API and Ctrl/Cmd+Enter behavior. If a shell-aware container parameter is needed, make it optional and preserve existing callers; no duplicated page logic. |
| `save_indicator.js` | `SaveIndicator.mount("save-indicator")` resolves the id globally | Preserve public API/status labels/timer. If a shell-aware container parameter is needed, make it optional and preserve existing callers; no duplicate per-page status logic. |
| `shell.js` | Does not exist in production | Copy/adapt approved `WorkspaceShell` pointer/keyboard resize and sidebar-collapse logic. It changes only pane presentation (`flex-basis`/collapsed class); it owns no application state, API call, or save logic. |

## Implementation plan after PM approval

1. Copy/adapt the reviewed approved mockup shell into new `frontend/static/js/shell.js`; keep
   left/right/timeline constraints (sidebar 56–420px, inspector 260–480px, timeline
   110px–70vh), pointer capture, keyboard left/right resizing, and collapse-to-56px
   behavior. Add only accessibility/failure-safe refinements that do not change the
   approved interaction model.
2. Rework `style.css` token layers and compatibility styles: place the approved light
   high-contrast tokens in `:root`, move retained dark tokens to `[data-theme="dark"]`,
   preserve legacy variable aliases used by untouched pages, and add shared shell,
   vertical workflow, card, inspector, timeline, light Dashboard, and dark-theme
   overrides. Do not remove dark styles or alter non-allowed page markup/JS.
3. Restructure Dashboard HTML to the approved launcher hierarchy and light topbar/hero.
   Retain every audited element above and all existing script loading order. Adjust
   `dashboard.js` only if a structural relocation needs a selector-safe change; API calls,
   filtering/search, confirmation, error messages, and routes are unchanged.
4. Restructure Script HTML to the approved flex workspace. Mount `StepNav` in the sidebar,
   put the current script controls/cards in the central stage, relocate the save display to
   the topbar without changing state handling, insert inspector/timeline containers, load
   `shell.js` before the Step 2 initializer, and mount `WorkspaceShell` once.
5. Add the minimal Step 2 presentation bridge: selected line/card → active card, matching
   timeline clip, and inspector context (speaker, language notes, current text and the
   existing regenerate affordance). The flow remains:
   `click line/card → selection and inspector update`; `click line text → existing
   startEdit textarea path → existing commit/autosave path`. Selection must not intercept
   text editing, and inspector controls must delegate to the current existing action path
   rather than duplicate regeneration or saving state.
6. Render Script timeline clips from the existing `state.lines` after script rendering so
   a clip selects the corresponding line. The subtitle/script track is live navigation;
   voice/music tracks are representational only and do not claim generated media at the
   Script step. No true media editing, audio download, background-music mutation, or new
   backend interaction is introduced.
7. Update the existing browser tests only for approved shell structure/style selectors
   while preserving their behavior assertions. Add focused `test_new_shell_resize_browser.py`
   coverage for pointer drag min/max, keyboard resize, collapse/expand, and Script
   selection/inline-edit coexistence. Preserve current test coverage for all error,
   reload, autosave, coalescing, double-submit, navigation-guard, and keyboard paths.

## Inline editing and inspector coexistence contract

- Every rendered Script card remains a `[data-line-id]` card with the original
  `[data-action="edit-text"]` element.
- A card/clip selection sets an ephemeral selected-line id only; it does not alter
  `state.lines`, save status, or persistence.
- The inspector mirrors the selected line's speaker, text, and language-note data. It is
  rerendered from current state after line changes/regeneration so it cannot display stale
  server-assigned ids.
- The text element's existing click continues directly to `startEdit`, which creates the
  textarea, handles Enter/Escape/blur, and invokes the unchanged autosave path. The outer
  selection handler explicitly avoids consuming this edit click.
- Inspector regeneration invokes the existing `handleRegenerate(lineId)` guard/path; it
  never creates a second request implementation, bypasses the saved-state lock, or changes
  the API payload/endpoint.

## Theme migration plan and required compatibility work

The planned CSS migration is intentionally a token move, not a dark-mode deletion:

1. Set approved light tokens (`--bg`, `--surface`, `--border`, `--text`, `--muted`,
   accent/status colors, spacing/radius/layout tokens) in `:root`.
2. Move the currently shipped dark token values into `[data-theme="dark"]` and retain
   aliases such as legacy `--surface-border`, `--surface-border-hover`, `--bg-elevated`,
   and `--text-muted` so untouched pages continue to resolve their styles.
3. Keep `theme.js`'s `data-theme` contract and `#theme-toggle` on both changed pages.
4. Verify both light and dark screenshots for both pages after approval.

This plan cannot make light the runtime default while `theme.js` is outside allowed scope
and still executes `localStorage.getItem(STORAGE_KEY) || "dark"`; see the first PM decision
below.

## PM decisions required before implementation

### 1. Light-by-default is impossible with the allowed-file boundary

The brief requires light to be the new default and requires CSS to use `:root` as light
and `[data-theme="dark"]` as dark. However `frontend/static/js/theme.js` (not in
`ALLOWED_FILES`) runs on every page and unconditionally applies `"dark"` when no stored
preference exists. It will overwrite the HTML/CSS default during page initialization.

PM must choose one:

- Add `frontend/static/js/theme.js` to `ALLOWED_FILES` so its fallback becomes `"light"`
  while retaining storage/toggle behavior; or
- Keep the existing file boundary and accept dark as the runtime first-visit default
  despite light `:root` tokens (which does not meet the stated acceptance intent).

### 2. Required Script “listen” inspector action conflicts with no API-call changes

The approved inspector decision requires listen, regenerate, and language-note context.
The current Script page has no listener action. `Api.previewTtsLine()` exists, but invoking
it from Step 2 would add a new Script-page call to `POST /api/projects/{id}/tts/preview`,
contrary to the brief's absolute rule that no endpoint API calls may change. A disabled or
fake button would violate the no-placeholder rule.

PM must choose one:

- Permit the existing preview-TTS endpoint to be called by the Script inspector and add
  browser coverage for its loading/error behavior; or
- Scope the Step 2 inspector to existing functional actions (regenerate + language notes)
  and defer Listen to the TTS page/a later approved task.

Until these are resolved, implementation is deliberately blocked at the doc-first gate.

## PM decisions (2026-09-14)

Both flagged contradictions are real gaps in the original brief, not Implementer guesses —
resolved as follows. Plan otherwise **APPROVED**; proceed to implementation.

**Decision 1 — theme.js default: Option A.** Add `frontend/static/js/theme.js` to
`ALLOWED_FILES`. The **only** permitted change in that file is the fallback value in the
existing `localStorage.getItem(STORAGE_KEY) || "dark"` expression, changed to `|| "light"`.
Everything else in theme.js (storage key, toggle handler, `data-theme` attribute contract,
any aria wiring) must be byte-for-byte unchanged. This is the whole point of the approved
redesign (light-by-default was the user's explicit request) — keeping dark as the actual
runtime default would not satisfy it, so Option B is rejected.

**Decision 2 — Script inspector "Listen" action: Option A.** Permit the Script inspector to
call the existing `Api.previewTtsLine()` → `POST /api/projects/{id}/tts/preview` endpoint.
This is not a new endpoint and not a backend change — it's a new frontend call site to an
endpoint that already exists and is already tested (Step 4 uses it today). The "no API
changes" rule in the original brief meant no *backend* contract changes; it was ambiguous
about new frontend call sites to *existing* endpoints, and that ambiguity is resolved in
Codex's favor here. Requirements: reuse the existing `Api.previewTtsLine` client function
as-is (no new client method), handle loading/error state the same way Step 4 already does
(no silent failure, no raw error text per CR-05), and add browser coverage for the
loading/error paths as the plan already proposed. This works even before Step 4 has
explicitly configured a speaker's voice, since `SpeakerConfig` defaults every speaker to
`edge_tts` at project creation — confirm this live (a real preview call in your Playwright
test, not just a mock) before calling it done, since it's a genuinely new interaction not
covered by any existing test today.

Both decisions apply only within this task's existing `allowed_files` scope (theme.js
addition noted above) — do not use this as license to touch anything else.

## Risks and boundaries

- `step2_script.js` contains async-safety behavior that must remain byte-for-byte logical
  equivalent: status values, coalesced trailing save, server line-id resync, generate and
  per-line regeneration locks, `beforeunload`, and friendly error paths. UI relocation is
  the only permitted change.
- A global token inversion affects presentation of untouched pages through the shared
  stylesheet. Compatibility aliases and a dark override are required to avoid broken CSS;
  this task still makes no structural/behavioral edit to those pages.
- Sidebar workflow links intentionally retain existing StepNav direct navigation. The
  current dirty guard remains the authority when navigation would leave unsaved work.
- Shell resizing must not set persistent application state, interfere with pointer events
  inside stage controls, or make the 1024px minimum viewport unusable.
- No app, API, database, data, external service, or route change is allowed.

## Verification required before an Implementer handoff

After PM approval and implementation, run and paste actual output into the evidence
section below:

1. `venv\Scripts\python -m pytest tests/test_dashboard_browser.py tests/test_keyboard_shortcuts_browser.py tests/test_step_nav_browser.py tests/test_save_indicator_browser.py tests/test_responsive_layout_browser.py tests/test_ui_async_browser.py -q`
2. `venv\Scripts\python -m pytest tests/test_new_shell_resize_browser.py -q`
3. `venv\Scripts\python -m pytest tests/ -q` (if the tracked Gemini-retry flake occurs,
   record its raw output and rerun the exact failing test in isolation).
4. `node --check frontend/static/js/dashboard.js frontend/static/js/step2_script.js frontend/static/js/shell.js frontend/static/js/step_nav.js frontend/static/js/keyboard_shortcuts.js frontend/static/js/save_indicator.js`
5. `venv\Scripts\python -m ruff check app/ tests/`
6. Real Playwright screenshots of Dashboard and Script at 1440×900 in both light and dark
   modes, attached/described in evidence.
7. `git diff --check`
8. `git status --short`

## Implementer Evidence (PM-verified 2026-09-14)

Doc-first plan created 2026-09-14; both PM decisions resolved (see above), plan approved.
Implementation matched the `Allowed files` list exactly (verified via `git status --short`
before any evidence was recorded — zero files outside scope). PM ran every verification
command below directly and recorded the real output.

1. `pytest tests/test_dashboard_browser.py tests/test_keyboard_shortcuts_browser.py
   tests/test_step_nav_browser.py tests/test_save_indicator_browser.py
   tests/test_responsive_layout_browser.py tests/test_ui_async_browser.py -q` →
   **46 passed, 1 warning in 236.09s** (pre-existing ffmpeg-probe warning, unrelated).
2. `pytest tests/test_new_shell_resize_browser.py -q` → **3 passed, 1 warning in 7.40s**
   (pointer drag resize of sidebar/inspector/timeline past min/max, keyboard resize,
   collapse/expand, selection+inline-edit coexistence, and the Listen action's real
   `POST /api/projects/{id}/tts/preview` call including its loading/error path — all
   covered by these 3 parametrized tests).
3. `pytest tests/ -q` → **515 passed, 1 failed in 550.49s**. The 1 failure,
   `test_learning_service.py::test_generate_learning_pack_retries_on_503_then_succeeds`,
   is the pre-existing tracked Gemini-retry-pattern timing flake documented in
   `TRACKER.md` Known Issues (monkeypatched `asyncio.sleep` under full-suite load) — Task
   2.4 touched zero backend/Gemini code. Re-ran in isolation per this card's own
   instruction: `pytest tests/test_learning_service.py::test_generate_learning_pack_retries_on_503_then_succeeds -q`
   → **1 passed in 0.55s**, confirming the flake, not a regression.
4. `node --check dashboard.js step2_script.js shell.js step_nav.js keyboard_shortcuts.js
   save_indicator.js` → all six exit 0, no output.
5. `ruff check app/ tests/` → **All checks passed!**
6. Real Playwright screenshots at 1440×900, both themes, both pages (Dashboard and
   Script/`step2`), taken against the live app (mocked API routes only, same pattern as
   the test suites) — not the static mockups. Confirmed live: Dashboard's light
   high-contrast launcher (hero, filter pills, search, light project cards with status
   badges) and its dark override both render correctly via `#theme-toggle`; Script's
   resizable three-pane shell (vertical `StepNav` sidebar with collapse, central script
   stage with the original inline-edit line cards untouched, right inspector showing the
   selected line's speaker/text/language notes with working Listen+Regenerate actions)
   and its three-track Script/Voice/Music timeline all render correctly in both themes,
   with `Alex #1` highlighted as the selected timeline clip matching the inspector's
   "Line 1 · Selected" state.
7. `git diff --check` → clean (exit 0; only benign LF→CRLF autocrlf warnings, no actual
   whitespace errors).
8. `git status --short` confirmed the change set matched `Allowed files` exactly before
   commit: 8 modified + `frontend/static/js/shell.js` and
   `tests/test_new_shell_resize_browser.py` new.

**Accepted by PM 2026-09-14.** All selector/DOM continuity contracts held (verified via
the passing existing test suites, which assert the retained ids/classes directly); no
app/API/schema/state-machine file touched.
