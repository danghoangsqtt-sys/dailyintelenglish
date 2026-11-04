# Task 94.4 — Lina service

See [PLAN.md](../PLAN.md), D143–D146, and `.viepilot/ui-direction/session-2026-11-03-alt/e/step-1.html` ... `step-7.html`.

## Design (written before code)

- `GET /api/assistant/line?page=&project_id=`: one line from the app's state (D145) -- Home: videos waiting; Step 2: a
  line the AI review changed; Step 4: lines edited after their voice; Step 5: pictures missing; Channel: an empty
  publishing day this week; else none. Rules are pure functions with unit tests.
- `GET /api/assistant/frames/...` adds the three-quarter view (`?view=side`).
- `assistant.js`: on working pages a one-line note with her face (never over the content), a speaker button that reads
  the line with the app's VieNeu voice only when pressed (D146), reduced motion respected.

## Paths

`backend/api/assistant.py`, `backend/content/assistant_lines.py` (new), `frontend/static/js/assistant.js` (new), the pages that show a note

## Verification

Unit tests for the line rules; a browser test that the note appears with a line and nothing when there is none.
