# Task 20.4 — Library backend

## Handover

### Files added/changed

- `app/models/visuals.py` — character/scene inputs and fixed options (§4.1).
- `app/services/visuals/library_service.py` — character assets, lock rules, scenes, face crop and safe content paths (§§4–5.1).
- `app/services/visuals/pipelines.py` — candidate, sheet and scene-preview jobs (§§2.4, 5.1).
- `app/api/visuals.py` — library, content and job routes (§6).
- `app/main.py`, `app/services/visuals/runner.py` — handler registration and queue wake behavior (§5.3).
- `tests/test_visuals_library_api.py` — lifecycle and containment tests (§10).
- `.viepilot/phases/20-ai-visuals/tasks/task-20.4.md` — this handover.

### Tests added

- `test_character_lifecycle_and_content`
- `test_scene_crud_preview_builtin_and_kill_switch`
- `test_character_delete_force_and_content_path_guard`

### Verification

- Focused lifecycle tests: `3 passed, 2 warnings in 4.30s`.
- Cross-loop regression plus both visuals test modules after startup queue fix: `11 passed, 2 warnings in 6.67s`.
- Ruff (`ruff check` on touched Python paths): `All checks passed!`
- Full suite (`python -m pytest -q`): `1254 passed, 2 warnings in 447.13s (0:07:27)`.
- TypeScript and Vitest are not required because `video-renderer/` was unchanged.

### Deviations from spec

- None.

### Open questions for the PM

- None.
