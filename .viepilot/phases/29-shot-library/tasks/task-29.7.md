# Task 29.7: Shot Library UI (ENH-020)

## Plan

- New page `/shots` (`frontend/pages/shot_library.html`, `frontend/static/js/shot_library.js`): grid of library pictures with
  filters (scene, framing, review), per-picture Approve / Reject / Delete, "Approve all in view" (after looking), badges for
  needs review / approved / rejected / stale / used N times, an empty-state hint.
- Sidebar: a "Shot Library" link on all 11 pages (and the new one).
- Step 5: "+ Add to library" under every finished non-insert shot that was drawn here, a "from library" badge on shots copied
  from it, and a coverage line "Shot Library: X of Y pictures are ready to reuse; Z will be drawn".
- `api.js`: list / review / delete / add / coverage calls. Route `GET /shots` in `app/main.py`.

## Paths

- `frontend/pages/shot_library.html`
- `frontend/static/js/shot_library.js`
- `frontend/static/js/api.js`
- `frontend/static/js/step5_video.js`
- `frontend/pages/step5_video.html`
- `frontend/static/css/style.css`
- `app/main.py`
- `tests/test_shot_library_browser.py`

## Verification

`tests/test_shot_library_browser.py` (add, review once, coverage line, a second run served from the library, sidebar link) and the
sidebar suite green.
