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

- [x] Seven approved Tier 1 assets enable Talking Starter.
- [x] Fifteen and twenty-nine assets upgrade readiness without changing Tier 1 behavior.
- [x] Missing optional assets use deterministic fallbacks and never crash rendering.
- [x] Lina/Alex compatibility manifests remain equivalent to their current 29-key sets.

## Implementation Notes

- Resolve approved database slots by character ID and pinned identity/profile version before falling back to the legacy filesystem manifest.
- Materialize a renderer-compatible manifest at the render boundary; do not change the Remotion prop contract.
- Tier 1 fallbacks must be deterministic and remain within the seven approved keys.
- Keep full Lina/Alex legacy manifests byte-for-byte addressable and verify their 29 canonical names are unchanged.

## Completion Evidence

- Renderer resolution now reads approved database sprite slots by character ID and pinned profile version, then falls back to the legacy manifest when no DB set exists.
- Historical stale assets remain renderable for an already pinned project after a new identity version starts.
- Tier 1 plans request only calm/smile/surprised/blink states and deterministically omit unavailable gestures or downgrade optional expressions.
- Tier/legacy/renderer regression: 16 passed; Ruff and diff checks pass.

