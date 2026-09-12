# Phase 1 State — Full Feature Build

## Metadata
- **Phase:** 1
- **Slug:** 01-full-feature-build
- **Status:** in_progress
- **Started:** 2026-09-10
- **Current Day:** Day 2 / 21 (2026-09-11)
- **Target Completion:** 2026-09-17
- **Milestone Progress:** 4 / 10 major tasks (40%)
- **Subtask Progress:** 18 / 29 granular subtasks (62%)
- **Test Suite Status:** 298 passed (218 unit/integration + 5 browser E2E + 7 dashboard browser E2E + 22 TTS unit/API + 19 music unit/API/browser + 27 thumbnail prompt/service/API), ruff clean. One pre-existing flaky test in `test_script_service.py` observed twice under full-suite load, confirmed passing in isolation both times — tracked, not a regression.

---

## Tasks Status & Acceptance Evidence

### Task 1.1: Project Setup & Infrastructure
- **Status:** 🔄 In Progress (4 / 5 subtasks complete)
- **Details:**
  - Python virtual environment configured (`venv`).
  - Directory structure created: `app/`, `frontend/`, `data/`, `prompts/`, `models/`, `tests/`.
  - FastAPI skeleton initialized (`app/main.py`) with CORS, lifespan, router mounts, `/health` 200.
  - SQLite database initialized (`app/db/database.py`) with schema tables.
  - Dependency check script (`scripts/check_dependencies.py`) verified in code; waiting on local machine environment setup (`ffmpeg`, `.env` key, local model weights).

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
- **Status:** 🔄 In Progress (Sub-task 1.6a done; 1.6b/1.6c pending)
- **Details:** Split into sub-tasks since ffmpeg/OmniVoice model are unavailable on this
  machine (see Known Issues).
  - **1.6a DONE:** `TTSService.synthesize_line()` — Edge TTS synthesis (all 10 accents x
    3 genders mapped in `EDGE_TTS_VOICE_MAP`, live-verified 20/20), OmniVoice path with
    `asyncio.Semaphore(2)` and an honest not-yet-available fallback (no model weights on
    this machine), retry-once-on-empty-audio for a real transient Edge TTS failure found
    during live testing. Routes: `POST /api/projects/{id}/tts/preview`,
    `GET /api/projects/{id}/tts/cache/{line_id}.mp3`. 22 new tests, 252 total passing.
  - **1.6b (AudioService, mixing/normalization) and 1.6c (TTS Studio UI):** deferred until
    `ffmpeg` is installed on this machine.

### Task 1.7: Step 5 — Video Studio
- **Status:** ⏳ Planned
- **Details:** VideoService (background + subtitle burned + SRT), LivePortrait, Video UI.

### Task 1.8: Step 6 — Thumbnail Generator
- **Status:** 🔄 In Progress (Sub-task 1.8a done; 1.8b pending)
- **Details:** By Codex, PM-accepted 2026-09-12.
  - **1.8a DONE:** `ThumbnailService` — Gemini text/palette suggestions (`responseJsonSchema`,
    exact-count + duplicate-rejection Pydantic validation, no vision call needed — text-only),
    5 deterministic Pillow templates (`minimal_clean`, `gradient_bold`, `modern_split`,
    `dynamic_wave`, `podcast_classic`) using Pillow's embedded scalable default font (no
    system/hardcoded font path), render+persist with rollback-safe filesystem/DB sequencing
    (new files staged before the DB swap, old files removed only after commit), safe content
    route `GET /api/projects/{id}/thumbnails/{thumbnail_id}/{aspect}.{format}`. 27 new tests
    (6 prompt + 11 service + 10 API). PM independently re-rendered all 5 templates from the
    actual service code and visually confirmed professional-quality output.
  - **1.8b (interactive UI — template gallery, manual editor, download):** deferred, needs its
    own plan/review.

### Task 1.9: Step 7 — YouTube Package
- **Status:** ⏳ Planned
- **Details:** YouTubePackageService, metadata/tags/chapters generator, UI.

### Task 1.10: Music Library
- **Status:** 🔄 In Progress (Sub-task 1.10a done; 1.10b pending)
- **Details:** By Codex (second AI Implementer), PM-accepted 2026-09-12.
  - **1.10a DONE:** ffmpeg-independent Music Library UI at `/music` — upload (50MB limit,
    magic-byte validation, atomic no-clobber duplicate naming via `os.link`), list, native
    `<audio>` preview, confirm-gated delete. `app/api/music.py`
    (`GET/POST /api/music`, `GET/DELETE /api/music/{filename}`), `ARCHITECTURE.md` synced.
    19 new tests (15 API incl. a real `ThreadPoolExecutor`/`Barrier` concurrency test, 4
    Playwright browser E2E). 271 total tests pass.
  - **1.10b (waveform visualization, volume leveling, Step 4/5 background-track
    selection/ducking):** deferred — needs `ffmpeg` AND the `audioop-lts` backport for
    `pydub` (Python 3.14 removed the stdlib `audioop` module it depends on).
