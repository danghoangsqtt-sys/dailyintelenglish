# Phase 2 State — Testing & Polish

## Metadata
- **Phase:** 2
- **Slug:** 02-testing-polish
- **Status:** in_progress
- **Started:** 2026-09-13
- **Target Completion:** 2026-09-20 (per ROADMAP.md's Day 8-14 target, adjusted forward
  since Phase 1 finished on Day 3 instead of Day 7)
- **Milestone Progress:** 3 / 4 major tasks fully done (2.1 Quality Testing — ✅ DONE,
  all 4 ROADMAP items closed at the automated-proxy-review level the user approved, 3
  real findings logged for follow-up; 2.3 UX Polish — ✅ DONE, all 7 ROADMAP items
  resolved; 2.4 UI Redesign Slice 1 — ✅ DONE; 2.2 Bug Fixes & Performance has its
  buildable scope done — 1 item fixed, 1 already-done-closed-via-audit, 1 moot, 1
  genuinely deferred as a future task). Task 2.4 was added as new scope after the
  original ROADMAP.md Phase 2 bullets were written (see
  `.viepilot/ui-direction/2026-09-14/notes.md`), so the 3-task ROADMAP count predates it.
- **Test Suite Status:** 515 passed, 1 pre-existing tracked flake (confirmed via isolated
  re-run, not a regression), ruff clean, all `node --check` clean

---

## Tasks Status & Acceptance Evidence

### Task 2.1: Quality Testing
- **Status:** ✅ Done (2026-09-14). Split into sub-tasks like 2.3 was — all 4 ROADMAP
  items closed at the automated-proxy-review level the user approved at two `/vp-auto`
  control points.
  - [x] **Task 2.1a + 2.1b — CEFR accuracy testing: DONE.** Task 2.1a
    (`scripts/generate_cefr_review_samples.py`) is code-complete and PM-accepted, and its
    real 18-call run now lands 18/18 (prior partial runs hit real network/quota
    conditions, not a code defect). Task 2.1b: PM read all 18 generated scripts in full
    (user-approved at a `/vp-auto` control point: PM does an automated-proxy review
    first, flags anything needing human judgment) — verdict **14 PASS, 4 BORDERLINE
    (A2/B1/B2 × news, a genre-specific idiom-density drift, not a defect), 0 FLAG**.
    Nothing required the user's own read. See `tasks/task-2.1a.md` and
    `tasks/task-2.1b.md`.
  - [x] **Task 2.1c — Multi-accent TTS, Audio quality, Video testing: DONE.** Real
    technical measurement (LUFS, silence gaps, subtitle-timestamp sync) against the
    actual production service functions, per a second user decision (PM cannot
    literally "listen" to audio; proxy method is real numbers). 20/20 real Edge TTS
    syntheses across all 10 accents × 2 genders; no-music mixes measured -16.01 LUFS
    (0.01dB off target); real video render confirmed exact subtitle sync. **3 real
    findings surfaced, none fixed in this read-only pass** (see TRACKER.md Known
    Issues): `scottish` duplicates `british`'s voice ids (upstream Edge TTS limitation);
    background-music mixes drift to -17.12 LUFS (outside the ±1dB tolerance, root cause
    identified); no 9:16 video output exists anywhere (a missing feature). See
    `tasks/task-2.1c.md` for the full measurement record.

### Task 2.2: Bug Fixes & Performance
- **Status:** ✅ Done for its buildable scope (2026-09-13, Task 2.2) — 2 of 4 ROADMAP
  items resolved, 1 moot, 1 genuinely deferred (see below); no further code planned under
  this task card
- **Details:** Audited all 4 ROADMAP items first. (1) "Fix any blocking API calls → move
  to executor" — a research-agent grep + direct file review found 4 real gaps across
  `video_service.py`, `tts_service.py`, `audio_service.py`, `app/api/tts.py` (not the
  ~25 already-correct `asyncio.to_thread` usages elsewhere); all 4 fixed, wrapping each
  in `asyncio.to_thread` (new small sync helpers where more than one blocking call needed
  grouping). 55 pre-existing tests across the 5 touched-file test suites pass completely
  unmodified — proves zero behavior change, purely an event-loop-blocking fix. (2)
  "Optimize OmniVoice batch" — moot, real OmniVoice integration will not be pursued per
  the user's 2026-09-13 decision. (3) "Add progress cancellation (stop mid-generation)" —
  audited the architecture: every generation route is a synchronous request/response call
  with no background-job/cancellation mechanism anywhere in the app; building real
  cancellation is a genuinely large architectural change, not a bug fix — **explicitly
  deferred as a separate future task**, not closed. (4) "Fix Gemini retry logic for 429" —
  already done during Phase 1 (all 4 Gemini-calling services have 1s→2s→4s backoff on
  429 only); this ROADMAP line predated that work and was never updated — closed via
  audit, no code needed. 493 total tests pass. See `tasks/task-2.2.md` for the full
  record.

### Task 2.3: UX Polish — ✅ DONE (2026-09-13), all 7 ROADMAP items resolved
- **Status:** ✅ Done
- **Details:** ROADMAP.md's "UX Polish" bullet had 7 items; `task-2.3.md` covers the
  first 2 (step progress indicator, breadcrumb navigation), `task-2.3b.md` covers item 3
  (keyboard shortcuts), `task-2.3c.md` covers item 5 (error toasts) and closes item 4
  (empty states) via audit, `task-2.3d.md` closes item 7 (responsive layout) via audit,
  `task-2.3e.md` covers item 6 (auto-save indicator) and closes this task entirely.
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
  - **Error toasts — DONE (2026-09-13, Task 2.3c, PM as Implementer via `/vp-auto`
    continuation) — also closes "Empty states" via audit:** audited first rather than
    assuming — all 7 step pages and `music_library.js` already had a working
    friendly-error system (the latter under different element ids, `#error-message`/
    `#status-message`, which a naive grep initially missed). The Dashboard (`/`) was the
    one real gap: a failed project load silently rendered the same "No projects yet."
    copy as a genuinely empty account, and a failed delete used a raw
    `alert(err.message)` — the one remaining CR-05 violation in the whole app. Fixed both
    with the same `#error-banner` pattern already proven everywhere else (new
    `showError`/`clearError` helpers in `dashboard.js`, a `loadFailed` flag so a failed
    load never looks like an empty account). "Empty states" needed no code at all —
    every page that can be meaningfully empty already handles it. 2 new Playwright
    tests; caught a real test-authoring bug along the way (a dialog handler returning a
    tuple hid its `dialog.accept()` coroutine from Playwright's fire-and-forget
    scheduling, deadlocking a `confirm()` dialog). 482 total tests pass. See
    `tasks/task-2.3c.md` for the full record.
  - **Responsive layout — DONE (2026-09-13, Task 2.3d, PM as Implementer via `/vp-auto`
    continuation):** ran a real Playwright audit before any planning — all 9 pages
    already have zero horizontal overflow at a 1024px viewport, thanks to the consistent
    `repeat(auto-fit, minmax(...))` grid pattern used app-wide plus `/step6`'s existing
    `@media (max-width: 1180px)` stacking rule (already covers 1024px). No code change
    needed. New permanent regression suite `tests/test_responsive_layout_browser.py` (9
    tests, one per page, realistic mocked data reused from each page's own existing test
    fixtures) pins the finding so it can't silently regress. 491 total tests pass. See
    `tasks/task-2.3d.md` for the full record.
  - **Auto-save indicator — DONE (2026-09-13, Task 2.3e, PM as Implementer via `/vp-auto`
    continuation) — closes Task 2.3 entirely:** new shared
    `frontend/static/js/save_indicator.js` (`SaveIndicator.mount()`, same pattern as
    `StepNav`/`KeyboardShortcuts`) mounted in the header of `/step2`, `/step3`, `/step6`
    — the 3 pages with an existing page-level `saved`/`dirty`/`saving`/`failed` state
    machine (BUG-012/Task 1.8b) — as an addition alongside each page's existing inline
    `#save-status` element, wired via exactly one new line inside each page's existing
    central setter function. `/step4` (per-speaker-field autosave, no single "document"
    concept), `/step1`/`/step5`/`/step7`/Dashboard/Music Library (no page-level autosave
    concept) intentionally excluded — documented reasoning per page, same class of
    deliberate scope cut as this session's prior sub-tasks. 2 new Playwright tests
    (`/step2`, `/step6` — the two distinct setter-function implementations); the existing
    `tests/test_ui_async_browser.py` autosave-race suite re-run unmodified and still
    passes, confirming the existing inline indicator is untouched. Live-verified with a
    real delayed-response screenshot showing "Saving…" in the header. 493 total tests
    pass. See `tasks/task-2.3e.md` for the full record.

### Task 2.4: UI Redesign Slice 1 — Dashboard + Script Workspace
- **Status:** ✅ Done (2026-09-14)
- **Details:** Doc-first plan approved with 2 PM decisions resolved (`theme.js` added to
  allowed files for the light-by-default fallback; Script inspector permitted to call the
  existing `previewTtsLine`/`POST /api/projects/{id}/tts/preview` endpoint — no new
  backend surface). Dashboard rebuilt as the light, high-contrast launcher (hero,
  filter/search toolbar, light project cards) while keeping every existing
  list/filter/search/delete/new-project behavior and selector (`#project-grid`,
  `#empty-state`, `[data-filter]`, `#search-input`, `[data-action]`/`[data-id]`,
  `#theme-toggle`). Step 2 rebuilt as the CapCut-style Script workspace: new
  `frontend/static/js/shell.js` (`WorkspaceShell`) drives a resizable/collapsible
  sidebar (vertical `StepNav`), central script stage (original inline-edit line cards
  untouched — `[data-line-id]`, `[data-action="edit-text"]` preserved exactly), a
  selected-line inspector (speaker/text/language notes + Listen + Regenerate), and a
  three-track Script/Voice/Music timeline. Shared tokens flipped to light-by-default in
  `:root` with dark values moved under `[data-theme="dark"]`, legacy variable aliases
  kept so untouched pages don't break. 49 new/updated Playwright tests (46 across the
  touched shared-module suites + 3 new in `tests/test_new_shell_resize_browser.py`
  covering pointer/keyboard resize, collapse/expand, selection+inline-edit coexistence,
  and the real Listen→preview-endpoint call including its error path), 516 total tests
  (515 pass + 1 pre-existing tracked Gemini-retry flake, confirmed via isolated re-run,
  not a regression — Task 2.4 touched zero backend code). `ruff` clean, all six touched
  JS files `node --check` clean. Real Playwright screenshots at 1440×900 confirmed both
  pages in both themes render correctly against the live app. See `tasks/task-2.4.md`
  for the full record and evidence.
