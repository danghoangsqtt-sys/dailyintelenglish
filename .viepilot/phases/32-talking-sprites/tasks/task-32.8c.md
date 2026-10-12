# Task 32.8c: Never mix lines without word timings silently (BUG-030, D77)

## Why

Gate B-22 (2026-10-12): no karaoke captions. The Demo Episode's per-line TTS cache dates from 2026-09-15, before Task 19.2
added the `.words.json` sidecar. Step 4 "Generate All" re-synthesizes every line (so it is safe), but `POST .../audio/generate`
mixes whatever is cached: on 2026-10-06 it reused the old MP3s, `_aggregate_word_boundaries` returned `[]` for all 30 lines,
and every caption fell back to the plain line with no warning.

## Plan

- `app/api/audio.py` `generate_audio` (the orchestration layer; `AudioService` stays "mix only, never synthesize"): before
  mixing, find lines whose cached MP3 has no `.words.json` sidecar and re-synthesize them with
  `tts_service.synthesize_line` (or `synthesize_line_audio` + `save_line_audio_cache` to keep the network call outside the DB lock) (Edge TTS, `boundary="WordBoundary"`), outside the DB lock as Step 4 does.
- `tts_service`: a small helper `has_word_timings(audio_cache_path)` next to `_word_timestamps_path`, used by the API and tests.
- Report, do not hide: the audio job result carries `lines_without_words` (expected 0); Step 4 shows a warning when it is not 0
  (for example an Edge TTS response with no word events), and the Remotion props builder logs it.

## Paths

- `app/api/audio.py`
- `app/services/tts_service.py`
- `app/services/audio_service.py`
- `frontend/static/js/step4_tts.js`
- `tests/test_audio_api.py`
- `tests/test_audio_service.py`
- `tests/test_tts_word_boundary.py`

## Verification

Tests with a fake TTS: a line with MP3 but no sidecar is re-synthesized before the mix; a line with both files is reused
(no synthesis call); the job reports `lines_without_words`. Check which test files exist first and extend them rather than
add new ones where possible. Full suite + Ruff.
