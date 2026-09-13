# Task 1.6: Step 4 — TTS Audio Studio

## Meta
- **ID**: 1.6
- **Phase**: 1
- **Status**: in_progress (1.6a, 1.6b done; 1.6c pending)
- **Priority**: high
- **Assignee**: AI

## Paths
- `app/services/tts_service.py`
- `app/services/audio_service.py`
- `app/api/tts.py`
- `frontend/pages/step4_tts.html`
- `frontend/static/js/step4_tts.js`

## Acceptance Criteria
- [ ] TTSService supports OmniVoice local GPU with concurrency semaphore(2) — semaphore
  wired (`asyncio.Semaphore(MAX_CONCURRENT_TTS)`), but real GPU inference is not yet
  integrated into `_synthesize_omnivoice()` (deliberately deferred — needs a ref_audio
  design decision, see TRACKER.md)
- [x] Automatic fallback to Edge TTS on OOM / error — any `_synthesize_omnivoice` exception
  falls back, tested in `tests/test_tts_service.py`
- [x] AudioService mixes tracks with speaker pauses and volume normalization — Sub-task 1.6b
- [ ] TTS UI supports audio preview, regeneration, and export — pending Sub-task 1.6c

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

## Implementation Notes (2026-09-13, Sub-task 1.6b: AudioService — mixing, loudness, background music)

`ffmpeg` (via `DIE_FFMPEG_PATH`) and `pydub`+`audioop-lts` are now verified working
end-to-end (see TRACKER.md Known Issues — RESOLVED). This unblocks 1.6b. Per Task 1.10's
PM Acceptance note, background-music selection + loudness leveling were explicitly
deferred here "alongside AudioService" — so this sub-task also closes that piece of 1.10,
not just the 1.6 AudioService bullet.

Scope (matches ROADMAP.md Task 1.6 "AudioService" bullet exactly):
- Mix all of a project's script lines (already-synthesized per-line audio from 1.6a) into
  one continuous track, in `line_index` order.
- Insert silence between lines: `SILENCE_SAME_SPEAKER_MS` (300ms) when consecutive lines
  share a speaker, `SILENCE_DIFFERENT_SPEAKER_MS` (500ms) otherwise (both constants already
  defined in `app/core/constants.py`, unused until now).
- Normalize integrated loudness to `TARGET_LOUDNESS_LUFS` (-16, already defined) using real
  ITU-R BS.1770 loudness measurement (`pyloudnorm`), not a dBFS-average approximation
  mislabeled as LUFS.
- Optional background music: if the project has a `background_music` filename (from
  `data/music_library/`, per Task 1.10), loop/trim it to the mixed track's duration and
  overlay at a flat ceiling of `MUSIC_DUCKING_MAX_DBFS` (-18 dBFS, already defined). This is
  a **static-level duck** (music kept quiet under the whole track), not dynamic
  speech-reactive ducking — documented honestly as a simplification, matching the
  complexity budget of the rest of Phase 1.
- Export MP3 192kbps + WAV 44100Hz/16-bit to `data/audio/{project_id}/` (matches the
  pre-existing `.gitignore` convention and the `data/audio/uuid/final.mp3` example already
  in ARCHITECTURE.md's project JSON shape, not a new directory name).
- Generate a timestamps JSON (`[{start_sec, end_sec, label, speaker_id}]`, label = speaker
  name) — this becomes the *real* source for YouTube chapters once Sub-task 1.9b picks it
  up (currently 1.9a estimates chapters from word count only).
- Persist to the existing (currently-unused) `audio_jobs` table via `003` — no, `audio_jobs`
  is already in `001_init.sql`; no new migration needed. One row per project (`UNIQUE
  project_id`), UPSERT pattern like `youtube_packages`.
- Advance `projects.status` from `script_generated` -> `audio_generated` on success — but
  only when the current status is exactly `script_generated` (the state machine is
  forward-only, one step at a time); if the project is already past that (e.g. regenerating
  audio later), skip the status write rather than raising, since re-mixing shouldn't be
  blocked by the state machine.

Deliberate deviation from `ARCHITECTURE.md`'s `GET /api/projects/{id}/audio/status` "(SSE)"
label: every other `*/generate` endpoint in this codebase (script, learning, thumbnail,
youtube) is a synchronous await-then-return call with no SSE anywhere in the actual
implementation, and mixing a short podcast is a few seconds of local CPU work. `audio/status`
is implemented as a plain polling GET returning the `audio_jobs` row, consistent with how
the rest of the app actually works today, not a real `text/event-stream`. Noting this here
so it isn't mistaken for a missed requirement.

Files:
- `app/services/audio_service.py` (new): `mix_project(project, lines, background_music_filename) -> dict`.
  - Caller (`app/api/audio.py`) takes a `_read_transaction()` snapshot of the project,
    speakers, and script lines with `audio_cache_path` + `duration_seconds` (new query,
    since `script_service.get_script` doesn't select `audio_cache_path`), and passes
    `background_music` through from the request body (optional filename, validated against
    `data/music_library/` — no project-table column added; there's no UI to set one yet,
    per-call selection is enough for this sub-task and mirrors how 1.10a's music routes
    already work by filename, not by DB id).
  - Raise `AudioMixError` (already defined) if any line has no `audio_cache_path` yet (caller
    must synthesize all lines first — this function does not call TTS itself, keeping
    AudioService's responsibility to audio processing only, per ARCHITECTURE.md's
    TTSService/AudioService split).
  - Pure pydub/pyloudnorm mixing work runs inside `asyncio.to_thread()` — never blocks the
    event loop (Forbidden Scope in this task file, already stated for 1.6a, applies here too).
  - Returns `{mp3_path, wav_path, timestamps, duration_seconds, loudness_lufs}`.
- `app/api/audio.py` (new): `audio_router = APIRouter(prefix="/api/projects/{project_id}/audio")`.
  - `POST /generate` — `_read_transaction()` to snapshot + validate all lines have cached
    audio (else `AudioMixError` "line X has no synthesized audio yet"); run
    `audio_service.mix_project` with no lock held; `_write_transaction()` to UPSERT the
    `audio_jobs` row and best-effort advance project status.
  - `GET /status` — return the current `audio_jobs` row (404 if none yet).
  - `GET /download?format=mp3|wav` — `FileResponse` from the stored path.
  - Register in `app/main.py`.
- `app/models/audio.py` (new): `GenerateAudioRequest` (empty body reserved for future options
  like an override background-music filename), `AudioJobOut`.
- `app/core/constants.py`: no new constants needed — `SILENCE_SAME_SPEAKER_MS`,
  `SILENCE_DIFFERENT_SPEAKER_MS`, `TARGET_LOUDNESS_LUFS`, `MUSIC_DUCKING_MAX_DBFS` already exist.
- `requirements.txt`: add `pyloudnorm>=0.1.1` (small, pure-Python + numpy/scipy, both already
  installed transitively via the OmniVoice install) for real LUFS measurement.
- `tests/test_audio_service.py` (new): build real tiny audio fixtures with
  `pydub.AudioSegment.silent()`/a generated sine tone (never fake byte strings — pydub must
  actually decode them), verify: silence-gap durations differ same-speaker vs different-speaker,
  loudness lands within tolerance of `TARGET_LOUDNESS_LUFS` after normalization, background
  music is capped at `MUSIC_DUCKING_MAX_DBFS`, timestamps are monotonically increasing and sum
  to the final duration, `AudioMixError` on a line missing `audio_cache_path`.
- `tests/test_audio_api.py` (new): API-level tests for generate/status/download (success, 404s,
  409/422 on missing synthesized lines).

Forbidden Scope for this sub-task: no TTS Studio UI (1.6c), no dynamic speech-reactive
ducking, no real SSE streaming, no video/timestamps-to-YouTube wiring (that's 1.9b's job to
consume this sub-task's `timestamps` output later).

## Sub-task 1.6b Result (2026-09-13) — DONE

Delivered exactly the plan above: `app/services/audio_service.py`, `app/models/audio.py`,
`app/api/audio.py` (registered in `app/main.py`), `pyloudnorm` added to `requirements.txt`,
25 new tests (`tests/test_audio_service.py` 13, `tests/test_audio_api.py` 12).

Real bug found and fixed during implementation (not after): this pydub version's media
probing (`pydub.utils.get_prober_name()`) does its own `which("ffprobe")` PATH lookup and
silently ignores `AudioSegment.converter`/any class-attribute override — confirmed by
reading the installed `pydub/utils.py` source after `AudioSegment.from_file()` failed with
`FileNotFoundError` despite `AudioSegment.converter` being set correctly. Fixed by
prepending `DIE_FFMPEG_PATH`'s directory to this process's `PATH` env var at import time
(`_ensure_ffmpeg_dir_on_path`) — affects only this process, not the system-wide PATH.

Live-verified with real audio (not mocked): a manual smoke script mixed 3 real
tone-generated MP3 lines end-to-end (2 same-speaker + 1 different-speaker), confirming
exact silence-gap timing (300ms/500ms), loudness normalization landing at exactly -16.0
LUFS, background-music ducking correctly capping a loud track and correctly leaving a
quiet track untouched, and a missing-line / missing-music-file error path — before any of
this was written into the automated test suite, matching this project's standing PM
requirement to verify with real command output, not just green tests.

Test philosophy note: unlike Gemini/Edge TTS (network, mocked everywhere), `ffmpeg` is a
required local system binary this project cannot function without, so
`tests/test_audio_service.py` exercises the real `pydub`+`ffmpeg`/`ffprobe` pipeline on
real, tiny, tone-generated audio — the same "exercise the real local library" approach
already used for Pillow in `tests/test_thumbnail_service.py`. `tests/test_audio_api.py`
mocks only the Edge TTS network call (returning a real decodable tone MP3, not a fake byte
string) so the mixing step downstream is still real.

This sub-task also closes the piece of **Task 1.10** (background-music selection +
loudness leveling) that its PM Acceptance explicitly deferred "alongside AudioService" —
see task-1.10.md.

### Verification output

`venv\Scripts\python -m pytest tests/test_audio_service.py tests/test_audio_api.py -q` (exit 0):
```
.........................                                                [100%]
25 passed, 3 warnings in 7.99s
```

`venv\Scripts\python -m pytest tests/ -q` (exit 0):
```
375 passed, 3 warnings in 135.09s (0:02:15)
```

`venv\Scripts\python -m ruff check app/ tests/` (exit 0): `All checks passed!`

`node --check frontend/static/js/api.js` (exit 0)

`git diff --check` (exit 0, only pre-existing CRLF-on-touch warnings, no real errors)

Not done (deferred to 1.6c): TTS Audio Studio UI (`frontend/pages/step4_audio.html`) —
speaker voice assignment, per-line preview, sliders, "Generate All" button wired to
`/audio/generate`, player, download buttons.
