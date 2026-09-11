# Changelog — Daily Intel English Studio

All notable changes to this project will be documented in this file.
Format: [Keep a Changelog](https://keepachangelog.com/en/1.0.0/)
Versioning: [SemVer](https://semver.org/)

---

## [Unreleased]

### Added
- Initial project crystallization from brainstorm session 2026-09-10
- Architecture design: FastAPI + OmniVoice + Gemini + ffmpeg stack
- 7-step production pipeline design
- SQLite database schema
- FastAPI skeleton (CORS, lifespan, routers), SQLite init via aiosqlite, dark-mode dashboard UI
- `ProjectService` full CRUD (create/get/list/update/delete) with validated Pydantic models (`ScriptConfig`, `SpeakerConfig`, `ProjectUpdate`) and `POST/GET/PUT/DELETE /api/projects[/{id}]`
- Forward-only project state machine: `draft → script_generated → audio_generated → video_generated → complete` — no skipping or reverting
- Atomic `num_speakers`/`speakers` updates — the two can only change together, keeping the `speakers` table and the `num_speakers` column consistent
- `config_json` is recomputed from the merged project state on every update, not only at creation
- Global `RequestValidationError` handler so Pydantic 422s use the same `{success, data, error, meta}` envelope as every other response
- All settings namespaced under a `DIE_` env-var prefix, so generic system env vars (e.g. bare `DEBUG`) can no longer crash startup or leak into config
- `scripts/check_dependencies.py` now checks the configured ffmpeg path and Gemini API key the same way the app itself resolves them (`settings.FFMPEG_PATH`, `settings.GEMINI_API_KEY`), plus a new OmniVoice model directory check
- `ruff` added as the lint gate; 30 automated tests (`pytest`) covering project CRUD, validation, and dependency-check logic
- Step 1 — Script Config wizard (`/step1`): full form (name, topic, CEFR, duration presets/custom, num_speakers, 10 genres, 10 accents, 6 language-feature toggles, dynamic speaker cards), submitting via `Api.createProject()` with a loading state, double-submit lock, and a friendly-only error banner (raw API errors are logged to console, never shown to the user)
- Dashboard's "New Project" button now opens `/step1` instead of a placeholder alert
- A minimal Step 2 entry-point placeholder (`/step2`) that carries the created `project_id`/name — the real Step 2 UI ships in Task 1.4
- Script prompt templates (`prompts/script/`): 1 Jinja2 base + 10 genre blocks + 6 CEFR blocks, loaded async via `app/core/prompt_loader.py`
- `ScriptService` (`app/services/script_service.py`): `generate_script()`/`regenerate_line()` via the Gemini REST API (`httpx.AsyncClient`, `responseMimeType=application/json`, exponential backoff 1s→2s→4s on HTTP 429 only), plus persistence (`save_script`/`get_script`/`get_script_line`/`update_script_line`)
- Step 2 — Script Generation UI (`/step2`, `step2_script.html`/`.js`) replacing the Task 1.3 placeholder: generate, per-line regenerate, click-to-edit with autosave, "Regenerate All", and `GET /api/projects/{id}/script` so a reload/revisit never loses the script
- `POST .../script/generate` and `PUT .../script` auto-advance a project from `draft` to `script_generated`
- Step 3 — Learning Content Wizard & Service (Task 1.5):
  - `LearningContentService` (`app/services/learning_service.py`): generates structured vocabulary (with IPA, part of speech, bilingual definitions, examples), idioms, grammar points, and comprehension quiz via Gemini REST API (`gemini-3.8-flash`) with strict JSON schema enforcement (`responseJsonSchema`) and retry/backoff on 429
  - Dedicated SQLite table `learning_contents` (`app/db/migrations/002_learning_content.sql`) with UPSERT and foreign key cascade to `projects(id)`
  - REST endpoints: `POST /api/projects/{id}/learning/generate`, `GET /api/projects/{id}/learning`, and `PUT /api/projects/{id}/learning`
  - Step 3 UI (`frontend/pages/step3_learning.html`, `step3_learning.js`): 4-tab interface (Vocabulary, Idioms, Grammar, Quiz with answer reveal), inline editing, coalesced trailing autosave, and "Regenerate Pack" confirmation modal
  - Step 4 placeholder entry point (`frontend/pages/step4_tts_placeholder.html`, `GET /step4`)
- `ENH-002`: Architecture diagram sidecars (`.viepilot/architecture/data-flow.mermaid`, `module-dependencies.mermaid`) and Diagram source references in `ARCHITECTURE.md`
- `ENH-003`: Gemini Implementer Delivery Protocol and contract (`docs/GEMINI_CODE_PROMPT.md`, `.viepilot/SYSTEM-RULES.md`, updated `CLAUDE_CODE_PROMPT.md`)

### Fixed
- Step 2 autosave now resyncs script-line ids from the `PUT .../script` response (the save always reissues fresh ids) and serializes overlapping autosaves into one coalesced trailing save instead of firing them concurrently; Regenerate is disabled for the full duration of an in-flight save
- Step 2 no longer shows the "Generate Script" panel when loading an existing script fails — previously this could invite overwriting a script that actually exists but just failed to load
- `GEMINI_MODEL` moved off the shut-down `gemini-2.0-flash` to `gemini-3.8-flash` (Google's current default Flash model)
- Every write to the shared `aiosqlite` connection (create/update/delete project, script generate/regenerate/save) and every read from it (list/get project, `GET .../script`, and the pre-read steps of generate/regenerate/save) now serializes on one connection-wide lock (`app/api/projects.py::_write_transaction` / `_read_transaction`) — closes a HIGH-severity bug where an unrelated concurrent request could interleave into another request's uncommitted transaction and be wiped out by its rollback (dirty/phantom reads and writes). The lock is never held across a Gemini call. `db.commit()` now runs inside the `try` so a commit failure also triggers a rollback
- `BUG-001`: Fixed JSON syntax error (trailing comma) in `.viepilot/HANDOFF.json`, restored phase structure (`.viepilot/phases/01-full-feature-build/`)
- `BUG-002`: Reconciled counters across `TRACKER.md` (14/29 tasks, Day 2/21), `ROADMAP.md` (checked Task 1.5 with commit hashes), and `HANDOFF.json`
- `BUG-003`: Re-established 10 phase task cards (`tasks/task-1.1.md` through `task-1.10.md`), verified with `vp-tools phase-info 1` and `vp-tools progress`
- `BUG-004`: Fixed double-encoded UTF-8 in `README.md`, updated documentation to use `DIE_GEMINI_API_KEY`, synchronized `database-schema.sql` with migration 002, removed stale Gemini 2.0 and JSON-sidecar references
- `BUG-005`: Resolved HTTP 500 on explicit null fields in `PUT /api/projects/{id}/learning` by adding `@model_validator(mode="before")` on `LearningPackUpdate` to reject nulls with HTTP 422, reinforced with service-level validation
- `BUG-006`: Resolved empty/whitespace-only project and speaker names by adding string validators (`min_length=1`, whitespace stripping) to Pydantic models and service layer
- `BUG-007`: Enforced strict Gemini structured-output schema on all AI generation calls (`ScriptService`, `LearningContentService`), added dedicated `regenerate_line.txt` template and `render_regenerate_line_prompt`; confirmed structural determinism is achieved via schema (see `BUG-011`), sampling `temperature` intentionally left unset so "Regenerate" keeps returning varied content
- `BUG-008`: Fixed race conditions and data loss on rapid Step navigation by adding dirty state checks, save awaiting in `handleNextStep`, UI action locking, and `beforeunload` warning in Step 2 and Step 3
- `BUG-009`: Restored PM-only acceptance authority — all Sprint 1.5R requests reverted to `ready_for_review` pending explicit PM sign-off (`AR-06`); reconciled test counts (223) and `_write_lock` terminology across `TRACKER.md`/`PHASE-STATE.md`/`HANDOFF.json`/`ROADMAP.md`/`task-1.5.md`
- `BUG-010`: Fixed `README.md` Task 1.7–1.10 numbering to match `ROADMAP.md`/`SPEC.md` (1.7 Video Studio, 1.8 Thumbnail Generator, 1.9 YouTube Package, 1.10 Music Library), confirmed `.viepilot/ARCHITECTURE.md` and `docs/walkthrough-sprint-1.5r.md` are committed and `git diff --check` is clean
- `BUG-011`: Switched `ScriptService`/`LearningContentService` from the unsupported `responseSchema` field to Gemini's `responseJsonSchema` field (the correct carrier for Pydantic's `$defs`/`$ref` output), removed the silent schema-less fallback on `TypeError`, added wire-payload regression tests
- `BUG-012`: Added explicit `saveStatus` state machine (`saved`/`dirty`/`saving`/`failed`) to Step 2/Step 3 so navigation only proceeds after a confirmed save, with a real `/step4` placeholder route and a Playwright regression suite (`tests/test_ui_async_browser.py`) for save/failure/retry/rapid-edit races

---

## [0.1.0] — 2026-09-10

### Added
- Project initialized
- `.viepilot/` architecture artifacts created
- Brainstorm session completed

[Unreleased]: https://github.com/danghoangsqtt-sys/dailyintelenglish/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/danghoangsqtt-sys/dailyintelenglish/releases/tag/v0.1.0
