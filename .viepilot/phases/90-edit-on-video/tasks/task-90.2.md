# Task 90.2 — "Sửa trên video" editor

See [PLAN.md](../PLAN.md), task 90.1 for the API.

## Design (written before code)

- `frontend/static/js/beat_editor.js` (new, `window.BeatEditor.mount(container, projectId, style)`), mounted by
  `step5_video.js` in the line-drawn section when the style is `roots` or `grammar` (D128).
- Layout: three columns on a wide screen, stacked on a narrow one — beat list (number, beat kind, spoken text, a dot
  when the line's audio must be made again) | the 9:16 player (`window.SoloPreview.mount` with the props from
  `GET /beats`; selecting a beat seeks to its start) | the form for the selected beat.
- Form, grammar: scene label, title, subtitle (applied to the whole scene); the cards of the line in order, each with
  its fields by kind (formula / lego chips: text + colour-role select; compare: two sentences and translations; table:
  a grid of inputs with add / remove row; example: sentence, translation, marked words; rule / sticker / stamp /
  promise / core: text; quiz: question and options); move up / down, remove, "Thêm thẻ" (kind picker). Word roots:
  meaning, split parts (text, role, meaning), breakdown, example and translation, picture description, icons, answer.
- Every change: update the line(s) locally (the same propagation as 90.1 for grammar scenes), rebuild the props'
  `lines[i].grammar|roots` and call `player.update(props)` — the video shows the change at once; autosave after 800 ms
  (`PUT /beats`), status "Đã lưu" / "Đang lưu…".
- Undo / redo: a stack of line snapshots; Ctrl+Z / Ctrl+Y and two buttons.
- Spoken text: a textarea per beat; saving it calls `PUT /beats/{line_id}/text`; the line gets the "cần tạo lại giọng"
  dot (90.3 adds the button).
- Word roots: "Vẽ lại hình" for the selected word (`POST /api/projects/{id}/beats/picture` → `roots_pictures` draws one
  picture again with the edited description; disabled while drawing).
- Copy in English in the code, Vietnamese in `i18n_vi.js`; `api.js` methods `getBeats`, `saveBeats`, `saveBeatText`,
  `redrawBeatPicture`.

## Paths

`frontend/static/js/beat_editor.js`, `frontend/static/js/step5_video.js`, `frontend/pages/step5_video.html`,
`frontend/static/css/style.css` (or the page's stylesheet), `frontend/static/js/api.js`, `frontend/static/js/i18n_vi.js`,
`backend/api/beats.py`, `backend/media/roots_pictures.py`, `tests/test_beat_editor_browser.py`.

## Verification

`pytest tests/test_beat_editor_browser.py -q`; manual look in the sandbox.
