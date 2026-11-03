# Task 87.1 — VieNeu engine (isolated worker)

See [PLAN.md](../PLAN.md), D125.

## Objective

A speaker can use `tts_engine = "vieneu"` with one of the 25 VieNeu v3 Turbo presets. A line synthesised with it gives
a WAV in the audio cache and a word-timestamps file in the same format as Edge, so karaoke, caption paging, previews and
the video renderer need no change. Edge stays the default; nothing else changes engine.

## Paths

- `scripts/setup_vieneu.ps1` (new) — create `.venv-vieneu` with Python 3.12 via `uv` (fallback `py -3.12`), install
  `vieneu==3.8.3` and `faster-whisper`, pre-download the model at a pinned revision (`61b85e3…`) and the Whisper `small`
  model; idempotent; clear error text in Vietnamese and English.
- `backend/ai/tts/vieneu_worker.py` (new) — plain script run by the isolated interpreter: reads a JSON job (text, voice,
  temperature, out path), synthesises, aligns words with faster-whisper (`word_timestamps=True`, audio decoded through
  ffmpeg into PCM, not PyAV), maps recognised words onto the script tokens in order, writes WAV + JSON. Runs `python -I`.
- `backend/ai/tts/vieneu_service.py` (new) — `is_available()`, `list_presets()`, `synthesize(text, voice) -> (bytes,
  list[WordBoundary])` through a subprocess with timeout; shared GPU lease only when CUDA is used; caps-to-lower for
  all-caps Latin words before sending; raises `TTSError` with the real cause.
- `backend/ai/tts/tts_service.py` — dispatch on the speaker's `tts_engine`; cache fingerprint includes engine + voice +
  model revision.
- `backend/core/constants.py` — `TTS_ENGINES = ["edge_tts", "vieneu"]`, `VIENEU_*` constants (timeout, revision, presets).
- `backend/core/voice.py`, `backend/ai/tts/voice_catalog_service.py` — accept VieNeu preset ids for `vieneu` speakers;
  Edge validation unchanged.
- `.gitignore` — `.venv-vieneu/`.
- Tests: `tests/test_vieneu_service.py` (worker contract with a fake interpreter, caps normalisation, alignment mapping,
  missing-environment error, cache fingerprint), updates to the existing tests that assert Edge is the only engine.

## Best practices

- Never import `vieneu` or `torch` in the app process; the app venv stays unchanged (Phase 75 pattern).
- Alignment never invents words: unmatched script tokens get interpolated times between neighbours, flagged in the log.
- Keep the WordBoundary JSON shape identical to Edge's.

## Verification

- `pytest tests/test_vieneu_service.py tests/test_tts_service.py -q` — pass.
- Manual: run the setup script, synthesise the three research lines, transcript matches, timings monotonic.
