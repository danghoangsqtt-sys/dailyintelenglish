# Task 28.5: Shot checks that work on photographs (faces) and a "check this shot" mark in Step 5

## Owner decisions (2026-10-06)

1. **Approved the download** of a small face-detection model to count the people in a shot.
2. **Approved marking** a shot that still fails its checks after the retries, in Step 5, so the owner can regenerate it
   (instead of silently accepting it, or rendering two candidates).

## Evidence (Task 28.4b report)

- The "extra person" check cuts the picture out with an anime model: on photographs it said 0.0 on a market full of
  vendors and let a three-person duo through (shot 12).
- A shot that still has the wrong garment colour after 2 retries is accepted with no sign to the user.
- Probe with the candidate model (`ultraface-rfb-320.onnx`, via the onnxruntime already in `venv-image`): singles 1
  face, duos 2, inserts 0, the fixed shot 12 = 2, and **3 on the original three-person shot 12**.

## The model

- UltraFace "version-RFB-320" (`Linzaer/Ultra-Light-Fast-Generic-Face-Detector-1MB`), **MIT licence**, 1,270,727 bytes,
  SHA-256 `34cd7e60aeff28744c657de7a3dc64e872d506741de66987f3426f2b79f88017`, pinned to commit
  `0f9ca4a9fc80170fd505168fd1132b837141f7df`. Stored at `models/image/face/ultraface-rfb-320.onnx` (already
  downloaded by the owner's approval, verified by hash). Input 320 x 240, `(pixel - 127) / 128`, outputs `scores`
  (softmax, column 1 = face) and `boxes` (normalised corners); the worker adds the confidence cut and the NMS.

## Plan

### Part A: count faces instead of the anime cut-out

1. **Worker** (`scripts/image_worker.py`): a `count_faces` command (`input_path`, optional `threshold` 0.7 and
   `iou` 0.3) returning `{"faces": n, "boxes": [[x1, y1, x2, y2, score], ...]}` in pixels. It loads the model once,
   downloads it if the file is missing (URL pinned to the commit, size and SHA-256 checked, an error with the reason if
   it fails), and runs on the CPU provider.
2. **Fake engine** (`engine.py`): `count_faces` answers `expected_faces` from the request, so the tests run without a
   GPU.
3. **Pipeline** (`pipelines.py`): `_extra_person_pass` is rewritten: after the first render it counts the faces; more
   faces than the people in the shot (`len(context["people"])`) is an extra person, so it re-renders with a new seed
   (same step as today, at most `VISUALS_EXTRA_PERSON_RETRIES`) and keeps the render with the fewest extra faces. It
   now runs for singles too. The report `extra_person_check.json` lists the faces of each try. A final face count of
   `final.png` (after the refine and the hand repair) feeds the review note.
4. **Cleanup:** the cut-out code (`shot_checks.head_gap_box`, `gap_occupancy`, `_gap_score`, the 0.5 threshold and their
   tests) is removed; `shot_checks.py` becomes the small pure helpers for the face rule (`extra_faces(count, people)`).
   `scripts/smoke_ai_visuals.py` keeps reading the report name.

### Part B: the "check this shot" mark

1. **Migration `015_shot_review.sql`:** `ALTER TABLE project_shots ADD COLUMN review_note TEXT` (NULL = nothing to
   check).
2. **Pipeline:** `_colour_pass` also returns the notes of people whose garment still fails after the retries ("Minh's
   shirt is not black"); the final face count adds "3 faces found for 2 people". The shot's final update writes the
   joined note (or NULL), and starting a (re)generation clears it.
3. **API:** the shot view already returns every column; `review_note` is included (checked by a test).
4. **Step 5** (`step5_video.js` and its CSS): a shot with a note gets an amber "Check this shot: <note>" line and the
   Regenerate button becomes the primary button; a shot without one is unchanged. The text says what to do ("Press
   Regenerate to try again").

## Paths

- `scripts/image_worker.py`
- `app/services/visuals/engine.py`
- `app/services/visuals/pipelines.py`
- `app/services/visuals/shot_checks.py`
- `app/db/migrations/015_shot_review.sql` (new)
- `frontend/static/js/step5_video.js`
- `frontend/pages/step5_video.html`
- `tests/test_visuals_colour_check.py`
- `tests/test_visuals_phase28.py`
- `tests/test_shot_faces.py` (new)
- `tests/test_shot_review_browser.py` (new)
- `tests/fixtures/` (new: two small face images for the real-model test)
- `docs/operations/phase28-shots-real-pipeline.md`

## Tests

- **Real model** (`tests/test_shot_faces.py`, skipped when the model file is absent): the worker's face function counts
  0 on a blank image, 1 on a single portrait, 2 on two portraits side by side, and 3 on the original three-person shot
  (a 560 x 315 crop of the saved contact sheet, kept as a fixture); the hash of the model file matches the pinned one.
- **Pipeline with the fake engine:** a duo whose first render has 3 faces is re-rendered and the render with the fewest
  extra faces is kept; a duo that still has 3 faces after the retries gets a review note; a clean duo and a single
  get none; a colour failure that survives the retries gets "<name>'s shirt is not black"; regenerating clears the note.
- **Migration and API:** the column exists, an existing shot row reads `review_note = null`.
- **Browser (Step 5, mocked API):** a shot with a note shows the amber line and a primary Regenerate button; one
  without does not.
- The old anime-cut-out tests are replaced by these; all other visuals tests stay green.

## Verification

- New and affected tests green, then the full suite.
- Real run on the throw-away copy of the data (second app instance): regenerate shot 12 and one clean duo: the face
  report and the note behave as expected, and a screenshot of Step 5 with a flagged shot is looked at.

## Out of scope

Trouser colour in seated duos (the legs are hidden by the table) and the choice of a better outfit-lock prompt for
the swapped-outfit case.

## Implementation notes (2026-10-06)

- Done as planned (A and B). The worker prints to stderr (stdout is its protocol channel), so the real-model test
  reads both streams. The wording of a colour note is "may not be <colour>" because the heuristic can be wrong.
- Real run on the data copy: see `docs/operations/phase28-shots-real-pipeline.md` (Task 28.5 section). It found and
  fixed a false alarm of the black rule from the data.
- Tests: `tests/test_shot_faces.py` (9, with the real model), `tests/test_shot_review_browser.py` (1), the black
  sample in `tests/test_visuals_phase28.py`; the two old cut-out tests were removed.

## Task 28.5 closed (2026-10-06)

Full suite: **1506 passed** (1498 + 8 new net: +11 new, 2 old cut-out tests removed, +1 sample).
