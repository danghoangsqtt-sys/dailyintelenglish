# Task 29.6: Resumable batch generator for the core set (ENH-020)

## Plan

- `scripts/build_shot_library.py` (HTTP, the app owns the GPU queue): per scene of a plan a throw-away builder project with the
  cast, the normal shot job draws the framing set (a single of each person, a duo close, a duo wide), every picture without a
  check note is copied to the library as `pending`; the builder project is deleted at the end.
- Resumable: a scene that already holds a full set for this cast is skipped; `--max-minutes` stops starting new scenes
  and the same command carries on later. A Markdown coverage report is written.
- Default plan v1 (the plan's proposed scenes): Cafe, Classroom, Library, Park, Office, Living room, City street, Kitchen.
  The four open owner questions (GPU hours, scenes first, gesture list, repetition) were not answered, so the plan stays at this
  proposal and one framing set per scene; expression variants wait for the Task 29.3 spike.

## Paths

- `scripts/build_shot_library.py`
- `tests/test_build_shot_library.py`
- `docs/operations/phase29-library-batch.md` (the real run)

## Verification

Tests (fake engine, real app over HTTP): the library fills scene by scene, the builder project is removed, a second run skips
complete scenes, a time budget stops cleanly. Real run on the real data (after a database backup): 27 pictures in 8 scenes in
about 55 minutes of GPU; 5 pictures with a check note were left out; sheets `docs/operations/phase29-library-batch-1.png`
and `-2.png`.
