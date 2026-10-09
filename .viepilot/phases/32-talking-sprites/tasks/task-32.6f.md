# Task 32.6f — Verification and Demo Episode

## Objective

Run the Phase 32 automated suite and render the existing Demo Episode, which has three approved insert beats.

## Paths

- `docs/operations/phase32-activity-cutaway-verification.md` — commands, results, coverage snapshot and output paths.
- `docs/operations/phase32-demo-cutaway-notes.md` — frame/time inspection for the three inserts.

## Verification

- Targeted backend/API/browser tests for Tasks 32.6a–d.
- `venv\Scripts\python.exe -m pytest tests/ -x`.
- `npm run test -- --run` and `npx tsc --noEmit` in `video-renderer/`.
- Real Enhanced Demo Episode render and ffprobe/visual inspection.

## Acceptance Criteria

- [ ] All automated checks pass or pre-existing failures are documented with non-regression evidence.
- [ ] Demo has exactly three reported insert beats and no subtitle/audio discontinuity.
