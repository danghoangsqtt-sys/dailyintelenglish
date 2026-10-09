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

- [ ] Character-specific > generic > existing sprites fallback.
- [ ] No asset for another named character can match.
- [ ] Step 5 reports coverage before render and explains missing items.
