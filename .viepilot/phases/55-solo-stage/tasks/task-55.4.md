# Task 55.4 — Media bridge and Step 5 editor

Status: planned 2026-10-21.

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
