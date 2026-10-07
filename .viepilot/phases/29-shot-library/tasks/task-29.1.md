# Task 29.1: Gaze toward the other person (spike, then the fix in the pipeline)

## Owner feedback (2026-10-07)

"The characters are communicating but only look toward the screen; it is not nice and not natural."

## Cause (read from the code and the pictures)

- `pipelines._contexts` hands every person the character's `face.png`: a **frontal** face looking into the lens. It is
  the IP-Adapter reference of the one-pass render, of the colour retry and of the duo refine, so it pulls every head and
  every gaze to the camera although `geometry.person_pose` turns the skeleton's head keypoints ("right" / "left").
- No prompt says where anyone looks. The three-quarter views of the character sheets (Task 28.2) turn the head only
  15 to 20 degrees and still look at the camera, so they are no better.

## Hypotheses to test (same seeds, the real shot job, a duo and a single)

- **A (today):** frontal reference, no gaze words.
- **B (words):** gaze words in the prompts (duo: "looking at each other"; each person's refine: "looking right" / "looking
  left"; single: "looking to the side"), frontal reference.
- **C (words + turned reference):** B plus a **turned reference** per character: a face turned about 35 degrees and glancing
  sideways, made once in the character sheet generator (`face_turn`), stored as a library asset `face_turned`; the left
  person gets it as is (looks right), the right person a mirrored copy (looks left); a single speaker looks right.

A setting `VISUALS_GAZE` (`off` | `words` | `turned`) switches them so the three can be compared on the real pipeline; the
winner becomes the default.

## Plan

1. `scripts/character_sheet_realvis.py`: a `face_turn` panel (skeleton: nose 0.40, eyes shifted, far ear hidden; prompt "head
   turned to the right, eyes looking sideways at someone off camera"; weak face reference 0.3); 3 seeds per character; the
   owner-visible picks are saved next to the sheets.
2. `recipes.py`: `gaze_words(role, side)`; the duo, refine and single prompts take an optional gaze; budgets re-checked
   with the real tokenizer.
3. `library_service.py` / `pipelines.py`: the optional `face_turned` asset (a script adds it to Lan and Minh; a new
   `pick_reference` also crops it), `_contexts` picks the reference per person and side, a mirrored copy is cached.
4. `config.py`: `VISUALS_GAZE`.
5. Run A, B, C on the data copy for 3 duo shots and 2 singles; sheets; Claude judges (are the eyes toward the partner, is
   the identity still right, are the colour and face checks still passing); the owner sees the sheet.
6. Keep the winner as the default; tests: prompts and budgets, the reference chosen per person and side (fake engine
   records the requests), the mirror, the setting, and a migration-free asset kind.

## Paths

- `scripts/character_sheet_realvis.py`
- `scripts/add_turned_references.py` (new: adds `face_turned` to the library characters, with a backup)
- `app/services/visuals/recipes.py`
- `app/services/visuals/pipelines.py`
- `app/services/visuals/library_service.py`
- `app/core/config.py`
- `tests/test_visuals_gaze.py` (new)
- `docs/operations/phase29-gaze.md` (the report)

## Verification

- Real comparison sheets A / B / C; the winner is looked at on 5 shots; the full suite green.
- The real library is changed only by `add_turned_references.py` after a database backup; the shot runs use the data copy.

## Out of scope

Expression and gesture variants and camera angles (Task 29.3), inserts with a character (Task 29.2).
