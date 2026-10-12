# Task 33.6 — Tiered sprite readiness and renderer compatibility

## Objective

Support the existing 29-picture sprite contract for every profile while allowing seven approved Tier 1 pictures to unlock Talking Starter.

## Paths

- `app/services/visuals/sprite_service.py`
- `app/services/visuals/sprite_plan.py`
- `app/services/video_service.py`
- `frontend/static/js/characters.js`
- `tests/test_character_sprite_tiers.py`
- `tests/test_sprite_service.py`
- `tests/test_sprite_video_props.py`

## File-Level Plan

1. Replace filesystem/name assumptions with character ID, pinned profile version, and current approved slot rows.
2. Define Tier 1 (7), Tier 2 total (15), and Tier 3 total (29) readiness and exact missing-key explanations.
3. Materialize compatibility manifests for the existing renderer and use safe expression/gesture fallback within the pinned tier.
4. Verify old complete Lina/Alex packs still select the same keys and new Tier 1 packs never request unavailable optional sprites.

## Verification

`venv\Scripts\python.exe -m pytest tests/test_character_sprite_tiers.py tests/test_sprite_service.py tests/test_sprite_video_props.py -q`

## Acceptance Criteria

- [ ] Seven approved Tier 1 assets enable Talking Starter.
- [ ] Fifteen and twenty-nine assets upgrade readiness without changing Tier 1 behavior.
- [ ] Missing optional assets use deterministic fallbacks and never crash rendering.
- [ ] Lina/Alex compatibility manifests remain equivalent to their current 29-key sets.

## Amendment A (2026-10-12, D81, D82)

- Placement: with one male and one female in a beat the male takes the left slot and the female the right, whatever the
  speaker order; with the same gender, speaker 1 left, speaker 2 right. Replace the speaker-index slot mapping in
  `video_renderer_remotion.py` with a pure placement function shared by props and tests.
- Facing: a character on the side opposite its `sprite_facing` is mirrored (Remotion `scaleX(-1)` on the sprite box, mouth and
  face regions mirrored with it, gestures included); an approved opposite-facing pack is used instead when present.
- Paths add: `app/services/video_renderer_remotion.py`, `video-renderer/src/Sprites.tsx`, `video-renderer/src/spriteTimeline.ts`,
  `video-renderer/src/spriteTimeline.test.ts`, `tests/test_sprite_video_props.py`.
- Verification adds: female-first project still renders male left; two-male and two-female projects face each other; Alex/Lina
  Demo Episode unchanged (male left, female right already).
