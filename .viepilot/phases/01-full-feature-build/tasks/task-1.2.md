# Task 1.2: Dashboard & Project Management

## Meta
- **ID**: 1.2
- **Phase**: 1
- **Status**: in_progress
- **Priority**: high
- **Assignee**: AI

## Paths
- `app/models/project.py`
- `app/services/project_service.py`
- `app/api/projects.py`
- `frontend/pages/dashboard.html`
- `frontend/static/js/dashboard.js`
- `tests/test_projects_api.py`
- `tests/test_project_service.py`

## Acceptance Criteria
- [x] ProjectService CRUD with atomic speaker updates, config_json sync, forward-only status machine
- [x] Automated test suite covering project CRUD and validation (30 tests pass)
- [ ] Automated UI tests for dashboard listing, filtering, navigation

## Forbidden Scope
- No direct database writes outside ProjectService and write transaction lock
- No skipping pipeline stages in status transitions

## Verification Commands
- `venv\Scripts\python -m pytest tests/test_projects_api.py tests/test_project_service.py -q`
- `venv\Scripts\python -m pytest tests/test_dashboard_browser.py -q`
- `venv\Scripts\ruff check app/`

## Implementation Notes (2026-09-11, PM-executed sub-task: dashboard UI tests)
Remaining acceptance criterion is "Automated UI tests for dashboard listing, filtering, navigation."
Dashboard (`frontend/pages/dashboard.html` + `dashboard.js`, served at `/`) has no backend
dependency beyond `GET /api/projects` and `DELETE /api/projects/{id}` — same route-mocking
pattern already used in `tests/test_ui_async_browser.py` (live uvicorn server + Playwright
`page.route()` interception, no real DB writes) will be reused, new file
`tests/test_dashboard_browser.py`, no changes to app/service files (Forbidden Scope: none of
the existing dashboard behavior changes, tests only).

Planned scenarios:
1. Listing: seed 3 mock projects (draft / script_generated / complete) via route mock of
   `GET /api/projects`; assert 3 `.project-card` render with correct status badge text.
2. Filtering: click `[data-filter="draft"]`; assert only the draft card remains visible
   (others removed from `#project-grid` innerHTML) and empty-state stays hidden.
3. Search: type into `#search-input` a substring of one project's name; assert only the
   matching card renders.
4. Empty state: mock `GET /api/projects` returning `[]`; assert `#empty-state` visible with
   the "No projects yet" copy, `#project-grid` empty.
5. New Project navigation: click `#new-project-btn`; assert navigation to `/step1`.
6. Continue navigation: click `[data-action="continue"]` on a `draft` card; assert navigation
   to `/step2?project_id=<id>`.
7. Delete: click `[data-action="delete"]`, auto-accept the `confirm()` dialog via Playwright's
   `page.on("dialog", ...)`, mock `DELETE /api/projects/{id}` 200; assert the card is removed
   from the DOM without a page reload.

No production code changes expected; if a real bug in dashboard.js surfaces during testing,
fix it under the existing Forbidden Scope (UI-state layer only, no direct DB access).
