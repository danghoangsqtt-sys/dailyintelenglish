# Task 24.1 — Storyboard data model, validation and API (doc-first card)

## Objective

A project can hold a **storyboard**: an ordered list of beats that covers every script line exactly
once. Each beat is a story moment: a place (a library scene, or a proposed new place), who is on
screen, what they do and how they feel. 24.2 fills it with AI, 24.4 lets the owner edit it, and 24.5
generates images from it. This task stores and validates it, and tells the owner what it will cost in
images (owner E4: default cap 12).

## Paths

- `app/db/migrations/010_storyboard.sql` (new)
- `app/models/storyboard.py` (new)
- `app/services/visuals/storyboard_service.py` (new)
- `app/api/storyboard.py` (new) + `app/main.py` (router registration)
- `app/core/config.py` (`VISUALS_IMAGE_CAP`)
- `tests/test_storyboard_api.py` (new)

## File-Level Plan

- **010_storyboard.sql:**
  - `project_storyboards(project_id PK → projects ON DELETE CASCADE, status draft|approved, source ai|rule|owner, updated_at)`;
  - `project_beats(id PK, project_id → projects CASCADE, position, line_from, line_to, kind scene|insert, scene_id → scenes ON DELETE SET NULL, new_place, speakers_json, action, expression, created_at, updated_at, UNIQUE(project_id, position))`.
- **models/storyboard.py:** `BeatInput`:
  - `line_from`/`line_to` ≥ 0, from ≤ to;
  - `kind`;
  - `scene_id | new_place`: exactly one for a `scene` beat, optional for an `insert`;
  - `new_place` uses the same phrase rule as scene places (≤ 5 words, letters/spaces/hyphens);
  - `speakers` 0–2 distinct indexes;
  - `action` ≤ 8 words, same character rule;
  - `expression` ∈ calm | smile | laugh | surprised | thinking | worried | serious.

  `StoryboardInput(beats ≥ 1, status draft|approved = draft)`.
- **storyboard_service.py:**
  - `get_storyboard(db, project_id)`;
  - `replace_storyboard(db, project_id, body, source)`: validates against the project:
    - beats sorted by `line_from` tile `0..n-1` with no gap/overlap (n = script line count);
    - speakers ⊆ cast speaker indexes;
    - `scene_id`s exist;
    - the image estimate ≤ `VISUALS_IMAGE_CAP`, else 422 with the count.
  - `estimate_images(beats, cast_size)`:
    - per distinct place (scene_id or new_place): the framing set = cast singles + (2 duos if cast ≥ 2);
    - + 1 per additional distinct action in that place;
    - + 1 per insert.

  Returns `{beats, status, source, estimate:{images, cap, gpu_minutes≈images×2}, warnings}`. A warning
  appears when a beat's speakers include someone not speaking in its lines.
- **api/storyboard.py:**
  - `GET /api/projects/{id}/storyboard` (404 project; `{beats: []}` when none);
  - `PUT /api/projects/{id}/storyboard` (source `owner`);
  - `ok()` envelope and existing exceptions, like `api/visuals.py`.
- **config:** `VISUALS_IMAGE_CAP: int = 12`.

## Best practices

Additive migration only; aiosqlite with `read_transaction`/`write_transaction` as in the visuals
services; Pydantic v2 validators; no N+1 queries; deterministic pure `estimate_images` (unit-tested).

## Verification

- `venv\Scripts\python -m pytest -q tests/test_storyboard_api.py` →
  - round-trip;
  - gap/overlap/out-of-range rejected;
  - unknown scene/speaker rejected;
  - cap exceeded rejected with the count;
  - estimate examples;
  - cascade on project delete.
- Full suite green; `ruff check app tests` clean.
