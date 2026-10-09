# Task 32.6c — Matching and coverage

## Objective

Select approved activity images deterministically for storyboard insert beats and expose matched/missing coverage in Step 5 before render.

## Paths

- `app/services/visuals/activity_matcher.py` — pure normalization, scoring and stable tie-breaking.
- `app/services/visuals/activity_library_service.py` — approved candidate query and render-use recording integration.
- `app/services/video_renderer_remotion.py` — activity coverage and render-prop selection integration.
- `app/api/visuals.py` — project activity-coverage endpoint.
- `frontend/static/js/api.js` — coverage request.
- `frontend/pages/step5_video.html` — coverage summary container.
- `frontend/static/js/step5_video.js` — display matched/generic/sprite-fallback/missing results.
- `tests/test_activity_matcher.py` — scoring and coverage tests.
- `tests/test_activity_coverage_browser.py` — Step 5 coverage browser test.

## File-Level Plan

1. Score canonical activity/alias phrases against insert action and dialogue text; optional context contributes only after activity qualification.
2. Rank exact character-specific candidate first, then generic candidate; exclude other-character assets entirely. Require the documented threshold; never use a weak semantic match.
3. Rotate ties by least recent/least used and ID, returning rationale, score and selected asset. Missing/invalid candidates yield `missing`, not an error.
4. Coverage reports every insert as character match, generic match or missing; missing renders retain the existing sprite scene and do not block rendering.

## Verification

`venv\Scripts\python.exe -m pytest tests/test_activity_matcher.py tests/test_activity_coverage_browser.py -q`

## Acceptance Criteria

- [x] Character-specific > generic > existing sprites fallback.
- [x] No asset for another named character can match.
- [x] Step 5 reports coverage before render and explains missing items.

## Result — 2026-10-09

- Matching is deterministic and explainable: canonical activity/aliases qualify a candidate,
  context raises its score, character scope outranks generic, another character is excluded,
  and equal variants rotate by use count, oldest use and stable ID.
- The project coverage API returns per-beat `character`, `generic` or `missing` status plus
  aggregate counts. Every missing action explicitly declares `sprites` as its safe fallback.
- Step 5 shows character/generic totals and names each missing action before render.
- A successful Remotion render returns its selected activity IDs; the video route records their
  beat and final video-job ID inside the same transaction that publishes the successful job.
  Preview, coverage, and failed/fallback renders do not increment usage.
- Verification: required matcher/browser gate 9 passed; broader Activity Library, sprite-props
  and video-API regression gate 45 passed; targeted Ruff and `git diff --check` passed.
