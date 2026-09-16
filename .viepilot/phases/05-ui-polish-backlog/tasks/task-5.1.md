# Task 5.1: Dashboard scale — client-side pagination

## Meta
- **ID**: 5.1 (first task of Phase 5 — UI Polish Backlog)
- **Phase**: 5
- **Status**: done (2026-09-17)
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

## Implementer Evidence (Awaiting PM Review — 2026-09-17)

Implementation is ready for PM review. Implementer did not change the task Status and
did not commit or push.

### Implementation summary

- Added client-side pagination with a fixed page size of 24. `Api.listProjects()` and
  the backend/API remain unchanged; `render()` filters the full client-side collection,
  clamps the current page, slices one page, and creates only those cards in the DOM.
- Added static Previous/Next controls and a live “Page X of Y” indicator. The controls
  are hidden for zero or one page, and the boundary button is disabled on the first and
  last page.
- Filter and search input changes reset the page index to zero before rendering.
  Successful deletion uses the same centralized render-time clamp, so deleting the only
  card on the last page returns to the new last valid page.
- Added only two minimal shared-style rules for pagination layout; the buttons reuse the
  existing `.btn`/`.btn-ghost` design system.
- No async operation, API call, project ordering, filter definition, or project-card
  behavior was changed.

### PM clarification — isolated pagination fixture

The original `MOCK_PROJECTS` constant was not expanded or otherwise changed, and its
six pre-existing consumers were left unchanged. Pagination coverage uses the separate
`_pagination_projects(count)` factory exclusively; its 3/25/50-project data sets are
local to the new pagination tests and cannot change the DOM seen by the existing tests.

### Browser coverage and visual verification

New real-Chromium coverage verifies:

- A 50-project response creates exactly 24 `.project-card` nodes on pages 1 and 2,
  two on page 3, correct indicator text, and correct Previous/Next disabled states.
- Reload resets the session-only page index to page 1.
- Both status-filter and search changes reset from page 2 to page 1 while the filtered
  result still spans multiple pages.
- Deleting the sole card on page 2 of a 25-project result renders the 24-card first page
  and hides the now-unnecessary controls.
- A separate 3-project pagination fixture renders three cards and no visible controls.

An additional disposable real-Chromium check at 1440×900 used 50 intercepted projects.
It measured 24 cards in the DOM, `Page 1 of 3`, Previous disabled, Next enabled, and no
horizontal document overflow. The full-page screenshot was kept outside the repository:
`C:\Users\Admin\AppData\Local\Temp\dashboard-pagination-task-5.1.png`.

### Targeted verification

`venv\Scripts\python.exe -m pytest tests/test_dashboard_browser.py -q` (exit code 0):

```text
..................                                                       [100%]
18 passed in 26.83s
```

`venv\Scripts\python.exe -m pytest tests/test_responsive_layout_browser.py::test_dashboard_no_overflow_at_1024 -q` (exit code 0):

```text
.                                                                        [100%]
1 passed in 3.06s
```

### Required verification output

`venv\Scripts\python.exe -m pytest tests/ -q` (exit code 1 — one known Gemini-retry
timing flake, confirmed passing in isolation below):

```text
........................................................................ [ 12%]
........................................................................ [ 25%]
........................................................................ [ 38%]
........................................................................ [ 50%]
..................................................F..................... [ 63%]
........................................................................ [ 76%]
........................................................................ [ 89%]
..............................................................           [100%]
================================== FAILURES ===================================
______________ test_generate_script_backoff_sequence_is_1s_2s_4s ______________

monkeypatch = <_pytest.monkeypatch.MonkeyPatch object at 0x000001FED88C7A80>
no_real_sleep = [0.1, 0.1, 0.1, 0.1, 0.1, 0.1, ...]

    async def test_generate_script_backoff_sequence_is_1s_2s_4s(monkeypatch, no_real_sleep):
        queue_responses(
            monkeypatch,
            [
                FakeResponse(429, text="rate limited"),
                FakeResponse(429, text="rate limited"),
                FakeResponse(429, text="rate limited"),
                gemini_ok_response(VALID_LINES),
            ],
        )

        await script_service.generate_script("proj-1", SAMPLE_CONFIG)

>       assert no_real_sleep == [1.0, 2.0, 4.0]
E       assert [0.1, 0.1, 0....0.1, 0.1, ...] == [1.0, 2.0, 4.0]
E
E         At index 0 diff: 0.1 != 1.0
E         Left contains 6898487 more items, first extra item: 0.1
E         Use -v to get more diff

tests\test_script_service.py:145: AssertionError
------------------------------ Captured log call ------------------------------
WARNING  app.services.script_service:script_service.py:122 gemini_retryable_error model=gemini-3.8-flash prompt_hash=56199050ed00c89c status=429 attempt=1 retry_in_s=1.0
WARNING  app.services.script_service:script_service.py:122 gemini_retryable_error model=gemini-3.8-flash prompt_hash=56199050ed00c89c status=429 attempt=2 retry_in_s=2.0
WARNING  app.services.script_service:script_service.py:122 gemini_retryable_error model=gemini-3.8-flash prompt_hash=56199050ed00c89c status=429 attempt=3 retry_in_s=4.0
============================== warnings summary ===============================
venv\Lib\site-packages\fastapi\testclient.py:1
  D:\DataAdmin\Daily_Intel_English\venv\Lib\site-packages\fastapi\testclient.py:1: StarletteDeprecationWarning: Using `httpx` with `starlette.testclient` is deprecated; install `httpx2` instead.
    from starlette.testclient import TestClient as TestClient  # noqa

venv\Lib\site-packages\starlette\testclient.py:53
  D:\DataAdmin\Daily_Intel_English\venv\Lib\site-packages\starlette\testclient.py:53: DeprecationWarning: The anyio.abc.BlockingPortal alias is deprecated, use anyio.from_thread.BlockingPortal instead.
    _PortalFactoryType = Callable[[], AbstractContextManager[anyio.abc.BlockingPortal]]

-- Docs: https://docs.pytest.org/en/stable/how-to/capture-warnings.html
=========================== short test summary info ===========================
FAILED tests/test_script_service.py::test_generate_script_backoff_sequence_is_1s_2s_4s
1 failed, 565 passed, 2 warnings in 1146.05s (0:19:06)
```

The failure is the task card's explicitly accepted pre-existing Gemini-retry timing
flake class. Task 5.1 touches no Python/backend/Gemini code. The exact failing test was
immediately rerun in isolation:

`venv\Scripts\python.exe -m pytest tests/test_script_service.py::test_generate_script_backoff_sequence_is_1s_2s_4s -q` (exit code 0):

```text
.                                                                        [100%]
1 passed in 0.65s
```

`venv\Scripts\python.exe -m ruff check app/ tests/` (exit code 0):

```text
All checks passed!
```

`node --check frontend/static/js/dashboard.js` (exit code 0):

```text
(no stdout or stderr)
```

`git diff --check` (exit code 0):

```text
warning: in the working copy of '.viepilot/phases/05-ui-polish-backlog/tasks/task-5.1.md', LF will be replaced by CRLF the next time Git touches it
warning: in the working copy of 'frontend/pages/dashboard.html', LF will be replaced by CRLF the next time Git touches it
warning: in the working copy of 'frontend/static/css/style.css', LF will be replaced by CRLF the next time Git touches it
warning: in the working copy of 'frontend/static/js/dashboard.js', LF will be replaced by CRLF the next time Git touches it
warning: in the working copy of 'tests/test_dashboard_browser.py', LF will be replaced by CRLF the next time Git touches it
```

These are Windows line-ending conversion notices, not whitespace errors.

## PM Re-review (2026-09-17) — ACCEPTED

Independently re-verified everything rather than accepting the report on its word.

**Diff review** — read the full `git diff` for all 4 touched files:
- `dashboard.js`: the clamp logic is centralized inside `render()` itself
  (`currentPage = Math.max(0, Math.min(currentPage, Math.max(totalPages - 1, 0)))`,
  computed fresh on every call before anything else) — this means the delete handler
  needed **zero** changes to satisfy the "clamp after delete" requirement, since
  `render()` already re-clamps on every invocation including the one delete already
  calls. Confirmed via the diff that `setupProjectActions()`/the delete handler was not
  touched at all — a cleaner solution than the explicit post-delete clamp call the task
  card anticipated, not a shortcut.
  `currentPage = 0` was added to both `setupFilters()`'s and `setupSearch()`'s handlers,
  satisfying the reset-on-change requirement exactly.
  Confirmed no `localStorage`/`sessionStorage` calls were added — matches "no
  persistence across reload."
- `dashboard.html`: the new `#project-pagination` nav sits as a sibling of
  `#project-grid`, uses only existing `.btn`/`.btn-ghost` classes, all-English copy
  (`← Previous`, `Next →`, `Project pages` aria-label).
- `style.css`: exactly 2 new minimal layout rules, no new button styles, confirmed.
- `tests/test_dashboard_browser.py`: confirmed the diff never touches `MOCK_PROJECTS`
  or any of its 6 existing consumers — `_pagination_projects(count)` is a fully
  separate factory inserted after it.

**New test review**: 4 new tests directly exercise every required decision —
`test_dashboard_pagination_caps_dom_navigates_and_resets_on_reload` asserts exact card
counts and first/last ids across all 3 pages of a 50-project set plus reload-resets-to-
page-1; `test_dashboard_pagination_is_hidden_for_a_single_page`; the filter/search
reset test navigates to page 2 twice (once per interaction) and confirms both reset to
page 1 with the right recomputed total pages; the delete-clamp test seeds exactly 25
projects (so page 2 has precisely 1 card), deletes it, and confirms the clamp back to
page 1 (24 cards) with pagination now correctly hidden.

**PM independently re-ran every verification command**: 18/18 dashboard tests pass,
1/1 responsive test passes, `ruff check` clean, `node --check` clean, `git diff --check`
exit 0 — all matched the Implementer's report exactly.

**Screenshot review**: the disposable 1440×900 screenshot confirms clean rendering, 24
cards, correct "Page 1 of 3" indicator, correct disabled states, no horizontal
overflow. Separately noticed the Dashboard's hero text ("Tạo podcast tiếng Anh chuẩn
với AI") is in Vietnamese — investigated via `git log -S`, confirmed this has been
present since the very first commit of the project (2026-09-10, Task 1.1) and is
**not** something this task touched or introduced (the diff never goes near the hero
section). This is the concrete instance behind the general "UI mixes Vietnamese and
English copy" P2 finding that was explicitly accepted as a permanent characteristic
when Task 4.3 was dropped on 2026-09-16 — noted here for completeness, not treated as
a new or in-scope defect.

**Full suite, run independently**: 560 passed, 6 failed in 601.25s — all 6 in
`tests/test_script_service.py`/`tests/test_learning_service.py`/
`tests/test_youtube_service.py`'s Gemini-retry timing tests (the documented
`no_real_sleep`-fixture flake class, worse than usual this run because the run itself
ran markedly slower than the ~250-450s baseline). All 6 confirmed passing instantly
in isolation together (`0.59s` total). Task 5.1 touched zero backend/Gemini code, so
this is non-regressive by construction, not just by re-run — same known, accepted
flake class, just a heavier manifestation this particular run.

**Zero real defects found on PM review.** Accepted as delivered — no changes
requested.

**This closes Task 5.1.** Phase 5 continues with Task 5.2 (timeline polish) next.
