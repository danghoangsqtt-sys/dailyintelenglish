# Phase 91 — Edit every kind of video on its video (2026-11-03)

Owner (2026-11-03, while Phase 90 was being checked): "áp dụng sửa trên video cho các dạng video khác, điều chỉnh tính
năng cho phù hợp với các dạng khác nhau". Phase 90 gave word-roots and grammar Shorts a "Sửa trên video" editor.

## What each kind has today (checked in the code)

| Kind | What is on screen comes from | Editing today |
|---|---|---|
| Solo explainers: news, blur, mistakes, wordday, top5, quiz, listen, VOX, presenter (Short and 16:9) | the explainer plan's segments (visual, texts, pictures) | Step 5 already has a plan editor with the live preview player; spoken lines only in Step 2 |
| Slow English podcast | each line's text and its Vietnamese translation | Step 2 (text, translation); nothing on the video |
| Vocabulary flashcards | the word lines and the lesson's vocabulary (part of speech, IPA, Vietnamese meaning) | Step 2 text; Step 3 lesson; nothing on the video |
| Chat, would you rather | the two speakers' lines | Step 2; nothing on the video |
| Conversation 16:9 (talking characters) | lines, storyboard (scenes, sprites, inserts) | Step 2, Step 5 storyboard with sketches; no live video (sprites are drawn by the renderer from local assets) |

All kinds: saving Step 2 rewrites every line, so every line's voice is made again even when one line changed.

## Decisions (defaults; the owner may change them)

- **D131 — one editing model for all kinds:** where the kind is drawn from its lines, the Phase 90 editor (beat list,
  live 9:16 video, form) is used with the fields that kind shows; where the kind already has its own visual editor
  (solo explainers, the conversation storyboard), that editor keeps the visuals and gains the spoken lines with "make
  the voice of the changed lines" instead of a second editor.
- **D132 — the conversation 16:9 has no live video:** its talking characters need the renderer's local sprite assets;
  it gets line editing and changed-lines voice in the storyboard, and the render shows the result.
- **D133 — a changed line keeps nothing else:** a spoken text change makes only that line's voice again, everywhere
  (also from Step 2).

## Tasks

1. **91.1 Step 2 keeps unchanged voices** — `script_service.save_script` keeps each line's id and audio cache when its
   position, speaker and text are unchanged (D133); Step 4 then synthesizes only the changed lines. Test.
   Paths: `backend/content/script_service.py`, `tests/`.
2. **91.2 Line-drawn Shorts in the editor** — `beats_service` gets per-kind adapters: slow podcast (spoken line,
   Vietnamese translation), flashcards (word line; the word's part of speech, IPA and Vietnamese meaning saved to the
   lesson's vocabulary), chat / would you rather (each message, its speaker). Preview props include the translation /
   lesson exactly as the render does. `beat_editor.js` shows the matching form; Step 5 mounts it for these kinds.
   Paths: `backend/content/beats_service.py`, `backend/api/beats.py`, `frontend/static/js/beat_editor.js`,
   `frontend/static/js/step5_video.js`, `frontend/static/js/i18n_vi.js`, tests.
3. **91.3 Spoken lines in the existing editors** — a shared "Spoken lines" panel (`frontend/static/js/line_panel.js`):
   each line's text, save one line (`PUT /api/projects/{id}/beats/{line}/text`, opened to every kind), "Make the voice
   again (N)"; mounted in the solo explainer editor (whose live preview reloads after the voice) and under the
   conversation storyboard. Paths: `backend/content/beats_service.py`, `frontend/static/js/line_panel.js`,
   `frontend/static/js/explainer_editor.js`, `frontend/static/js/storyboard.js` or `step5_video.js`, tests.
4. **91.4 Verify** — browser tests per kind; real sandbox edits of a slow podcast, a flashcards, a chat, a news Short
   and a 16:9 conversation (one line + one on-screen text each), voice only for the changed lines, render, frames.

Task cards are written when the phase starts.
