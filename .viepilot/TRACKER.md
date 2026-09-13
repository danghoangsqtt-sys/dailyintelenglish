# TRACKER.md — Daily Intel English Studio

## Current Status

**Phase:** 1 done; Phase 2 started  
**Day:** 3 / 21  
**Started:** 2026-09-10 (Phase 2 opened 2026-09-13)  
**Target:** 2026-09-30  

## Progress Overview

*Task counting rule: Phase 1 has 10 major tasks (1.1–1.10) [currently 10/10 done, 100%,
including Sub-task 1.9c which closed the one gap found during Phase 1 close-out review
against ROADMAP.md's stricter phase-level "Acceptance Criteria (Phase 1 Complete)"
checklist] with 30 discrete checklist subtasks (29 original + Sub-task 1.7c, added
2026-09-13 once the user resolved the avatar-sourcing decision) [currently 28/30 done,
93% — the remaining 2 are real OmniVoice GPU inference integration (Task 1.6 — **decided
2026-09-13: will not be pursued**, Edge TTS is now the sole official engine, not "blocked"
anymore) and LivePortrait lip-sync inference itself (Task 1.7 — the separate
avatar-sourcing question is resolved and delivered as Sub-task 1.7c, but the actual
lip-sync model integration is a distinct, not-yet-started future effort), neither
required for any task's own acceptance criteria]. Progress reflects completed subtasks.*

| Phase | Status | Tasks Done | Tasks Total |
|-------|--------|-----------|-------------|
| Phase 1 — Build | ✅ Complete | 28 | 30 |
| Phase 2 — Testing | 🔄 In Progress | 0 | 10 |
| Phase 3 — Review | ⏳ Not Started | 0 | 6 |

## Phase 1 Task Status

### 1.1 Project Setup
- [x] Python environment
- [x] Directory structure
- [x] FastAPI skeleton
- [x] SQLite setup
- [x] Dependency check script — `venv\Scripts\python scripts\check_dependencies.py` now reports all-GREEN (Python, ffmpeg, GPU, Gemini key, OmniVoice model, data dirs) as of 2026-09-13, once every Known Issues blocker was resolved. **Task 1.1 closed.**

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
- [x] TTSService — OmniVoice — **Won't do, by user decision 2026-09-13.** Semaphore(2) +
  fallback logic stay in place as a tested, honest fallback branch; model weights stay
  downloaded and load-verified as evidence of an informed decision (see Known Issues), but
  real `_synthesize_omnivoice()` integration will not be pursued — the actual API is
  zero-shot voice cloning from a reference sample, not the "voice design" the original
  ROADMAP envisioned, and Edge TTS is now the sole official TTS engine.
- [x] TTSService — Edge TTS — `app/services/tts_service.py`, `EDGE_TTS_VOICE_MAP` (10 accents x 3 genders), retry-once-on-empty-audio, live-verified 20/20 real synthesis calls. `POST /api/projects/{id}/tts/preview` + `GET .../tts/cache/{line_id}.mp3`. 22 new tests, 252 total pass.
- [x] AudioService — Sub-task 1.6b (2026-09-13): `app/services/audio_service.py` — real silence gaps (300ms/500ms), real ITU-R BS.1770 loudness normalization (`pyloudnorm`) to -16 LUFS, background-music static-level ducking, MP3+WAV export, real per-line timestamps. `POST/GET .../audio/generate`, `/status`, `/download`. 25 new tests against a real ffmpeg pipeline (not mocked), 375 total pass. Also closes Task 1.10's deferred loudness/background-music piece.
- [x] TTS Audio Studio UI — Sub-task 1.6c (2026-09-13): `frontend/pages/step4_tts.html` + `step4_tts.js` at `/step4`. Per-speaker engine/speed/pitch/volume autosave via a new narrow `PATCH /api/projects/{id}/speakers/{speaker_id}` (avoids a real cascade-delete landmine in the existing full-replace speakers route — see task-1.6.md), per-line preview playback, sequential "Generate All" (synthesize every line, then mix), MP3/WAV download. 13 new tests (6 API + 7 Playwright E2E), 388 total pass. **Task 1.6 sub-task split now fully done** — only real OmniVoice GPU inference remains, blocked on a user design decision (not part of the 1.6a/b/c split).

### 1.7 Video Studio — ✅ DONE (2026-09-13) for both sub-tasks
- [x] VideoService — Background + Subtitle — Sub-task 1.7a (2026-09-13): `app/services/video_service.py` renders a project's completed audio mix (Task 1.6) into an MP4 using one of 3 fixed pre-rendered background templates (`frontend/static/video_backgrounds/`, generated via `scripts/generate_video_background_assets.py`, same deterministic-asset precedent as thumbnail templates) plus real burned-in subtitles (ffmpeg `subtitles` filter, libass, confirmed present in the installed build) built from AudioService's real measured per-line timestamps. `GET /api/video/templates`, `POST/GET /api/projects/{id}/video/{generate,status,download}`. 20 new tests (real ffmpeg pipeline, not mocked), 407 pass + 1 pre-existing unrelated flaky Gemini-retry test confirmed passing in isolation (see Known Issues).
- [ ] VideoService — LivePortrait lip-sync inference — the avatar-sourcing question that
  used to block this is resolved (user decision 2026-09-13: upload, see Sub-task 1.7c,
  done); the actual lip-sync model integration itself remains a separate, not-yet-started
  future effort
- [x] Video Studio UI — Sub-task 1.7b (2026-09-13): `/step5` (`frontend/pages/step5_video.html`/`step5_video.js`) — background-template selector, synchronous Generate, `<video>` preview, MP4/SRT downloads, empty state directing to Step 4 when no audio exists. `/step4` gained its first pipeline-nav button ("Next: Video Studio →"). No avatar/lips-sync controls (that backend path doesn't exist). 7 new Playwright tests, 428 total pass. **Closes Task 1.7's sub-task split.**
- [x] Speaker avatar upload — Sub-task 1.7c (2026-09-13): `app/services/avatar_service.py`
  (magic-byte-checked PNG/JPEG upload, 8MB cap, one mutable file per speaker) +
  `POST/GET/DELETE /api/projects/{id}/speakers/{id}/avatar` + a `/step5` upload/preview/
  remove section, not wired into video generation. `project_service.get_project` now maps
  the stored path to a served URL — never a raw filesystem path in any API response. 20
  new backend tests + 1 new Playwright test, 473 total pass (1 pre-existing unrelated flaky
  Gemini-retry test, see Known Issues). Caught+fixed a real `.hidden`-vs-`.btn`-CSS bug via
  a live screenshot (see Known Issues).

### 1.8 Thumbnail Generator — ✅ DONE (2026-09-12)
- [x] ThumbnailService — Sub-task 1.8a by Codex: Gemini text/palette suggestions (`responseJsonSchema`, exact-count + duplicate rejection), atomic render+persist with rollback-safe filesystem/DB sequencing, safe content route. 27 new tests, 298 total pass. PM independently re-rendered all 5 templates and confirmed real image quality.
- [x] 5 thumbnail templates — `minimal_clean`, `gradient_bold`, `modern_split`, `dynamic_wave`, `podcast_classic`, deterministically generated, font is Pillow's embedded scalable default (no system path)
- [x] Thumbnail UI — Sub-task 1.8b by Codex (session ran out of quota mid-task; PM independently verified/completed acceptance from the actual code and a fresh full test run, not a written report): `/step6` page, template gallery, generate/regenerate (confirm-gated), favorite selection (atomic single-UPDATE), manual headline/color editor with optimistic-concurrency re-render (SQL-level compare-and-swap, `ConflictError` 409 on stale edits), revision-token cache-busted asset URLs, full `saved`/`dirty`/`saving`/`failed` async-safety state machine matching Step 2/3. 17 new tests (11 service/API + 6 real-browser), 314 total pass, ruff clean, no flaky test recurrence.

### 1.9 YouTube Package — ✅ DONE (2026-09-13), all three sub-tasks complete
- [x] YouTubePackageService — Sub-task 1.9a by Claude Code (PM+Implementer, Codex out of quota): titles (3 variants)/description/tags/estimated chapters via Gemini `responseJsonSchema`. New migration `003_youtube_package.sql`. 30 new backend tests; caught+fixed a real tag-whitespace round-trip bug before landing.
- [x] YouTube Package UI — `/step7`, read-only display + copy-to-clipboard + confirm-gated Regenerate. 6 new browser tests; caught+fixed a real `[hidden]`-vs-CSS-specificity bug via actual Playwright browser testing (a unit test would have missed it).
- [x] Sub-task 1.9b (2026-09-13) — closes Task 1.9's own acceptance criteria: chapters now **measured** from AudioService's real timestamps when audio exists (`real_chapters_from_timestamps()`, additive migration `004_youtube_chapters_measured.sql`), else estimated as before. New `GET .../youtube/export` streams an in-memory `.zip` (video+thumbnail+SRT+metadata.txt) once video + a favorite thumbnail both exist. 13 new tests including a real end-to-end pipeline test (not mocked), 421 total pass. Caught+fixed a real bug via browser test: frontend defaulted to claiming "Measured" on an `undefined` flag — fixed to require explicit `=== false`.
- [x] **Sub-task 1.9c (2026-09-13, by Codex, PM-accepted)** — closes the gap found during Phase 1 close-out review: `.zip` export gains a 5th file, `transcript_and_vocabulary.txt`, with the full script transcript (speaker names resolved, `AudioService`-style ID fallback) plus Learning Content (vocabulary/idioms/grammar/comprehension questions) when generated — a project with no Learning Content still exports successfully with a plain notice, never a new hard prerequisite. `metadata.txt` untouched. 10 new tests (real Vietnamese/emoji/long-text Unicode round-tripped through an actual zip decode, plus a real end-to-end pipeline test), 437 total pass (1 pre-existing unrelated flaky Gemini-retry test —6th occurrence of the known/accepted flake — confirmed passing in isolation). PM independently re-verified every command and read the full diff before accepting — see `.viepilot/phases/01-full-feature-build/tasks/task-1.9c.md`.

### 1.10 Music Library — ✅ DONE (2026-09-13)
- [x] Music Library UI — Sub-task 1.10a (ffmpeg-independent) by Codex: upload (50MB limit, magic-byte validation, atomic no-clobber duplicate naming), list, native audio preview, confirm-gated delete at `/music`. 19 new tests (15 API + 4 Playwright), 271 total pass.
- [x] Volume leveling + Step 4/5 background-track selection/ducking — delivered in Task 1.6 Sub-task 1.6b (`app/services/audio_service.py`), 2026-09-13.
- [x] Waveform visualization — Sub-task 1.10c (2026-09-13): `frontend/static/js/waveform.js`, a reusable canvas waveform (Web Audio API decode, played/unplayed tinting, click-to-seek) wired into `/music`'s track cards. Verified with real decodable audio (pydub-generated, not the existing tests' fake `ID3...` bytes which don't decode) — confirmed real drawn pixels and accurate click-to-seek via a disposable Playwright script before writing the committed suite. 4 new tests. **Closes Task 1.10 — all acceptance criteria done.**

## Phase 2 Task Status

### 2.1 Quality Testing
- [ ] No task card yet (CEFR accuracy, multi-accent TTS, audio quality, video testing — see ROADMAP.md)

### 2.2 Bug Fixes & Performance — buildable scope done 2026-09-13 (Task 2.2)
- [x] Fix any blocking API calls → move to executor — a research-agent audit + direct
  file review found 4 real gaps (not the ~25 already-correct usages elsewhere):
  `video_service.generate_video()` (background-check/mkdir/SRT-write),
  `tts_service.synthesize_line()` (model-exists-check/mkdir/audio-write — a per-line hot
  path), `audio_service.mix_project()` (background-music existence check), and
  `app/api/tts.py`'s `list_engines()` (model-exists + `shutil.which("piper")`). All 4
  wrapped in `asyncio.to_thread`; 55 pre-existing tests pass completely unmodified,
  proving zero behavior change.
- [ ] Optimize OmniVoice batch — moot, real OmniVoice integration will not be pursued
  (2026-09-13 decision).
- [ ] Add progress cancellation (stop mid-generation) — **genuinely deferred, not
  closed**: audited the architecture and found every generation route is a synchronous
  request/response call with no background-job/cancellation mechanism anywhere; building
  real cancellation is a large architectural change, a separate future task.
- [x] Fix Gemini retry logic for 429 — already done during Phase 1 (1s→2s→4s backoff on
  429 only, all 4 Gemini-calling services); this line predated that work. Closed via
  audit, no code needed.
- See `.viepilot/phases/02-testing-polish/tasks/task-2.2.md` for the full record.

### 2.3 UX Polish — ✅ DONE (2026-09-13), all 7/7 ROADMAP items resolved (4 shipped code, 3 audited/already satisfied)
- [x] Step progress indicator + breadcrumb navigation — done 2026-09-13, by Codex,
  PM-accepted. New `frontend/static/js/step_nav.js` (`StepNav.render()`, pure synchronous
  DOM, no network) mounted on all 7 step pages showing "Step X of 7" + 7 clickable pills;
  missing `project_id` degrades to clean bare URLs, never `null`/`undefined`; no business
  logic/state machine/`beforeunload` guard touched anywhere (confirmed via full diff
  review). 15 new Playwright tests, 452 total pass. Codex's session ended mid-verification
  on a usage limit (implementation, its own tests, and lint were already done and correct
  on disk — only the write-up was missing); PM independently re-verified every command
  from scratch and took its own screenshot before accepting. Deliberately narrow first
  slice of the 7-item "UX Polish" ROADMAP bullet.
- [x] Keyboard shortcuts (Ctrl+Enter to generate, Esc to cancel) — done 2026-09-13,
  Task 2.3b, PM as Implementer (`/vp-auto` autonomous continuation). Audited first: every
  step page already has one consistent primary-button id (`submit-btn` on `/step1`,
  `generate-btn` on `/step2`-`/step7`), all with a real `.disabled` property; `Esc` to
  cancel was already substantially satisfied (native `confirm()` dialogs are
  Escape-cancelable for free; `/step2`/`/step3`'s inline-edit fields already revert on
  Escape) — so the only real gap was `Ctrl+Enter`. New `frontend/static/js/
  keyboard_shortcuts.js` (`KeyboardShortcuts.init({ primaryButtonId })`, same pattern as
  `StepNav`), one line + one init call per page (14 files, 14 insertions, 0 deletions —
  confirmed via `git diff --stat`). Safely does nothing when the button is hidden (an
  existing script/pack/package case) or genuinely disabled, so it can never fire the
  wrong action. Caught and fixed a real bug in the new module before shipping (a top-level
  `const` doesn't attach to `window` in a classic script — silently "worked" via shared
  lexical scope between same-page classic scripts, but `window.KeyboardShortcuts` was
  `undefined`; fixed to match `StepNav`'s explicit `window.X = Object.freeze(...)`
  pattern) plus two test-writing mistakes caught before they could hide a real defect (a
  wrong 404-vs-`data:null` assumption about `GET .../youtube`'s "no package yet" contract,
  and a missing `/tts/preview` mock that let `/step4`'s generate flow silently hit the
  real, unmocked backend and fail before ever reaching `/audio/generate`). 6 new
  Playwright tests (`/step2`, `/step4`, `/step7`), 480 total pass. See `task-2.3b.md` for
  the full record.
- [x] Error toasts — done 2026-09-13, Task 2.3c, PM as Implementer (`/vp-auto` autonomous
  continuation). Audited first: all 7 step pages and `music_library.js` already had a
  working friendly-error system (the latter under different element ids — a naive
  `error-banner` grep missed it, not a real gap). The Dashboard was the one real gap: a
  failed project load silently rendered "No projects yet." — indistinguishable from a
  genuinely empty account — and a failed delete used a raw `alert(err.message)`, the last
  remaining CR-05 violation in the app. Fixed both with the same `#error-banner` pattern
  already used everywhere else; new `loadFailed` flag stops a failed load from ever
  looking like an empty account. 2 new Playwright tests; caught a real test-authoring bug
  along the way (a dialog handler returning a tuple hid its `dialog.accept()` coroutine
  from Playwright's fire-and-forget scheduling, deadlocking a `confirm()` dialog — fixed
  by using a named function that returns the coroutine directly). 482 total pass.
- [x] Empty states — closed 2026-09-13 via audit alongside Task 2.3c, no code needed:
  Dashboard and Music Library both already show a helpful message for a genuinely empty
  list; `/step1` is a pure form with nothing to be "empty"; `/step7`'s `#generate-panel`
  already serves as its own empty/call-to-action state.
- [x] Responsive layout — closed 2026-09-13, Task 2.3d, PM as Implementer (`/vp-auto`
  autonomous continuation). Ran a real Playwright audit before any planning: all 9 pages
  already have zero horizontal overflow at a 1024px viewport, thanks to the app-wide
  `repeat(auto-fit, minmax(...))` grid pattern plus `/step6`'s existing `@media
  (max-width: 1180px)` rule (already covers 1024px). No code change needed. New
  permanent `tests/test_responsive_layout_browser.py` (9 tests) pins the finding. 491
  total pass.
- [x] Auto-save indicator — closed 2026-09-13, Task 2.3e, PM as Implementer (`/vp-auto`
  autonomous continuation). New shared `frontend/static/js/save_indicator.js`
  (`SaveIndicator.mount()`, same pattern as `StepNav`/`KeyboardShortcuts`) mounted in the
  header of `/step2`, `/step3`, `/step6` — the 3 pages with an existing page-level
  autosave state machine — as an addition alongside each page's existing inline
  `#save-status` element, wired via one new line inside each page's existing central
  setter function. `/step4` (per-speaker-field autosave, no single "document" concept)
  and `/step1`/`/step5`/`/step7`/Dashboard/Music Library (no page-level autosave concept)
  intentionally excluded. 2 new Playwright tests; existing autosave-race suite re-run
  unmodified and still passes. 493 total pass. **This closes Task 2.3 entirely — all 7
  "UX Polish" ROADMAP items resolved.**

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
| 2026-09-12 | Codex's first assignment (Task 1.6 Sub-task 1.6b, AudioService) correctly self-deferred after a real environment preflight: no `ffmpeg`, no `pydub` in its sandbox. Redirected (PM-approved) to Task 1.10 Sub-task 1.10a — ffmpeg-independent Music Library UI — with 4 PM-required additions (50MB upload limit, no-clobber duplicate naming, magic-byte validation, `ARCHITECTURE.md` sync). Codex delivered all 4; PM independently re-ran every verification command (not just trusted the pasted output) and read the actual diff before accepting — first real Codex delivery matched its own report exactly, no BUG-010-style discrepancy. 19 new tests (real `ThreadPoolExecutor`/`Barrier` concurrency test proves the no-clobber placement is actually race-safe, not just sequentially tested). Also confirmed independently: `pydub` fails on this venv's Python 3.14 with `ModuleNotFoundError: No module named 'audioop'` (Codex's sandbox hit the same error) — logged in Known Issues, will still block Sub-task 1.6b/1.10b later even after `ffmpeg` is installed, unless `audioop-lts` is added first. | Codex; PM (Claude Code) |
| 2026-09-12 | Task 1.8 (Thumbnail Generator) assigned to Codex — chosen over Task 1.9 because 1.9's acceptance criteria require a .zip with video/thumbnail/SRT that don't exist yet. Codex proposed splitting into 1.8a (backend: Gemini suggestions, 5 Pillow templates, render+persist, APIs) and 1.8b (UI editor, separate plan). PM verified the font claim independently (`ImageFont.load_default(size=...)` genuinely scales, confirmed by measuring rendered text width at two sizes; the font itself — Aileron — is base64-embedded in Pillow's own source, zero filesystem/OS dependency) before approving. PM also required one clarification before implementation: the pre-existing `thumbnails` DB table has one row per `(template_name, variant_index)`, not a many-to-many shape, so the variant→template assignment rule needed to be explicit — Codex resolved this by making `template_name` a required request field (one template per generation batch, not round-robin across all 5), which PM confirmed matches the schema. After implementation, PM independently re-rendered all 5 templates using the actual service code and visually confirmed professional-quality output (not just trusting the "visually inspected" claim in the report) before accepting. 27 new tests, 298/298 pass. | Codex; PM (Claude Code) |
| 2026-09-12 | Task 1.8 CLOSED: Codex's Sub-task 1.8b plan (PUT .../favorite exclusive select, PATCH .../thumbnails/{id} optimistic-concurrency edit with a `revision` compare-and-swap, cache-busted asset URLs) was PM-approved without changes — Codex identified two real races/bugs (stale-edit clobbering, stale browser image cache) beyond the minimum ask and solved both correctly. Codex's session ran out of quota mid-implementation, before running final verification or writing its evidence report. PM (Claude Code) independently read every changed/new file end-to-end (not reconstructing from a report that was never written), confirmed the SQL-level CAS in `update_thumbnail_revision` and the single-statement atomic `select_favorite`, confirmed the Step 2/3-style async-safety state machine in the new `step6_thumbnail.js`, and ran a fresh full verification pass (314/314 tests, ruff clean, no flaky-test recurrence) before completing the acceptance record and closing Task 1.8 end-to-end. | Codex; PM (Claude Code) |
| 2026-09-12 | Codex ran out of quota entirely; Claude Code took over as both PM and Implementer (self-plan, self-implement, self-verify with the same rigor used reviewing Codex). Task 1.9 (YouTube Package) Sub-task 1.9a: titles/description/tags/estimated chapters via Gemini, new migration `003_youtube_package.sql` (dropped-and-recreated `youtube_packages`, same precedent as `002_learning_content.sql` for a never-used table), `/step7` read-only display UI. Chapters are honestly labelled as estimates (no real audio exists — Task 1.7 blocked on ffmpeg). Two real bugs caught and fixed by the test suite before landing: (1) tag whitespace lost on DB round-trip (unit test), (2) `#generate-panel[hidden]` silently overridden by a higher-specificity `display: grid` ID rule — only caught because a real Playwright browser test asserted actual visibility, not just DOM state. 36 new tests, 350/350 total pass. | PM (Claude Code) |
| 2026-09-13 | User filled in a real `DIE_GEMINI_API_KEY`. PM independently verified it live (one real HTTP call to `gemini-3.8-flash`, not just checking the value was non-empty) rather than trusting the user's "already updated" report — the first check actually showed the key was still empty (`dotenv_values()` returned length 0), so the user was asked to re-save before the second check confirmed it really was present and working. Key value itself was never echoed/logged anywhere, including here, despite appearing in plaintext in a system-level file-diff notification at one point. | User; PM (Claude Code) |
| 2026-09-13 | Task 1.6 Sub-task 1.6b (AudioService) delivered by PM (Claude Code) as Implementer, ffmpeg/OmniVoice blockers now resolved. `app/services/audio_service.py`: real silence gaps (300ms/500ms same/different speaker), real ITU-R BS.1770 loudness normalization to -16 LUFS via `pyloudnorm` (not a dBFS approximation mislabeled as LUFS), background-music static-level ducking capped at `MUSIC_DUCKING_MAX_DBFS`, MP3(192k)+WAV(44100Hz/16-bit) export, real measured per-line timestamps. New routes `POST/GET /api/projects/{id}/audio/{generate,status,download}`. Real bug found and fixed during implementation: this pydub version's `ffprobe` PATH lookup ignores `AudioSegment.converter`, requiring a process-PATH shim for `DIE_FFMPEG_PATH` (documented in Known Issues so it isn't re-discovered from scratch). This sub-task also closes the loudness-leveling/background-track-selection acceptance criteria Task 1.10 had explicitly deferred "alongside AudioService." 25 new tests exercising the real ffmpeg pipeline (not mocked, following the same "exercise the real local library" approach as Pillow thumbnail tests), 375/375 total pass, ruff clean. | PM (Claude Code) |
| 2026-09-13 | User went offline (traveling) and explicitly authorized full autonomous PM+Implementer decision-making for this session, with strict self-verification and no shortcuts. Task 1.6 Sub-task 1.6c (TTS Audio Studio UI) delivered: `frontend/pages/step4_tts.html` + `step4_tts.js` at `/step4` (replacing and deleting the superseded placeholder), speaker voice-assignment panel, per-line preview, background-music selector, sequential "Generate All", MP3/WAV download. **Real architectural landmine found during planning and avoided by design**: the existing `PUT /api/projects/{id}` (`ProjectUpdate.speakers`) does a full delete-and-reinsert of every speaker row with new UUIDs, and `script_lines.speaker_id` has `ON DELETE CASCADE` — calling that route from Audio Studio (reached only once a script exists) to tweak one speaker's voice settings would have silently deleted the entire script. Proved this was a real, reachable hazard (not theoretical) by first writing a regression test against the *existing* route confirming the cascade-delete, then building a new narrow `PATCH /api/projects/{id}/speakers/{speaker_id}` (updates in place, never deletes) instead of reusing the unsafe path. This closes Task 1.6's sub-task split entirely (1.6a/1.6b/1.6c all done) — only real OmniVoice GPU inference remains, which was never part of that split and stays blocked on a user design decision. 13 new tests (6 API + 7 Playwright E2E with network-mocking, same pattern as `test_youtube_browser.py`), 388/388 total pass, ruff clean, `node --check` clean. Also independently smoke-tested the entire real pipeline end-to-end outside the test suite (real project → real script → real speaker patch → real TTS synthesis → real ffmpeg mix → real download → real status-machine advance) and took a real Playwright screenshot to visually confirm the rendered page before calling this done. | User; PM (Claude Code) |
| 2026-09-13 | Also closed Task 1.1 (dependency check script now reports all-GREEN — every Known Issues blocker resolved this session) while continuing autonomously. Task 1.7 Sub-task 1.7a (VideoService background+subtitle backend) delivered: `app/services/video_service.py` renders a project's completed audio mix (Task 1.6) into an MP4 with burned-in subtitles (ffmpeg `subtitles`/libass filter) over one of 3 fixed pre-rendered background templates (`scripts/generate_video_background_assets.py` → `frontend/static/video_backgrounds/`, same deterministic-asset precedent as thumbnail templates). SRT cues come from AudioService's real measured per-line timestamps, extended with a small backward-compatible `text` field addition so subtitles show actual dialogue, not just a speaker label. **Verified the real ffmpeg build before writing any production code**: confirmed `--enable-libass`, and worked out via a real throwaway proof-of-concept exactly how ffmpeg's `subtitles` filter needs Windows paths escaped (`\\` and `:` both need escaping in the filtergraph value) — the real implementation worked end-to-end on the first full run because of this upfront verification, not through trial and error against production code. Level 3 (LivePortrait avatar lip-sync) deliberately deferred: no speaker has an avatar image and no upload/generation feature exists, the same class of blocker as OmniVoice's `ref_audio` — a real user decision, not something to fabricate. 20 new tests (real ffmpeg pipeline, not mocked), 407/408 pass (1 pre-existing unrelated flaky Gemini-retry test — this time in `test_learning_service.py`, a third distinct module — confirmed passing in isolation, now the 5th occurrence of this known/accepted flake). Also live-smoke-tested the entire real pipeline outside the test suite and extracted a real video frame confirming the correct speaker name + dialogue text burned in against the chosen background template. | PM (Claude Code) |
| 2026-09-13 | Task 1.9 Sub-task 1.9b (full `.zip` export + measured chapters) delivered, **closing Task 1.9 entirely**, since Task 1.7's real video+SRT and Task 1.6's real timestamps now both exist. `real_chapters_from_timestamps()` replaces the word-count estimate whenever a project's audio has been mixed (additive migration `004_youtube_chapters_measured.sql` — unlike `002`/`003`'s drop-and-recreate, `youtube_packages` is now a live, actively-used table, so the correct move is additive, not destructive). New `GET .../youtube/export` streams an in-memory zip (video.mp4 + subtitles.srt + the favorite thumbnail.png + metadata.txt) once all three exist, naming exactly which prerequisite is missing otherwise. Real bug caught by a live Playwright assertion, not inline review: the first frontend version defaulted to displaying "✅ Measured from the final generated audio" whenever `chapters_estimated` was simply `undefined` (JavaScript falsy-ternary bug) — fixed to require an explicit `=== false` before ever claiming precision. `tests/test_youtube_export_api.py` exercises the real end-to-end chain (real script → real Edge TTS network-mocked synthesis → real AudioService mix → real VideoService render → real Pillow thumbnail render, only the two Gemini text calls mocked → real zip assembly), not a shortcut around the very features this sub-task depends on. 13 new tests, 421/421 total pass, ruff clean. | PM (Claude Code) |
| 2026-09-13 | User said "tiếp tục" (continue). Task 1.7 Sub-task 1.7b (Video Studio UI) delivered, **closing Task 1.7's sub-task split**: `/step5` (`frontend/pages/step5_video.html`/`step5_video.js`) with a background-template selector (3 fixed templates only — no avatar/lips-sync controls, since that backend path doesn't exist and building UI for a feature that always fails would be a fake feature, not a scope cut), synchronous Generate (no fake progress bar for a near-instant ffmpeg render), `<video>` preview, MP4/SRT downloads, and an empty state directing back to Step 4 when no audio exists yet. `/step4` gained its first pipeline-navigation button ("Next: Video Studio →") — it never had one before since Task 1.6's acceptance criteria didn't require it, but closing the chain now that Step 5 exists was a natural, low-risk addition. 7 new Playwright tests (network-mocked, same pattern as the Task 1.6c browser suite), 428/428 total pass, ruff clean. Live-smoke-tested the real API end-to-end (real project → real script → real Edge-TTS-mocked synthesis → real AudioService mix → real VideoService render, all through the same TestClient the page's JS would call) and took a real Playwright screenshot confirming visual consistency with the rest of the app before calling this done. Phase 1 now stands at 9/10 major tasks done — only Task 1.10 (waveform visualization, unassigned) remains in progress. | User; PM (Claude Code) |
| 2026-09-13 | Task 1.10 Sub-task 1.10c (waveform visualization) delivered, **closing Task 1.10 — all 10 Phase 1 major tasks now done**. Implemented directly (no separate plan-then-implement round-trip) since it's a small, self-contained, additive, pure-frontend feature with no backend change or architecture decision — but still verified as thoroughly as any larger sub-task before landing. New `frontend/static/js/waveform.js`: decodes each track via the Web Audio API, draws a canvas waveform with played/unplayed tinting (colors resolved from the real `--accent`/`--text-muted` CSS custom properties, not duplicated), and supports click-to-seek; wired into `/music`'s track cards. Deliberately did not touch Step 4's audio players or reopen the already-closed Task 1.6 — this sub-task closes only Task 1.10's own remaining acceptance criterion. **Real bug avoided by testing deliberately**: the project's existing music-library browser tests all use a fake `ID3...` byte string that passes the backend's magic-byte check but is not real MP3 frame data and does NOT decode via the Web Audio API — testing the new feature against that fixture would have only proven the graceful-failure path. `tests/test_music_library_waveform_browser.py` uses real pydub-generated audio instead, with a separate dedicated test for the undecodable-audio graceful-failure path. Verified with a disposable Playwright script before writing the committed suite: confirmed real non-transparent pixels via `canvas.getImageData()` and that clicking at 70% of the waveform moved `audio.currentTime` to ~70% of its duration; took a full-page screenshot to visually confirm the bar shape and tinting render correctly. 4 new tests, ruff clean. Two items remain deliberately open across the whole phase, neither blocking any task's acceptance criteria: real OmniVoice GPU inference (Task 1.6) and Level 3 LivePortrait avatar lip-sync (Task 1.7) — both need a real user decision on a reference-asset source (`ref_audio` / avatar images) that no amount of autonomous engineering judgment can substitute for. | User; PM (Claude Code) |
| 2026-09-13 | Codex's quota restored. Phase 2 (Testing & Polish) opened: `.viepilot/phases/02-testing-polish/` scaffolded (`PHASE-STATE.md`), first task card `tasks/task-2.3.md` written (PM) and assigned to Codex — a deliberately narrow first slice of ROADMAP.md's 7-item "UX Polish" bullet: shared step-progress + breadcrumb navigation (`StepNav.render()`) across all 7 step pages, since the pipeline only became fully navigable end-to-end this session and had no way to jump between steps. Also caught and fixed a real doc-drift bug while scaffolding Phase 2: `.viepilot/phases/01-full-feature-build/PHASE-STATE.md`'s top `## Metadata` block (milestone/subtask/test-count summary) had been stale since early in Phase 1 (still read "5/10 major tasks, 350 tests") even though every individual task section below it was kept current all session — corrected to 10/10, 432 tests, done. | User; PM (Claude Code) |
| 2026-09-13 | Task 1.9c (transcript + Learning Content in the YouTube export) delivered by Codex — its first assignment since quota was restored — and PM-accepted after independent re-verification of every command and a full diff read, not just the pasted report. `build_export_zip()` gained a 5th zip member, `transcript_and_vocabulary.txt`: the full script transcript (speaker names resolved with the same `AudioService`-style ID fallback) plus, when generated, the Learning Content pack — a project with none still exports successfully with a plain notice, correctly never made a hard prerequisite. `metadata.txt` byte-for-byte unchanged, confirmed via new negative assertions in the API test. PM specifically traced `learning_service.update_learning_content()`'s write path back to `app/api/learning.py`'s `payload: LearningPackUpdate` typed route parameter to confirm Codex's direct dict-key access on required fields (`item['word']`, etc.) is safe by construction, not a missed edge case. 10 new tests including a real end-to-end pipeline test (project → script → audio → video → thumbnail → Learning Content, only Gemini calls mocked) and real Vietnamese/emoji/long-text Unicode round-tripped through an actual zip decode. 437 total, 436 passed + 1 failed in that run — the failure is the known Gemini-retry flake (6th occurrence), confirmed passing in isolation, unrelated to this change. **This closes Task 1.9 entirely and closes the one gap found in Phase 1's close-out review — Phase 1 now has zero open items against any task's own acceptance criteria or the phase-level completion checklist**, leaving only the two already-known, deliberately deferred items (OmniVoice `ref_audio`, LivePortrait avatar images) that need a user decision, not more engineering. | Codex; PM (Claude Code) |
| 2026-09-13 | Task 2.3's step-progress + breadcrumb slice delivered by Codex and PM-accepted, but under an unusual circumstance: Codex's session hit its usage limit mid-verification, after finishing the plan, implementation, its own `tests/test_step_nav_browser.py` run (15 passed), and lint/syntax checks — all already correct on disk — but while still watching a full-suite run reach its summary (it had explicitly chosen to wait for the real result rather than guess at the cause of the one failure it had seen, which is exactly the right call per this project's process). It was cut off before writing any evidence into the task card. PM treated this the same as the earlier Codex-quota-exhaustion incident on Task 1.8b: read every diff line-by-line across all 18 changed/new files from scratch (not reconstructing from a report that didn't exist), independently re-ran every verification command, and took its own Playwright screenshot of `/step2` to visually confirm the rendered component before writing up both the Implementer Evidence and PM Acceptance sections itself. Full re-run: 452/452 pass, no flake this time. New `frontend/static/js/step_nav.js` (`StepNav.render()`) is a pure synchronous DOM component — no network calls, no async state — mounted identically on all 7 step pages; confirmed the one specific risk flagged during plan review (each page independently parsing its own `location.search` rather than depending on `init()`-internal state) was implemented exactly as specified. | Codex; PM (Claude Code) |
| 2026-09-13 | User asked PM to analyze and decide the two deliberately-deferred Phase 1 items (OmniVoice `ref_audio` sourcing, LivePortrait avatar sourcing) and implement directly. PM presented the real tradeoffs rather than picking silently — OmniVoice's real API is voice *cloning* (needs a real audio sample, raising consent/rights questions), not the text-described "voice design" the original plan assumed, and doesn't clearly beat the already-working Edge TTS; LivePortrait's own model integration is a separate large effort from just picking an avatar source. User confirmed both PM recommendations via AskUserQuestion: (1) stop pursuing OmniVoice cloning, Edge TTS becomes the sole official TTS engine; (2) build only the avatar-upload feature now (matches the original ROADMAP design of user-supplied images, never app-generated likenesses), defer actual LivePortrait model research/integration. |
| 2026-09-13 | Both decisions above implemented in two chunks, verified and committed separately. **Chunk A** (formalize Edge-TTS-only): `SpeakerConfig.tts_engine` default `"omnivoice"` → `"edge_tts"`; Step 4's now-dead engine `<select>` removed (only speed/pitch/volume remain editable); `ROADMAP.md`/`ARCHITECTURE.md`/`SYSTEM-RULES.md`/`task-1.6.md` updated to record the decision and reasoning; OmniVoice's fallback code path deliberately left in place as an honest, still-tested branch. 453/453 tests pass. Committed `3e0895d`, pushed. **Chunk B** (Sub-task 1.7c, avatar upload — doc-first task card written before any code, per standing discipline): new `app/services/avatar_service.py`, 3 new routes, `/step5` gets an upload/preview/remove section per speaker, `project_service.get_project` now maps the stored path to a served URL so a raw filesystem path is never returned to a client. Live-verified end-to-end with a real (non-mocked) upload→serve→delete cycle through the real API, then a live Playwright screenshot caught a real bug before it shipped: the Remove button used `.hidden` on a `.btn`-classed element, which this app's stylesheet's unconditional `.btn { display: inline-flex }` silently overrides (author-stylesheet rules always beat same/lower-specificity UA rules like `[hidden]`, regardless of source order) — fixed by not appending the button when unneeded, re-verified with a second screenshot. Flagged (not fixed, out of this task's scope) that `step6_thumbnail.js`'s `retry-save-btn` likely has the exact same latent bug. 20 new backend tests + 1 new Playwright test, 474 total; two separate full-suite runs each hit exactly one instance of the pre-existing documented Gemini-retry timing flake (a different test each time), both confirmed passing in isolation — not a regression. | User; PM (Claude Code) |
| 2026-09-13 | `/vp-auto` continuation ("tiếp tục nào"): audited ROADMAP.md's remaining 5
  "UX Polish" items before picking one, rather than assuming the wording maps 1:1 onto
  missing work — found "Error toasts" and "Empty states" already substantially satisfied
  by existing patterns (friendly-only `#error-banner` on every page since Task 1.3's
  CR-05; contextual `.empty-state` panels already exist for every "nothing yet" state that
  matters), and "Esc to cancel" already covered by native `confirm()` dialogs plus
  `/step2`/`/step3`'s existing inline-edit revert handlers. Picked "Keyboard shortcuts"
  (`Ctrl+Enter` to generate) as the one genuinely unbuilt, cleanly-scoped item — new
  `task-2.3b.md`, doc-first plan written before any code. Delivered
  `frontend/static/js/keyboard_shortcuts.js` on all 7 step pages; caught and fixed a real
  bug in the module itself (top-level `const` doesn't attach to `window` in a classic
  script) and two test-writing mistakes (wrong 404-vs-null API contract assumption, a
  missing `/tts/preview` mock) before either could hide a real defect. 6 new tests, 480
  total pass. | PM (Claude Code) |
| 2026-09-13 | `/vp-auto` continuation ("tiếp tục"): re-audited the two "substantially
  satisfied" UX Polish items from the previous entry — "Error toasts" and "Empty states"
  — with a real page-by-page check rather than resting on the earlier high-level read.
  Found `music_library.js` genuinely already covers "Error toasts" (different element
  ids than the step-page convention, which a naive grep had missed), but the Dashboard
  (`/`) had two real, confirmed gaps: a failed project load silently rendered "No
  projects yet." — indistinguishable from a genuinely empty account — and a failed
  delete used a raw `alert(err.message)`, the last remaining CR-05 violation anywhere in
  the app. New `task-2.3c.md`, doc-first plan first. Fixed both with the same
  `#error-banner` pattern already proven on every step page; "Empty states" needed no
  code at all once checked (every page that can be meaningfully empty already handles
  it). 2 new Playwright tests; caught a real test-authoring bug along the way (a dialog
  handler returning a tuple hid its `dialog.accept()` coroutine from Playwright's
  fire-and-forget scheduling, deadlocking a `confirm()` dialog). Full suite: 482 passed,
  0 failures, no flake this run. | PM (Claude Code) |
| 2026-09-13 | `/vp-auto` continuation ("tiếp tục"): picked "Responsive layout" (the last
  auditable item before the genuinely bigger "auto-save indicator" one) — same discipline
  as the prior two turns, ran a real proof-of-concept audit before writing a plan. A
  disposable Playwright script loaded all 9 pages at a real 1024x800 viewport with
  realistic mocked data and checked `scrollWidth` vs `clientWidth`: zero overflow
  anywhere. Screenshots of the two most layout-complex pages (`/step4`'s two-column
  speaker grid, `/step6`'s preview+editor grid) confirmed clean, non-overlapping layouts,
  not just "no scrollbar." Root cause of why this already worked with no dedicated
  effort: this app's CSS consistently uses `repeat(auto-fit, minmax(...))` for every
  card/variant grid (self-reflowing by construction), and `/step6`'s one fixed
  two-column layout already had a `@media (max-width: 1180px)` rule stacking it well
  before 1024px. New `task-2.3d.md` (doc-first, written after the audit but before any
  test file existed), then a permanent 9-page regression suite
  (`tests/test_responsive_layout_browser.py`) so this can't silently regress later — no
  production code touched. 491 total pass. This closes 6 of ROADMAP.md's 7 "UX Polish"
  items; only "auto-save indicator" remains unassigned. | PM (Claude Code) |
| 2026-09-13 | `/vp-auto` continuation: tackled the last "UX Polish" item, "Auto-save
  indicator" — the one already flagged as genuinely bigger than a pure audit (unlike the
  prior 2 items) since it touches 3 pages' existing, tested autosave state machines.
  Audited exactly which pages have a real page-level autosave concept first:
  `/step2`/`/step3`/`/step6` each already have one central save-status setter function
  (BUG-012/Task 1.8b); `/step4` autosaves per-speaker-field independently with no single
  "document" to reflect; `/step1`/`/step5`/`/step7`/Dashboard/Music Library have no
  page-level autosave concept at all. New `task-2.3e.md` scoped to exactly the 3 pages
  that qualify, as a purely *additive* change (new shared `save_indicator.js` header
  component, one new line inside each page's existing setter function) — deliberately
  not touching or relocating the existing inline `#save-status` elements, so
  `tests/test_ui_async_browser.py`'s existing autosave-race assertions needed zero
  changes and were re-run unmodified to prove it. 2 new Playwright tests, 493 total pass.
  **This closes Task 2.3 entirely — all 7 ROADMAP.md "UX Polish" items now resolved**
  (4 shipped code across 2.3/2.3b/2.3e, 3 closed via audit with no code change across
  2.3c/2.3d). | PM (Claude Code) |
| 2026-09-13 | `/vp-auto` continuation: with all of "2.3 UX Polish" done, moved to Task 2.2
  "Bug Fixes & Performance." Audited all 4 ROADMAP items before scoping: dispatched a
  read-only research agent to grep every `async def` in `app/services/*.py`/`app/api/*.py`
  for blocking filesystem calls not wrapped in `asyncio.to_thread`, then independently
  confirmed its findings by reading each file directly (and found one more of the same
  class — `shutil.which("piper")` in `app/api/tts.py` — that the agent's search patterns
  hadn't targeted). 4 genuine gaps found and fixed (not the ~25 already-correct usages
  elsewhere), the most consequential being `tts_service.synthesize_line()`'s unwrapped
  model-check/mkdir/audio-write, since that function runs per script line during
  "Generate All" — a real hot path under concurrent synthesis, not just a one-off
  request. "Fix Gemini retry logic for 429" turned out to already be done (built during
  Phase 1, the ROADMAP line simply never got checked off). "Optimize OmniVoice batch" is
  moot post-decision. "Add progress cancellation" was explicitly NOT closed — audited the
  architecture (every generate route is synchronous request/response, no background-job
  or cancellation mechanism exists anywhere) and correctly recognized this needs a real
  architectural change, not a quick fix, so it stays open as a separate future task
  rather than being forced into a slice it doesn't fit. 55 pre-existing tests across the
  4 touched files pass completely unmodified, proving zero behavior change. 493 total
  pass. | PM (Claude Code) |
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

- ~~`ffmpeg` not found in PATH~~ **RESOLVED 2026-09-12**: installed via `winget install Gyan.FFmpeg` (9.0.1, full build). Note: Windows PATH updates only apply to newly-started processes — any shell open before the install won't see it. `.env`'s `DIE_FFMPEG_PATH` now points at the absolute exe path so the app itself doesn't depend on shell PATH freshness. Unblocks Task 1.6 Sub-task 1.6b (AudioService) and Task 1.7 (Video Studio) — see the `pydub`/`audioop` item below for a second, separate blocker on 1.6b.
- ~~`DIE_GEMINI_API_KEY` empty~~ **RESOLVED 2026-09-13**: user filled in their real key. Verified with one real live call to `gemini-3.8-flash` (not just presence/length) — HTTP 200, model replied as instructed, real token usage reported. Key value itself was never printed/logged anywhere, including this file. All Gemini-backed services (script/learning/thumbnail/youtube) were already fully implemented and tested against mocks; this confirms the real integration also works end-to-end.
- ~~OmniVoice model not downloaded~~ **RESOLVED 2026-09-13**: researched the real k2-fsa/OmniVoice project (Apache 2.0, GitHub + HuggingFace, verified via web search — not guessed) before touching anything. Installed `torch==2.11.0+cu128` (the docs' pinned `2.8.0+cu128` no longer exists on the index; first attempt at an unpinned `torch` install silently resolved to a CPU-only build — caught by checking `torch.cuda.is_available()`, not assumed) + `torchaudio==2.11.0+cu128` + `omnivoice==0.2.1`. Downloaded the real model (`huggingface_hub.snapshot_download`, 3.27 GB: `model.safetensors` 2.45GB + `audio_tokenizer/model.safetensors` 805MB) directly into `models/omnivoice/` (matching `settings.OMNIVOICE_MODEL_PATH`, confirmed gitignored). Verified end-to-end for real: `OmniVoice.from_pretrained("models/omnivoice", device_map="cuda:0", dtype=torch.float16)` actually loaded onto the RTX 3060 (2.03GB VRAM used) — not just "files exist on disk." `scripts/check_dependencies.py` now reports OmniVoice GREEN.
  - **DECIDED 2026-09-13, by the user: not pursuing real OmniVoice integration.**
    `torch`/`torchaudio`/`omnivoice` remain NOT added to `requirements.txt`, and
    `_synthesize_omnivoice()` in `tts_service.py` keeps honestly raising "model not
    loaded" — permanently, not as a temporary gap. Reasoning presented to the user and
    confirmed: OmniVoice's real API (`model.generate(text=..., ref_audio="ref.wav",
    ref_text=...)`) is zero-shot voice *cloning* from a reference audio sample, not the
    text-described "voice design" the original ROADMAP envisioned via
    `speaker.voice_description` — closing that gap would need either the user's own
    licensed voice recordings or a royalty-free reference-voice preset library, and
    either way doesn't clearly improve on Edge TTS (already live-verified, 10 accents x 3
    genders) enough to justify the voice-cloning consent/rights surface it would open.
    **Edge TTS is now the sole official TTS engine.** The downloaded model weights and
    verified GPU-load code stay as evidence this was a real, informed decision, not a
    skipped one — see the resolved item above for that record. Sub-task 1.6a's semaphore/
    fallback plumbing around `_synthesize_omnivoice()` is left in place unchanged (still
    an honest, tested fallback branch, doesn't hurt anything) but the Step 4 UI no longer
    offers OmniVoice as a selectable engine (there is no real behavior difference to
    choose between anymore).
- ~~`pydub` `ModuleNotFoundError: No module named 'audioop'`~~ **RESOLVED 2026-09-12**: added `audioop-lts>=0.2.1; python_version >= "3.13"` to `requirements.txt` and installed it. Verified end-to-end for real (not just import): `pydub.AudioSegment.silent()` → `set_frame_rate()` → `.export(..., format="mp3")` actually produced a valid non-empty MP3 file via the real ffmpeg binary. **Task 1.6 Sub-task 1.6b (AudioService) delivered 2026-09-13** — see Task 1.6 above.
- **LivePortrait avatar lip-sync (Task 1.7 Level 3) — scope decided 2026-09-13, by the
  user:** avatar image sourcing follows the original ROADMAP design (user uploads their
  own image per speaker; the app never auto-generates or reuses a real person's likeness
  without their action). **Sub-task 1.7c (avatar upload) delivered 2026-09-13** —
  `app/services/avatar_service.py` + `POST/GET/DELETE /api/projects/{id}/speakers/{id}/avatar`
  + a `/step5` upload/preview/remove section — see task-1.7c.md. Real LivePortrait model
  integration (the actual lip-sync inference pipeline) remains explicitly deferred as a
  separate, later research+build effort comparable in size to the OmniVoice deep-dive —
  not started, not scheduled yet.
- **`.hidden` silently ignored on `.btn`-classed elements (found 2026-09-13 while building
  Task 1.7c, via a live screenshot, not the automated suite):** this app's `style.css` has
  no `[hidden]` rule anywhere, so an unconditional `.btn { display: inline-flex }` — an
  author-stylesheet rule, which the CSS cascade always ranks above a same-origin-tier
  user-agent rule like `[hidden] { display: none }` regardless of selector specificity —
  keeps a `.btn`-classed element visibly showing even with `el.hidden = true`. Fixed in
  `step5_video.js`'s new Remove-avatar button by not appending it to the DOM at all when
  unneeded, rather than toggling `.hidden`. **Not yet fixed**, and likely present:
  `frontend/static/js/step6_thumbnail.js`'s `retry-save-btn` (`class="btn btn-ghost
  btn-sm" hidden` in `frontend/pages/step6_thumbnail.html`) uses the exact same pattern —
  worth a small dedicated cleanup pass (either add a real `[hidden] { display: none
  !important; }` rule to `style.css` once, or convert call sites to conditional DOM
  insertion like 1.7c's fix).
- Real gotcha found while building AudioService (2026-09-13, not a blocker, documented so it isn't re-discovered from scratch): this pydub version's media-probing step (`pydub.utils.get_prober_name()`) does its own `which("ffprobe")` PATH lookup and silently ignores `AudioSegment.converter`/any class-attribute override — `AudioSegment.from_file()` failed with `FileNotFoundError` even with `DIE_FFMPEG_PATH` correctly configured, until `app/services/audio_service.py::_ensure_ffmpeg_dir_on_path` prepended ffmpeg's directory onto this process's `PATH` env var at import time.
- **Known, accepted flake (not a bug in project code):** any Gemini retry/backoff-pattern
  test (seen so far in `tests/test_script_service.py`, `tests/test_youtube_service.py`,
  and `tests/test_learning_service.py` — three unrelated modules sharing only the "mocks
  `asyncio.sleep` to a no-op" shape) occasionally fails exactly once during a full `pytest
  tests/ -q` run — always passes instantly in isolation, and most recurrences correlate
  with the full-suite run itself being unusually slow (229–305s vs the ~90–130s baseline),
  pointing at system-load-induced timing sensitivity rather than a real defect. 6
  occurrences now (248.22s full-suite run for the 6th; two more during Task 1.7c's
  verification — `test_learning_service.py` (2 tests) at 307.72s, then a *different* test,
  `test_script_service.py::test_generate_script_non_429_error_does_not_retry`, at 350.80s
  — plus one more during Task 2.3b's verification,
  `test_learning_service.py::test_generate_learning_pack_exhausts_retries_raises`, at
  453.85s — plus two at once during Task 2.2's verification (both in
  `test_learning_service.py`: `test_generate_learning_pack_exhausts_retries_raises` and
  `test_generate_learning_pack_non_429_error_does_not_retry`) at 447.13s — all fully
  consistent with the pattern: slower-than-baseline full-suite runs, instant pass in
  isolation), tracked in `.viepilot/debug/session-debug-20260912T000000Z.json`
  (closed `wontfix` 2026-09-13). If a full-suite run ever shows a Gemini retry/backoff test
  failing, re-run it in isolation before treating it as a real regression — do not block
  on it if isolation passes.

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
