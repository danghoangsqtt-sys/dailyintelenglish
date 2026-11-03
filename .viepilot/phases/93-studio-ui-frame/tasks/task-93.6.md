# Task 93.6 — Videos

See [PLAN.md](../PLAN.md), D138–D142, and the look in `.viepilot/ui-direction/session-2026-11-03-alt/e/`.

## Design (written before code)

- New `frontend/pages/videos.html` (`/videos`): tabs by state with counts, search, filter chips, the table (title, kind,
  CEFR, length; state pill; 7-step strip; SEO; schedule or views; Open), rows stack on phones; a By step board view;
  the project actions of the dashboard grid (open, folder, delete ...) kept in a row menu.

## Paths

`frontend/pages/videos.html`, `frontend/static/js/videos.js` (new, from the dashboard grid code), `backend/main.py`

## Verification

Project list tests moved here; search and tabs filter; delete still asks to confirm.
