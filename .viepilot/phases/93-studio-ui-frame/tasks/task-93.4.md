# Task 93.4 — Create video

See [PLAN.md](../PLAN.md), D138–D142, and the look in `.viepilot/ui-direction/session-2026-11-03-alt/e/`.

## Design (written before code)

- New `frontend/pages/create.html` (`/create`): two modes (One video -> `/step1?kind=...`; Many Shorts -> the Shorts
  batch flow, moved here from `shorts_batch.html` with its IDs and script); a Lina note; filters (group, format); the
  template gallery grouped by purpose with the Phase 92 clips (`template_samples.js`). `#batch` opens the batch mode.

## Paths

`frontend/pages/create.html`, `frontend/pages/shorts_batch.html`, `frontend/static/js/shorts_batch.js`, `frontend/static/js/template_samples.js`, `backend/main.py`

## Verification

Shorts batch browser tests pass on `/create#batch`; gallery cards link to Step 1 with the kind.
