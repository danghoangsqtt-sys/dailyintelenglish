# Task 56.3 — Dashboard "Start here"

Status: planned 2026-10-21.

## Paths
- backend/channel/dashboard_service.py (`start`), frontend/pages/dashboard.html, frontend/static/js/dashboard_channel.js, frontend/static/css/style.css
- tests/test_dashboard_api.py, tests/test_dashboard_cockpit_browser.py

## File-Level Plan
API `start`: `continue` = the most recently updated project whose video is not finished through YouTube, with its next step label and link; `next_episode` = the first planned episode without a project (by date, then plan order) with a link to its series on `/channel`; each null when absent. Page: a "Start here" section above the existing ones with three cards (Continue · Next planned episode · New video → the existing New project action) and the 7-step path (Config → Script → Learning → Audio → Video → Thumbnail → YouTube). Empty cases say what to do (e.g. "No channel plan yet — plan the channel").

## Tests
API: start block for an empty DB, an unfinished project, a planned episode. Browser: the three cards render and link correctly.
