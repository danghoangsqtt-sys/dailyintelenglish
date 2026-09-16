# Task 5.1: Dashboard scale — client-side pagination

## Meta
- **ID**: 5.1 (first task of Phase 5 — UI Polish Backlog)
- **Phase**: 5
- **Status**: in_progress (2026-09-16)
- **Priority**: high (real, measured usability problem, not cosmetic)
- **Assignee**: Codex (Implementer) — PM (Claude Code) writes/accepts, per the AR-06
  PM-Implementer contract (`docs/CODEX_CODE_PROMPT.md`, `.viepilot/SYSTEM-RULES.md`)

## Doc-First Gate

Origin: a 2026-09-16 Codex read-only UI audit measured the Dashboard rendering 176 real
project cards / 358 buttons in a single `innerHTML` pass, producing a page roughly
17,000px tall. PM re-confirmed this is still real (not stale) before opening this task.
Logged in `.viepilot/TRACKER.md`'s Decision Log (2026-09-16) and scoped into Phase 5 in
`docs/brainstorm/session-2026-09-16.md`.

## Current state (researched before writing this plan — do not re-derive from scratch)

`frontend/static/js/dashboard.js`:
- `loadProjects()` (line ~100) calls `Api.listProjects()` once on page load — this hits
  `GET /api/projects` (`app/api/projects.py:100-106`), which returns **every** project
  with no `limit`/`offset` support at all (confirmed: no query params accepted). This
  task does **not** change that — see Required decisions below.
- `render()` (line ~69) filters `allProjects` by `activeFilter`/`searchTerm`, then does
  `grid.innerHTML = filtered.map(projectCardHtml).join("")` — **every** filtered result
  renders every time, no slicing.
- `render()` is called from 3 places: `setupFilters()`'s click handler,
  `setupSearch()`'s input handler, and the delete action's success handler (in
  `setupProjectActions()`).
- `frontend/pages/dashboard.html`: `#project-grid` (the render target) and
  `#empty-state` (shown when `filtered.length === 0`) are siblings inside `<main>`, no
  existing pagination controls.
- Grid CSS: `frontend/static/css/style.css:212`, `.project-grid { grid-template-columns:
  repeat(auto-fill, minmax(280px, 1fr)); }` — responsive column count (roughly 3-6
  columns depending on viewport width), not a fixed grid.

## Objective

Add client-side pagination to the Dashboard's project grid — cap how many cards render
at once, with Prev/Next controls, without changing what data is fetched or any backend
behavior.

### Required decisions (already settled by PM, do not re-litigate)

1. **Client-side pagination only, no backend change.** `Api.listProjects()`/
   `GET /api/projects` keep returning the full list in one call — 176 projects is a
   small JSON payload, the actual problem is unbounded **DOM rendering**, not the
   fetch. Adding `limit`/`offset` to the backend would be a real API/schema change this
   task does not need and should not make.
2. **Fixed-size pagination (Prev/Next + page indicator), not infinite scroll or true
   virtualization.** Simpler to implement and test correctly than virtual-scrolling
   DOM recycling, and fully solves the measured problem (unbounded page height) at the
   real scale involved (176 projects, not tens of thousands). Page size: a number that
   divides cleanly across the grid's common column counts (e.g. **24** — works cleanly
   at 3/4/6 columns). Exact number is Codex's implementation call within that
   reasoning; state it in the plan.
3. **Filter and search changes must reset to page 1.** Since `render()` is already
   called fresh on every filter-button click and every search-input event, this should
   fall out naturally as long as the page-index state resets alongside — call this out
   explicitly in the plan and verify it with a real test, don't assume.
4. **Deleting the last card on the last page must not leave an empty page visible.**
   After a successful delete, if the current page index is now out of range for the
   new filtered/paginated result (e.g., you deleted the only card on page 8 of 8),
   clamp back to the new last valid page rather than showing an empty grid with visible
   Prev/Next controls pointing nowhere.
5. **Pagination controls only render when there's more than one page.** Don't show
   Prev/Next/page-indicator UI for the common case (a handful of projects) — this
   matches the project's own precedent of never showing dead/no-op controls.

## Proposed File-Level Plan

- `frontend/static/js/dashboard.js`: add page-index state; slice `filtered` to the
  current page before rendering; add pagination control rendering (Prev/Next + "Page X
  of Y" or equivalent) wired to page-index state; reset page index to 0 on
  filter/search change; clamp page index after delete.
- `frontend/pages/dashboard.html`: add a pagination controls container near
  `#project-grid` (exact placement/markup — Codex to propose, minimal, reusing existing
  `.btn`/`.btn-ghost` classes rather than inventing new button styles).
- `frontend/static/css/style.css` or a page-local `<style>` block in `dashboard.html` —
  only if genuinely needed for the pagination control's layout; prefer reusing existing
  shared classes first.
- New or extended browser test file — Codex to confirm exact filename in the pre-code
  plan (e.g. `tests/test_dashboard_browser.py` extended, or a new
  `tests/test_dashboard_pagination_browser.py`) — must include a real test seeded with
  more than one page's worth of mock projects (the existing `MOCK_PROJECTS` fixture in
  `tests/test_dashboard_browser.py` is small — check whether it needs a larger seed set
  for pagination coverage, or a dedicated new fixture).

## Allowed files
- `frontend/static/js/dashboard.js`
- `frontend/pages/dashboard.html`
- `frontend/static/css/style.css` (only if needed per above — state whether it was
  needed in the evidence)
- `tests/test_dashboard_browser.py` and/or a new pagination-specific test file — Codex
  to confirm exact filename(s) in the pre-code plan.
- This task card, for plan/evidence updates.

## PM Plan Review (2026-09-16) — APPROVED WITH ONE CLARIFICATION

Codex presented its pre-code plan per AR-06's 3-step process. Plan matches every
required decision in this task card (client-side only, page size 24, filter/search
reset, delete-clamp, no-pagination-on-one-page, no storage persistence across reload).

**One clarification requested before coding, not a change to the plan's substance**:
PM checked `tests/test_dashboard_browser.py` and found the existing `MOCK_PROJECTS`
constant (3-4 entries) is shared by **6** existing tests (listing, filter, search,
new-project-button, delete, and one more — confirmed via
`grep -n "MOCK_PROJECTS" tests/test_dashboard_browser.py`). The plan says "seed over 24
projects" for the new pagination tests without stating whether that means growing
`MOCK_PROJECTS` itself or adding a separate, dedicated fixture. Growing the shared
constant to 24+ entries would silently change what every one of those 6 existing tests
sees (only page 1's cards would be visible/countable in the DOM), risking a real,
subtle regression in tests that currently assume the full small set renders at once.
**Required**: use a separate, dedicated large fixture for the new pagination tests
(e.g., generated inline, like `[_project(i) for i in range(30)]`) — leave
`MOCK_PROJECTS` and all 6 of its existing consumers completely untouched. Please
confirm this explicitly in the evidence (not just imply it).

**Allowed files — confirmed/locked, exactly as Codex named them**:
- `frontend/static/js/dashboard.js`
- `frontend/pages/dashboard.html`
- `frontend/static/css/style.css` (minimal layout only, confirmed)
- `tests/test_dashboard_browser.py` (extended, not a new file — confirmed no conflict)
- This task card, for evidence only (Status field remains PM-only)

**Plan approved with the above clarification. No other changes requested.** Codex may
proceed to implementation.

## Verification checklist
- [ ] Manual/automated: seed more than one page's worth of mock projects, confirm only
  the current page's cards render in the DOM (not all of them, just hidden via CSS —
  a real DOM-count assertion, not just visual).
- [ ] Prev/Next navigate correctly; controls disable/hide appropriately at the first
  and last page.
- [ ] Changing filter or search resets to page 1.
- [ ] Deleting the last card on the last page clamps back to a valid page, never shows
  an empty grid with active-looking Prev/Next controls.
- [ ] Pagination controls don't appear at all when everything fits on one page.
- [ ] Full suite passes with 0 unexpected failures — the known Gemini-retry flake
  class is the only acceptable non-deterministic failure, and only if it reproduces as
  a pass in isolation.
- [ ] `ruff check app/ tests/`, `node --check` on touched JS, `git diff --check` — all
  clean, real output pasted.
