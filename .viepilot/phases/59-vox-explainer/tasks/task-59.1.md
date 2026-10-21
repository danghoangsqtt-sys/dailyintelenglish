# Task 59.1 — Data and contracts

Status: planned 2026-10-22.

## Paths
- backend/db/migrations/031_explainer_style.sql (new)
- backend/schemas/project.py (`explainer_style`), backend/content/project_service.py (columns, copy-settings)
- backend/schemas/explainer.py (VOX visual kinds, Solo/VOX unions, proposal models)
- tests/test_vox_explainer.py (new)

## File-Level Plan
`projects.explainer_style TEXT` ('presenter' for every existing Solo project, NULL for conversations). `ScriptConfig.explainer_style: 'presenter' | 'vox' | None` — only for Solo; default 'presenter'. New visual kinds (plain text, bounded):
- `quote`: `text` (≤ 220), `highlight` (a phrase of the text, ≤ 80), `attribution` (≤ 80).
- `chart`: `chart_type` bar | line, `title`, `unit` (≤ 20), `items` 2–8 of `{label ≤ 40, value number}`.
- `timeline`: `title`, `events` 2–6 of `{when ≤ 30, label ≤ 80}`.
- `map`: `title`, `places` 1–5 of `{name ≤ 60, country ISO-3166 numeric/alpha-3 ≤ 3, lat −90…90, lon −180…180}`, optional `route` (two place indexes), `highlight_countries` ≤ 6 codes.
`SoloVisual` = the four existing kinds; `AnyVisual` = Solo + VOX kinds. Stored segments accept `AnyVisual`; the Solo proposal model/schema keeps `SoloVisual` so Solo prompts and plans are unchanged.

## Tests
Schema bounds; a Solo plan refuses VOX kinds; migration sets 'presenter' on old Solo projects; copy-settings keeps the style.
