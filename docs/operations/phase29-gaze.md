# Phase 29, Task 29.1: gaze toward the other person (ENH-020)

Date: 2026-10-07. Owner feedback on the Gate B-20 episode: "the characters talk but only look at the screen, it is not natural".

## Cause

The IP-Adapter face reference of both people is a frontal portrait, and the prompts never said where to look: the model copies the
reference gaze, so everyone stares into the lens.

## Three variants, the same 12 shots of the Gate B-20 demo (data copy, same seeds and plan)

| Variant | `VISUALS_GAZE` | What changes |
|---|---|---|
| A baseline | `off` | nothing (Gate B-20 as sent) |
| B words | `words` | gaze words in the prompts ("looking at her", "looking to the left"...) and a turned head skeleton for single shots |
| C turned references | `turned` | B plus a second face reference per person, turned about 30 degrees toward the other one (`face_turned` library asset, mirrored for the person on the right) |

Comparison sheets (9 person shots, inserts left out): `docs/operations/phase29-gaze-compare-1.png`, `phase29-gaze-compare-2.png`.

## Result (judged on the sheets)

- **A:** both look at the lens in every shot; shot 10 has a broken head.
- **B:** the gaze moves only in some shots; it also drew a stranger beside Minh (shot 6) and a giant face (shot 12).
- **C:** in the duo shots (4, 6, 8, 10, 12 and the close shot 3) the two look at each other or off to the side; the single shots look past the lens in a natural shot / reverse shot way. No broken head and no third person in the nine shots. Identity holds (long hair and white blouse for Lan, black tousled hair for Minh), though Minh's face is a little broader than in A.
- **Colour:** Minh's top is wrong in shots 1 (navy), 9 (white) and 12 (white shirt with a black vest). The review marks flagged 1 and 9; shot 12 passed unflagged (a known weakness of the colour check, same family as the lit-black false alarm). A also had this error rate, so C is not worse.

## Decision

**C is the default now** (`VISUALS_GAZE = "turned"`). A character without a `face_turned` asset keeps its front face, so nothing breaks for new characters; the old behaviour is `DIE_VISUALS_GAZE=off`.

The real library got the turned faces with `scripts/add_turned_references.py` (database backup `data/backups/app_before_turned_faces_29_1_20261007.db`). Lan: woman seed 7, Minh: man seed 21 (`docs/operations/phase28-characters/*_face_turn.png`).

## Not done here

Outfit swaps in duo shots stay the main weakness (about one shot in three on the first pass, caught by the review marks and the retry); the answer is the shot library of Task 29.4 onward (generate once, review once, reuse).
