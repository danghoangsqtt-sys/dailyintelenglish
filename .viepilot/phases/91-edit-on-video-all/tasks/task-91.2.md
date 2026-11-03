# Task 91.2 — Line-drawn Shorts in the editor

## Design (written before code)

- `beats_service`: per-kind adapters keyed by `explainer_style`:
  - `slowpod`: card = `{translation_vi}` read from / written to `language_notes.translation_vi`; preview line field
    `translation`.
  - `flashcards`: a card line ("wash up. wash up.") has card = `{word, part_of_speech, ipa, meaning_vi}` from the
    lesson's vocabulary item of that word (learning content); saving writes those fields back to the lesson; other
    lines (deck name, follow) have no card. Preview props carry `learning.vocab` like the render.
  - `chat`, `wyr`: no card; the editor shows the message text and its speaker name (read-only), the would-you-rather
    asking line with a hint that its options are the "A or B" text.
  - `roots`, `grammar`: as Phase 90.
  `load` builds props with `shortStyle` and, for slowpod / flashcards, the same `translation` / `learning` fields as
  `video_renderer_remotion._build_input_props`.
- `beat_editor.js`: the form by kind (translation field; flashcard fields; message text only), no card add / remove for
  these kinds; Step 5 mounts the editor for every line-drawn Short.

## Paths

`backend/content/beats_service.py`, `backend/api/beats.py`, `frontend/static/js/beat_editor.js`,
`frontend/static/js/step5_video.js`, `frontend/static/js/i18n_vi.js`, `tests/test_beats_api.py`,
`tests/test_beat_editor_browser.py`.

## Verification

`pytest tests/test_beats_api.py tests/test_beat_editor_browser.py -q`.
