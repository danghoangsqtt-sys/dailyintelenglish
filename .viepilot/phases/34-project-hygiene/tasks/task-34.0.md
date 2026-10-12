# Task 34.0: Land the Activity Library manual-upload work

## Why

The working tree has carried the 2026-10-09 owner decision (manual image names, vision auto-naming removed) uncommitted for three
days: 20 files, including the deletion of `activity_analysis_service.py`, `scripts/activity_vision_worker.py` and its test. Phase 34
edits several of the same `.viepilot/` files, so this work lands first and on its own.

## Plan

1. Run the full Python suite and the Vitest suite. If anything fails, stop and report; do not commit.
2. Commit 1 (code and its docs): `app/`, `frontend/`, `tests/`, `scripts/`, `requirements-image.txt`, `.env.example`,
   `docs/operations/activity-library-*.md`, `CHANGELOG.md`.
3. The `.viepilot/` changes (TRACKER decision rows, request files) go into the Phase 34 plan commit that follows.

## Paths

- `app/api/visuals.py`
- `app/core/config.py`
- `app/models/visuals.py`
- `app/services/visuals/activity_library_service.py`
- `app/services/visuals/activity_analysis_service.py` (deleted)
- `scripts/activity_vision_worker.py` (deleted)
- `frontend/pages/shot_library.html`
- `frontend/static/js/api.js`
- `frontend/static/js/shot_library.js`
- `tests/test_activity_library.py`
- `tests/test_activity_library_browser.py`
- `tests/test_activity_analysis_service.py` (deleted)
- `docs/operations/activity-library-manual-upload.md`
- `docs/operations/activity-library-image-manifest.md`
- `docs/operations/activity-library-local-vision.md` (deleted)
- `requirements-image.txt`
- `.env.example`
- `CHANGELOG.md`

## Verification

Full pytest and Vitest pass counts are recorded in the commit message; `git status` shows only `.viepilot/` changes afterwards.
