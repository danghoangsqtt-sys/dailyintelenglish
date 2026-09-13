# Task 2.3b: UX Polish — Keyboard Shortcuts

## Meta
- **ID**: 2.3b (second independent slice of ROADMAP.md Phase 2 "UX Polish" — task-2.3.md
  explicitly scoped itself to items 1–2 only and required separate task cards for the
  rest; this covers item 3, "Keyboard shortcuts: Ctrl+Enter to generate, Esc to cancel")
- **Phase**: 2
- **Status**: done (2026-09-13)
- **Priority**: low
- **Assignee**: PM (Claude, autonomous continuation via `/vp-auto`, "tiếp tục nào")

## Context (read before planning)

ROADMAP.md's "2.3 UX Polish" bullet has 7 items. Items 1–2 (step progress indicator,
breadcrumb nav) are done (`task-2.3.md`, `StepNav`). This card covers item 3 only:
"Keyboard shortcuts: `Ctrl+Enter` to generate, `Esc` to cancel."

Audited the actual current state before scoping (do not assume the ROADMAP wording maps
1:1 onto missing work):

- Every one of the 7 step pages already has a single, consistently-named primary action
  button: `id="generate-btn"` on `/step2` through `/step7`, `id="submit-btn"` on `/step1`
  (Create Project — the step-1 equivalent of "generate"). Every one of these already sets
  the real `.disabled` DOM property (not just a visual/aria fake) while busy or not ready
  — confirmed by reading `step1_config.js`, `step2_script.js`, `step4_tts.js`,
  `step5_video.js`, `step6_thumbnail.js`, `step7_youtube.js` directly. `Ctrl+Enter` is
  genuinely not wired anywhere (`grep -rn "ctrlKey|metaKey" frontend/static/js` only
  matches unrelated existing keydown handlers — see below).
- "`Esc` to cancel" is **already substantially implemented**, just not centrally documented
  as satisfying this ROADMAP line:
  - Every confirm-gated destructive action in this app (`step2_script.js`'s Regenerate
    All, `step3_learning.js`'s Regenerate Pack, `step6_thumbnail.js`'s regenerate) uses
    the native `window.confirm()` dialog, which the browser itself already closes/cancels
    on `Escape` for free — no code needed, and none should be added (a custom modal would
    be a regression, not an improvement).
  - `step2_script.js`'s inline script-line edit (`textarea` `keydown` handler) and
    `step3_learning.js`'s inline `contenteditable` field edit (`handleContentKeydown`)
    both already revert to the original value and blur on `Escape`.
  - `step6_thumbnail.js`'s headline/color editor fields are continuous-autosave-on-input
    (no discrete "editing session" with an original value to revert to — every keystroke
    already schedules a save) — there's nothing meaningful for `Escape` to cancel there
    without inventing a wholly new snapshot/revert feature, which is explicitly out of
    scope for a UX-polish keyboard-shortcut task. Documented as an intentional scope
    exclusion below, not a missed case.

So the only real, missing work is wiring `Ctrl+Enter` (and `Cmd+Enter` on Mac, a normal
platform courtesy, not a ROADMAP requirement but effectively free to add alongside) to
each page's existing primary button.

## Objective

Add one small shared, reusable keyboard-shortcut module — same "pure, synchronous,
no-network" component pattern as `step_nav.js` — mounted on all 7 step pages, so
`Ctrl+Enter`/`Cmd+Enter` clicks that page's primary action button, but only when it
genuinely exists, is enabled, and is visible (so it never fires "Generate" on a
`hidden` `#generate-panel` when a script/pack already exists — in that state there is no
single unambiguous "primary" action to trigger, and firing the wrong one would be worse
than doing nothing).

## Paths (`allowed_files` — do not touch anything outside this list)

- `frontend/static/js/keyboard_shortcuts.js` (new)
- `frontend/pages/step1_config.html`
- `frontend/pages/step2_script.html`
- `frontend/pages/step3_learning.html`
- `frontend/pages/step4_tts.html`
- `frontend/pages/step5_video.html`
- `frontend/pages/step6_thumbnail.html`
- `frontend/pages/step7_youtube.html`
- `frontend/static/js/step1_config.js`
- `frontend/static/js/step2_script.js`
- `frontend/static/js/step3_learning.js`
- `frontend/static/js/step4_tts.js`
- `frontend/static/js/step5_video.js`
- `frontend/static/js/step6_thumbnail.js`
- `frontend/static/js/step7_youtube.js`
- `tests/test_keyboard_shortcuts_browser.py` (new)
- `.viepilot/phases/02-testing-polish/tasks/task-2.3b.md` (this file)

## Acceptance Criteria

- [x] `KeyboardShortcuts.init({ primaryButtonId })` (new shared module): on
  `Ctrl+Enter`/`Cmd+Enter` anywhere on the page, finds the element by id, and clicks it
  only if it exists, `!button.disabled`, and it is visible (`button.offsetParent !==
  null` — correctly returns `false` for anything inside a `hidden` ancestor, e.g.
  `#generate-panel[hidden]` on `/step2`/`/step3`). Calls `event.preventDefault()` only
  when it actually clicks something, so the browser's own default handling elsewhere is
  never suppressed.
- [x] Mounted on all 7 step pages: `primaryButtonId: "submit-btn"` on `/step1`,
  `"generate-btn"` on `/step2` through `/step7` — one line per page's existing
  `DOMContentLoaded` handler, same integration style as `StepNav`.
- [x] Does not change any existing page's business logic, state machine, disabled-state
  computation, or `beforeunload` guard — the shortcut only ever does what a real mouse
  click on the same button would already do.
- [x] `Esc` to cancel: no code changes — verified already correct via the native
  `confirm()` dialogs and the two existing inline-edit revert handlers (see Context).
  This acceptance item is "verify and document," not "implement."
- [x] New Playwright tests (network-mocked, same pattern as `test_step_nav_browser.py`):
  for at least `/step2`, `/step4`, and `/step7` — `Ctrl+Enter` triggers the real generate
  call when the button is enabled and visible; does nothing when the button is disabled;
  does nothing when the generate panel is hidden (existing script/pack case, `/step2`
  and `/step3` only, since that is the one real hazard this task must not introduce).

## Forbidden Scope

- No new backend routes or API changes — purely a client-side convenience over buttons
  that already exist and already work correctly via mouse click.
- No custom modal/dialog system to replace native `confirm()` — Escape already works
  there for free; adding a custom modal would be a regression, not this task's job.
- No new "snapshot and revert on Escape" feature for `step6_thumbnail.js`'s
  continuous-autosave editor fields — explicitly out of scope (see Context).
- No changes to any of the other remaining "UX Polish" items (auto-save indicator,
  empty states, error toasts, responsive layout) — separate task cards.
- No `git add .`, no self-approval beyond this session's own standing autonomous
  authorization already recorded in TRACKER.md's Decision Log.

## Verification Commands

- `venv\Scripts\python -m pytest tests/test_keyboard_shortcuts_browser.py -q`
- `venv\Scripts\python -m pytest tests/ -q` (must still show 474+ passed, 0 new failures)
- `venv\Scripts\python -m ruff check app/ tests/`
- `node --check frontend/static/js/keyboard_shortcuts.js`
- `node --check` on every modified JS file
- `git diff --check`

## Result (2026-09-13) — DONE

Delivered exactly the plan above: `frontend/static/js/keyboard_shortcuts.js`
(`KeyboardShortcuts.init({ primaryButtonId })`), one `<script>` line + one `.init()` call
on all 7 step pages, each `primaryButtonId` matching the page's real button id
(`submit-btn` on `/step1`, `generate-btn` elsewhere). Every integration diff is exactly
one line per file (14 files, 14 insertions, confirmed via `git diff --stat`) — no existing
logic touched.

**Two real bugs caught while writing the test suite, not by inspection — both fixed
before this task could be called done:**

1. **The shortcut module itself didn't actually attach to `window`.** First draft used
   `const KeyboardShortcuts = (() => {...})();` at the top level of the script. In a
   classic (non-module) `<script>`, a top-level `const` becomes a *lexical* binding
   shared across all classic scripts on the page — so `step4_tts.js`'s
   `KeyboardShortcuts.init(...)` call actually still worked via that shared lexical
   scope, which is why an early manual smoke check (`typeof KeyboardShortcuts` from
   within a same-realm script) looked fine and even fired a real click. But
   `typeof window.KeyboardShortcuts` — a property lookup, which is how any future
   consumer or a stricter test would reasonably check for it — was `undefined`, and relying
   on implicit multi-script lexical sharing rather than an explicit `window` property is
   fragile (breaks the instant any of these scripts becomes a module, gets bundled, or
   reordered). Fixed to match `step_nav.js`'s own established pattern exactly:
   `window.KeyboardShortcuts = Object.freeze({ init })` inside the IIFE.
2. **A genuinely wrong test fixture, not a real product bug**, but worth recording:
   `tests/test_keyboard_shortcuts_browser.py`'s first draft mocked `GET
   /api/projects/{id}/youtube` as a 404 for "no package yet." `step7_youtube.js` treats
   *any* failed `getYoutubePackage()` call as a genuine load failure
   (`packageLoadFailed = true`, generate-panel and content both hidden, error banner
   shown) — unlike its own `video/status`/`audio/status` calls, which do treat 404 as an
   expected "not ready yet" case. The real contract (confirmed by reading
   `tests/test_youtube_browser.py`'s existing `_mock_project_and_package` helper) is
   `200` with `data: null` for "no package yet." Fixed the test fixture to match; this is
   a testing mistake on my part, not a step7 defect — didn't touch `step7_youtube.js`.

Also found and fixed, while building the step4 tests: `generateAll()` calls
`POST .../tts/preview` per line *before* `POST .../audio/generate` — the first test draft
only mocked `/audio/generate`, so the flow was failing at the (unmocked) preview call
against the real backend ("Project not found") and never reaching generate at all. Fixed
by mocking `/tts/preview` and `/tts/cache/` too, matching `tests/test_tts_audio_browser.py`'s
existing fixture shape.

6 new Playwright tests across `/step2` (visible-panel fires, hidden-panel no-ops),
`/step4` (enabled fires, real-disabled-mid-flight no-ops — using a genuinely delayed mock
response, not a race-prone zero-delay one), and `/step7` (visible-panel fires,
hidden-panel no-ops).

### Verification output

`venv\Scripts\python -m pytest tests/test_keyboard_shortcuts_browser.py -q` (exit 0):
```
6 passed in 20.85s
```

`venv\Scripts\python -m pytest tests/test_step_nav_browser.py tests/test_ui_async_browser.py tests/test_tts_audio_browser.py tests/test_video_studio_browser.py tests/test_youtube_browser.py tests/test_thumbnail_browser.py tests/test_dashboard_browser.py tests/test_keyboard_shortcuts_browser.py -q` (exit 0, regression check across every other browser suite touching a page this task modified):
```
63 passed in 187.27s
```

`venv\Scripts\python -m ruff check app/ tests/` (exit 0): `All checks passed!`

`node --check` on `keyboard_shortcuts.js` and all 7 modified `step*.js` files: all exit 0.

`git diff --stat` on the 14 integration files: exactly 1 insertion each, 0 deletions —
confirmed no accidental collateral edits.

`venv\Scripts\python -m pytest tests/ -q` (exit 0, full suite):
```
1 failed, 479 passed, 3 warnings in 453.85s (0:07:33)
```
The one failure, `test_learning_service.py::test_generate_learning_pack_exhausts_retries_raises`,
is the documented Gemini-retry full-suite timing flake (TRACKER.md Known Issues) — this
run was itself unusually slow (453.85s vs the ~90-130s baseline), matching the flake's own
established correlation. Re-ran in isolation: `1 passed in 0.54s`. 480 total tests
(479 + this one, both counted once it passes) — not a regression, and unrelated to any
file this task touched.
