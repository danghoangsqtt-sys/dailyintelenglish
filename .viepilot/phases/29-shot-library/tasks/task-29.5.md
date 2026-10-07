# Task 29.5: Matcher and the library-first project shot job (ENH-020)

## Plan

- `shot_library_service.find_match`: same scene, framing, ordered characters and action; the expression is the same (calm and
  smile stand in for each other); the gaze setting must agree; a stale or face-changed shot is skipped and marked stale;
  ranked by fewest uses, then least recently used; a shot already used in this episode is excluded.
- `shot_library_service.reuse_for_rows`: copies the approved match into each pending non-insert shot (no GPU), records
  `source = library` and `library_shot_id`.
- `pipelines.project_shots` calls it before `_generate_set`, so only the missing shots are drawn; `shot_regenerate` never
  uses the library (an explicit redraw), and resets `source` to `generated`.
- Optional auto add of a passed shot as `pending` (`VISUALS_LIBRARY_AUTO_ADD`).

## Paths

- `app/services/visuals/shot_library_service.py`
- `app/services/visuals/pipelines.py`
- `app/services/visuals/project_visuals_service.py`
- `tests/test_shot_library.py`

## Verification

Fake-engine tests: nothing drawn when all four shots are approved in the library; only the rejected one drawn; stale shots
not reused; regenerate draws anew; the setting switches it off. A real run on the Demo Episode is done after the batch (29.6).
