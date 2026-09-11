# Task 1.5: Step 3 — Learning Content

## Meta
- **ID**: 1.5
- **Phase**: 1
- **Status**: done
- **Priority**: high
- **Assignee**: AI

## Paths
- `prompts/learning/learning_pack.txt`
- `app/services/learning_service.py`
- `app/models/learning.py`
- `frontend/pages/step3_learning.html`
- `frontend/static/js/step3_learning.js`
- `tests/test_learning_api.py`

## Acceptance Criteria
- [x] Prompt template `learning_pack.txt` renders with script and config
- [x] LearningContentService extracts vocab, idioms, grammar, and quiz via Gemini REST with `LearningPackOut` validation
- [x] SQLite persistence in `learning_contents` table with UPSERT
- [x] Step 3 UI renders 4 tabs with answer toggle, coalesced trailing autosave, and confirm on regen
- [x] 20 dedicated automated tests pass; 223 total tests pass (218 unit/integration + 5 browser E2E)

## Forbidden Scope
- No synchronous/blocking network calls
- No partial state wipeout on failed LLM generation

## Verification Commands
- `venv\Scripts\python -m pytest tests/test_learning_api.py -q`
- `node --check frontend/static/js/step3_learning.js`
