# Task 93.2 — One rail and redirects

See [PLAN.md](../PLAN.md), D138–D142, and the look in `.viepilot/ui-direction/session-2026-11-03-alt/e/`.

## Design (written before code)

- `app_sidebar.js` draws the rail from one list into the empty `<aside id="app-sidebar">`: brand, Create video (primary),
  Today (count of videos waiting), Channel, Videos, Library, then Settings at the bottom; `aria-current` from the path
  (`/automation`, `/channel` -> Channel; `/videos`, `/step*` -> Videos; `/library`, `/characters`, `/activities`, `/music` ->
  Library; `/create`, `/shorts-batch` -> Create video). Collapse to icons stays (remembered); under 860 px the rail
  becomes a bottom tab bar (the drawer and its opener go).
- Every page's sidebar markup becomes `<aside id="app-sidebar" class="app-sidebar" aria-label="App navigation"></aside>`.
- `backend/main.py`: new routes `/create`, `/videos`, `/library`; `/automation` -> `/channel#auto`, `/shorts-batch` ->
  `/create#batch`, `/characters` -> `/library#characters`, `/activities` -> `/library#scenes`, `/music` -> `/library#music`
  once their content has moved (93.4-93.7).

## Paths

`frontend/static/js/app_sidebar.js`, `frontend/pages/*.html`, `frontend/static/css/style.css`, `backend/main.py`

## Verification

`tests/test_app_sidebar_browser.py` rewritten for the new links, tab bar and collapse; a redirect test.
