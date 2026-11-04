# Task 94.1 — Step frame

See [PLAN.md](../PLAN.md), D143–D146, and `.viepilot/ui-direction/session-2026-11-03-alt/e/step-1.html` ... `step-7.html`.

## Design (written before code)

- `step_nav.js` gets the `stages` variant: Content (1 Config, 2 Script, 3 Learning), Production (4 Audio, 5 Video),
  Publishing (6 Thumbnail, 7 YouTube) as one horizontal bar; done steps show a tick, the current one is marked
  (`aria-current="step"`); links keep `?project_id=`.
- Every step page renders the stage bar at the top of its main pane (above its stage header) instead of the vertical
  list in the left pane; the left pane keeps its summary and notes. `#step-nav` stays (the bar renders into it).
- A sticky bar at the bottom of the main pane: Back (the previous step) and the step's own next action, moved there
  from the page (the button keeps its ID and handler).

## Paths

`frontend/static/js/step_nav.js`, `frontend/pages/step1_config.html` ... `step7_youtube.html`, `frontend/static/css/style.css`

## Verification

Step browser tests pass; a test that each step shows the three stages with the right current step and the sticky bar.
