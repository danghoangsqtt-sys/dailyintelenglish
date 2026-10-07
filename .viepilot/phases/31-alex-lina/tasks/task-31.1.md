# Task 31.1: Alex and Lina replace Lan and Minh

## Owner request (2026-10-07)

"Change the two characters, male and female, to ALEX and LINA, Russian nationality, not Vietnamese any more; I made the character pictures
outside (attached)." The owner's sheets: Lina, long dark brown hair, white halter mini dress; Alex, side-swept brown hair with blond
highlights, navy suit, white shirt, black bow tie.

## Plan

- `app/models/visuals.py`: tops `suit jacket`, `mini dress`; bottoms `suit trousers`, `mini dress`; a dress is one garment (the same item
  and colour for top and bottom).
- `app/services/visuals/recipes.py`: `outfit_phrase` (dress as one garment, the suit with its white shirt and black bow tie),
  `negative_for` (a suit is not fought: no "jacket", "blazer" or "multicolored clothes" negatives when a suit is in the picture).
- `app/services/visuals/colour_check.py`: the thighs under a dress are skin, so the bottom colour is not measured for a dress.
- `app/services/visuals/library_service.delete_character` + `shot_library_service.delete_for_character`: a deleted character leaves no
  library pictures behind.
- `scripts/replace_with_alex_lina.py`: cuts the face references (front, turned 45 degrees and mirrored to look right), the smile and
  surprised portraits and the full-body view from the owner's sheets (`docs/operations/phase31-characters/`), creates the characters
  through the library service, moves the cast by gender, deletes Lan and Minh (and their library pictures); backups first.

## Paths

- `app/models/visuals.py`
- `app/services/visuals/recipes.py`
- `app/services/visuals/colour_check.py`
- `app/services/visuals/library_service.py`
- `app/services/visuals/shot_library_service.py`
- `scripts/replace_with_alex_lina.py`
- `tests/test_visuals_alex_lina.py`

## Verification

`tests/test_visuals_alex_lina.py` (outfits, negatives, the real CLIP budgets, the colour check, the delete cascade); a rehearsal of the
script on a copy of the data; a real shot batch with the new characters on the copy; the script applied to the real data (backups
`data/backups/app_before_alex_lina_31_20261007_data.db`).
