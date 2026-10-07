# PHASE-STATE — Phase 29: Ready-made shot library of Lan and Minh (ENH-020)

- **Status:** planned 2026-10-07 (owner request). **Plan:** `docs/implementation/phase-29-shot-library.md`.
- **Started 2026-10-07:** the owner reviewed the Gate B-20 episode (cuts too ghosty, both people stare at the camera, inserts should show a character) and asked to continue with this phase to fix what was discussed.

| Task | Description | Status |
|---|---|---|
| 29.0 | Cleaner cuts: near-hard cuts between shots (owner feedback 2026-10-07) | done 2026-10-07 (vitest 47, real render checked) |
| 29.1 | Gaze toward the other person (spike, then the fix in the pipeline) | done 2026-10-07 (variant C `turned` is the default; `docs/operations/phase29-gaze.md`) |
| 29.2 | Inserts with a character | done 2026-10-07 (`docs/operations/phase29-inserts.md`) |
| 29.3 | Library vocabulary spike (variants, gestures, camera angles) | planned |
| 29.4 | Data model and service (shot_library, review state) | done 2026-10-07 (`tasks/task-29.4.md`, tests/test_shot_library.py) |
| 29.5 | Matcher and the library-first shot job | done 2026-10-07 (`tasks/task-29.5.md`, tests/test_shot_library.py) |
| 29.6 | Resumable batch generator for the core set | planned |
| 29.7 | Shot Library UI, "from library" / "Add to library", coverage view | done 2026-10-07 (`tasks/task-29.7.md`, tests/test_shot_library_browser.py) |
| 29.8 | Gate B-21 (owner times an episode against generating everything) | planned |
