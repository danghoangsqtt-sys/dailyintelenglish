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

## Amendment A (2026-10-12, D79)

- **Quick create** is the first and only required screen: name, gender, accent/nationality, appearance, outfit. Saving it
  creates the profile, picks the Edge TTS voice from gender + accent and opens the prompt pack.
- The former steps for personality, role, speaking style and detailed voice stay available as optional, resumable sections;
  they no longer block video readiness.

## Implementation Notes (2026-10-12, before coding; D79, D84, D86)

- `/characters` gets a first, default **Profiles** tab (new `frontend/static/js/character_profiles.js`); the existing local
  generation tab (renamed "Generate locally") and the Scenes tab stay as they are. Tab switching becomes one function for the
  three tabs in `characters.js`.
- Left column: search, Active/Archived filter, **New character**, and one card per profile (picture, name, gender, badges
  "Video ready", "Talking ready", "n/29 pictures").
- Right panel, one page scroll: **Quick create** (name, gender, accent, nationality, appearance, outfit — the only required
  screen) or the selected profile: header (voice, facing), Duplicate / Archive-Restore / Delete, readiness with every
  missing item, **Details (optional)** fields autosaved on change with a visible Saving/Saved/Failed state.
- The picture slots of 33.5 sit in the same panel under the profile (the owner's flow: create, then fill slots).
