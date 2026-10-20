# Task 53.2 — Show a refused upload's reason on its card

Status: planned 2026-10-20.

## Objective

When a slot upload is refused, the card shows why (e.g. "head changed …") instead of silently returning to Empty with the reason only at the top of the panel.

## Paths

- frontend/static/js/character_profiles.js
- frontend/static/css/ (slot note error style only if no existing `.is-error` style applies)
- tests/ (existing character profile browser test module)
- .viepilot/requests/BUG-049.md

## File-Level Plan

- `state.slotErrors` keyed by slot; `assetAction(work, message, slot)` records the error for that slot in its catch before `renderSlots()`, and clears it on success.
- Batch upload: `result.failed[]` entries set their slot's error.
- `slotCard` renders `<p class="slot-note is-error" role="alert">` under the drop zone when the slot has an error; cleared when the profile/view changes.
- Top-of-panel notice stays as is.

## Verification

Browser test: a 422 from the upload endpoint shows its message inside that card; a later successful upload clears it. `node --check`; focused browser tests.
