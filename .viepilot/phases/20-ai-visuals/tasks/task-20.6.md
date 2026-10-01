# Task 20.6 — Project visuals

## Handover

### Files added/changed

- `app/services/visuals/project_visuals_service.py` — cast, ordered scenes, shot records, warnings, regeneration seeds and contained shot paths (§§5.2, 6).
- `app/services/visuals/pipelines.py` — three worker lifetimes for shot encoding, pose rendering, duo refinement and hand repair (§5.2).
- `app/api/visuals.py`, `app/models/visuals.py`, `app/main.py` — project visuals routes, cast validation and job handler registration (§6).
- `app/services/project_service.py` — shot file cleanup during project deletion (§5.2).
- `frontend/pages/step5_video.html`, `frontend/static/js/step5_video.js`, `frontend/static/js/api.js` — cast and scene selection, shot progress and grid, raw/final toggle, regeneration (§7.2).
- `tests/test_visuals_project_api.py`, `tests/test_visuals_project_browser.py` — fake-engine API and Playwright coverage (§10).
- `.viepilot/phases/20-ai-visuals/tasks/task-20.6.md` — this handover.

### Tests added

- `test_cast_validation_warning_and_speaker_replacement`
- `test_shot_sets_regenerate_and_content_guard` (three cast/scene combinations)
- `test_project_delete_removes_visual_files`
- `test_shot_prompt_truncation_from_fake_encode`
- `test_step5_cast_scenes_generate_grid_and_regenerate`

### Verification

- Focused API and Playwright: `7 passed, 2 warnings in 26.31s`.
- `node --check frontend/static/js/api.js` and `node --check frontend/static/js/step5_video.js`: clean (exit 0).
- Ruff (`ruff check` on touched Python paths): `All checks passed!`
- Full suite (`python -m pytest -q`): `1263 passed, 2 warnings in 509.61s (0:08:29)`.
- TypeScript and Vitest are not required because `video-renderer/` was unchanged.

### Deviations from spec

- None.

### Open questions for the PM

- None.
