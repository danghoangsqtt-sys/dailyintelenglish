# Task 91.3 — Spoken lines in the existing editors

## Design (written before code)

- Backend: `PUT /api/projects/{id}/beats/{line_id}/text` works for every kind (the card check is only for the kinds
  with cards); a new `GET /api/projects/{id}/beats/lines` returns `[{id, text, speaker, audio_ok}]` for any kind.
- `frontend/static/js/line_panel.js` (new, `LinePanel.mount(container, projectId, {onVoice})`): the spoken lines with a
  text box each, "Save" per line, "Make the voice again (N)" (the Phase 90 flow: synthesize the stale lines, then mix),
  then `onVoice()` (the solo editor reloads its preview).
- Mounted: in the solo explainer editor (news, blur, mistakes, wordday, top5, quiz, listen, VOX, presenter) under its
  player, and in Step 5 under the conversation storyboard (D132: no live video there).

## Paths

`backend/content/beats_service.py`, `backend/api/beats.py`, `frontend/static/js/line_panel.js`,
`frontend/static/js/explainer_editor.js`, `frontend/static/js/step5_video.js`, `frontend/pages/step5_video.html`,
`frontend/static/css/style.css`, `frontend/static/js/i18n_vi.js`, tests.

## Verification

Browser tests for a news Short and a conversation.
