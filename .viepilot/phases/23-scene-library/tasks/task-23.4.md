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
