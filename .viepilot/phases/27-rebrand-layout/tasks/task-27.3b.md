# Task 27.3b: Character and Scene libraries as large image grids with a detail panel

## Owner decision behind it (brainstorm D61, 2026-10-06)

Canva-style libraries: large image cards, a right-hand detail panel that stays in view. The prototype is
`.viepilot/ui-direction/session-2026-10-06/index.html`. The Music Library keeps its list (Task 27.3a gave it the play
button and the multi-upload); only characters and scenes move to grids here.

## Facts (read from the code, 2026-10-06)

- `characters.html` + `characters.js` hold both tabs. Characters: a narrow list of small round avatars (`#character-list`,
  `.library-card`) and the editor card (`.library-editor`) with the form, the candidates, the sheet and the lock steps.
  Scenes: the scene form first, then the category chips and the card grid (`#scene-grid`, `.library-scene`).
- The character view has `face_url` and `sheet_urls`; the new characters have a full-body sheet picture that makes a
  much better card than a 56 px face.
- Existing browser tests pin only ids and buttons (`#character-list`, `#new-character`, `#scenes-tab`, `#scene-grid`,
  `.library-scene`, its `h3` and `.scene-meta`, the Edit / Duplicate / Plate buttons); no test pins a card's shape.
  So the redesign keeps every id, class and button name.

## Design

- **Characters:** `#character-list` becomes a grid of vertical **tiles** (`.character-tile`, also `.library-card`): a
  3:4 picture (the full-body sheet view, else the face), the name, the status badge and a **swatch per outfit colour**
  (`.library-swatch`, title "white top"). The selected tile has `aria-current="true"` and an accent ring.
  The editor card is the **detail panel** on the right: sticky, scrolls inside itself, with a **hero** (`#character-hero`:
  the face picture, name, status, outfit swatches) above the form. A new character shows no hero.
- **Scenes:** the page is a two-column layout: on the left the chips and a grid of larger cards (the plate, name,
  place, meta, buttons); on the right a sticky **detail panel** with the selected scene's big plate
  (`#scene-detail-plate`), its name, place and meta, and below it the existing scene form. A click on a card (not on one
  of its buttons) selects it (`aria-current`); Edit still fills the form.
- Narrow screens (below 900 px): one column; the detail panel follows the grid and is not sticky.
- Colour names map to CSS colours in one table; an unknown name falls back to a grey swatch.

## Paths

- `app/services/visuals/library_service.py`
- `frontend/pages/characters.html`
- `frontend/static/js/characters.js`
- `tests/test_library_grid_browser.py` (new)
- `tests/test_visuals_library_api.py`

## File-Level Plan

1. **API:** the character view gets `body_url` (the `full_body` sheet view, or null); a test in
   `test_visuals_library_api.py` checks it.
2. **JS:** `renderCharacterList` builds the tiles; a new `renderCharacterHero` fills `#character-hero`;
   `renderScenes` marks and selects cards and fills `#scene-detail` (new `state.selectedSceneId`,
   `renderSceneDetail`).
3. **HTML/CSS:** the two-column layouts, the tile and card styles, the sticky panels, the hero, the swatches, the
   responsive rules; dark mode uses the existing tokens.
4. **Tests** (`tests/test_library_grid_browser.py`): at 1400 px the character tiles are portrait pictures at least
   140 px wide, each with one swatch per outfit colour and the right title; the detail panel is right of the list and
   sticky; a click selects a tile and the hero shows its face and name; at 700 px the layout is one column; on the
   scenes tab the detail panel is right of the grid, a click on a card selects it and shows its plate (a plate is made
   with the fake engine) and place, and Edit still fills the form.

## Verification

- New tests and the existing library browser tests green, then the full suite.
- Screenshots (light and dark) of both tabs with the real new characters and plates on a throw-away copy of the data;
  looked at, then sent to the owner.

## Out of scope

The music list as a grid, the studio frame (27.4), drag and drop of characters.

## Implementation notes (2026-10-06)

- Done as planned: `body_url` in the character view; portrait tiles (full-body picture, name, status, an outfit swatch per
  garment) and a hero in the sticky detail panel; the scenes tab is a grid of larger cards with a sticky side panel (the
  selected scene's big plate, place and meta, with the form below it); selecting a card (not its buttons) updates the
  panel, and Edit selects too. Below 900 px everything stacks.
- Found with the real data: the empty progress strip left a 64 px gap under the page heading (now hidden when empty).
- Tests: `tests/test_library_grid_browser.py` (3), one API test; the 6 existing library browser tests pass unchanged.
- Screenshots with Lan, Minh and the 55 new plates, light and dark: `docs/operations/ui-audit/library-*.png`.
