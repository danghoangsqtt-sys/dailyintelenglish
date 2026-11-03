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

## Implementation notes (2026-11-03, before code)

- Measured on this machine: loading VieNeu takes 8.9 s and Whisper `small` 2.0 s; one line then takes ~3 s on CPU.
  So the worker is a **persistent line-delimited process** (the `.venv-image` worker pattern: handshake, one JSON request
  per line, one JSON reply), started on the first VieNeu line and closed after `VIENEU_IDLE_SECONDS` without work. CPU
  only (no torch in `.venv-vieneu`), so it never competes with Qwen for the GPU.
- The worker returns the WAV path and Whisper's words with times; **alignment runs in the app** (`vieneu_service.align_words`,
  pure and unit-tested): script words are matched to recognised words with `difflib` on accent-folded lower-case
  tokens; matched words take Whisper's times, the rest are spread over the gap between neighbours by length. One
  boundary per script word, text without surrounding punctuation (as Edge's).
- A take whose match ratio is below `VIENEU_MIN_WORD_MATCH` is synthesized once more; the better take is kept.
- Speed: VieNeu has no rate control, so the speaker's speed is applied with ffmpeg `atempo` and timings are scaled;
  volume as a gain; pitch is ignored for VieNeu.
- Default presets: Ngọc Huyền (female / neutral), Thiện Minh (male). Model files live under
  `backend/ai/models/vieneu` (`HF_HOME`), already gitignored with the other local models.
- The SDK default temperature is kept (the owner chose from samples made with it).

## Best practices

- Never import `vieneu` or `torch` in the app process; the app venv stays unchanged (Phase 75 pattern).
- Alignment never invents words: unmatched script tokens get interpolated times between neighbours, flagged in the log.
- Keep the WordBoundary JSON shape identical to Edge's.

## Verification

- `pytest tests/test_vieneu_service.py tests/test_tts_service.py -q` — pass.
- Manual: run the setup script, synthesise the three research lines, transcript matches, timings monotonic.

## Result (2026-11-03)

- `pytest tests/test_vieneu_service.py` 8 passed (alignment, caps, presets, dispatch, fake-worker contract with retry and
  speed scaling); TTS/projects/script suites 203 passed with 87.2.
- Real worker on this machine (`scripts/setup_vieneu.ps1`, model in `backend/ai/models/vieneu`): three research lines in
  Thiện Minh's voice, 11.0 s (first line, model load) / 3.0 s / 3.6 s; every script word got a monotonic time, English
  words included ("We@6.27 compress@6.47 … space@8.13").
- Found while running: `-I` ignores PYTHONIOENCODING (the worker now sets UTF-8 on its pipes); Windows PowerShell 5.1
  turns native stderr into errors under `Stop`; an interrupted venv has no `pyvenv.cfg`; ONNX Runtime refuses graph data
  reached through the hub cache's symlinks (`HF_HUB_DISABLE_SYMLINKS=1`).
