# Task 55.2 — Layout rules v2: waist-up stage

Status: implemented_verified 2026-10-21.

## Paths
- frontend/static/explainer-layout-rules.json
- backend/library/explainer_layout_service.py
- backend/schemas/explainer.py (placement ranges)
- renderer/src/explainerLayout.ts (+ test)
- tests/test_explainer_layout.py

## File-Level Plan
- Rules `version: 2`: per aspect `stage` (head top, figure scale range as a multiple of frame height so the waist meets the bottom edge, anchors); card panels opposite the presenter; caption/header unchanged in 16:9; 9:16 follows the conversation vertical zones (scene/card area on top, captions, presenter below).
- `measure_front`: add a `core` alpha (calm/blink poses: head and torso) next to the union.
- Proof: panel inside safe, outside caption/header and outside the presenter's core box (hands may cross); presenter head top inside safe; motion envelope rule kept. Placement ranges widened (height up to the stage maximum, feet line may exceed 1).
- `arrange`: alternate left/right by segment at the stage scale; activity segments need no panel (presenter over the full-frame insert).

## Verification
Python and TS proof tests for both aspects; v1 layouts reported outdated.

## Verification result 2026-10-21

- Rules `version: 2` with per-aspect `stage` (16:9: head top 0.155, figure 2.05× frame height, range 1.5–2.6, right side; 9:16: head top 0.545, 1.08×, 0.85–1.3, centre) and panels opposite the presenter; 9:16 caption moved between the card area and the presenter as in the conversation vertical video. `EXPLAINER_LAYOUT_RULES_VERSION = 2`; placement `y` ≤ 4 and `height` ≤ 3 in the schema.
- `measure_front` adds a `core` alpha from calm/blink poses. Proof: card inside safe, outside caption/header and outside the presenter's core (clipped to the frame); head box (`headFraction` 0.12) inside safe and below the brand line; activity visuals have no card. `arrange` keeps one stage side and tries smaller sizes before switching side.
- Real Lina pack (read-only): default 16:9 and 9:16 card/activity layouts prove; 16:9 torso spans x 0.544–0.889, card x 0.04–0.53.
- Tests: 2 new stage tests (defaults fit both aspects; card over torso, head under brand, rules v1, small size refused); explainer layout/API/plan/project suites pass; Ruff clean.
