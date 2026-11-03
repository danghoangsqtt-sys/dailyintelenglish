# Task 90.3 — Only the changed lines' audio

## Design (written before code)

- Check how Step 4's audio action treats lines whose cache still matches (`tts_service.cache_matches`); if it already
  synthesizes only the missing ones, the editor reuses that action; if not, the audio job skips matching lines.
- Editor: when any line's audio is out of date, a bar "N câu cần tạo lại giọng · Tạo lại giọng" runs the audio action
  (synthesis of those lines + the mix), polls until done, then reloads `GET /beats` so the player has the new timings.
- Test: a project with cached audio for every line; one line's text changed through the beats API; the audio action
  calls the TTS engine once.

## Paths

`backend/ai/tts/*` or `backend/media/audio_service.py` (only if needed), `frontend/static/js/beat_editor.js`,
`tests/test_beats_api.py`.

## Verification

`pytest tests/test_beats_api.py -q`.
