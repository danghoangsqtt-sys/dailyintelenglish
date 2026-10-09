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

- [x] All automated checks pass or pre-existing failures are documented with non-regression evidence.
- [x] Demo has exactly three reported insert beats and no subtitle/audio discontinuity.

## Result — 2026-10-09

- 42 targeted tests passed. The complete Python suite passed as 1,411 non-browser tests
  plus 235 browser tests across all 42 browser files (1,646 total); two cumulative
  Playwright `page.goto` flakes from monolithic runs were each disproved by three isolated
  passes and by the complete segmented run.
- Remotion Vitest 65/65, TypeScript and Phase 32 Ruff checks passed.
- The production API rendered Demo Episode with exactly three approved generic cutaways,
  `fallback_used=false`, and persisted all three usage-history rows atomically.
- ffprobe, full decode, packet-gap analysis and 15 boundary/midpoint frames confirm H.264
  1280×720 + continuous AAC, 0.3-second fades, 6-second cap and uninterrupted overlays.
- Evidence: `docs/operations/phase32-activity-cutaway-verification.md` and
  `docs/operations/phase32-demo-cutaway-notes.md`.
