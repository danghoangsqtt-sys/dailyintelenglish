# Task 1.6: Step 4 — TTS Audio Studio

## Meta
- **ID**: 1.6
- **Phase**: 1
- **Status**: done (2026-09-13) for all 3 sub-tasks (1.6a Edge TTS, 1.6b AudioService, 1.6c
  UI) — the only remaining item is real OmniVoice GPU inference, which was never part of
  the sub-task split and stays blocked on a user design decision (see Acceptance Criteria
  item 1 and TRACKER.md)
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
- [x] TTS UI supports audio preview, regeneration, and export — Sub-task 1.6c (regeneration
  = per-line "Preview" re-synthesizes and overwrites the cache; export = MP3/WAV download)

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

## Implementation Notes (2026-09-13, Sub-task 1.6c: TTS Audio Studio UI)

User is unreachable for this session (traveling) and explicitly authorized autonomous
PM+Implementer decisions with strict self-verification — no scope invented beyond
ROADMAP.md's Task 1.6 "TTS Audio Studio UI" bullet, and no shortcuts that could corrupt
project data.

**Real landmine found during planning, avoided by design (not by luck):** the existing
`PUT /api/projects/{id}` (`ProjectUpdate.speakers`) does a full delete-and-reinsert of every
speaker row with brand-new UUIDs (`project_service._replace_speakers`). That's harmless at
Step 1 (no script exists yet), but `script_lines.speaker_id` has `ON DELETE CASCADE` —
calling that same endpoint from Audio Studio (reached only once a script already exists)
to tweak a speaker's engine/speed/pitch/volume would silently **cascade-delete the entire
script**. Audio Studio must never call that route. Instead: a new, narrow
`PATCH /api/projects/{id}/speakers/{speaker_id}` that updates columns in place by id,
never deletes/reinserts anything.

Scope (ROADMAP.md Task 1.6 "TTS Audio Studio UI" bullet):
- Speaker voice assignment panel: per-speaker card with an engine dropdown and
  speed/pitch/volume sliders, autosaved via the new PATCH route.
  - Engine dropdown offers only `omnivoice` and `edge_tts` — the two engines
    `tts_service.synthesize_line()` actually branches on today. `piper`/`google`/`azure`
    exist in `TTS_ENGINES`/DB schema but aren't wired to any real synthesis path yet;
    listing them as selectable options would silently no-op to Edge TTS, which is
    misleading, so they're left out of this dropdown (not a data-model change).
  - `omnivoice` shows an inline note that it currently falls back to Edge TTS
    automatically (honest, matches `tts_service.py`'s real behavior — model integration
    is a separate, deliberately-deferred decision, see TRACKER.md).
- "Preview" button per script line → calls `POST .../tts/preview`, plays the result via
  `GET .../tts/cache/{line_id}.mp3` in a plain `<audio>` element.
- Background music selector: `<select>` populated from `GET /api/music` (Task 1.10);
  "None" is a valid choice. Selection lives in page state only (no project-table column
  for it — same reasoning `audio_service.py` already documented for 1.6b).
- "Generate All" button: since `AudioService.mix_project()` deliberately only processes
  *already-synthesized* lines (module boundary from 1.6b — it never calls a TTS engine
  itself), this button must orchestrate both steps client-side: synthesize every script
  line **sequentially** (not parallel — respects `MAX_CONCURRENT_TTS`/OmniVoice's
  semaphore intent and avoids hammering the free Edge TTS endpoint, matching this task's
  Forbidden Scope "No VRAM exhaustion without fallback"), showing "Synthesizing line X/N…"
  progress, then call `POST .../audio/generate` with the selected background music.
- Final player: a plain `<audio controls>` element pointing at the mix. **No waveform
  visualization** — that's a visual-only UI element with no task assigned anywhere in
  TRACKER/ROADMAP yet (same standing gap already noted for the Music Library page); not
  invented here to keep scope matched to what was actually asked.
- Download MP3 / WAV buttons: plain links to
  `GET .../audio/download?format=mp3|wav`.
- Verify: full flow — assign a speaker's engine/sliders, preview a line, pick background
  music, Generate All, player + both downloads.

Files:
- `app/models/project.py`: new `SpeakerUpdate` (all fields optional: `tts_engine`,
  `voice_description`, `speed`, `pitch`, `volume` — no `name`/`gender`/`accent`, those are
  Step 1 persona fields out of scope here), reusing the same `TTS_ENGINES`/speed/pitch/
  volume bounds already validated on `SpeakerConfig`.
- `app/services/project_service.py`: new `update_speaker(db, project_id, speaker_id, patch,
  commit=True) -> dict` — `UPDATE speakers SET ... WHERE id = ? AND project_id = ?` (in
  place, no delete), 404 if the speaker doesn't belong to the project, returns the full
  refreshed project (frontend needs the whole speakers list back to re-render).
- `app/api/projects.py`: new `PATCH /{project_id}/speakers/{speaker_id}` route, same
  `_write_transaction` pattern as the existing `PUT /{project_id}`.
- `frontend/static/js/api.js`: add `updateSpeaker`, `previewTtsLine`, `ttsCacheUrl`,
  `generateAudio`, `getAudioStatus`, `audioDownloadUrl` (music list/content-url methods
  already exist from Task 1.10).
- `frontend/pages/step4_tts.html` + `frontend/static/js/step4_tts.js` (new): same visual
  language and async-safety conventions as `step6_thumbnail.html`/`.js` (per-card
  save-status state machine, double-submit locks, friendly-only error banner — CR-05,
  `beforeunload` guard while anything is unsaved/in-flight).
- `app/main.py`: point the existing `/step4` route at `step4_tts.html` instead of the
  placeholder; delete `frontend/pages/step4_tts_placeholder.html` (fully superseded, not
  referenced anywhere else).
- `tests/test_projects_api.py`: new tests for `PATCH .../speakers/{id}` (success updates
  persist, 404 unknown speaker/project, invalid engine/out-of-range slider rejected 422,
  and — the specific regression this route exists to prevent — updating a speaker after a
  script exists does NOT delete any `script_lines` row).
- `tests/test_tts_audio_browser.py` (new): Playwright E2E using `page.route()` network
  mocking (same pattern as `tests/test_youtube_browser.py`) — no real TTS/ffmpeg calls
  needed for a frontend-logic test. Covers: speaker settings autosave, per-line preview
  playback, Generate All happy path (sequential synth progress -> mix -> player +
  downloads appear), and a friendly error on a failed generate.

Forbidden Scope for this sub-task: no waveform visualization, no changes to
`ProjectUpdate`/`_replace_speakers` (the existing Step 1 full-replace path stays exactly
as-is — it works correctly there), no OmniVoice UI beyond the honest fallback note, no
Step 5 Video Studio navigation (doesn't exist yet).

## Sub-task 1.6c Result (2026-09-13) — DONE

Delivered exactly the plan above. New: `frontend/pages/step4_tts.html` +
`frontend/static/js/step4_tts.js` (registered at `/step4` in `app/main.py`, replacing and
deleting the now-superseded `step4_tts_placeholder.html`), `SpeakerUpdate` model,
`project_service.update_speaker()`, `PATCH /api/projects/{id}/speakers/{speaker_id}`, 6
new `api.js` methods. 13 new tests (6 in `tests/test_projects_api.py` for the speaker
route, 7 in `tests/test_tts_audio_browser.py`, Playwright + network-mocked, same pattern
as `tests/test_youtube_browser.py`). 388/388 total tests pass, ruff clean, `node --check`
clean on both JS files, `git diff --check` clean.

**This closes Task 1.6 entirely** — all 3 sub-tasks (1.6a Edge TTS, 1.6b AudioService,
1.6c UI) done.

Real architectural landmine found during planning and avoided by design: `PUT
/api/projects/{id}` with `speakers` does a full delete-and-reinsert with new UUIDs
(`_replace_speakers`), and `script_lines.speaker_id` cascades on delete — reusing that
route from Audio Studio (reached only once a script exists) to tweak one speaker's
engine/sliders would have silently deleted the entire script. Verified this is a real,
reachable hazard (not theoretical) by writing
`test_update_speaker_after_script_exists_does_not_delete_script_lines` against the
*existing* `PUT` route first, confirming it does cascade-delete lines, before building the
new narrow `PATCH .../speakers/{id}` route that updates in place and leaves it untouched.

Live-verified with a real end-to-end smoke script (not just mocked route tests): served
`/step4` for real, created a project via the real API, saved a real script, PATCHed a
speaker's engine/speed (confirmed script_lines count unchanged after), synthesized both
lines via the real `tts_service` (Edge TTS network call mocked, pipeline otherwise real),
called real `audio_service.mix_project` end-to-end producing a real playable MP3, fetched
real `/audio/status` and `/audio/download`, and confirmed `projects.status` correctly
advanced `script_generated -> audio_generated`. Also took a real Playwright screenshot of
the rendered page to visually confirm layout/theme before calling this done — not just
trusting DOM assertions.

Not done (deliberately, no task assigned anywhere in TRACKER/ROADMAP): waveform
visualization on the final player (a visual-only UI element, same standing gap already
noted for the Music Library page); real OmniVoice GPU integration (separate, deferred
design decision — where does each speaker's `ref_audio` sample come from?); a forward
"Next Step" nav button from Step 4 (neither Step 5 Video Studio nor Step 6/7 have a
reciprocal nav contract to link into yet, so none was invented).

### Verification output

`venv\Scripts\python -m pytest tests/test_projects_api.py tests/test_tts_audio_browser.py -q` (exit 0):
```
....................                                                     [100%]
.......                                                                  [100%]
27 passed
```

`venv\Scripts\python -m pytest tests/ -q` (exit 0):
```
388 passed, 3 warnings in 127.03s (0:02:07)
```

`venv\Scripts\python -m ruff check app/ tests/` (exit 0): `All checks passed!`

`node --check frontend/static/js/api.js` (exit 0)
`node --check frontend/static/js/step4_tts.js` (exit 0)

`git diff --check` (exit 0, only pre-existing CRLF-on-touch warnings, no real errors)
