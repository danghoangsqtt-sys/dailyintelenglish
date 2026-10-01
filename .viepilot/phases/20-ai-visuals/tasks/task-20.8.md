# Task 20.8 — AI Visuals smoke and closeout

## Handover

### Files added/changed

- `scripts/smoke_ai_visuals.py` — isolated temporary-data API run from two generated characters through sheets, approval, lock, two scenes, eight shots and a Remotion still for each shot kind (§11, Task 20.8).
- `docs/operations/owner-runbook-gate-b14.md` — fake/real smoke commands, real execution evidence and owner Gate B-14 checks (§11).
- `CHANGELOG.md`, `.viepilot/phases/20-ai-visuals/PHASE-STATE.md` — feature build and task state rows (§11).
- `.viepilot/phases/20-ai-visuals/tasks/task-20.8.md` — this handover.

### Tests added

- The executable `scripts/smoke_ai_visuals.py --fake` is the required CI-style end-to-end smoke. It uses the fake image engine and real API, database, job runner and Remotion still renderer. No separate pytest case was added for this same sequence.

### Verification

- Fake smoke (`python scripts/smoke_ai_visuals.py --fake`): pass, exit 0, two locked characters, eight complete shots, three 1280×720 Remotion stills; shot generation `4.34 s`, stills `8.91 s`.
- Real smoke (`python scripts/smoke_ai_visuals.py --output-dir data/tmp/gate-b14-smoke`): pass, exit 0, RTX 3060; project `50b87215-e72e-43c2-a61a-a3704edc99c1`, eight complete shots and three 1280×720 stills; shot generation `598.32 s`, stills `10.42 s`. Still files are under `data/tmp/gate-b14-smoke/20261001T061647Z-50b87215/` and remain untracked.
- Ruff (`ruff check scripts/smoke_ai_visuals.py`): `All checks passed!`
- Full suite (`python -m pytest -q`): `1268 passed, 2 warnings in 479.35s (0:07:59)`.
- TypeScript and Vitest are not required for this task because `video-renderer/` was unchanged.

### Deviations from spec

- None.

### Open questions for the PM

- The real `duo_close` still contains an unintended third person, and outfit colors drift from the references. Should Gate B-14 request a recipe or model adjustment after the owner compares duo refine on/off across three real episodes? The implementer did not alter any §2 prompt or number.
