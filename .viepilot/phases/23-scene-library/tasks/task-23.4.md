# Task 23.4 — Scene Library UI v2 (doc-first card)

The Scenes tab of `/characters` already lists, creates, edits, deletes and previews scenes
(Task 20.5). This task surfaces the 23.2 fields and makes 16+ scenes browsable.

## Backend

- `GET /api/visuals/scenes` rows gain `used_count` (projects whose scene list contains the
  scene) — one grouped query, no N+1.
- `POST /api/visuals/scenes/{id}/duplicate` → a user scene "<name> copy" (numbered on name
  clash) with the same place/staging/category/time, a new seed, no plate.

## Frontend (`characters.html` / `characters.js`)

- Form: **Category** and **Time of day** selects (options from `/api/visuals/options`).
- Grid: **category filter chips** (All + each category present) above the grid; a card shows
  the plate (or a "No plate yet — generated on first use" placeholder), name, place, a badge
  line `category · time of day · staging`, and "Used in N project(s)".
- Actions per card: Edit, Preview/↻ Plate, **Duplicate**, Delete (user scenes only, unchanged).
- Editing the place or time of day shows "Saving will clear the plate; it is regenerated on
  next use." before saving.

## Tests

API: `used_count`, duplicate (copy naming, fields, no plate). Browser (Playwright, fake engine):
create with category/time → badge text; filter chip hides other categories; duplicate adds a
card; the stale-plate warning appears on place edit.

## Results (2026-10-05)

- Backend: `used_count` via one grouped LEFT JOIN; `POST /scenes/{id}/duplicate` ("<name> copy",
  "copy 2", …); the plate URL carries `?v=<updated_at>` so a regenerated plate is not served from the
  browser cache.
- UI: Category + Time of day selects, category chips with counts, plate or "No plate yet" placeholder,
  `category · time · staging · Used in N projects`, Duplicate, "↻ Plate"/"Make plate", stale-plate
  warning on place/time edits.
- Checked live on the owner's real library (16 cards, 16 plates loaded, chips All 16 / city 1 / food 3 /
  home 2 / nature 3 / school 3 / travel 2 / work 2).
- Tests: +1 API, +1 browser; `test_visuals_library_browser` follows the button rename. The Step 5 browser
  test now disables colour retries (fake solid colours always fail the check, and the job outgrew the
  30 s UI wait). Full suite **1294 passed**.
