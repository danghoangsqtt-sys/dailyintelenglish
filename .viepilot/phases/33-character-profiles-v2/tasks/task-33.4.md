# Task 33.4 — Character Library and creation wizard

## Objective

Replace the long create/edit form with a clear ten-step, game-like wizard and upgrade the Character Library to show reusable profile details and progress.

## Paths

- `frontend/pages/characters.html`
- `frontend/static/js/characters.js`
- `frontend/static/js/api.js`
- `frontend/static/css/style.css`
- `tests/test_character_profiles_browser.py`

## File-Level Plan

1. Add search, lifecycle/readiness filters, profile cards, and a large selected-profile panel based on the approved library UI direction.
2. Build Steps 0–10 with one purpose per screen, fixed progress, a large live preview, Back/Continue, Skip for optional tiers, and Resume setup.
3. Autosave changed fields with visible saving/saved/failed states and retry without discarding local edits.
4. Use one page scroll, readable text, responsive stacked layout, keyboard focus management, and sticky primary actions at narrow widths.

## Verification

`venv\Scripts\python.exe -m pytest tests/test_character_profiles_browser.py -q`

## Acceptance Criteria

- [ ] The user never needs to fill the complete profile on one screen.
- [ ] Refreshing after each required step resumes at the saved step with entered data.
- [ ] Readiness and missing actions are visible from both card and detail views.
- [ ] The page remains usable at 1024 px wide without nested form scrolling or tiny labels.

## Implementation Notes

- Keep the existing Scenes tab and legacy local image generation workflow available while replacing the character create/edit form.
- Use the Phase 33 profile API for search, lifecycle filters, duplicate, archive, restore, and persisted `wizard_step` progress.
- Treat Steps 1–4 as profile setup, Steps 5–10 as guided asset/readiness checkpoints; optional sprite tiers may be skipped.
- Autosave only changed fields, retain unsaved form values after a failed request, and expose a visible retry action.
- Keep the wizard in the page flow at 1024 px and below so the document owns scrolling; avoid scrollable form panes.

