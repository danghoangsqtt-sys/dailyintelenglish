# Task 93.7 — Library

See [PLAN.md](../PLAN.md), D138–D142, and the look in `.viepilot/ui-direction/session-2026-11-03-alt/e/`.

## Design (written before code)

- New `frontend/pages/library.html` (`/library`) with tabs: Characters (the characters page), Scenes and pictures (the
  activity and scene library), Voices (voice catalogue with play), Music (music library), Brand (brand box from
  Settings). Each tab keeps its IDs and script; `#characters`, `#scenes`, `#voices`, `#music`, `#brand`.

## Paths

`frontend/pages/library.html`, `frontend/pages/characters.html`, `frontend/pages/shot_library.html`, `frontend/pages/music_library.html`, their scripts

## Verification

Character, activity and music library browser tests pass on the tabs.
