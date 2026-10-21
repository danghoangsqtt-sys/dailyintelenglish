# Task 56.1 — Activity Library rename and layout

Status: planned 2026-10-21.

## Paths
- frontend/pages/*.html (sidebar link), frontend/pages/shot_library.html, frontend/static/js/shot_library.js
- backend/main.py (`/activities`, `/shots` alias), backend/channel/dashboard_service.py (review action link)
- backend/media/ai_scene.py, backend/media/video_renderer_remotion.py (error text naming "Shot Library"; sprites live on the Character Library)
- tests/test_activity_library_browser.py, tests/test_app_sidebar_browser.py

## File-Level Plan
Sidebar label/title/aria "Activity Library", href `/activities`, current-page mark on the page. Page title "Activity Library". Tabs: "Activity pictures" (default) and "Scene backgrounds" (the background import, open, with the folder and count). Left shelf list: All, Generic, every character, with picture counts; replaces the Scope select. Review chips (All / Needs review / Approved / Rejected) drive the existing `review_state` filter. Toolbar keeps select-all + bulk buttons; "Add activity pictures" at the top; the folder import moves to the end of the tab. Characters load before the first render so card names are right.

## Tests
Browser: rename visible in the sidebar; `/activities` and `/shots` serve the page; shelves filter the grid and show counts; chips filter by review state; the background tab shows the import.
