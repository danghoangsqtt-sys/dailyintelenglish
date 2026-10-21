# Task 56.4 — Step bar

Status: planned 2026-10-21.

## Paths
- backend/channel/dashboard_service.py (`project_progress`), backend/api/projects.py (`GET /{id}/progress`)
- frontend/static/js/step_guide.js (new), frontend/pages/step1..7 (script tag), frontend/static/css/style.css
- tests/test_step_guide.py (new, API + browser)

## File-Level Plan
Progress = the dashboard's step checks for one project (script, learning, audio, video, thumbnail, youtube; config is done once the project exists) with a short "to finish" hint per step. `StepGuide` adds a sticky bar at the bottom of the step's stage: "✓ <step> done" or "To finish this step: …", and "Next: Step N — <label> →" (on Step 7: back to the Dashboard). It refreshes on window focus and every 15 s while the page is visible, so it follows the page's own saves without touching the step scripts. Step 1 without a project shows no bar.

## Tests
API: progress for a new project and one with a script. Browser: Step 2 of a project with a script shows done + a next link to Step 3; without a script it shows the hint.
