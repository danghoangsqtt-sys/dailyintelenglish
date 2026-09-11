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
- `venv\Scripts\ruff check app/`
