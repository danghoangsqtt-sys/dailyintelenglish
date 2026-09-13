# Task 2.3: UX Polish — Step Progress Indicator + Breadcrumb Navigation

## Meta
- **ID**: 2.3 (partial — this task card covers ROADMAP.md Phase 2 "UX Polish" items 1–2 only:
  step progress indicator + breadcrumb navigation. The other 2.3 items — auto-save
  indicator, keyboard shortcuts, empty states, error toasts, responsive layout — are
  explicitly NOT part of this task card and must not be touched.)
- **Phase**: 2
- **Status**: done (2026-09-13) — implemented by Codex (session ended mid-verification on
  usage limit, evidence reconstructed and independently re-verified by PM), PM-accepted
- **Priority**: medium
- **Assignee**: AI (Codex)

## Context (read before planning)

Phase 1 is done — all 10 major tasks shipped (`.viepilot/TRACKER.md`,
`.viepilot/phases/01-full-feature-build/PHASE-STATE.md`). The 7-step production pipeline
is now fully navigable end-to-end for the first time:

`/step1` (Config) → `/step2` (Script) → `/step3` (Learning) → `/step4` (TTS Audio) →
`/step5` (Video) → `/step6` (Thumbnail) → `/step7` (YouTube Package)

Every page already carries `?project_id=...` in its URL and reads it via
`URLSearchParams` in its own `init()`. Every page has the same structural shell:
`<header class="topbar">...</header>` followed by a `<main class="main">` (some pages
also have their own `.page-header` div inside `<main>` — do not confuse the two).

There is currently no shared way for a user to see which step they're on or jump back to
an earlier one — each page is an island reachable only by URL or a same-page "Next Step"
button (and not even all pages have one; `/step4` and `/step3` are the only two with a
forward-nav button today).

## Objective

Add ONE shared, reusable step-progress + breadcrumb component, rendered identically on
all 7 step pages, showing "Step X of 7" and letting the user click any step's pill to jump
directly to it (carrying the current `project_id`). This is ROADMAP.md Phase 2 → "UX
Polish" → items 1–2 ("Step progress indicator" + "Breadcrumb navigation").

## Paths (`allowed_files` — do not touch anything outside this list)

- `frontend/static/js/step_nav.js` (new)
- `frontend/static/css/style.css` (add `.step-nav`/`.step-nav-pill` rules only — do not
  touch any existing rule)
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
- `tests/test_step_nav_browser.py` (new)
- `.viepilot/phases/02-testing-polish/tasks/task-2.3.md` (this file — plan + evidence only;
  do not change `## Meta` status or acceptance checkboxes, do not touch
  `PHASE-STATE.md`/`TRACKER.md`/`ROADMAP.md`/`CHANGELOG.md` — PM updates those on acceptance)

## Acceptance Criteria

- [x] A shared `StepNav.render(containerId, { projectId, currentStep })` renders "Step X
      of 7" plus 7 clickable pills (one per step), each labelled with a short step name
      (Config / Script / Learning / Audio / Video / Thumbnail / YouTube)
- [x] Rendered identically on all 7 step pages, in the same structural position (a new
      `<div id="step-nav"></div>` placed immediately after the closing `</header>` tag and
      before `<main>`, on every page)
- [x] The current step's pill is visually distinct (e.g. accent-colored / "active" state);
      other pills are clickable links to `/step{N}?project_id={projectId}`
- [x] If `project_id` is missing from the URL (page reached with no project — an existing,
      already-handled error case on every page), the component either doesn't render or
      renders without a `project_id` query string on its links — never a broken link with
      `project_id=null` or `project_id=undefined`
- [x] Does not change any existing page's business logic, state machine, or the existing
      per-page `beforeunload` unsaved-changes guards — those keep working exactly as they
      do today; StepNav is a pure navigation affordance layered on top, not a replacement
      for the "Next Step" buttons that already exist on `/step3` and `/step4`
- [x] Verify: a new Playwright suite loads each of the 7 pages (network-mocked, same
      pattern as `tests/test_tts_audio_browser.py`/`tests/test_video_studio_browser.py`)
      and asserts: the correct "Step X of 7" text, the correct pill marked active, and
      that clicking a different pill navigates to the right URL with `project_id` intact

## Forbidden Scope

- No new backend routes, no API calls of any kind — this is pure client-side navigation
  using data the URL/page already has
- No changes to any of the 5 remaining Phase 2 "UX Polish" items (auto-save indicator,
  keyboard shortcuts, empty states, error toasts, responsive layout) — separate task cards
- No new "Next Step" buttons beyond what already exists on `/step3`/`/step4` — this task
  is about jumping to *any* step, not adding more forward-only buttons
- No refactor of any existing page's CSS/JS beyond the one-line integration needed to
  mount `StepNav`
- No `git add .`, no self-approval, no status/checkbox edits beyond this file's plan section

## Verification Commands

- `venv\Scripts\python -m pytest tests/test_step_nav_browser.py -q`
- `venv\Scripts\python -m pytest tests/ -q` (must still show 432+ passed, 0 new failures)
- `venv\Scripts\python -m ruff check app/ tests/`
- `node --check frontend/static/js/step_nav.js`
- `node --check` on every modified JS file
- `git diff --check`

## Environment preflight required before planning

Same as every task — see `docs/CODEX_CODE_PROMPT.md`. This task is backend/ffmpeg/GPU-independent
(pure frontend static assets + Playwright), so the only preflight that matters here is
confirming the repository's Playwright Chromium install actually runs in your sandbox
(`venv\Scripts\python -m pytest tests/test_dashboard_browser.py -q` is a fast, existing,
known-good smoke check for that). If Playwright isn't available in your sandbox, report
that explicitly — do not claim browser verification you didn't actually run.

## Implementer Evidence (Codex — reconstructed by PM, see note)

Codex ran out of usage quota mid-verification, after the plan was PM-approved, all code
written, and its own targeted test run (`tests/test_step_nav_browser.py`, 15 passed) and
lint/syntax checks already completed — but before it could write this evidence section or
finish watching the full-suite run to its end (it had reached ~63% with exactly one
failure, correctly still waiting for the summary rather than guessing, when its session
was cut off). Everything below is PM re-deriving and independently re-verifying the actual
delivered state from the real diff and by re-running every command itself — not copying
anything Codex claimed, since it never got to write a claim.

### Delivered

- `frontend/static/js/step_nav.js` (new): `window.StepNav.render(containerId, {
  projectId, currentStep })`. Pure synchronous DOM code, no network/async state. Missing
  or blank `projectId` renders bare `/step{N}` links (never `project_id=null`/`undefined`,
  verified via `URLSearchParams` construction only when a non-empty id is present). Active
  step gets both a `.active` class and `aria-current="step"`. Throws `RangeError` on an
  out-of-range `currentStep` (1-7) — a deliberate fail-loud guard, not a silent fallback.
- `frontend/static/css/style.css`: `.step-nav`/`.step-nav-pill` rules appended at the end
  of the file only — no existing rule touched (confirmed via diff). Uses existing design
  tokens (`--surface`, `--surface-border`, `--accent`, `--accent-soft`, `--text-muted`)
  so it follows the current theme automatically. `overflow-x: auto` on the container
  handles narrow viewports without wrapping/breaking layout.
- All 7 `frontend/pages/step*.html`: `<div id="step-nav"></div>` inserted immediately
  after `</header>` and before `<main>` (confirmed identical position via diff on every
  file), `<script src="/static/js/step_nav.js">` inserted before each page's own script.
- All 7 `frontend/static/js/step*.js`: exactly one line added as the first statement
  inside the existing `DOMContentLoaded` handler — `StepNav.render("step-nav", {
  projectId: new URLSearchParams(window.location.search).get("project_id"), currentStep:
  N })` — each page parses its own `location.search` independently rather than reusing
  any `init()`-internal state, per the PM plan-review note. No other line in any of these
  7 files changed (confirmed via diff — every hunk is exactly this one addition).
- `tests/test_step_nav_browser.py` (new): parametrized across all 7 pages (`range(1, 8)`)
  for both the happy-path render/navigate case and the missing-`project_id` case (14 cases
  total), plus one dedicated reload-persistence test — 15 tests. Assertions cover: aria
  label, exact "Step X of 7" text, all 7 pill labels in the right order, exactly one
  `aria-current="step"` on the right pill, a real computed-style color difference between
  active/inactive pills (not just a class-name check), the DOM sitting exactly between
  `header.topbar` and `main.main`, click-through navigation preserving `project_id`, and
  that missing-`project_id` links never contain the strings `null`/`undefined` on any of
  the 7 pages.

### Files changed

- `frontend/static/js/step_nav.js` (new)
- `frontend/static/css/style.css`
- `frontend/pages/step1_config.html` through `step7_youtube.html` (7 files)
- `frontend/static/js/step1_config.js` through `step7_youtube.js` (7 files)
- `tests/test_step_nav_browser.py` (new)
- `.viepilot/phases/02-testing-polish/tasks/task-2.3.md` (this file)

### Verification output (all re-run fresh by PM, not reused from Codex's partial run)

`venv\Scripts\python -m pytest tests/test_step_nav_browser.py -q` (exit 0):
```
...............                                                          [100%]
15 passed, 1 warning in 36.65s
```

`venv\Scripts\python -m ruff check app/ tests/` (exit 0): `All checks passed!`

`node --check` on `step_nav.js` and all 7 `step*.js` files: all exit 0.

`git diff --check` (exit 0): only pre-existing CRLF-on-touch notices, no real errors.

`venv\Scripts\python -m pytest tests/ -q` (exit 0):
```
452 passed, 3 warnings in 183.47s (0:03:03)
```
(No flake this run — the previously-tracked Gemini-retry flake, now 6 occurrences deep in
`.viepilot/debug/session-debug-20260912T000000Z.json`, simply didn't trigger this time,
consistent with its "occasional, load-correlated" profile.)

Also took a real Playwright screenshot of `/step2` with `StepNav` rendered to visually
confirm the active-pill styling and layout before accepting — not just trusting the DOM
assertions.

### Remaining limits / risks

- Only 2 of ROADMAP.md's 7 "UX Polish" items are covered (as scoped) — auto-save
  indicator, keyboard shortcuts, empty states, error toasts, and responsive layout remain
  unassigned.
- `StepNav` is purely a navigation affordance; it does not know or care whether a step is
  "complete" — every pill is always clickable regardless of pipeline progress, by design
  (task card explicitly asked for jump-to-any-step, not a gated wizard).

## PM Acceptance (2026-09-13)

Codex's session ended mid-verification (usage limit), but everything it had already done
— plan, implementation, its own test file, its own lint pass — was already complete and
correct on disk; only the write-up was missing. PM independently re-verified from scratch
rather than trusting any partial claim:

- Read every diff line-by-line across all 16 changed files + 2 new files. Confirmed: CSS
  is purely additive: (no existing rule touched); each of the 14 HTML/JS integration
  diffs is exactly the one line/block described above, nothing else; `step_nav.js` matches
  the plan exactly, including the "no null/undefined" URL handling and the independent
  `URLSearchParams` parse per page (the specific risk flagged during plan review).
- Re-ran `tests/test_step_nav_browser.py` myself: 15/15 pass.
- Re-ran `ruff check` and `node --check` on every touched JS file myself: all clean.
- Re-ran `git diff --check` myself: clean.
- Re-ran the full suite myself: 452/452 pass (437 pre-existing + 15 new) — no flake this
  time at all, better than Codex's own in-progress run.
- Took an independent real screenshot of the rendered component (not reusing any asset
  Codex might have produced, since none existed) to visually confirm before accepting.

**Accepted.** Closes Task 2.3's step-progress + breadcrumb slice. The remaining 5 "UX
Polish" ROADMAP items have no task card yet.
