# Task 2.3: UX Polish — Step Progress Indicator + Breadcrumb Navigation

## Meta
- **ID**: 2.3 (partial — this task card covers ROADMAP.md Phase 2 "UX Polish" items 1–2 only:
  step progress indicator + breadcrumb navigation. The other 2.3 items — auto-save
  indicator, keyboard shortcuts, empty states, error toasts, responsive layout — are
  explicitly NOT part of this task card and must not be touched.)
- **Phase**: 2
- **Status**: planned
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

- [ ] A shared `StepNav.render(containerId, { projectId, currentStep })` renders "Step X
      of 7" plus 7 clickable pills (one per step), each labelled with a short step name
      (Config / Script / Learning / Audio / Video / Thumbnail / YouTube)
- [ ] Rendered identically on all 7 step pages, in the same structural position (a new
      `<div id="step-nav"></div>` placed immediately after the closing `</header>` tag and
      before `<main>`, on every page)
- [ ] The current step's pill is visually distinct (e.g. accent-colored / "active" state);
      other pills are clickable links to `/step{N}?project_id={projectId}`
- [ ] If `project_id` is missing from the URL (page reached with no project — an existing,
      already-handled error case on every page), the component either doesn't render or
      renders without a `project_id` query string on its links — never a broken link with
      `project_id=null` or `project_id=undefined`
- [ ] Does not change any existing page's business logic, state machine, or the existing
      per-page `beforeunload` unsaved-changes guards — those keep working exactly as they
      do today; StepNav is a pure navigation affordance layered on top, not a replacement
      for the "Next Step" buttons that already exist on `/step3` and `/step4`
- [ ] Verify: a new Playwright suite loads each of the 7 pages (network-mocked, same
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
