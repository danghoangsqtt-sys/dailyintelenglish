# Task 2.3d: UX Polish — Responsive Layout (close via audit + regression test)

## Meta
- **ID**: 2.3d (fourth independent slice of ROADMAP.md Phase 2 "UX Polish" — covers item 7,
  "Responsive layout: works at 1024px width minimum")
- **Phase**: 2
- **Status**: done (2026-09-13)
- **Priority**: low
- **Assignee**: PM (Claude, autonomous continuation via `/vp-auto`, "tiếp tục")

## Context (read before planning)

Same discipline as `task-2.3b.md`/`task-2.3c.md`: ran a real proof-of-concept audit
**before** committing to a plan, rather than assuming CSS work was needed.

Built a disposable Playwright script that loaded all 9 pages (`/`, `/music`,
`/step1`-`/step7`) at a real `1024x800` viewport with realistic mocked API data (reusing
each page's own existing test fixtures where possible), and checked
`document.documentElement.scrollWidth` against `clientWidth` on each. Result: **zero
horizontal overflow on any page.** Also took full-page screenshots of the two most
layout-complex pages (`/step4`'s two-column speaker grid, `/step6`'s
preview+editor `.editor-layout` grid) and visually confirmed clean, non-overlapping,
legible layouts — no cramped or broken UI, not just "technically no scrollbar."

Why this already works, without any dedicated "responsive" effort during Phase 1: this
app's CSS consistently uses `grid-template-columns: repeat(auto-fit, minmax(...))` for
every card/variant grid (self-reflowing by construction, no media query needed), and
`/step6` — the one page with a genuinely fixed two-column, non-auto-fit layout
(`.editor-layout`) — already has a `@media (max-width: 1180px)` rule stacking it to a
single column, which already covers 1024px (1024 < 1180).

So there is no real layout defect to fix here. The task is to **make this verified,
durable, and documented** — the previous 9 tasks' hard-won UI correctness could regress
silently at narrow widths with no test ever catching it. Add a permanent regression
suite pinning "no horizontal overflow at 1024px" across all 9 pages, then close the
ROADMAP item.

## Objective

Add a Playwright regression suite that loads every page at `1024x800` with realistic
mocked data and asserts no horizontal overflow (`scrollWidth <= clientWidth`), so any
future change that breaks this gets caught automatically instead of relying on a
one-off audit.

## Paths (`allowed_files` — do not touch anything outside this list)

- `tests/test_responsive_layout_browser.py` (new)
- `.viepilot/phases/02-testing-polish/tasks/task-2.3d.md` (this file)

## Acceptance Criteria

- [x] New Playwright suite, one test per page (9 total: `/`, `/music`, `/step1` through
  `/step7`), each loading with realistic mocked API data (reusing the real response
  shapes already proven in each page's own existing browser test file — e.g.
  `tests/test_youtube_browser.py`'s `PACKAGE` shape for `/step7`, not an invented
  approximation) at a `1024x800` viewport, asserting
  `document.documentElement.scrollWidth <= document.documentElement.clientWidth`.
- [x] No production code changes — this task's own audit found no real defect. If the
  new suite reveals a genuine regression not caught by the earlier manual audit, fix it
  and document the fix in this file's Result section (contingency only, not the
  expected outcome).

## Forbidden Scope

- No CSS/layout changes speculatively "to be safe" — only fix what the new automated
  suite actually proves is broken.
- No changes to any other remaining "UX Polish" item (auto-save indicator) — separate
  task card.
- No new shared "responsive testing" framework/utility beyond this one test file — this
  app has no other multi-viewport test suite yet, so there's no existing convention to
  extend.

## Verification Commands

- `venv\Scripts\python -m pytest tests/test_responsive_layout_browser.py -q`
- `venv\Scripts\python -m pytest tests/ -q` (must still show 482+ passed, 0 new failures)
- `venv\Scripts\python -m ruff check app/ tests/`
- `git diff --check`

## Result (2026-09-13) — DONE

Delivered exactly the plan above: `tests/test_responsive_layout_browser.py`, 9 tests (one
per page), each using realistic mocked data with response shapes verified against each
page's own existing test file (`PACKAGE`/`titles`/`chapters_text` for `/step7` taken
directly from `tests/test_youtube_browser.py`; `TEMPLATES` for `/step6` from
`tests/test_thumbnail_browser.py`; script/learning/audio/video shapes matching the
already-established fixtures used across this session's other new test files). All 9
pass on the first run, confirming the manual audit finding: no code change needed.

No production code touched — the audit genuinely found nothing broken. This closes the
last item of ROADMAP.md's "UX Polish" bullet that this session set out to audit; only
"Auto-save indicator" remains unassigned.

### Verification output

`venv\Scripts\python -m pytest tests/test_responsive_layout_browser.py -q` (exit 0):
```
9 passed in 20.71s
```

`venv\Scripts\python -m ruff check app/ tests/` (exit 0): `All checks passed!`

`git diff --check` (exit 0): only pre-existing CRLF-on-touch notices, no real errors.

Full-suite run recorded in TRACKER.md's Decision Log for this task.
