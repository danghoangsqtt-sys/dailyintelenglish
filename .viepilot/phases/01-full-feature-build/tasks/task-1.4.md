# Task 1.4: Step 2 — AI Script Generation

## Meta
- **ID**: 1.4
- **Phase**: 1
- **Status**: done
- **Priority**: high
- **Assignee**: AI

## Paths
- `prompts/script/`
- `app/services/script_service.py`
- `app/models/script.py`
- `frontend/pages/step2_script.html`
- `frontend/static/js/step2_script.js`
- `tests/test_script_service.py`
- `tests/test_projects_write_lock.py`

## Acceptance Criteria
- [x] Jinja2 prompt templates loaded async with genre and CEFR blocks (101 tests)
- [x] ScriptService calls Gemini REST, handles 429 backoff, validates speaker UUIDs, persists lines
- [x] Step 2 UI supports generate, line edit, single line regen, and confirm dialog for regen all
- [x] Status auto-advances draft -> script_generated
- [x] Concurrency hardening (1.4D-FIX2/FIX2B/FIX2C): connection-wide read/write transactions prevent race conditions and dirty reads
- [x] Browser E2E verified with persisted reload

## Forbidden Scope
- No SDK blocking calls in event loop
- No per-line ID collisions across generations

## Verification Commands
- `venv\Scripts\python -m pytest tests/test_script_service.py tests/test_projects_write_lock.py -q`
- `node --check frontend/static/js/step2_script.js`
