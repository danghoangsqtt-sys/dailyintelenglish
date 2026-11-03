# Phase 90 — Edit a word-roots or grammar Short on its video (2026-11-03, planned)

Owner (2026-11-03): "Mở phần tạo video short dạng ngữ pháp lên cho tôi xem để xem thử là người dùng có thể kiểm tra
chỉnh sửa nội dung trực tiếp không? thay vì tạo lại từ đầu toàn bộ video thì chỉ cần sửa vài nội dung trên video thôi
giống các phần mềm edit video", then "Lập kế hoạch".

## Today

- Step 2 edits a line's spoken text only. The cards on screen (formula chips, rule, table, labels and titles of a
  grammar Short; meaning, split, example, picture of a word-roots Short) live in each line's `language_notes` and have
  no editor. "Regenerate this line" is hidden for these Shorts (Phase 88 quality round).
- Any change means: audio for the changed lines, the mix, and a full render (about 1–2 minutes for a 1–2 minute Short).
- A grammar line carries its scene header and every card shown so far (cumulative), so one card appears in several
  lines; a hand edit of the raw notes would have to be repeated in each of them.
- Reusable pieces: the Remotion preview player in the app (`window.SoloPreview`, used by the solo explainer editor and
  the Shorts batch preview), the render's own props builder (`video_renderer_remotion._build_input_props`), the TTS
  per-line cache (`tts_service.cache_matches`: unchanged lines are not synthesized again).

## Goal

In Step 5 of a `grammar` or `roots` Short, a "Sửa trên video" editor like a video editor: the list of beats, the 9:16
video playing beside it, and a form for the selected beat. Every edit shows on the video at once (no render). Spoken
text edits re-make only the changed lines' audio. "Tạo video" renders once at the end.

## Decisions (defaults; the owner may change them)

- **D128 — where:** Step 5 of these two Short kinds (the page that today shows only the render button); Step 2 links to
  it. Not a new page.
- **D129 — what is editable:** every text the viewer sees (labels, titles, subtitles, card texts, chips and their colour
  role, table cells, example sentences and translations; for word roots: meaning, split parts and meanings, example,
  picture description) plus adding, removing and reordering a scene's cards. Timing stays tied to the narration (no
  dragging on a timeline). Fonts, colours of the brand and layout are not editable.
- **D130 — card edits do not touch the audio:** saving cards keeps the audio and marks only the video as out of date;
  a spoken text change marks that line's audio out of date and the editor offers "Tạo lại giọng cho N câu".

## Tasks

1. **90.1 Beats API** — `GET /api/projects/{id}/beats` (lines with their text and card, and preview props: the render's
   own props with the last audio, or a silent preview with estimated timings when there is no audio yet);
   `PUT /api/projects/{id}/beats` (cards only, validated by kind: grammar cards against the lesson card rules, roots
   cards against the family card fields; the line text is not changed; video marked out of date, audio kept);
   one card edited in one line is applied to the same card in the later lines of its scene (cumulative cards), a header
   edit to every line of its scene. Tests. Paths: `backend/api/beats.py` (new), `backend/content/beats_service.py`
   (new), `backend/content/grammar_lesson.py`, `backend/content/word_family.py`, `backend/main.py`, tests.
2. **90.2 Editor UI** — `frontend/static/js/beat_editor.js` (new) mounted by `step5_video.js` for `roots` / `grammar`:
   beat list (number, beat kind, spoken text), the 9:16 player (`SoloPreview`) that seeks to the selected beat, the
   form for its header and cards (chips with a colour-role picker, table grid, add / remove / move a card), live update
   of the player from the edited props, autosave, undo / redo (Ctrl+Z / Ctrl+Y), Vietnamese copy. Word roots: "Vẽ lại
   hình" for one word (Qwen, then the library). Paths: `frontend/static/js/beat_editor.js`,
   `frontend/static/js/step5_video.js`, `frontend/pages/step5_video.html`, `frontend/static/css/*`,
   `frontend/static/js/i18n_vi.js`, `frontend/static/js/api.js`, `backend/media/roots_pictures.py`.
3. **90.3 Changed lines only** — spoken text edits in the editor; "Tạo lại giọng cho N câu" runs the audio step that
   synthesizes only lines whose cache no longer matches, then the mix; the preview reloads with the new timings; a
   test proves one changed line makes one TTS call. Paths: `backend/ai/tts/*`, `backend/api/tts.py` (if a scoped
   action is needed), `frontend/static/js/beat_editor.js`, tests.
4. **90.4 Verify** — browser tests (edit a chip, a table cell, a label, one spoken line; undo; render); a real sandbox
   run: edit one grammar Short and one word-roots Short, render, check the frames, and time edit + render against
   making the Short again.

Task cards are written when the phase starts.
