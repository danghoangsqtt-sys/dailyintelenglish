# Task 20.3 — Foundation

## Handover

**Status:** stopped before implementation under the Phase 20 stop condition for a required change outside the files listed in spec §3.

### Files added/changed

- `.viepilot/phases/20-ai-visuals/tasks/task-20.3.md` — this handover.

### Implementation mapped to spec

- None. The blocker was found while reading the source of truth and reference implementations, before writing application code.

### Tests added and verification

- Tests added: none.
- Base commit full suite, before any change: `1244 passed, 2 warnings in 427.71s (0:07:07)`.
- Ruff baseline (`ruff check app tests`): `All checks passed!`
- TypeScript baseline (`npx tsc --noEmit`): clean (no output, exit 0).
- Vitest baseline (`npx vitest run`): `Test Files  5 passed (5)` and `Tests  34 passed (34)`.
- The task-specific test commands were not run because no implementation files were changed.

### Deviation from spec

- Task 20.3 has not been implemented. The stop condition requires a PM ruling before changing `scripts/image_worker.py`, which is outside the spec §3 file list.

### Open question for the PM

Spec §2.2 requires storing and surfacing the worker's `prompt_tokens` and `prompt_truncated` for every image; §10 says the worker is the ground truth because the estimator can miss rare-word token splits. Project shots use `encode` followed by `generate` with `embeds_path` (§§2.4, 5.2). In `scripts/image_worker.py`, `encode` computes the real token metadata but writes it only into a PyTorch `.pt` file and returns no per-item metadata in its JSON response (lines 541–559). The later `generate` response has no token metadata for an embeddings render because `call.get("prompt")` is absent (line 473). The app cannot read that `.pt` file without importing torch, which §12 forbids, or send another worker command, which does not exist. May the implementer make an additive change to `scripts/image_worker.py` so `encode` returns each item's `prompt_tokens` and `prompt_truncated` in its JSON response? If that file must remain untouched, what approved way should the app obtain the worker's actual token metadata for shots?
