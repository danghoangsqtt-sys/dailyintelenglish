# Task 20.5 — Library UI

## Handover

### Files added/changed

- `frontend/pages/characters.html`, `frontend/static/js/characters.js` — Character Library form, cards, candidate/sheet review, lock flow, scenes tab and job progress (§7.1).
- `frontend/static/js/api.js` — library and image-job client methods (§§6–7.1).
- `frontend/pages/dashboard.html`, `frontend/pages/step5_video.html`, `app/main.py` — page route and links (§7.1).
- `tests/test_visuals_library_browser.py` — Playwright lifecycle and disabled-generation tests (§10).
- `.viepilot/phases/20-ai-visuals/tasks/task-20.5.md` — this handover.

### Tests added

- `test_library_create_pick_approve_lock_and_read_only`
- `test_library_health_off_disables_generate_but_keeps_browsing`

### Verification

- Playwright: `2 passed in 6.50s`.
- `node --check frontend/static/js/characters.js` and `node --check frontend/static/js/api.js`: clean (exit 0).
- Ruff (`ruff check` on touched Python paths): `All checks passed!`
- Full suite (`python -m pytest -q`): `1256 passed, 2 warnings in 486.72s (0:08:06)`.
- TypeScript and Vitest are not required because `video-renderer/` was unchanged.

### Deviations from spec

- None.

### Open questions for the PM

- None.
