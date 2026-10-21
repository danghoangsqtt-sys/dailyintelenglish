# Task 55.2 — Layout rules v2: waist-up stage

Status: planned 2026-10-21.

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
