# Task 1.6: Step 4 — TTS Audio Studio

## Meta
- **ID**: 1.6
- **Phase**: 1
- **Status**: planned
- **Priority**: high
- **Assignee**: AI

## Paths
- `app/services/tts_service.py`
- `app/services/audio_service.py`
- `app/api/tts.py`
- `frontend/pages/step4_tts.html`
- `frontend/static/js/step4_tts.js`

## Acceptance Criteria
- [ ] TTSService supports OmniVoice local GPU with concurrency semaphore(2)
- [ ] Automatic fallback to Edge TTS on OOM / error
- [ ] AudioService mixes tracks with speaker pauses and volume normalization
- [ ] TTS UI supports audio preview, regeneration, and export

## Forbidden Scope
- No blocking the event loop with ffmpeg or audio model synthesis
- No VRAM exhaustion without fallback

## Verification Commands
- `venv\Scripts\python -m pytest tests/`
- `venv\Scripts\ruff check app/`

## Implementation Notes (2026-09-11, Sub-task 1.6a: Edge-TTS-first vertical slice)
This machine has no `ffmpeg`, no `.env`/Gemini key, and no OmniVoice model weights
(`models/omnivoice/` is empty — see TRACKER.md Known Issues). Per PM decision, Task 1.6
is split into sub-tasks so progress isn't blocked on local environment setup:

**Sub-task 1.6a (this one):** `TTSService` line-level synthesis via Edge TTS (works
today, no local dependency beyond internet + the already-installed `edge-tts` package),
with the OmniVoice path implemented as a clean, honest fallback branch — not a fake
success path. `AudioService` (mixing/normalization, needs ffmpeg) and the TTS Studio UI
are deferred to later sub-tasks (1.6b, 1.6c) once ffmpeg is available.

Files:
- `app/services/tts_service.py` (new): `synthesize_line(db, project, line, speaker) -> dict`.
  - If `speaker.tts_engine == "omnivoice"` AND `settings.OMNIVOICE_MODEL_PATH.exists()`:
    try `_synthesize_omnivoice()` inside `asyncio.Semaphore(settings.OMNIVOICE_MAX_CONCURRENT)`
    (per SYSTEM-RULES "OmniVoice Rules" + `MAX_CONCURRENT_TTS`); on ANY exception (model not
    loaded, OOM, etc.) log a warning and fall back to Edge TTS — never raise past this point
    unless Edge TTS also fails.
  - Otherwise (or on OmniVoice failure): `_synthesize_edge_tts()` using `edge_tts.Communicate`,
    voice selected via a new `EDGE_TTS_VOICE_MAP` constant (accent x gender -> Edge neural
    voice id; `scottish` has no distinct Edge locale, documented fallback to `en-GB`;
    `neutral` gender falls back to that locale's female voice — Edge TTS has no true
    gender-neutral neural voice).
  - `_synthesize_omnivoice()` is a real code path (semaphore + call site), but since no model
    is loaded on this machine it always raises `TTSEngineUnavailableError` for now — this is
    the correct, honest state until the model weights exist, not a stub to silently replace
    later; the fallback logic around it is what's actually being delivered and tested.
  - Saves output to `data/tts_cache/{project_id}/{line_id}.mp3`, updates
    `script_lines.audio_cache_path` (duration_seconds intentionally left untouched — computing
    MP3 duration needs ffmpeg/pydub, deferred to sub-task 1.6b alongside AudioService).
  - Raises `TTSError` (already defined in `app/core/exceptions.py`) only if Edge TTS itself
    fails (e.g. network error) after the OmniVoice fallback.
- `app/api/tts.py` (extend): add `preview_router = APIRouter(prefix="/api/projects/{project_id}/tts")`
  with `POST /preview` taking `{"line_id": str}` (new `PreviewLineRequest` in `app/models/tts.py`),
  matching the `/script/regenerate` request pattern. Route: `_read_transaction()` to load
  project + line, call `tts_service.synthesize_line()` with no lock held (network call), return
  `{audio_url, engine_used}` via `ok()`. Per ARCHITECTURE.md: `POST /api/projects/{id}/tts/preview`.
- `app/main.py`: register the new preview router; mount `/static/tts_cache` -> `data/tts_cache`
  is NOT needed since audio is served via a small `GET /api/projects/{id}/tts/cache/{line_id}.mp3`
  route instead of StaticFiles (avoids exposing the whole `data/` tree).
- `app/models/tts.py` (new): `PreviewLineRequest`.
- `tests/test_tts_service.py` (new): mock `edge_tts.Communicate` (no real network calls in
  tests, same pattern as mocking `httpx` for Gemini), verify OmniVoice-unavailable ->
  Edge TTS path, verify voice map covers all 10 accents x 3 genders, verify cache file written,
  verify `audio_cache_path` persisted.
- `tests/test_tts_api.py` (new): API-level TestClient tests for the preview route (success,
  404 unknown line, unknown project).

Forbidden Scope for this sub-task: no AudioService, no ffmpeg calls, no TTS Studio UI, no
duration extraction, no real OmniVoice model integration (that needs the actual model weights
this machine doesn't have).

## Sub-task 1.6a Result (2026-09-11) — DONE
Delivered: `app/services/tts_service.py`, `app/models/tts.py`, extended `app/api/tts.py`
(`POST /api/projects/{id}/tts/preview`, `GET /api/projects/{id}/tts/cache/{line_id}.mp3`),
`EDGE_TTS_VOICE_MAP` in `app/core/constants.py`, 22 new tests (`tests/test_tts_service.py`,
`tests/test_tts_api.py`), plus a defensive fixture in `tests/conftest.py` resetting the
module-level `_omnivoice_semaphore` per test (same event-loop-binding hazard already fixed
once for `_write_lock`).

Live-verified (not just mocked): a real `_synthesize_edge_tts` smoke test across all 10
accents x 2 genders succeeded 20/20; one run hit a transient Edge TTS "no audio received"
response, which surfaced a real gap — the first implementation had no retry — fixed by adding
a retry-once-on-empty-audio guard (`EDGE_TTS_MAX_ATTEMPTS = 2`) before landing the sub-task,
not after. 252/252 tests pass, `ruff check` clean.

Not done (deferred to 1.6b/1.6c, blocked on local ffmpeg + OmniVoice model weights):
AudioService (mixing/normalization), TTS Studio UI, duration extraction, real OmniVoice
GPU inference.
