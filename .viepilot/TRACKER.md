# TRACKER.md — Daily Intel English Studio

## Current Status

**Phase:** 1 — Full Feature Build  
**Day:** 2 / 21  
**Started:** 2026-09-10  
**Target:** 2026-09-30  

## Progress Overview

*Task counting rule: Phase 1 has 10 major tasks (1.1–1.10) [currently 4/10 done, 40%] with 29 discrete checklist subtasks [currently 16/29 done, 55%]. Progress reflects completed subtasks.*

| Phase | Status | Tasks Done | Tasks Total |
|-------|--------|-----------|-------------|
| Phase 1 — Build | 🔄 In Progress | 16 | 29 |
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
- [x] Dashboard UI — "New Project" navigates to `/step1` (Task 1.3); "Continue" navigates to `/step2?project_id=...` for `draft`/`script_generated` projects (Task 1.4). 7 automated Playwright browser tests (`tests/test_dashboard_browser.py`): listing with status badges, status filter, name search, empty state, New Project navigation, Continue navigation, delete-after-confirm removes card without reload. 230 total tests pass.

### 1.3 Script Config Wizard
- [x] Config API route — `POST/GET/PUT/DELETE /api/projects[/{id}]`, `ScriptConfig`/`SpeakerConfig`/`ProjectUpdate` validated, invalid CEFR/genre/accent/status rejected with 422 in the standard envelope
- [x] Script Config UI — `frontend/pages/step1_config.html` + `step1_config.js`, full form (name, topic (required), CEFR, duration presets/custom, num_speakers sanitized to an integer 1–6, 10 genres, 10 accents, 6 language-feature toggles, speaker cards kept in exact sync with num_speakers), submits via `Api.createProject()` only, loading state + double-submit lock, friendly-only error banner (raw API errors go to console, never the UI — CR-05). On success, navigates to a minimal Step 2 entry-point placeholder (`/step2`) carrying the real `project_id` — no Task 1.4 logic implemented. Verified end-to-end in a real headless browser (Playwright): all 6 required scenarios pass, including num_speakers edge cases (2.5→3, empty→1, 0→1, 7→6), empty-topic blocking with 0 network requests, and API-error responses never leaking raw backend text into the UI.

### 1.4 AI Script Generation
- [x] Prompt templates (10 genres × CEFR) — `prompts/script/` (1 Jinja2 base + 10 genre blocks + 6 CEFR blocks), loaded async via `app/core/prompt_loader.py`. Solo-speaker mode overrides genre turn-pattern/balance rules; CEFR blocks state a ceiling, gated by the language-feature toggles (never a mandate); genre/CEFR validated against constants before any path is built. 101 tests. **Committed** (`2b1629d`).
- [x] ScriptService — `app/services/script_service.py`: `generate_script()` (Gemini REST via `httpx.AsyncClient`, `responseMimeType=application/json`, exponential backoff 1s→2s→4s on HTTP 429 only, Pydantic schema validation, speaker_id enforced as a real UUID belonging to the project — two-layer defense against hallucination), `regenerate_line()`, and DB persistence (`save_script`/`get_script`/`get_script_line`/`update_script_line`, using `line_index` + fresh UUIDs rather than Gemini's own collision-prone `line_001`-style ids) — exposed via `POST .../script/generate`, `POST .../script/regenerate`, `PUT .../script` (`app/api/projects.py`), errors routed through the existing global `AppError` handler (AR-04) with no per-route try/except needed. 153 tests pass.
- [x] Script Generation UI — `frontend/pages/step2_script.html` + `step2_script.js`: "Generate Script" (loading spinner + double-click lock), script viewer (color-coded speaker chips, `<details>` expand/collapse for language notes), per-line "Regenerate" (own spinner, only that card updates), click-to-edit text with textarea → autosave gathers the whole script and calls `PUT .../script`, "Regenerate All" (confirm() gate) and "Next: Learning Content →" (placeholder route for Task 1.5). `init()` loads any already-persisted script via the new `GET /api/projects/{id}/script` route so a reload or a revisit never shows a false empty state. `POST .../script/generate` and `PUT .../script` now advance `draft → script_generated` automatically (`app/api/projects.py::_advance_to_script_generated`), so the Dashboard's "Script Ready" filter and badge actually populate, and Dashboard's "Continue" button now navigates to `/step2?project_id=...` for `draft`/`script_generated` projects instead of being dead UI. 160 tests pass (7 new: GET /script empty/populated/404, status-transition on generate and on save, idempotent on repeat generate). Verified in a real headless browser end-to-end: create → generate (seeded via the real service layer, not mocked, to prove actual DB persistence) → F5 reload keeps the script and its language notes → Dashboard shows "Script Ready" → Continue reopens Step 2 with the full script intact → Regenerate All's confirm() dialog gates the overwrite.
- [x] **1.4D-FIX2 / FIX2B gate (PM-required hardening, closed before Sprint 1.5A)** — two rounds:
  - **FIX2**: `step2_script.js` autosave resyncs line ids from the `PUT .../script` response into the DOM and serializes overlapping autosaves (coalesced into one trailing save) instead of firing them concurrently; Regenerate is disabled for the full duration of an in-flight save; the Generate panel stays hidden (not just the script list) when loading the existing script fails, so Generate can never silently overwrite a script that just failed to load; script save + status-advance merged into one transaction with rollback; `GEMINI_MODEL` moved off the shut-down `gemini-2.0-flash` to `gemini-3.8-flash` (Google's current default Flash model, verified live).
  - **FIX2B**: the FIX2 rollback fix used a per-project `asyncio.Lock` (`defaultdict`), which only prevented same-project races — a PM review caught that every OTHER write endpoint (create/update/delete project, regenerate) touches the same shared singleton connection with zero locking, so an unrelated concurrent write could still interleave into (and be wiped out by) another request's rollback. Replaced with one connection-wide `_write_lock` (`app/api/projects.py::_write_transaction`), applied to **every** write route, with `db.commit()` moved inside the `try` so a commit failure also rolls back.
  - Test count: 160 → 163 (FIX2) → 165 (FIX2B, +2 deterministic concurrency/rollback tests in `tests/test_projects_write_lock.py`). `ruff check` clean, `pytest -x` 165/165, `node --check` clean, browser E2E (Playwright, real Chromium) green both rounds. Not committed — held pending PM sign-off.

### 1.5 Learning Content
- [x] Prompt templates — `prompts/learning/learning_pack.txt`, rendered async via `app/core/prompt_loader.py`
- [x] LearningContentService — `app/services/learning_service.py` (Gemini REST via `httpx.AsyncClient`, `gemini-3.8-flash`, 429 backoff 1s→2s→4s, Pydantic schema validation `LearningPackOut`, SQLite persistence `learning_contents` table with UPSERT and `commit` parameter). 20 tests. **Committed** (`b06eb07`).
- [x] Learning Content UI — `frontend/pages/step3_learning.html` + `step3_learning.js` + route `/step3` in `app/main.py`: 4 tabs (Vocabulary with IPA/PoS/definitions, Idioms, Grammar, Quiz with answer toggle), Coalesced Trailing Autosave with dirty-sections queue, Regenerate Pack confirm dialog, and Next Step navigation to `/step4`. 223 tests pass (218 unit/integration + 5 browser E2E).

### 1.6 TTS Audio Studio
- [ ] TTSService — OmniVoice — semaphore(2) + fallback logic implemented and tested, but no real GPU inference (no model weights on this machine, `models/omnivoice/` empty)
- [x] TTSService — Edge TTS — `app/services/tts_service.py`, `EDGE_TTS_VOICE_MAP` (10 accents x 3 genders), retry-once-on-empty-audio, live-verified 20/20 real synthesis calls. `POST /api/projects/{id}/tts/preview` + `GET .../tts/cache/{line_id}.mp3`. 22 new tests, 252 total pass.
- [ ] AudioService — deferred to Sub-task 1.6b (needs ffmpeg)
- [ ] TTS Audio Studio UI — deferred to Sub-task 1.6c (needs 1.6b)

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
| 2026-09-10 | `GEMINI_MODEL` moved from `gemini-2.0-flash` to `gemini-3.8-flash` | `gemini-2.0-flash` was shut down 2026-06-01; `gemini-3.8-flash` is Google's current "New Stable" default Flash model per `ai.google.dev/gemini-api/docs/models` (checked live, FIX2 gate) |
| 2026-09-10 | Every write endpoint on `app/api/projects.py` (create/update/delete project, script generate/regenerate/save) serializes on **one connection-wide** `asyncio.Lock` (`_write_transaction`), not a per-project lock | FIX2's first pass used a per-project lock, which only stops two requests for the *same* project from interleaving. PM review (FIX2B) found the whole app shares a single `aiosqlite` connection with exactly one implicit transaction at a time — an unrelated concurrent write (e.g. a project rename) could still interleave into another request's transaction and get wiped out by that request's `rollback()`. A connection-wide lock is the only correct fix given one shared connection; `db.commit()` was also moved inside the `try` so a commit failure rolls back too, not just a failure in the wrapped writes |
| 2026-09-11 | Gemini `generationConfig.temperature` is deliberately left unset (Gemini default) in `script_service.py` and `learning_service.py`, NOT pinned low | BUG-007 asked for a "deterministic output contract," but "Regenerate"/"Regenerate All"/"Regenerate Pack" resend the identical prompt expecting *different* wording each click — a low temperature would make Gemini return near-identical text every time, breaking that feature. Structural determinism (always-valid, schema-conforming JSON) is already guaranteed by `responseJsonSchema` + semantic validation (BUG-011), which is what actually matters for reliability; content-sampling determinism is neither required nor desirable here |
| 2026-09-11 | Task 1.2 closed via `/vp-auto` (PM-executed): added `tests/test_dashboard_browser.py` (7 Playwright tests — listing/badges, filter, search, empty state, New Project nav, Continue nav, delete-after-confirm) covering the last open acceptance criterion. No production code changes needed; dashboard.js already behaved correctly. 230/230 tests pass, ruff clean | `/vp-auto`; git tag `die-vp-p1-t1.2` |
| 2026-09-11 | Task 1.6 split into sub-tasks (1.6a/1.6b/1.6c) since `ffmpeg` and OmniVoice model weights are unavailable on this machine. Sub-task 1.6a (Edge-TTS-first) closed via `/vp-auto`: `TTSService.synthesize_line()`, `EDGE_TTS_VOICE_MAP` (all 10 accents x 3 genders, voice ids verified live against `edge_tts.list_voices()`), OmniVoice path wrapped in `asyncio.Semaphore(MAX_CONCURRENT_TTS)` with an honest "model not loaded" fallback (not a fake success), `POST /api/projects/{id}/tts/preview` + cache-serving route. Live smoke-testing across all 10 accents caught one transient real Edge TTS "no audio received" response — fixed by adding a retry-once-on-empty-audio guard *before* landing the sub-task, not shipped broken. Also fixed a latent event-loop-binding hazard on the new module-level `_omnivoice_semaphore` (same class of bug as `_write_lock`, same fix: reset per test in `conftest.py`). 22 new tests, 252/252 total pass, ruff clean | `/vp-auto`; git tag `die-vp-p1-t1.6a` |
| 2026-09-12 | User is bringing in Codex as a second AI Implementer (Claude Code stays PM). Generalized `SYSTEM-RULES.md` AR-06 from "PM-GEMINI" to "PM-Implementer" (binds whichever coding AI is assigned, not one vendor). Added `docs/CODEX_CODE_PROMPT.md` — Codex-specific variant of `docs/GEMINI_CODE_PROMPT.md`, same AR-06 contract, plus a mandatory environment-preflight step (Codex's sandbox may not match this Windows dev machine: ffmpeg/network/.env availability must be checked and reported, never assumed) and a stricter "paste real command output, not prose" evidence requirement given the BUG-010 false-claim incident. | User; PM (Claude Code) |
| 2026-09-11 | BUG-001 auto-logged by vp-audit Tier 1: restore valid machine-readable state | `vp-audit`; Backlog |
| 2026-09-11 | BUG-002 auto-logged by vp-audit Tier 1: reconcile Phase 1 progress counters | `vp-audit`; Backlog |
| 2026-09-11 | BUG-003 auto-logged by vp-audit Tier 1: enforce doc-first task gates | `vp-audit`; Backlog |
| 2026-09-11 | BUG-004 auto-logged by vp-audit Tier 2: synchronize project documentation | `vp-audit`; Backlog |
| 2026-09-11 | ENH-002 auto-logged by vp-audit Tier 2: restore diagram sidecars | `vp-audit`; Backlog |
| 2026-09-11 | BUG-005 auto-logged by vp-audit Tier 3: reject Learning Content null updates | `vp-audit`; Backlog |
| 2026-09-11 | BUG-006 auto-logged by vp-audit Tier 3: enforce nonblank project configuration | `vp-audit`; Backlog |
| 2026-09-11 | BUG-007 auto-logged by vp-audit Tier 3: deterministic Gemini output contract | `vp-audit`; Backlog |
| 2026-09-11 | BUG-008 auto-logged by vp-audit Tier 3: prevent UI lost updates and dead navigation | `vp-audit`; Backlog |
| 2026-09-11 | ENH-003 auto-logged by vp-audit Tier 3: strict PM-GEMINI delivery contract | `vp-audit`; Backlog |
| 2026-09-11 | BUG-009 auto-logged by vp-audit Tier 1: restore PM-only acceptance state after Gemini handoff | `vp-audit`; Backlog |
| 2026-09-11 | BUG-010 auto-logged by vp-audit Tier 2: reconcile stabilization documentation and delivery evidence | `vp-audit`; Backlog |
| 2026-09-11 | BUG-011 auto-logged by vp-audit Tier 3: send Pydantic schemas through the supported Gemini JSON Schema field | `vp-audit`; Backlog |
| 2026-09-11 | BUG-012 auto-logged by vp-audit Tier 3: close autosave failure races with browser-level regression coverage | `vp-audit`; Backlog |
| 2026-09-11 | PM audit review of all 15 `ready_for_review` requests: 11 accepted (BUG-001, 003, 004, 005, 006, 008, 011, 012, ENH-001, ENH-002, ENH-003) — `done`. 4 sent back `changes_requested`: BUG-002 (trailing whitespace on TRACKER.md:6 introduced by its own fix), BUG-007 (schema fixed but no `temperature` set — title promised "deterministic" output, not delivered), BUG-009 (stale "196 tests" left in ROADMAP.md/task-1.5.md), BUG-010 (**rejected — false claim**: implementer stated `git diff --check` exits 0 but it still exits 2 with the same 7 errors; README task numbering and ARCHITECTURE.md staging also unfixed despite being claimed done). See PM Acceptance/PM Review sections in each `.viepilot/requests/*.md` for full evidence. | PM (Claude Code); Backlog |
| 2026-09-11 | PM closed the remaining 4 items directly (user approved PM fixing in-session rather than round-tripping to GEMINI): **BUG-002** — corrected own finding: TRACKER.md:6's trailing spaces are the standard Markdown hard-line-break convention shared by lines 5/7/8, not a defect; no change made. **BUG-007** — corrected own finding: NOT setting `temperature` is the right call, not a gap — `step2_script.js`/`step3_learning.js` regenerate features depend on Gemini returning different wording for the same prompt each click; pinning temperature low would silently break "Regenerate". Structural determinism (BUG-007's actual acceptance criteria) is already satisfied via `responseJsonSchema` (BUG-011). **BUG-009** — fixed stale "196 tests" → "223 tests (218 unit/integration + 5 browser E2E)" in ROADMAP.md:111 and task-1.5.md:23; re-ran `pytest tests/ -q` live to confirm 223 before writing it. **BUG-010** — fixed README.md Task 1.7-1.10 numbering to match ROADMAP/TRACKER/SPEC (1.7=Video Studio, 1.8=Thumbnail, 1.9=YouTube Package, 1.10=Music Library; audio mixing folded into 1.6); re-verified whitespace/EOF and staging claims are now all true (`git diff --check` exit 0; ARCHITECTURE.md + walkthrough doc confirmed committed in `7c9f3d9`). All 15 Sprint 1.5R requests are now `done`. | PM (Claude Code); Backlog |

## Known Issues

- `ffmpeg` not found in PATH on this machine — blocks Task 1.6 (Audio) / 1.7 (Video). Needs manual install by user.
- `.env` not created yet — `DIE_GEMINI_API_KEY` unset, blocks Task 1.4 (Script Generation) once it calls Gemini. `.env.example` added (now with the `DIE_` env-var prefix — see Decision Log); user must copy it to `.env` and fill in the key.
- OmniVoice model not downloaded yet (`models/omnivoice` empty) — blocks Task 1.6 (TTS). `scripts/check_dependencies.py` now checks for this explicitly.
- None of the three items above are code bugs; they're machine/secrets setup the user must do locally.
- `pydub` (already in `requirements.txt`, used by the not-yet-built AudioService) fails to import on this venv's Python 3.14.7 with `ModuleNotFoundError: No module named 'audioop'` — Python 3.13 removed the `audioop` stdlib module (PEP 594) and `pydub` still depends on it. Will block Task 1.6 Sub-task 1.6b even once `ffmpeg` is installed, unless the `audioop-lts` PyPI backport is added to `requirements.txt` first. Discovered 2026-09-12 during PM review of Codex's Task 1.10 preflight (Codex's sandbox reported the same `pydub` import failure independently).

## Version

- App version: 0.1.0
- crystallize_version: 0.8.0
- crystallized_at: 2026-09-10T07:55:00+07:00

## Backlog

### Pending Requests
| ID | Type | Title | Priority | Status |
|----|------|-------|----------|--------|
| BUG-001 | Bug | Restore valid machine-readable ViePilot state | medium | done |
| BUG-002 | Bug | Reconcile Phase 1 progress counters | medium | done |
| BUG-003 | Bug | Enforce doc-first incremental task gates | medium | done |
| BUG-004 | Bug | Synchronize project documentation with implemented state | low | done |
| BUG-005 | Bug | Reject explicit null in Learning Content updates | high | done |
| BUG-006 | Bug | Enforce nonblank project configuration at API boundary | high | done |
| BUG-007 | Bug | Make Gemini output contract deterministic | high | done |
| BUG-008 | Bug | Prevent UI lost updates and dead Step 4 navigation | high | done |
| BUG-009 | Bug | Restore PM-only acceptance state after Gemini handoff | medium | done |
| BUG-010 | Bug | Reconcile stabilization documentation and delivery evidence | low | done |
| BUG-011 | Bug | Send Pydantic schemas through the supported Gemini JSON Schema field | high | done |
| BUG-012 | Bug | Close autosave failure races with browser-level regression coverage | high | done |
| ENH-001 | Enhancement | Phân quyền AI Agents (PM vs Dev) | high | done |
| ENH-002 | Enhancement | Restore architecture diagram sidecars | low | done |
| ENH-003 | Enhancement | Establish strict PM-GEMINI delivery contract | medium | done |
