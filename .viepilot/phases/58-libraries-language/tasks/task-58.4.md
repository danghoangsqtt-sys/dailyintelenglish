# Task 58.4 — Music compact list and shared player

Status: planned 2026-10-22.

## Paths
- frontend/pages/music_library.html, frontend/static/js/music_library.js
- tests/test_music_library_browser.py and the other music browser tests

## File-Level Plan
Header with "Upload music" (the existing file input; drag-and-drop anywhere on the page still uploads). Toolbar: search (title/artist/tags) and mood chips with counts. Each track is one row: play button, title + file name, mood, pace, length, licence badge (⚠ when the licence or source is missing), uses count when known, Edit, Delete. One player bar fixed at the bottom plays the selected row (the per-row `<audio>` elements go away; the waveform stays in the editor where it is used today). Edit opens a side panel with the existing form fields and Save/Cancel.

## Tests
Browser: search and chips filter rows; play loads the row into the shared player; Edit opens the panel and saves; existing music tests pass after following the new layout.
