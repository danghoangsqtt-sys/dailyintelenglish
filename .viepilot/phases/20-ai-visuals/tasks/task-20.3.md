# Task 20.3 — Foundation

## Handover

**Status:** implemented under PM Errata E1. The earlier stop question is resolved by the merged spec ruling.

### Files added/changed

- `app/db/migrations/008_ai_visuals.sql`, `app/db/database.py` — additive tables and idempotent built-in scene seed (§4).
- `app/services/visuals/__init__.py`, `recipes.py`, `geometry.py` — fixed prompts, estimator and ported pose/mask/hand helpers (§§2.2–2.7).
- `app/services/visuals/engine.py` — leased subprocess worker and deterministic fake engine (§3).
- `scripts/image_worker.py` — additive `encode.item_tokens` JSON response, per Errata E1.
- `app/services/visuals/jobs.py`, `runner.py` — durable FIFO jobs, duplicate guard, progress, image-boundary cancel and restart recovery (§5.3).
- `app/api/visuals.py`, `app/main.py`, `app/core/config.py` — health route, startup runner, and kill switches (§§3, 6).
- `tests/test_visuals_foundation.py` — foundation tests (§10).
- `.viepilot/phases/20-ai-visuals/tasks/task-20.3.md` — this handover.

### Tests added

- `test_migration_008_and_builtin_seed_once` (fresh and 007 databases)
- `test_recipe_strings_and_worst_case_budget`
- `test_geometry_heads_halves_ears_hands_and_refine_mask`
- `test_fake_engine_and_worker_token_response`
- `test_jobs_fifo_duplicate_cancel_recovery`
- `test_runner_cancels_at_boundary_and_gpu_error`

### Verification

- Base commit full suite: `1244 passed, 2 warnings in 427.71s (0:07:07)`.
- Focused tests: `7 passed in 1.98s`.
- Existing cross-loop script-save regression plus foundation tests, after fixing idle runner wake behavior: `8 passed, 2 warnings in 3.36s`.
- Ruff (`ruff check` on touched Python paths): `All checks passed!`
- Full suite (`python -m pytest -q`): `1251 passed, 2 warnings in 446.28s (0:07:26)`.
- TypeScript and Vitest are not required for this task because `video-renderer/` was unchanged.

### Deviations from spec

- None. The worker protocol addition is expressly authorized by Errata E1.

### Open questions for the PM

- None.
