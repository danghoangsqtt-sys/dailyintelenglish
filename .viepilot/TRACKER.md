# TRACKER.md — Daily Intel English Studio

## Current Status

**Phase:** 1 — Full Feature Build  
**Day:** 1 / 21  
**Started:** 2026-09-10  
**Target:** 2026-09-30  

## Progress Overview

| Phase | Status | Tasks Done | Tasks Total |
|-------|--------|-----------|-------------|
| Phase 1 — Build | 🔄 In Progress | 9 | 40 |
| Phase 2 — Testing | ⏳ Not Started | 0 | 10 |
| Phase 3 — Review | ⏳ Not Started | 0 | 6 |

## Phase 1 Task Status

### 1.1 Project Setup
- [x] Python environment
- [x] Directory structure
- [x] FastAPI skeleton
- [x] SQLite setup
- [ ] Dependency check script — script itself works and now also checks the OmniVoice model dir, but the run is not all-GREEN yet (ffmpeg / .env / OmniVoice model missing on this machine) — see Known Issues. Not marking done until it reports GREEN.

### 1.2 Dashboard
- [x] ProjectService CRUD — full create/get/list/update/delete, validated (Pydantic), atomic speaker updates, config_json always kept in sync, forward-only status state machine. 30 automated tests (service-level + full HTTP via TestClient) pass.
- [ ] Dashboard UI — "New Project" navigates to `/step1` (Task 1.3); "Continue" now navigates to `/step2?project_id=...` for `draft`/`script_generated` projects (Task 1.4). Still no automated UI test for the dashboard page itself, so leaving unchecked.

### 1.3 Script Config Wizard
- [x] Config API route — `POST/GET/PUT/DELETE /api/projects[/{id}]`, `ScriptConfig`/`SpeakerConfig`/`ProjectUpdate` validated, invalid CEFR/genre/accent/status rejected with 422 in the standard envelope
- [x] Script Config UI — `frontend/pages/step1_config.html` + `step1_config.js`, full form (name, topic (required), CEFR, duration presets/custom, num_speakers sanitized to an integer 1–6, 10 genres, 10 accents, 6 language-feature toggles, speaker cards kept in exact sync with num_speakers), submits via `Api.createProject()` only, loading state + double-submit lock, friendly-only error banner (raw API errors go to console, never the UI — CR-05). On success, navigates to a minimal Step 2 entry-point placeholder (`/step2`) carrying the real `project_id` — no Task 1.4 logic implemented. Verified end-to-end in a real headless browser (Playwright): all 6 required scenarios pass, including num_speakers edge cases (2.5→3, empty→1, 0→1, 7→6), empty-topic blocking with 0 network requests, and API-error responses never leaking raw backend text into the UI.

### 1.4 AI Script Generation
- [x] Prompt templates (10 genres × CEFR) — `prompts/script/` (1 Jinja2 base + 10 genre blocks + 6 CEFR blocks), loaded async via `app/core/prompt_loader.py`. Solo-speaker mode overrides genre turn-pattern/balance rules; CEFR blocks state a ceiling, gated by the language-feature toggles (never a mandate); genre/CEFR validated against constants before any path is built. 101 tests. **Committed** (`2b1629d`).
- [x] ScriptService — `app/services/script_service.py`: `generate_script()` (Gemini REST via `httpx.AsyncClient`, `responseMimeType=application/json`, exponential backoff 1s→2s→4s on HTTP 429 only, Pydantic schema validation, speaker_id enforced as a real UUID belonging to the project — two-layer defense against hallucination), `regenerate_line()`, and DB persistence (`save_script`/`get_script`/`get_script_line`/`update_script_line`, using `line_index` + fresh UUIDs rather than Gemini's own collision-prone `line_001`-style ids) — exposed via `POST .../script/generate`, `POST .../script/regenerate`, `PUT .../script` (`app/api/projects.py`), errors routed through the existing global `AppError` handler (AR-04) with no per-route try/except needed. 153 tests pass.
- [x] Script Generation UI — `frontend/pages/step2_script.html` + `step2_script.js`: "Generate Script" (loading spinner + double-click lock), script viewer (color-coded speaker chips, `<details>` expand/collapse for language notes), per-line "Regenerate" (own spinner, only that card updates), click-to-edit text with textarea → autosave gathers the whole script and calls `PUT .../script`, "Regenerate All" (confirm() gate) and "Next: Learning Content →" (placeholder route for Task 1.5). `init()` loads any already-persisted script via the new `GET /api/projects/{id}/script` route so a reload or a revisit never shows a false empty state. `POST .../script/generate` and `PUT .../script` now advance `draft → script_generated` automatically (`app/api/projects.py::_advance_to_script_generated`), so the Dashboard's "Script Ready" filter and badge actually populate, and Dashboard's "Continue" button now navigates to `/step2?project_id=...` for `draft`/`script_generated` projects instead of being dead UI. 160 tests pass (7 new: GET /script empty/populated/404, status-transition on generate and on save, idempotent on repeat generate). Verified in a real headless browser end-to-end: create → generate (seeded via the real service layer, not mocked, to prove actual DB persistence) → F5 reload keeps the script and its language notes → Dashboard shows "Script Ready" → Continue reopens Step 2 with the full script intact → Regenerate All's confirm() dialog gates the overwrite.

### 1.5 Learning Content
- [ ] Prompt templates
- [ ] LearningContentService
- [ ] Learning Content UI

### 1.6 TTS Audio Studio
- [ ] TTSService — OmniVoice
- [ ] TTSService — Edge TTS
- [ ] AudioService
- [ ] TTS Audio Studio UI

### 1.7 Video Studio
- [ ] VideoService — Background + Subtitle
- [ ] VideoService — LivePortrait (if time)
- [ ] Video Studio UI

### 1.8 Thumbnail Generator
- [ ] ThumbnailService
- [ ] 5 thumbnail templates
- [ ] Thumbnail UI

### 1.9 YouTube Package
- [ ] YouTubePackageService
- [ ] YouTube Package UI

### 1.10 Music Library
- [ ] Music Library UI

## Decision Log

| Date | Decision | Rationale |
|------|----------|-----------|
| 2026-09-10 | Tech stack: Python FastAPI + Vanilla HTML/JS | Fastest development, lightest footprint |
| 2026-09-10 | Primary TTS: OmniVoice (local GPU) | RTX 3060 12GB — RTF 0.025, voice design support |
| 2026-09-10 | Subtitle: Both burned-in + SRT | Maximum flexibility for YouTube upload |
| 2026-09-10 | Thumbnail: Template + AI fill + Manual editor | Consistent branding + flexibility |
| 2026-09-10 | Video: Level 3 with fallback strategy | Ambitious goal, safe fallback to background+subtitle |
| 2026-09-10 | Lips-sync: LivePortrait (priority) | Fastest inference, most VRAM-efficient |
| 2026-09-10 | All env vars namespaced under `DIE_` prefix (`DIE_DEBUG`, `DIE_APP_PORT`, `DIE_GEMINI_API_KEY`, ...) | Bare names like `DEBUG`/`APP_HOST` can already be set system-wide and previously crashed startup on bad types (e.g. `DEBUG=release`) or leaked into config unintentionally |
| 2026-09-10 | `ProjectUpdate` rejects explicit JSON `null`; `num_speakers`/`speakers` can only change together (atomic replace); `status` can only move exactly one step forward through `draft → script_generated → audio_generated → video_generated → complete` | Prevent silent data loss on partial auto-save payloads, keep speaker rows and the `num_speakers` column from drifting apart, and stop the UI/API from ever producing a project stuck in an inconsistent pipeline stage |
| 2026-09-10 | `config_json` is recomputed from the merged (current + patched) state on every `PUT /api/projects/{id}`, not just at creation | It was only ever written once at creation before, so it silently went stale after the first auto-save — now it's guaranteed to mirror the current columns/speakers on every write |
| 2026-09-10 | Step 1 wizard: `topic` is a required field client-side, `num_speakers` is always sanitized to a rounded integer clamped 1–6 before it drives speaker-card count, and API errors are logged to console but only ever shown to the user as one fixed friendly banner string | Code review during Task 1.3 caught three defects: decimal speaker counts produced a card count that didn't match the displayed number, an empty topic would silently reach Task 1.4 with nothing to generate a script from, and the error banner was echoing raw backend validation text (CR-05 violation) |
| 2026-09-10 | Step 2 had a placeholder page (`step2_placeholder.html`) through Task 1.3 that only displayed `project_id`/name | Proved the create → navigate handoff before pulling Task 1.4's script-generation scope forward. **Superseded in Task 1.4**: `step2_placeholder.html` deleted, `/step2` now serves the real `step2_script.html` |
| 2026-09-10 | `ScriptService` calls the Gemini REST endpoint directly via `httpx.AsyncClient` instead of the `google-generativeai` SDK | Native async (no `asyncio.to_thread`), direct control over HTTP status codes to detect 429 for backoff, and trivially mockable in tests (fake HTTP responses, no SDK internals to patch) |
| 2026-09-10 | Gemini script output is validated in two layers: Pydantic enforces `speaker_id` parses as a UUID, then the service checks that UUID is one of the project's actual speakers | A syntactically valid but hallucinated UUID would otherwise pass schema validation and fail later at the DB foreign-key layer with a much less useful error |
| 2026-09-10 | `script_lines.id` is always a freshly generated UUID (not Gemini's own `line_001`-style label); line order is tracked via the existing `line_index` column | Gemini's own per-response line ids aren't unique across projects/regenerations, and the schema already has `line_index` for ordering — same pattern as `speakers.speaker_index` |
| 2026-09-10 | Added `GET /api/projects/{id}/script`; `POST .../script/generate` and `PUT .../script` auto-advance a `draft` project to `script_generated` | PM review of the first Sprint 1.4D UI caught that `script_service.get_script()` existed but was never exposed, so Step 2 always showed the empty "Generate" state on reload/revisit — the "no GET route" call was framed as an intentional scope cut but was actually a data-loss risk (re-generate would silently overwrite an existing script) and a broken state machine (Dashboard's "Script Ready" filter never triggered) |

## Known Issues

- `ffmpeg` not found in PATH on this machine — blocks Task 1.6 (Audio) / 1.7 (Video). Needs manual install by user.
- `.env` not created yet — `DIE_GEMINI_API_KEY` unset, blocks Task 1.4 (Script Generation) once it calls Gemini. `.env.example` added (now with the `DIE_` env-var prefix — see Decision Log); user must copy it to `.env` and fill in the key.
- OmniVoice model not downloaded yet (`models/omnivoice` empty) — blocks Task 1.6 (TTS). `scripts/check_dependencies.py` now checks for this explicitly.
- None of the three items above are code bugs; they're machine/secrets setup the user must do locally.

## Version

- App version: 0.1.0
- crystallize_version: 0.8.0
- crystallized_at: 2026-09-10T07:55:00+07:00

## Backlog

### Pending Requests
| ID | Type | Title | Priority | Status |
|----|------|-------|----------|--------|
| ENH-001 | Enhancement | Phân quyền AI Agents (PM vs Dev) | high | done |
