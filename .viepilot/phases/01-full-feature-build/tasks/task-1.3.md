# Task 1.3: Step 1 — Script Config Wizard

## Meta
- **ID**: 1.3
- **Phase**: 1
- **Status**: done
- **Priority**: high
- **Assignee**: AI

## Paths
- `frontend/pages/step1_config.html`
- `frontend/static/js/step1_config.js`
- `app/api/projects.py`
- `app/models/project.py`
- `tests/test_projects_api.py`

## Acceptance Criteria
- [x] Config API endpoint validates input (CEFR, genre, duration, accents)
- [x] Step 1 UI provides full config form with required topic, integer speakers (1–6), speaker card sync
- [x] Double-submit prevention and friendly-only error banner implemented
- [x] Successful creation navigates to Step 2 with preserved project_id
- [x] Browser E2E verified across 6 test scenarios

## Forbidden Scope
- No leaky backend exception messages to UI
- No floating-point or out-of-range speaker counts

## Verification Commands
- `venv\Scripts\python -m pytest tests/test_projects_api.py -q`
- `node --check frontend/static/js/step1_config.js`
