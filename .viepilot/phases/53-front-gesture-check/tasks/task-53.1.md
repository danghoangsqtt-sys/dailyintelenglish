# Task 53.1 — Gesture head check compares the real head

Status: planned 2026-10-20.

## Objective

A front gesture whose hand is raised beside the shoulder or face (count-1/2/3, think, wave) passes when the head itself is unchanged; a redrawn or moved head is still refused.

## Paths

- backend/library/sprite_service.py
- tests/test_sprite_service.py (or the existing measure test module)
- .viepilot/requests/BUG-049.md

## File-Level Plan

- Add `HEAD_KEPT = 0.75` and `head_kept(rgba, reference)`: share of reference pixels inside the head zone (reference alpha, rows above `head_end`) that are still opaque (>200) with mean colour difference < 25.
- `measure(..., gesture=True)`:
  - replace `head differs {xor}%` (silhouette XOR, counts a new hand as head change) with `head changed (only N% of it is unchanged; a gesture may change the arms only)` when `head_kept < HEAD_KEPT`;
  - compute head top and head centre only inside the reference head's column span and silhouette, so a hand beside the head does not move them;
  - keep `body_kept` and canvas-edge checks unchanged.
- Non-gesture pictures (calm__open, blink) keep the current silhouette rules.
- Return `head_kept` in the measures dict for the slot note.

## Verification

Unit tests: raised hand beside the head passes; another identity's head fails; head shifted sideways fails; existing measure tests pass. Replay the calibration script: all 15 approved pictures still pass. Focused + full pytest.
