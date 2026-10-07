# Task 31.2: the owner's own pictures in the Shot Library

## Owner request (2026-10-07)

"I made scene pictures of the two characters talking to put into the library; give me the list of the 55 scenes I will make outside to
save time."

## Plan

- `shot_library_service`: an inbox folder (`data/library/shots_inbox`); the file name carries the tags
  (`scene__framing[__action][__expression]`, framing `duo-wide`, `duo-close`, `-rev`, `duo-wide-<left>-<right>`, `single-<name>`);
  `import_picture` (a PNG, cropped to 16:9 keeping the top, content-hash duplicate refused, `pending`, gaze tag `imported`),
  `import_inbox` (files that import move to `imported/`, the others stay with the reason).
- API: `GET /api/visuals/library/inbox`, `POST /api/visuals/library/inbox/import`; the Shot Library page gets an "Add your own pictures"
  card with the rules, the folder and an Import button.
- `docs/operations/scene-list-55.md`: the 55 built-in scenes (first 12 first), the file naming, size and clothes rules.

## Paths

- `app/services/visuals/shot_library_service.py`
- `app/api/visuals.py`
- `frontend/pages/shot_library.html`
- `frontend/static/js/shot_library.js`
- `frontend/static/js/api.js`
- `docs/operations/scene-list-55.md`
- `tests/test_shot_library_import.py`
- `tests/test_shot_library_browser.py`

## Verification

Import tests (tags, duplicates, bad names, 16:9 crop keeping the top, an imported picture reused after approval with no GPU work) and the
browser test of the card.
