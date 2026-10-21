# Task 55.4 — Media bridge and Step 5 editor

Status: implemented_verified 2026-10-21.

## Paths
- backend/library/explainer_media.py
- backend/api/explainer.py (scene/activity choice lists if needed)
- frontend/static/js/explainer_editor.js
- tests (explainer media/API, editor browser)

## File-Level Plan
- Preview: scoped URLs for plates/activities; production: copy pinned plates/activities with hash check into the render folder; record `activity_library_usage` for rendered activities.
- Editor: per-segment scene select and visual kind `activity` with an activity select; presenter height inputs use the v2 range from the rules file.

## Verification
Media/props tests, editor browser test, full pytest.

## Verification result 2026-10-21

- `explainer_media`: stage files hashed out of lock; approved renders refuse a changed plate/activity (`verify_unchanged`); preview gives `/api/visuals/scenes/{id}/preview` and `/api/visuals/library/activities/{id}/content`; production copies them with hash checks into the render folder and returns private `_activityUses` (one per activity segment), which the renderer pops before writing props so the video API records `activity_library_usage`.
- `GET /api/projects/{id}/explainer-plan/stage-choices`; `Api.getExplainerStageChoices`.
- Editor: scene select per segment, visual kind `activity` with an activity select (own pictures marked), presenter height input range read from `/static/explainer-layout-rules.json`.
- Tests: stage pin/stage/record/tamper test; editor picker browser test; Solo props 5 passed, editor browser 5 passed; `node --check`, Ruff clean.
