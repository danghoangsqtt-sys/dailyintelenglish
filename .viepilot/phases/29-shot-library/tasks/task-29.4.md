# Task 29.4: Shot library data model, service and API (ENH-020)

## Plan

- `app/db/migrations/016_shot_library.sql`: table `shot_library` (kind, scene, ordered character ids, action, expression,
  gaze, face signature, picture, review state pending/approved/rejected, stale, use count) and `project_shots.source` /
  `library_shot_id`.
- `app/services/visuals/shot_library_service.py`: add from a finished project shot (copy, pending, no duplicates by content
  hash), list with filters, review, delete, stale detection by the face signature of each character, coverage.
- `app/api/visuals.py`: `GET/PATCH/DELETE /api/visuals/library/shots`, `GET .../content`, `POST /api/projects/{id}/visuals/shots/{shot}/to-library`,
  `GET /api/projects/{id}/visuals/library-coverage`.
- `app/core/config.py`: `VISUALS_USE_LIBRARY` (default on), `VISUALS_LIBRARY_AUTO_ADD` (default off).

## Paths

- `app/db/migrations/016_shot_library.sql`
- `app/services/visuals/shot_library_service.py`
- `app/api/visuals.py`
- `app/models/visuals.py`
- `app/core/config.py`
- `tests/test_shot_library.py`

## Verification

`tests/test_shot_library.py` (9) and the visuals suites green.
