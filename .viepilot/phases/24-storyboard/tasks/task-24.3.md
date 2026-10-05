# Task 24.3 — Recipes v3: action + expression in shot prompts, pose library (doc-first card)

## Objective

A beat's `action` and `expression` (24.1/24.2) must show in its pictures. This task gives the image
recipes action and expression slots within CLIP's 77-token budget, and maps actions to OpenPose
arm/leg poses, so "drinking coffee" is drawn with a cup at the mouth and "pointing at a map" with
an extended arm. It is pure recipe/geometry work, verified on the GPU with a contact sheet;
wiring it into shot generation is 24.5.

## Paths

- `app/services/visuals/geometry.py` (action poses)
- `app/services/visuals/recipes.py` (beat prompts, expression words, token-budget guard)
- `scripts/spike_beat_poses.py` (new; GPU evidence, not shipped)
- `tests/test_visuals_beat_recipes.py` (new)

## File-Level Plan

- **geometry.py:**
  - `ACTION_CATEGORIES` = talk, point, drink, phone, think, wave, work, walk;
  - `action_category(action)`: keyword match in a fixed order, default `talk`;
  - `ACTION_POSES[category]`: elbow/wrist offsets for the near arm in head units (front-facing
    right arm). `work` adds the other arm; `walk` adds stride legs.
  - `beat_people(kind, staging, size, categories)` builds the existing `shot_people` geometry and
    replaces the gesturing arm with the category pose:
    - single → the right arm;
    - duo left person (faces right) → the mirrored left arm, toward the partner;
    - duo right person → the right arm, toward the partner.

    Legs only where the kind already draws legs (wide standing).
- **recipes.py:**
  - `EXPRESSION_WORDS` (calm → "calm friendly face", smile → "warm smile", laugh → "laughing
    happily", surprised → "surprised face", thinking → "thoughtful look", worried → "worried
    look", serious → "serious expression");
  - `compact_phrase(character)` (no role, no eye colour: the face IP carries identity);
  - `beat_single_prompt` / `beat_duo_prompt(..., action, expression)` with the order: style,
    person(s), framing, expression, action, place;
  - `fit_budget` trims the action's last words while the estimate exceeds 72 (the calibrated
    real-77 limit, 23.3), then drops the place (the 23.2 plate already carries it).
- **spike_beat_poses.py:**
  - the real worker pipeline (L1 encode with face + scene plate, L2 ControlNet render; no repair);
  - Lan singles × {talk, point, drink, phone, think, wave, work} with matching expressions;
  - two duo beats in the real Cafe plate;
  - contact sheet `docs/operations/phase24-t3-beat-poses.png`.

## Best practices

Pure functions with unit tests; no change to the existing `shot_people` / recipes used by today's
shot set (backward compatible); budget measured, not guessed.

## Verification

`tests/test_visuals_beat_recipes.py`:
- category matching (real AI actions from 24.2: "drinking coffee in a local cafe" → drink,
  "looking at a laptop screen together" → work, "pointing at a city map" → point, "walking through
  a green park" → walk, "talking earnestly" → talk);
- poses inside the frame for every kind × staging × category;
- budget: every built-in place × expression × the longest character × an 8-word action ≤ 72
  estimated, with the place kept where it fits.

GPU sheet reviewed: poses read as the actions. Full suite green; ruff clean.
