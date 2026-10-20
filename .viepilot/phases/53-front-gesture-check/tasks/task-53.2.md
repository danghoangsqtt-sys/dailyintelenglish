# Task 53.2 — Show a refused upload's reason on its card

Status: implemented_verified 2026-10-20.

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

## Verification result 2026-10-20

- `state.slotErrors` keyed by profile/view/slot; single uploads record or clear their slot's reason, batch uploads use `stored[].slot` / `failed[].slot`. The card shows `Not stored: <reason>` (`.slot-refused`, `role="alert"`) under the drop zone; the panel notice is unchanged. Existing `.slot-note .is-error` style reused (no CSS change).
- New browser test `test_a_refused_upload_shows_its_reason_on_the_card`: a 422 shows its reason on the card while it stays Empty; the next successful upload clears it. Profile UI browser suites 11 passed in 46.50 s; `node --check` clean.
