# Task 2.3e: UX Polish — Auto-save Indicator (last item, closes Task 2.3)

## Meta
- **ID**: 2.3e (fifth and final independent slice of ROADMAP.md Phase 2 "UX Polish" —
  covers item 6, "Auto-save indicator: 'Saved' / 'Saving...' in header")
- **Phase**: 2
- **Status**: done (2026-09-13)
- **Priority**: low
- **Assignee**: PM (Claude, autonomous continuation via `/vp-auto`)

## Context (read before planning)

Audited first, same discipline as every other 2.3 sub-task. Three pages
(`/step2`, `/step3`, `/step6`) already have a full `saved`/`dirty`/`saving`/`failed`
autosave state machine (BUG-012, Task 1.8b) with ONE central setter function each
(`setSaveStatusState` on `/step2`/`/step3`, `setSaveStatus` on `/step6`) that already
updates a `#save-status` element — but that element sits inline near the edited content
(next to the Next-Step button / editor panel), not in the page header, which is what the
ROADMAP line actually asks for.

`/step4` is a genuinely different shape: there is no single page-level "document" being
saved — each speaker card's speed/pitch/volume sliders autosave independently
(`state.speakerSave[speakerId]` entries, per-field debounce), and the existing UI already
shows each card's own status inline (`.speaker-save-status`). There is no natural
"aggregate saved/saving" concept to put in a header without inventing new
cross-field-aggregation state that this narrow slice doesn't need to build — same class
of deliberate scope cut as Task 2.3b's decision not to touch `step6_thumbnail.js`'s
`retry-save-btn` bug or Task 1.7c's "upload only, not lip-sync." `/step1` (one-shot
Create, no draft to autosave), `/step5` (no autosave — only a synchronous "Generate video"
action plus the separate avatar upload/remove buttons, each already showing its own inline
status), `/step7` (read-only display + explicit Generate/Regenerate, no draft autosave),
the Dashboard, and Music Library (no draft-editing concept at all) are excluded for the
same reason: no page-level autosave state machine exists there to reflect.

So the scope is: add ONE new shared, reusable header indicator component (same
"pure, synchronous" shape as `StepNav`/`KeyboardShortcuts`) and wire it into exactly
the 3 pages that already have a single central save-status setter function — as an
**additional** call inside that existing function, not a replacement for the existing
inline `#save-status` element (removing/relocating that would touch tested, working
behavior for no real benefit — `tests/test_ui_async_browser.py` asserts against
`#save-status` directly and must keep passing unchanged).

## Objective

Add `frontend/static/js/save_indicator.js` (`SaveIndicator.mount(containerId)` returning
`{ update(status) }`), mount it in the header (`<header class="topbar">`) of `/step2`,
`/step3`, `/step6`, and call `.update(status)` from inside each page's existing central
save-status setter function alongside its existing inline update — one extra line per
page, no existing logic touched.

## Paths (`allowed_files` — do not touch anything outside this list)

- `frontend/static/js/save_indicator.js` (new)
- `frontend/pages/step2_script.html`
- `frontend/pages/step3_learning.html`
- `frontend/pages/step6_thumbnail.html`
- `frontend/static/js/step2_script.js`
- `frontend/static/js/step3_learning.js`
- `frontend/static/js/step6_thumbnail.js`
- `tests/test_save_indicator_browser.py` (new)
- `.viepilot/phases/02-testing-polish/tasks/task-2.3e.md` (this file)

## Acceptance Criteria

- [x] `SaveIndicator.mount(containerId)` (new shared module, same `window.X =
  Object.freeze(...)` pattern as `StepNav`/`KeyboardShortcuts` — not a bare top-level
  `const`, matching the real bug found and fixed in Task 2.3b): renders "Saved" /
  "Unsaved changes" / "Saving…" / "Save failed" text into the container for
  `saved`/`dirty`/`saving`/`failed` respectively; a `"saved"` status auto-clears back to
  empty after 2s if the status hasn't changed again in the meantime (same fade behavior
  already proven in all 3 existing inline indicators) .
- [x] Mounted once per page in `<header class="topbar">` (a small `<span
  id="save-indicator" class="save-indicator"></span>` placed before the theme-toggle
  button) on `/step2`, `/step3`, `/step6` only.
- [x] Each of the 3 pages' existing central save-status setter function
  (`setSaveStatusState`/`setSaveStatus`) gains exactly one additional call —
  `saveIndicator.update(newStatus)` — alongside its existing inline `#save-status`
  update. The existing inline element and its exact text/markup are completely
  untouched.
- [x] No change to any existing state machine, debounce logic, retry-button wiring, or
  `beforeunload` guard on any of the 3 pages.
- [x] `tests/test_ui_async_browser.py` (existing, `/step2`/`/step3` autosave races) still
  passes unmodified — proves the existing inline indicator behavior is untouched.
- [x] New Playwright tests confirm the new header indicator reflects `saving` → `saved`
  (with fade) on at least `/step2` and `/step6` (one page per distinct setter-function
  implementation).

## Forbidden Scope

- No header indicator on `/step1`, `/step4`, `/step5`, `/step7`, Dashboard, or Music
  Library — none of them has a matching page-level autosave concept (see Context for the
  reasoning per page). Building one for `/step4` would require inventing new
  cross-speaker-field aggregation state, a bigger feature than this slice.
- No removal/relocation of any existing inline `#save-status` element — additive only.
- No fix for `step6_thumbnail.js`'s known `retry-save-btn` `.hidden`-on-`.btn` CSS bug
  (flagged in TRACKER.md Known Issues since Task 1.7c) — out of scope for this task.
- No `git add .`, no self-approval.

## Verification Commands

- `venv\Scripts\python -m pytest tests/test_save_indicator_browser.py -q`
- `venv\Scripts\python -m pytest tests/test_ui_async_browser.py -q` (must be unaffected)
- `venv\Scripts\python -m pytest tests/ -q` (must still show 491+ passed, 0 new failures)
- `venv\Scripts\python -m ruff check app/ tests/`
- `node --check frontend/static/js/save_indicator.js`
- `node --check` on the 3 modified JS files
- `git diff --check`

## Result (2026-09-13) — DONE

Delivered exactly the plan above. `frontend/static/js/save_indicator.js`:
`window.SaveIndicator.mount(containerId)` (explicit `window.X = Object.freeze(...)`
assignment, matching the real bug fixed in Task 2.3b rather than a bare top-level
`const`), returns `{ update(status) }`. Each of `/step2`, `/step3`, `/step6` gets a
`<span id="save-indicator" class="save-indicator"></span>` in `.topbar-actions` (before
the Dashboard link), `<script src="/static/js/save_indicator.js">` after
`keyboard_shortcuts.js`, a module-level `let saveIndicator = null;`, one
`saveIndicator = SaveIndicator.mount("save-indicator");` line in `DOMContentLoaded`
(right after the existing `KeyboardShortcuts.init(...)` line), and exactly one new
`if (saveIndicator) saveIndicator.update(newStatus);` line inside each page's existing
central save-status setter function — nothing else touched.

2 new Playwright tests (`/step2`'s inline-edit-then-autosave flow, `/step6`'s headline
autosave flow — the two distinct setter-function implementations), both asserting the
header indicator shows "Saving…" then "Saved" then fades back to empty, exactly like the
existing inline indicators already do. `tests/test_ui_async_browser.py` (the existing
`/step2`/`/step3` autosave-race suite) re-run unmodified and still passes, confirming the
existing inline `#save-status` behavior is completely untouched.

Live-verified with a real Playwright screenshot (delayed-response mock, not an instant
one, to actually catch the "Saving…" state mid-flight) — confirmed the header shows
"Saving…" next to the Dashboard link while a save is in flight.

**This closes Task 2.3 entirely** — all 7 ROADMAP.md "UX Polish" items are now resolved
(4 shipped code across 2.3/2.3b/2.3e, 3 closed via audit with no code change needed
across 2.3c/2.3d).

### Verification output

`venv\Scripts\python -m pytest tests/test_save_indicator_browser.py -q` (exit 0):
```
2 passed in 10.39s
```

`venv\Scripts\python -m pytest tests/test_ui_async_browser.py tests/test_thumbnail_browser.py -q` (exit 0):
```
11 passed in 28.04s
```

`venv\Scripts\python -m ruff check app/ tests/` (exit 0): `All checks passed!`

`node --check` on `save_indicator.js`, `step2_script.js`, `step3_learning.js`,
`step6_thumbnail.js`: all exit 0.

Full-suite run and final total recorded in TRACKER.md's Decision Log for this task.
