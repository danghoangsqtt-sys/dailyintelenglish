# Phase 1 State — Full Feature Build

## Metadata
- **Phase:** 1
- **Slug:** 01-full-feature-build
- **Status:** in_progress
- **Started:** 2026-09-10
- **Current Day:** Day 3 / 21 (2026-09-12)
- **Target Completion:** 2026-09-17
- **Milestone Progress:** 5 / 10 major tasks (50%)
- **Subtask Progress:** 21 / 29 granular subtasks (72%)
- **Test Suite Status:** 350 passed (218 unit/integration + 5 browser E2E + 7 dashboard browser E2E + 22 TTS unit/API + 19 music unit/API/browser + 44 thumbnail prompt/service/API/browser + 36 YouTube prompt/service/API/browser), ruff clean. One pre-existing flaky test in `test_script_service.py` observed twice under full-suite load in earlier sessions (not in the most recent run), confirmed passing in isolation both times — tracked, not a regression.

---

## Tasks Status & Acceptance Evidence

### Task 1.1: Project Setup & Infrastructure
- **Status:** ✅ Done (2026-09-13)
- **Details:**
  - Python virtual environment configured (`venv`).
  - Directory structure created: `app/`, `frontend/`, `data/`, `prompts/`, `models/`, `tests/`.
  - FastAPI skeleton initialized (`app/main.py`) with CORS, lifespan, router mounts, `/health` 200.
  - SQLite database initialized (`app/db/database.py`) with schema tables.
  - Dependency check script (`scripts/check_dependencies.py`) now reports all-GREEN on this
    machine (ffmpeg, GPU, Gemini key, OmniVoice model, data dirs all resolved this session).

### Task 1.2: Dashboard & Project Management
- **Status:** ✅ Done
- **Details:**
  - `ProjectService` CRUD fully implemented with Pydantic validation, atomic speaker replacement, `config_json` auto-sync, and forward-only status state machine.
  - **Evidence:** 30 automated service and HTTP API tests pass (`tests/test_projects_api.py`, `tests/test_project_service.py`).
  - Dashboard UI (`frontend/pages/dashboard.html`): loads, routes to `/step1` on "New Project" and `/step2?project_id=...` on "Continue".
  - **Evidence:** 7 automated Playwright browser tests (`tests/test_dashboard_browser.py`) covering listing/status badges, filter, search, empty state, New Project navigation, Continue navigation, and delete-after-confirm.

### Task 1.3: Step 1 — Script Config Wizard
- **Status:** ✅ Done
- **Details:**
  - Config API route (`POST /api/projects` + `ScriptConfig`/`SpeakerConfig`) operational.
  - Step 1 Config UI (`frontend/pages/step1_config.html`, `frontend/static/js/step1_config.js`) complete.
  - Required topic validation, integer-clamped num_speakers (1–6), speaker card sync, friendly error banners.
  - **Evidence:** Headless browser E2E (Playwright) verified all 6 scenarios; 30 unit/integration tests.

### Task 1.4: Step 2 — AI Script Generation
- **Status:** ✅ Done
- **Details:**
  - Jinja2 prompt templates for 10 genres × 6 CEFR levels (`prompts/script/`).
  - `ScriptService` with REST Gemini API, 429 exponential backoff, UUID speaker validation, DB persistence.
  - Step 2 Script UI (`frontend/pages/step2_script.html`, `frontend/static/js/step2_script.js`) with per-line editing, single-line regen, confirm dialog for "Regenerate All".
  - **Hardening (1.4D-FIX2/FIX2B/FIX2C gate):** Connection-wide `_write_lock` shared across both `_read_transaction` and `_write_transaction` preventing cross-project race conditions and dirty reads; `GEMINI_MODEL` updated to `gemini-3.8-flash`.
  - **Evidence:** 166 automated tests pass (`tests/test_script_service.py`, `tests/test_projects_write_lock.py`, etc.); real headless browser E2E verified.

### Task 1.5: Step 3 — Learning Content
- **Status:** ✅ Done
- **Details:**
  - Prompt templates (`prompts/learning/learning_pack.txt`).
  - `LearningContentService` (`app/services/learning_service.py`) generating vocabulary, idioms, grammar, and quizzes with `LearningPackOut` schema validation.
  - `learning_contents` table with UPSERT persistence.
  - Step 3 UI (`frontend/pages/step3_learning.html`, `frontend/static/js/step3_learning.js`) with 4 tabs, coalesced trailing autosave, dirty state tracking.
  - **Evidence:** 20 dedicated service/API tests, 223 total tests passing cleanly (218 unit/integration + 5 browser E2E).

### Task 1.6: Step 4 — TTS Audio Studio
- **Status:** ✅ Done (2026-09-13) for all 3 sub-tasks (1.6a/1.6b/1.6c). Real OmniVoice GPU
  inference remains open, blocked on a user design decision (not part of the sub-task
  split) — see TRACKER.md.
- **Details:** Split into sub-tasks since ffmpeg/OmniVoice model were unavailable on this
  machine at the time (now resolved — see Known Issues).
  - **1.6a DONE:** `TTSService.synthesize_line()` — Edge TTS synthesis (all 10 accents x
    3 genders mapped in `EDGE_TTS_VOICE_MAP`, live-verified 20/20), OmniVoice path with
    `asyncio.Semaphore(2)` and an honest not-yet-available fallback (no model weights on
    this machine), retry-once-on-empty-audio for a real transient Edge TTS failure found
    during live testing. Routes: `POST /api/projects/{id}/tts/preview`,
    `GET /api/projects/{id}/tts/cache/{line_id}.mp3`. 22 new tests, 252 total passing.
  - **1.6b DONE (2026-09-13):** `AudioService.mix_project()` — real silence gaps
    (300ms/500ms same/different speaker), real ITU-R BS.1770 loudness normalization to
    -16 LUFS (`pyloudnorm`), background-music static-level ducking, MP3+WAV export,
    real per-line timestamps JSON. Routes: `POST/GET /api/projects/{id}/audio/generate`,
    `/status`, `/download`. Real bug found+fixed: this pydub version's `ffprobe` lookup
    ignores `AudioSegment.converter`, needed a process-PATH shim for `DIE_FFMPEG_PATH`.
    25 new tests (real ffmpeg pipeline, not mocked), 375 total passing. Also closes
    Task 1.10's deferred background-music/loudness piece.
  - **1.6c DONE (2026-09-13):** `frontend/pages/step4_tts.html` + `step4_tts.js` at
    `/step4` (superseded placeholder deleted). Speaker voice-assignment panel (per-speaker
    autosave via a new narrow `PATCH /api/projects/{id}/speakers/{speaker_id}` — added
    specifically because the existing full-replace `PUT /{id}` speakers path would
    cascade-delete `script_lines` once a script exists, a real landmine found during
    planning and proved with a regression test before being avoided by design), per-line
    preview, background-music selector, sequential "Generate All" (synthesize each line,
    then mix — `AudioService` never calls TTS itself), MP3/WAV download. 13 new tests
    (6 API + 7 Playwright E2E, network-mocked), 388 total passing.

### Task 1.7: Step 5 — Video Studio
- **Status:** ✅ Done (2026-09-13) for both sub-tasks (1.7a backend, 1.7b UI). Level 3
  LivePortrait avatar lip-sync remains open, blocked on a user decision on avatar image
  sourcing (same class of blocker as OmniVoice's `ref_audio`) — not part of the sub-task
  split.
  - **1.7a DONE (2026-09-13):** `app/services/video_service.py` — real ffmpeg-rendered MP4
    from a project's completed audio mix (Task 1.6) + one of 3 fixed pre-rendered
    background templates (`frontend/static/video_backgrounds/`, via
    `scripts/generate_video_background_assets.py`) + real burned-in subtitles (ffmpeg
    `subtitles` filter/libass, confirmed present in the installed build via a real
    proof-of-concept before any production code was written). SRT built from
    AudioService's real measured per-line timestamps, extended with a `text` field
    (small backward-compatible change) so subtitles carry actual dialogue.
    `GET /api/video/templates`, `POST/GET /api/projects/{id}/video/{generate,status,download}`.
    20 new tests (real ffmpeg pipeline, not mocked), 407/408 pass (1 pre-existing
    unrelated flaky Gemini-retry test confirmed passing in isolation). Live-smoke-tested
    end-to-end with a real extracted video frame confirming correct speaker name +
    dialogue burned in.
  - **1.7b DONE (2026-09-13):** `frontend/pages/step5_video.html` + `step5_video.js` at
    `/step5` — background-template selector (3 fixed templates, no custom upload UI),
    synchronous Generate (no fake progress bar), `<video>` preview, MP4/SRT downloads,
    empty state directing back to Step 4 when no audio exists yet. `/step4` gained its
    first pipeline-nav button ("Next: Video Studio →"). 7 new Playwright tests
    (network-mocked), 428/428 total tests pass. Live-smoke-tested end-to-end through the
    real API and took a real screenshot to confirm visual consistency.

### Task 1.8: Step 6 — Thumbnail Generator
- **Status:** ✅ Done (2026-09-12)
- **Details:** By Codex, PM-accepted 2026-09-12.
  - **1.8a:** `ThumbnailService` — Gemini text/palette suggestions (`responseJsonSchema`,
    exact-count + duplicate-rejection Pydantic validation, no vision call needed — text-only),
    5 deterministic Pillow templates (`minimal_clean`, `gradient_bold`, `modern_split`,
    `dynamic_wave`, `podcast_classic`) using Pillow's embedded scalable default font (no
    system/hardcoded font path), render+persist with rollback-safe filesystem/DB sequencing
    (new files staged before the DB swap, old files removed only after commit), safe content
    route `GET /api/projects/{id}/thumbnails/{thumbnail_id}/{aspect}.{format}`. 27 new tests
    (6 prompt + 11 service + 10 API). PM independently re-rendered all 5 templates from the
    actual service code and visually confirmed professional-quality output.
  - **1.8b:** `/step6` interactive UI — template gallery, generate/regenerate (confirm-gated),
    exclusive favorite selection (`select_favorite`, one atomic `UPDATE ... CASE WHEN`),
    manual headline/color editor with optimistic-concurrency re-render (`update_thumbnail_revision`
    is a true SQL-level compare-and-swap; stale edits get `ConflictError` 409), cache-busted
    asset URLs (`?revision=` token). Full `saved`/`dirty`/`saving`/`failed` async-safety state
    machine in `step6_thumbnail.js` matching the established Step 2/3 pattern. Codex's session
    ran out of quota mid-implementation before writing its own evidence report; PM independently
    read every changed file end-to-end and ran a fresh full verification pass before accepting.
    17 new tests (11 service/API + 6 real-browser Playwright). 314 total tests pass, ruff clean.

### Task 1.9: Step 7 — YouTube Package
- **Status:** ✅ Done (2026-09-13) — both sub-tasks (1.9a, 1.9b) complete
- **Details:** By Claude Code acting as both PM and Implementer (Codex ran out of quota).
  - **1.9a DONE:** `YouTubeService.generate_package()` — 3 Gemini-generated title variants
    (click_worthy/educational/seo), description, tags (`YOUTUBE_TAGS_MAX_CHARS` enforced),
    and honestly-estimated chapters (`estimate_chapters()`, pure word-count-based function,
    no real audio duration exists yet). New migration `003_youtube_package.sql` (dropped
    and recreated the never-used `youtube_packages` table, same precedent as
    `002_learning_content.sql`). `/step7` read-only display UI with copy-to-clipboard and
    confirm-gated Regenerate. 30 new backend tests + 6 real-browser Playwright tests.
    Caught and fixed 2 real bugs before landing: a tag-whitespace DB round-trip bug (unit
    test) and a `[hidden]`-attribute-vs-CSS-specificity bug on `#generate-panel` (only
    caught by an actual browser visibility assertion, not a unit test).
  - **1.9b DONE (2026-09-13):** Chapters now **measured** from AudioService's real
    per-line timestamps when a project's audio exists (`real_chapters_from_timestamps()`),
    falling back to the 1.9a word-count estimate otherwise — `chapters_estimated` on the
    row says which, additive migration `004_youtube_chapters_measured.sql`. New
    `GET .../youtube/export` streams an in-memory `.zip` (video.mp4 + subtitles.srt +
    thumbnail.png + metadata.txt) once a completed video and a selected favorite
    thumbnail both exist. `/step7` UI shows the correct estimated-vs-measured label and a
    real download link (disabled with an explanatory note until ready). 13 new tests
    (real end-to-end pipeline test included, not mocked), 421 total pass. Caught a real
    bug via a browser test: the frontend defaulted to claiming "Measured" when
    `chapters_estimated` was simply undefined — fixed to require an explicit `=== false`.

### Task 1.10: Music Library
- **Status:** ✅ Done (2026-09-13) — all acceptance criteria complete
- **Details:** By Codex (second AI Implementer), PM-accepted 2026-09-12; loudness/ducking
  piece delivered by PM (Claude Code) in Task 1.6 Sub-task 1.6b; waveform visualization
  delivered by PM (Claude Code) in Sub-task 1.10c.
  - **1.10a DONE:** ffmpeg-independent Music Library UI at `/music` — upload (50MB limit,
    magic-byte validation, atomic no-clobber duplicate naming via `os.link`), list, native
    `<audio>` preview, confirm-gated delete. `app/api/music.py`
    (`GET/POST /api/music`, `GET/DELETE /api/music/{filename}`), `ARCHITECTURE.md` synced.
    19 new tests (15 API incl. a real `ThreadPoolExecutor`/`Barrier` concurrency test, 4
    Playwright browser E2E). 271 total tests pass.
  - **Volume leveling + Step 4/5 background-track selection/ducking — DONE (2026-09-13):**
    delivered as part of Task 1.6 Sub-task 1.6b (`app/services/audio_service.py`, real
    ITU-R BS.1770 loudness normalization + static-level ducking) and 1.6c (the `/step4`
    background-music `<select>`), not as a separate "1.10b" — see Task 1.6 above.
  - **Waveform visualization — DONE (2026-09-13), Sub-task 1.10c:** new
    `frontend/static/js/waveform.js` decodes each track via the Web Audio API and draws a
    real canvas waveform with played/unplayed tinting and click-to-seek, wired into
    `/music`'s track cards. Verified with real pydub-generated audio (not the existing
    tests' fake `ID3...` byte string, which doesn't decode) — confirmed real pixels drawn
    and accurate seek behavior via a disposable Playwright script before committing the
    permanent test suite. 4 new tests, 432 total tests pass. **Closes Task 1.10.**
