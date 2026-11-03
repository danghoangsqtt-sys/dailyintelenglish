# Task 93.3 — Today

See [PLAN.md](../PLAN.md), D138–D142, and the look in `.viepilot/ui-direction/session-2026-11-03-alt/e/`.

## Design (written before code)

- `dashboard.html` becomes Home: page head (title, date, the channel's fixed slots), Lina's band (summary of what waits,
  Review N videos, the next-topic box that opens Create with the topic), Waiting for you (rows from the automation
  review list and projects that need a fix, with their actions), In progress (running jobs with the 7-step strip),
  This week (the channel schedule as an agenda). The project grid and its controls move to Videos (93.6); the cockpit
  numbers go (each number once). IDs used by tests are kept where the element stays.
- Lina's band uses her front frames (`calm__closed`, `blink`, `gesture-wave`) from a small route that crops them from
  the library sprites (the Phase 94 service starts here).

## Paths

`frontend/pages/dashboard.html`, `frontend/static/js/dashboard.js`, `frontend/static/js/dashboard_channel.js`, `frontend/static/css/style.css`, `backend/api/assistant.py` (new, frames only)

## Verification

Dashboard browser tests updated; the band, rows and agenda render from mocked APIs; no sideways scroll at 375 px.
