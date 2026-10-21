# Task 58.3 — Character profile tabs

Status: planned 2026-10-22.

## Paths
- frontend/pages/characters.html, frontend/static/js/character_profiles.js
- tests/test_character_profiles_browser.py (and other character tests that open sections)

## File-Level Plan
Profile header: avatar, name, summary, readiness and the Duplicate/Archive/Delete buttons stay at the top of the detail card (sticky). Below it one tab row: the two existing picture-view buttons (Conversation · 29, Presenter · 21, ids and `data-picture-view` unchanged) plus "Voice" and "Details". Picture tabs show the slot tools and slots; Voice shows the voice picker (no longer inside `<details>`); Details shows the details form. The chosen tab is remembered while moving between characters. The list cards keep their content with a clearer selected state.

## Tests
Browser: tabs show one panel at a time; Voice and Details keep working (save); existing character tests pass after following the new tabs.
