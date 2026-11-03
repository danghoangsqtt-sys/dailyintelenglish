# Task 90.1 — Beats API

See [PLAN.md](../PLAN.md), D128–D130.

## Design (written before code)

- `backend/content/beats_service.py` (new):
  - `card_key(line)`: `"grammar"` or `"roots"` from the project's style; other styles are refused (ValidationError).
  - `load(db, project_id)` → `{style, lines: [{id, index, text, card, audio_ok}], props}`. `props` are the render's own
    props (`video_renderer_remotion._build_input_props`, vertical, with the complete audio job) built **without drawing
    pictures** (a new `draw_pictures=False` keeps only cached word pictures), or, when there is no complete audio,
    silent props with estimated timings (0.075 s per character, at least 1.6 s a line) and no audio path. Public paths
    only (no file-system paths). `audio_ok` = the line's TTS cache still matches.
  - `save_cards(db, project_id, edits)`: `edits = [{line_id, card}]`; each card validated by kind (grammar: header
    fields and a list of cards whose kinds and field lengths follow `grammar_lesson`; roots: the card fields of
    `word_family._card`) — extra keys dropped, lengths clipped; writes only `language_notes.<key>` (text, audio cache
    untouched); a `video_generated` / `complete` project goes back to `audio_generated` (video out of date, audio kept).
  - `propagate(lines, line_id, old, new)` (grammar): the header change goes to every line of the same scene; a card
    changed / removed / added is applied to the same card (by content) in the later lines of the scene, so cumulative
    cards stay consistent. Done in the client too (90.2) but the server is the source of truth: the client sends the
    edited lines it computed and the server re-validates each.
  - `save_text(db, project_id, line_id, text)`: one line's spoken text through `script_service.update_script_line`
    (keeps its card; clears only that line's audio cache) + `mark_script_changed` (audio must be made again; only this
    line is synthesized — 90.3).
- `backend/api/beats.py` (new, registered in `backend/main.py`): `GET /api/projects/{id}/beats`,
  `PUT /api/projects/{id}/beats` (`{"lines": [{"line_id", "card"}]}`),
  `PUT /api/projects/{id}/beats/{line_id}/text` (`{"text"}`).
- `backend/media/video_renderer_remotion.py`: `draw_pictures` parameter.

## Paths

`backend/content/beats_service.py`, `backend/api/beats.py`, `backend/main.py`, `backend/media/video_renderer_remotion.py`,
`tests/test_beats_api.py`.

## Verification

`pytest tests/test_beats_api.py tests/test_grammar_script.py tests/test_roots_script.py -q`; ruff.
