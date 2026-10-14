# PHASE-STATE — Phase 45: Audit follow-ups (2026-10-14)

- **Status:** complete 2026-10-14. BUG-032, ENH-032, BUG-031, BUG-033, BUG-034 and ENH-033 are implemented. Repackaging the exe waits for the outstanding owner gates.

| Task | Description | Status |
|---|---|---|
| 45.1 | Keep selected script and learning exports current across API edits and durable AI jobs (BUG-032) | done |
| 45.2 | Copy exports outside the shared DB lock, with safe concurrent status updates (ENH-032) | done |
| 45.3 | Route project-folder and Shorts requests through the shared frontend API client (ENH-033) | done |
| 45.4 | Refresh README and generated API reference (BUG-033, BUG-034) | done |
| 45.5 | Reconcile Phase 41–44 records, HANDOFF and eligible completion tags (BUG-031) | done |

## Constraints

- Phase 42/43/44 owner gates B-25/B-27/B-28 remain pending until the owner accepts them; B-26 is also pending per Phase 39.
- No new exe build before those gates. Existing `dist/` is preserved.
- The chosen export folder is user data: no deletion on unchecking a component or stopping export.

## Paths

- backend/content/export_service.py
- backend/api/export.py
- backend/api/projects.py
- backend/api/learning.py
- backend/content/script_pipeline.py
- backend/content/learning_pipeline.py
- frontend/static/js/api.js
- frontend/static/js/project_folder.js
- frontend/static/js/step5_shorts.js
- tests/test_phase41_export.py
- README.md
- docs/api.md
- .viepilot/ROADMAP.md
- .viepilot/TRACKER.md
- .viepilot/HANDOFF.json

## Verification

- Full Python suite: 1,602 passed; focused export suite: 7 passed.
- Renderer TypeScript check and 70 Vitest tests passed; Ruff, JavaScript syntax and `git diff --check` clean.
- Generated API reference matches the current OpenAPI schema (169 routes), including export and AI-scene routes.
- Phase state and eligible local tags checked against recorded gate decisions; the existing exe was left untouched.
