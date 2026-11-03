# Phase 90 summary — edit a word-roots or grammar Short on its video

Done 2026-11-03 on `owner-runs/20261001-r9` (not pushed, not installed). Defaults D128–D130 accepted ("Chạy Phase 90").

## What changed

- **Beats API** (90.1): `GET /api/projects/{id}/beats` (each line's card + live preview props: with the audio when it
  matches the script, silent with estimated timings otherwise), `PUT /beats` (cards checked by kind; text and audio
  kept; the video marked out of date), `PUT /beats/{line}/text` (one line's text; its card kept; only its audio
  cleared), `POST /beats/picture` (draw one word picture again), `GET /beats/pictures/{name}`.
- **Editor** (90.2): Step 5 of `roots` / `grammar` Shorts — beat list | the 9:16 video (the app's preview player) |
  the selected beat's form. Edits show on the video at once and autosave; grammar: a scene's header and shared cards
  change on all its lines; word roots: a word's meaning, split, picture… change on all its beats; undo / redo; spoken
  line saved alone. The browser preview got the Bangers / Patrick Hand fonts it was missing.
- **Changed lines only** (90.3): "Tạo lại giọng (N)" synthesizes only the lines whose voice no longer matches, then
  mixes.

## Real checks (sandbox, `docs/operations/phase90-screens/`)

- Grammar "I very like": a rule card and one spoken line edited → voice for 1 line + mix **9 s** (one TTS request in
  the log) → render **~52 s**; both edits in the video and its subtitles. Making the Short again takes ~2 min and gives
  a different lesson.
- Word roots RE-: one word's meaning edited once → applied to its hook / word / split beats → render 309 s (Qwen drew
  the missing line-art pictures this time).
- Found while checking: the scene's title edit did not reach its other lines (the scene was looked up by the edited
  title); a roots word edit did not reach its other beats; the beat names were not translated; the form overflowed.
  All fixed.
