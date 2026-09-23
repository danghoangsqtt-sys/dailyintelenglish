# TRACKER.md — Daily Intel English Studio

## Current Status

**Phase:** 1–13 done (Phase 13 closed 2026-09-22 under owner decision D11 — local-only, Gate B-3 script gate PASS 5/5); Phases 13–15 closed (15 closed 2026-09-22: structural failures eliminated, media gate PASS for the first time, owner's failing configuration completes 2/2; repetition is the single remaining, variable failure class). **Phase 16 (Stability Hardening) closed 2026-09-23**: worker loop guard, ffmpeg timeouts + atomic render, test-DB leak fixed + 447 leaked projects cleaned, repetition 0.00% in 9/9 completed scripts at Gate B-7; remaining failure class: global word-count overshoot (ENH-010). **Phase 17 (Budget-Aware Global Validation, ENH-010) planned 2026-09-23**; plan `docs/implementation/phase-17-global-length-repair.md`.
**Day:** 6 / 21  
**Started:** 2026-09-10 (Phases 1–12 complete; Phase 13 opened 2026-09-18 as user-approved reliability scope beyond the original plan)
**Target:** 2026-09-30 (all 3 originally-planned phases complete Day 6 — well ahead of schedule; Phase 4 is additional post-beta scope)  

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
required for any task's own acceptance criteria]. Progress reflects completed subtasks.
Phase 2's row counts discrete ROADMAP checklist items across 2.1 (4), 2.2 (4), 2.3 (7),
2.4 (3), 2.5 (3), and 2.6 (3, new scope added 2026-09-14, not in the original Phase 2
plan) = 24 total, 22 done (2.1's 4; 2.2's 2 real fixes — "Optimize OmniVoice batch" and
"Add progress cancellation" are moot/deferred, not counted done, and never will be under
this task card; 2.3's 7; 2.4's 3; 2.5's 3; 2.6's 3, all done 2026-09-14). **Phase 2
formally closed 2026-09-15** at 22/24 (92%) — the user chose to close at this buildable
scope rather than pull "progress cancellation"/LivePortrait lip-sync into Phase 2 first
(see Decision Log 2026-09-15); both remain logged as deferred future work, not phase
blockers. Phase 3 counts discrete ROADMAP checklist items across 3.1 (4), 3.2 (3), and
3.3 (4) = 11 total, all 11 done 2026-09-15 — **Phase 3 formally closed** (see Task
3.1/3.2/3.3 below). Phase 4 (new, scoped in the 2026-09-15 brainstorm session, not part
of the original plan) has 3 currently-tracked tasks, all now done: 4.1 done 2026-09-15
(partial improvement, honestly reported), 4.4 done 2026-09-16 (2 real P0 navigation
bugs found by a Codex UI audit, fixed by Codex, accepted by PM — see Task 4.4 below),
4.2 **fully closed 2026-09-16** (split per-page — 5/7 pages redesigned into the shell:
Learning/4.2a 2026-09-15, TTS/4.2b, Video/4.2c, Thumbnail/4.2d, and YouTube/4.2e all
2026-09-16, all four of 4.2b/c/d/e by Codex; 2/7 confirmed and closed as intentionally
out of scope: Music Library/Step1-Config, both deliberately NOT shell-based per the
2026-09-14 session, re-verified before closing rather than rubber-stamped). Task 4.3
(Vietnamese UI localization) was scoped in the same brainstorm session, became
eligible once Task 4.2 finished, but was **DROPPED 2026-09-16** by explicit user
decision at the first real planning question (loanword-handling style for terms like
Video/Thumbnail/Podcast) rather than answered — no task card written, no code
touched. **Phase 4 formally closed 2026-09-16** at 3 pursued tasks (4.1/4.2/4.4), all
done. See `docs/brainstorm/session-2026-09-15.md`. **Phase 5** (new, scoped in
`docs/brainstorm/session-2026-09-16.md` right after Phase 4 closed) addressed the
real, still-current P1/P2 findings from the 2026-09-16 Codex UI audit — 3 tasks, all
done 2026-09-17 by Codex, accepted by PM per AR-06 with zero real defects found
across any review: 5.1 Dashboard pagination, 5.2 timeline polish, 5.3 small polish
batch. **Phase 5 formally closed 2026-09-17.** **Phase 6** (new, scoped in
`docs/brainstorm/session-2026-09-17.md` right after Phase 5 closed) addresses 3 real,
independently-verified findings from a user-commissioned deep-dive Gemini audit —
theme flash on 4 pages, a dead-end "Missing project" error with no link back to the
Dashboard, and default (non-accent-colored) TTS range sliders. A 4th audit claim
(YouTube chapters always estimated) was traced and found to be a **false positive**
— the real-measurement code path already exists and works — so it's explicitly
excluded. Its one task done 2026-09-17 by Codex, accepted by PM per AR-06 with zero
real defects found. **Phase 6 formally closed 2026-09-17.** **Phase 7** (new, opened
right after Phase 6 closed) was scoped after the user ran `/vp-audit` 2026-09-17 for
deep independent re-verification of the 4 Gemini audit findings left unscoped
post-Phase-6. `GEMINI_RATE_LIMIT_RPM` turned out not to be unused (used by 2 CLI
sample scripts, a nuanced correction, not logged). DB single-connection lock (ENH-004)
and CSS fragmentation (ENH-005) were confirmed real but left in the backlog per user
decision. BUG-013 — script can be edited/regenerated after audio/video already exist,
with zero status guard and no staleness signal — was confirmed real and more serious
than originally described, so the user chose to open this phase to fix it. Its one
task (7.1) done 2026-09-18 by Codex, accepted by PM per AR-06 with zero real defects
found. **Phase 7 formally closed 2026-09-18.** **Phase 8** (new, opened right after
Phase 7 closed, at the user's explicit request to self-implement the remaining
findings to save time) re-investigated ENH-004 and found it already has a
deliberate, well-reasoned fix in place (a connection-wide lock already serializes
every route) — marked `wontfix`, no code changed. ENH-005 had a real, minimal fix:
reconciled a missing shared `.btn[aria-disabled="true"]` rule, removing 3 pages'
resulting inconsistent local overrides. Its one task (8.1) done 2026-09-18,
self-implemented and self-verified by PM. **Phase 8 formally closed 2026-09-18.**
**Phase 9** (new, opened 2026-09-18 right after Phase 8 closed) was scoped after the
user had Codex run its own independent, parallel read-only `/vp-audit` alongside
PM's own audit — Codex found 10 issues, PM independently re-verified all 5
"important" ones with zero false positives, and re-scored BUG-017 (a failed audio/
video regeneration attempt wiped a prior successful job's DB data — real data loss)
up to high after tracing the exact UPSERT bug. Its one task (9.1) fixed both BUG-017
and BUG-016 (voice-settings changes not invalidating downstream status, the same bug
class as BUG-013), done 2026-09-18 by Codex, accepted by PM per AR-06 with zero real
defects found. **Phase 9 formally closed 2026-09-18.** **Phase 10** (new, opened via
`/vp-debug` right after Phase 9 closed) fixed the 6 remaining backlog findings from
both 2026-09-18 audits (BUG-014, BUG-015, BUG-018, BUG-019, ENH-006, ENH-007) —
mid-phase the user made a standing policy change (PM self-implements directly
instead of delegating to Codex). Task 10.1 fixed BUG-018 (stale per-line audio
cache) and BUG-019 (avatar filesystem mutation not rolled back on a later
transaction failure, fixed via unique per-upload filenames + commit-then-cleanup
ordering). Task 10.2 fixed the 4 pure documentation findings. Both done 2026-09-18,
self-implemented and self-verified by PM with zero real defects found. **Phase 10
formally closed 2026-09-18.** Every finding from both 2026-09-18 audits is now
resolved. **Phase 11** (new, opened after a third independent Codex `/vp-audit`
pass run once Phase 10 closed) fixed 7 more findings — including a real miss in
PM's own Phase 10 work (`delete_avatar()` had BUG-019's exact root cause but was
incorrectly excluded) and a plausible root cause of this project's long-documented
Gemini-retry flake class (a shared test fixture that monkeypatched the
process-wide `asyncio.sleep` instead of a module-scoped one). Its one task (11.1)
done 2026-09-18, self-implemented and self-verified by PM with zero real defects
found. **Phase 11 formally closed 2026-09-18.***

| Phase | Status | Tasks Done | Tasks Total |
|-------|--------|-----------|-------------|
| Phase 1 — Build | ✅ Complete | 28 | 30 |
| Phase 2 — Testing | ✅ Complete (buildable scope) | 22 | 24 |
| Phase 3 — Review | ✅ Complete | 11 | 11 |
| Phase 4 — Post-Beta Polish (new) | ✅ Complete (Task 4.3 dropped) | 3 | 3 |
| Phase 5 — UI Polish Backlog (new) | ✅ Complete | 3 | 3 |
| Phase 6 — Quick Wins Batch (new) | ✅ Complete | 1 | 1 |
| Phase 7 — Script Edit Staleness (new) | ✅ Complete | 1 | 1 |
| Phase 8 — CSS Consolidation (new) | ✅ Complete | 1 | 1 |
| Phase 9 — Regeneration Integrity (new) | ✅ Complete | 1 | 1 |
| Phase 10 — Backlog Cleanup (new) | ✅ Complete | 2 | 2 |
| Phase 11 — Third Audit Fixes (new) | ✅ Complete | 1 | 1 |

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

### 2.1 Quality Testing — 4/4 ROADMAP items done (2026-09-14)
- [x] CEFR accuracy testing — done via Task 2.1a (CLI:
  `scripts/generate_cefr_review_samples.py`, code-complete and PM-accepted, real 18-call
  run now lands 18/18) + Task 2.1b (PM read all 18 real generated scripts in full,
  user-approved automated-proxy review at a `/vp-auto` control point). Verdict: 14 PASS,
  4 BORDERLINE (A2/B1/B2 × news — a genre-specific idiom-density drift, not a defect),
  0 FLAG. Nothing required the user's own read. See `tasks/task-2.1a.md` and
  `tasks/task-2.1b.md` for the full record.
- [x] Multi-accent TTS testing, Audio quality testing, Video testing — done via Task
  2.1c: real technical measurement (LUFS, silence gaps, subtitle-timestamp sync) against
  the actual production service functions, per a second user decision at a `/vp-auto`
  control point (PM can't literally "listen"; proxy method is real numbers). 20/20 real
  TTS syntheses across all 10 accents × 2 genders succeeded; no-music audio mixes landed
  at -16.01 LUFS (0.01dB off the -16 target); real video render confirmed exact
  subtitle-timestamp sync. **3 real findings surfaced, none fixed in this read-only
  pass** (see TRACKER.md Known Issues and `tasks/task-2.1c.md`): `scottish` accent
  duplicates `british`'s voice ids (upstream Edge TTS limitation, not a bug);
  background-music mixes drift to -17.12 LUFS, outside the ±1dB tolerance (a real bug,
  root cause identified); no 9:16 video output exists at all (a missing feature, not
  buildable to test yet). This closes Task 2.1's 4-item Quality Testing campaign at the
  automated-proxy-review level the user approved.

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

### 2.4 UI Redesign Slice 1 — Dashboard + Script Workspace — ✅ DONE (2026-09-14)
- [x] Dashboard → light, high-contrast project launcher — new hero + toolbar + light
  project-card shell; every existing list/filter/search/delete/new-project selector and
  behavior retained exactly (`#project-grid`, `#empty-state`, `[data-filter]`,
  `#search-input`, `[data-action]`/`[data-id]`, `#theme-toggle`).
- [x] Step 2 → CapCut-style Script workspace — new `frontend/static/js/shell.js`
  (`WorkspaceShell`): resizable/collapsible sidebar (vertical `StepNav`, sidebar
  56-420px), central script stage (original `[data-line-id]` inline-edit cards
  byte-for-byte behaviorally untouched), a selected-line inspector (260-480px; speaker,
  text, language notes, Listen via the existing `previewTtsLine` →
  `POST /api/projects/{id}/tts/preview` endpoint — no new backend surface — and
  Regenerate via the existing guarded `handleRegenerate` path), and a three-track
  Script/Voice/Music timeline (110px-70vh) whose Script lane drives selection.
- [x] Light-by-default theme migration — shared CSS tokens moved to light-first `:root`
  with dark values under `[data-theme="dark"]`, legacy variable aliases kept so untouched
  pages render unaffected; `theme.js`'s stored-preference fallback changed from `"dark"`
  to `"light"` (the one and only permitted line change in that file, verified via `git
  diff` byte-for-byte).
- Doc-first plan (`tasks/task-2.4.md`) flagged 2 real contradictions in the original
  brief before any code was written — PM resolved both explicitly (light-default needs
  `theme.js` in scope; the Listen action needs the existing preview endpoint, not a new
  one) rather than letting the Implementer guess. 49 new/updated Playwright tests (46
  across the touched shared-module suites — Dashboard, keyboard shortcuts, StepNav, save
  indicator, responsive layout, UI-async — + 3 new in
  `tests/test_new_shell_resize_browser.py` covering pointer/keyboard resize,
  collapse/expand, selection+inline-edit coexistence, and the real Listen call including
  its loading/error path). Full suite: 515/516 pass — the 1 failure
  (`test_learning_service.py::test_generate_learning_pack_retries_on_503_then_succeeds`)
  is the pre-existing tracked Gemini-retry timing flake (see Known Issues), confirmed via
  an isolated re-run (passed in 0.55s) since Task 2.4 touched zero backend/Gemini code.
  `ruff check app/ tests/` clean; `node --check` clean on all 6 touched JS files. Real
  Playwright screenshots at 1440×900 confirmed both pages render correctly in both themes
  against the live app. See `tasks/task-2.4.md` for the full record and evidence.

### 2.5 Fix the 3 real findings from Task 2.1c — ✅ DONE (2026-09-14)
- [x] Background-music LUFS drift — fixed in `audio_service._mix_project_sync`:
  normalize the final mix (voice + ducked music) once, after the overlay, instead of
  only the pre-music voice stem. Real measured result now within the declared ±1dB
  tolerance.
- [x] No 9:16 video output — fixed: new `_render_vertical_sync` (blurred-background-pad
  ffmpeg technique) as a second pass over the existing 16:9 render, wired through a new
  `aspect_ratio` field/column/download-format/UI-toggle. Default (16:9) unchanged. Real
  `ffprobe` confirms genuine 720×1280 output.
- [x] Scottish/British voice duplication — disclosed via a `title` tooltip on Step 1's
  Scottish accent option/chip (confirmed live: no Scottish Edge TTS voice exists to fix
  this in code).
- 2 additional real, blocking bugs found and fixed while verifying (disclosed): the
  `.hidden`-on-`.btn` CSS trap pre-flagged in Known Issues, and a real `init_db()`
  migration-replay crash on any second real app restart. See TRACKER.md Known Issues
  (both now marked RESOLVED) and `tasks/task-2.5.md` for the full record.
- 530/530 full suite passes (up from 515), zero flakes this run, `ruff`/`node --check`
  clean.

### 2.6 Fix 3 findings from the post-Task-2.5 audit pass — ✅ DONE (2026-09-14)
- [x] `ARCHITECTURE.md` doc drift — updated `### Video` API docs for `aspect_ratio` and
  the `mp4_vertical` download format.
- [x] Orphaned `mp4_path_vertical` on regenerate — `generate_video()` now deletes a
  stale vertical file when a later regenerate doesn't request `"9:16"` again.
- [x] `escapeHtml()` unsafe for attribute contexts — now escapes `"`/`'` too. Verified
  as a real bug via revert-and-confirm-failure before restoring the fix.
- 3 other findings (missing phase-completion tag, pre-existing error-path field-wiping,
  a migration-fallback design note) left noted-only in Known Issues per user choice.
- 532/533 full suite passes (1 pre-existing tracked flake, confirmed via isolated
  re-run), `ruff`/`node --check` clean.

**Phase 2 formally closed 2026-09-15** at a `/vp-auto` control point, user-approved: all
buildable scope done (22/24 discrete ROADMAP items); "Optimize OmniVoice batch" is moot
post-decision and "Add progress cancellation" remains explicitly deferred as a separate
future architectural task, neither blocking phase close. Full suite re-run clean before
closing: **533/533 pass** (the previously-tracked Gemini-retry timing flake did not recur
this run). Git tags `die-vp-p1-complete` (retroactive — a missing-tag gap found during
Task 2.6's audit, fixed here) and `die-vp-p2-complete` applied.

## Phase 3 Task Status

### 3.1 Documentation — ✅ DONE (2026-09-15), all 4/4 ROADMAP items resolved
- [x] `README.md` — updated with a Phase 2 section (Tasks 2.1–2.6 summary table, current
  532/533→533/533 test count), corrected the Step 5 pipeline-workflow line (LivePortrait
  status was stale — said "pending a user decision" when that decision was already made
  2026-09-13), corrected the Tech Stack Video line (previously implied LivePortrait
  shipped), added a Documentation table linking the 3 new docs below plus the existing
  `.viepilot/` references.
- [x] `docs/prompt-guide.md` (new) — how to customize `prompts/script/` (base + 10 genre
  blocks + 6 CEFR blocks) and `prompts/learning/learning_pack.txt`; documents the real
  CEFR-ceiling-vs-language-feature-toggle precedence rule and solo-speaker override
  exactly as implemented in `script_base.txt`/`prompt_loader.py`, not invented behavior;
  also covers thumbnail/YouTube prompts and the temperature-left-unset rationale.
- [x] `docs/tts-setup.md` (new) — Edge TTS voice map (`EDGE_TTS_VOICE_MAP`, 10 accents × 3
  genders), the Scottish/British voice-id duplication (upstream limitation, disclosed
  in-UI per Task 2.5c), and a full record of the OmniVoice investigation (real model
  downloaded/GPU-verified, why real integration was decided against, what's deliberately
  left in the code and why).
- [x] `docs/api.md` (new) — auto-generated from the app's real FastAPI OpenAPI schema
  (ROADMAP's own wording) via new `scripts/generate_api_docs.py`, which loads the app via
  `TestClient` and reads `app.openapi()` directly (no live server needed) rather than
  hand-written prose that can drift — the exact class of staleness Task 2.6a had to fix
  for `ARCHITECTURE.md`. 49 routes documented across all 9 mounted routers.
- Pure documentation task — no `app/`, `frontend/`, or `tests/` files touched. Also fixed
  a real doc-sync gap found while closing Phase 2: Task 2.6 had never been added to
  `CHANGELOG.md`'s `[Unreleased]` section despite being done and tagged — added
  retroactively.

### 3.2 Demo & Review — ✅ DONE (2026-09-15), all 3/3 ROADMAP items resolved
- [x] Sample outputs — new `scripts/generate_sample_episodes.py` generated 3 real
  episodes (A1/B1/C1, same topic/genre/speakers held constant so CEFR level is the only
  variable): real Gemini script generation + real Edge TTS synthesis + real ffmpeg mix
  for each, saved to `docs/samples/{level}/` (`script.md`, `script.json`, `audio.mp3`).
  First attempt hit a real transient `httpx.ReadTimeout` on A1 (same class of network
  flakiness as Task 2.1a's documented history, not a code defect); retried cleanly: A1
  (18 lines, 78.9s, -16.01 LUFS), B1 (12 lines, 78.8s), C1 (10 lines, 102.9s).
- [x] Demo video — new `scripts/record_demo_video.py` drives a real in-process
  `uvicorn` server + Playwright through the entire pipeline (project creation → script →
  learning content → TTS/audio → video → thumbnail → YouTube package) with video
  recording enabled, producing `docs/demo/demo-video.webm` (`ffprobe`-confirmed 223.9s,
  8.77MB — a real recording, not a stub). Two real bugs found and fixed while building
  the script: Step 1's speaker-name fields are empty by default and block submission
  (`Speaker N needs a name`) — diagnosed with a disposable debug script rather than
  guessed; and Step 4's original 120s wait timeout was too tight for ~29 sequential real
  Edge TTS calls — raised to 300s with error-banner/progress diagnostics added on
  timeout. The successful run absorbed several real Gemini 429/503s via the existing
  `GEMINI_MODEL_FALLBACKS` chain — real production resilience code exercising itself
  live, not a scripted scenario. See `docs/demo-video.md`.
- [x] Product review report — `docs/product-review.md`: feature checklist (Phases 1-3,
  every status cross-checked against ROADMAP.md), known issues (summarized from
  TRACKER.md's real Known Issues, linked back rather than duplicated), and future
  improvements (progress cancellation, LivePortrait lip-sync, the `news`-genre
  calibration drift, Phase 3's own remaining items).
- Pure deliverables task — no `app/`, `frontend/`, or `tests/` files touched.

### 3.3 Final Cleanup — ✅ DONE (2026-09-15), all 4/4 ROADMAP items resolved
- [x] Remove `print()` debug statements → `logging` — audited: `grep -rn "print(" app/
  --include="*.py"` returns zero matches. Already satisfied, no code needed.
- [x] `.env.example` — was stale: removed 5 dead `Settings` fields with zero real usages
  (`GOOGLE_TTS_API_KEY`, `AZURE_TTS_API_KEY`, `AZURE_TTS_REGION` — vestiges of the
  pre-decision multi-engine TTS design; `OMNIVOICE_DEVICE`/`OMNIVOICE_MAX_CONCURRENT` —
  the real concurrency limit is the unrelated hardcoded `MAX_CONCURRENT_TTS` constant)
  from both `app/core/config.py` and `.env.example`.
- [x] `requirements.txt` complete and pinned — audited: every entry already uses `==`
  (done during Phase 2's structural-risk audit, 2026-09-14). Already satisfied.
- [x] Git tag `v1.0.0-beta` — applied after verification and push.
- 2 full-suite runs during verification (1285.10s, 1054.27s — abnormally slow due to
  real system load, a Chrome Remote Desktop session active on this machine) each hit
  the pre-existing, tracked Gemini-retry timing flake once; confirmed non-regressive via
  isolated re-run (0.56s pass both times) — the change touched only `app/core/config.py`,
  unrelated to `script_service.py`'s retry timing. `ruff check app/core/config.py` clean.
  **This closes Task 3.3 and Phase 3 in full — 11/11 discrete ROADMAP items done.**

## Phase 4 Task Status

### 4.1 CEFR `news`-genre prompt tuning — ✅ DONE (2026-09-15), partial improvement
- [x] Added register-vs-complexity guidance to `prompts/script/news.txt`, directly
  targeting the 3 quoted failure patterns from Task 2.1b's real 18-sample review
  (Future Simple drift at A2, B2-leaning idioms at B1, C1-bordering vocabulary at B2).
- Verified with 3 real Gemini calls (`generate_cefr_review_samples.py --levels A2 B1 B2
  --genres news`), re-reviewed against Task 2.1b's exact rubric. **Honest result:
  partial, mixed improvement** — A2's specific indefinite-pronoun+modal pattern didn't
  recur but Future Simple usage persists; B1's exact flagged idiom ("a breath of fresh
  air") recurred verbatim; B2's idiom choice improved (more solidly B2-appropriate) but
  grammar (Past Perfect Continuous) still borders C1. Not overclaimed as a full fix —
  consistent with tuning a probabilistic model. See `tasks/task-4.1.md` for full
  before/after evidence. Single-file, prompt-only change — no `app/`/`tests/` touched.

### 4.2 UI Redesign Slice 2 — ✅ CLOSED (2026-09-16), 7/7 pages resolved

- [x] **4.2a — Learning (`/step3`) — ✅ DONE (2026-09-15)**: wrapped in the same
  3-panel shell Task 2.4 built for Script, deliberately no timeline (Learning has no
  sequential-items concept, confirmed decision from the 2026-09-14 UI-redesign session).
  New read-only item inspector (click a vocabulary/idiom/grammar/quiz card → full detail
  in the inspector; quiz inspector always shows the correct answer, independent of the
  main list's show/hide toggle) — deliberately no per-item action buttons, since no
  backend endpoint exists to regenerate a single item (would be a fake feature per this
  project's own precedent). Existing inline-`contenteditable`-edit + coalesced-trailing-
  autosave behavior kept exactly as-is — the inspector is a new, independent read path,
  never a second write path. 3 new Playwright tests — **first browser coverage this page
  has ever had** (previously only API/service-level tests existed). Real screenshots
  (1440×900, empty + populated) confirmed clean light-theme rendering.
  **Real regression found and fixed during verification**: `test_step_nav_browser.py`'s
  shared parametrized test assumed only Script (`current_step == 2`) used the 3-panel
  shell layout, so it failed for the newly-shell-based Step 3; root cause on the
  implementation side was `step3_learning.js`'s `StepNav.render()` call missing
  `variant: "workflow"` (present on Script's call) — fixed both the test's branching and
  the missing option, not just the test. 536/536 full suite passes (up from 533).
  Remaining pages (TTS, Video, Thumbnail, YouTube, Music Library, Step1-Config) not
  started. See `tasks/task-4.2a.md` for the full record.

- [x] **4.2b — TTS Audio Studio (`/step4`) — ✅ DONE (2026-09-16)**: first task
  delegated to Codex as Implementer since its quota was restored — Claude Code acted as
  PM per the AR-06 contract (`docs/CODEX_CODE_PROMPT.md`), writing the doc-first task
  card, reviewing the plan, and independently re-verifying before accepting. Wrapped in
  the same 3-panel shell, this time **with** a real 3-track timeline (Script/Voice/
  Music — TTS is one of the 3 pages with a genuine sequential-items concept, per the
  2026-09-14 session). Read-only inspector shows the selected line with an honest
  session-only preview-state badge (Not previewed/Synthesizing/Preview ready — never
  guesses persisted cache state on reload, verified by an actual page-reload test), a
  real Listen action reusing the existing preview endpoint, and a real
  scroll-to-speaker-card "Voice settings" affordance (no new write path). Existing
  per-speaker autosave debounce and the sequential Generate-All request order verified
  unchanged. 5 new Playwright tests.
  **Review round 1**: Codex correctly identified, before writing any other code, that
  `test_step_nav_browser.py`'s shell-layout branch would break for `current_step == 4`
  too (same class as 4.2a's regression) — reported it instead of silently fixing a file
  outside its assigned scope; PM pre-authorized the exact one-line fix.
  **Review round 2**: PM's own independent screenshot (not the test suite, not the
  Implementer's described screenshots) caught a real bug — `renderTimeline()` cleared
  the Script and Voice lanes on every re-render but never the Music lane, so it
  accumulated a duplicate stale clip on every selection/preview/music-change event;
  reproduced live (2 duplicate badges after just one click). Sent back to Codex with
  the exact fix and a regression-test assertion rather than accepting or patching it
  personally. Codex applied the scoped fix; PM re-verified independently, including a
  disposable 5-interaction stress-test script confirming exactly 1 clip survives
  repeated re-renders. 541/541 full suite passes (up from 536), zero flakes on PM's
  final run. See `tasks/task-4.2b.md` for the complete 2-round review record.

- [x] **4.2c — Video Studio (`/step5`) — ✅ DONE (2026-09-16)**: second task delegated
  end-to-end to Codex as Implementer, PM (Claude Code) accepted per AR-06. Video is one
  of the 3 pages (with Script/TTS) with a real timeline — but unlike TTS, this page had
  never fetched the script's lines before, so the plan added a new `Api.getScript()`
  call site (already-existing endpoint, not a new route) correlated by array index to
  the audio job's real per-line `timestamps`. Script track: read-only reference. Voice
  track: honestly labeled "Synced" (every line's audio already exists by the time this
  page is reachable — unlike TTS's in-progress preview states, that language wouldn't
  be true here). Music track: the real `background_music` filename or "No music
  selected". Read-only inspector shows real `M:SS – M:SS` measured timing — Codex
  proposed and PM confirmed **skipping playback** ("Play this segment") as a considered
  scope cut, since seek/race-on-reselect complexity wasn't worth it for an optional
  feature. A `/script`-fetch failure degrades gracefully (logs, shows a timeline-only
  message) rather than blocking the core avatar/template/generate workflow —
  deliberately designed this way because the pre-existing `tests/test_video_studio_
  browser.py` (correctly left out of scope, not touched) uses a fake project ID that
  would otherwise hit a real 404 from the live test server, not a mock. 4 new
  Playwright tests, plus the same pre-authorized `test_step_nav_browser.py` one-line
  extension (now `current_step in (2, 3, 4, 5)`) — the third time this exact regression
  class was pre-empted rather than rediscovered. **Zero real defects found on PM
  review this round** (contrast with 4.2b's Music-lane bug) — `renderTimeline()`
  proactively cleared all 3 lanes on every re-render from the start, directly informed
  by the prior task's post-mortem. PM still independently re-verified everything,
  including reading the full diff, re-running the pre-existing
  `test_video_studio_browser.py` (34/34 pass, confirming the graceful-degradation
  design choice), and a disposable 6-interaction stress-test screenshot of the Music
  lane (exactly 1 clip survived). 544/544 full suite passes (up from 541). See
  `tasks/task-4.2c.md` for the full record.

Task 4.2 **paused after 4.2c** (2026-09-16) to fix Task 4.4's P0 bugs first — see below.

- [x] **4.2d — Thumbnail Generator (`/step6`) — ✅ DONE (2026-09-16)**: third task
  delegated end-to-end to Codex as Implementer, accepted by PM per AR-06. Shell, no
  timeline (same as Learning). One important difference from every prior sub-task:
  Thumbnail already had a real, pre-existing write-path editor for the selected variant
  (headline + color palette, 400ms debounced autosave, trailing-save coalescing, 409
  stale-revision conflict handling, `SaveIndicator`, `beforeunload` guard) — the new
  inspector pane hosts this real editor as-is, not a new read-only view, since the
  write path already existed and wasn't invented. Stage hosts template selection +
  variant grid; every existing element id preserved unrenamed — verified one by one
  against the diff. CSS custom-property renames (`--text-muted`→`--muted` etc.) turned
  out to be true pre-existing aliases already defined in `style.css`, not a functional
  change. 2 new Playwright tests (`test_thumbnail_shell_browser.py`): real mouse-driven
  resize of both panes + sidebar collapse/re-expand, and a combined headline+color edit
  within one debounce window asserting exactly 1 `PATCH` fires with the correct
  payload. Same pre-authorized `test_step_nav_browser.py` extension
  (`current_step in (2,3,4,5,6)`). **PM flagged one open risk at plan-review time**
  (relocating the live preview into a 260-480px inspector, when a thumbnail's whole
  purpose is visual judgment) and asked for a screenshot in the evidence rather than
  blocking approval on it — resolved satisfactorily: the relocated preview stays
  legible, matching the similarly-sized thumbnails already used in the variant-grid
  browsing UI on the same page. **Zero real defects found on PM review** — PM
  independently re-ran every verification command and additionally ran its own
  disposable script + screenshots in both light and dark themes, confirming
  keyboard-driven resize also works (`ArrowLeft`/`ArrowRight` on the resizer, not just
  mouse drag). 560/560 full suite passes (up from 558). See `tasks/task-4.2d.md` for
  the full record. 4/7 Task 4.2 pages now done.

- [x] **4.2e — YouTube Package (`/step7`) — ✅ DONE (2026-09-16)**: fourth task
  delegated end-to-end to Codex as Implementer, accepted by PM per AR-06. Shell, no
  timeline. Real design question unique to this page: no per-item selection concept
  exists at all (titles/description/chapters/tags are all fully shown at once) —
  decision: inspector hosts the "Full Package Export" readiness panel (real dynamic
  state) instead of an item detail view; deliberately did not invent a click-to-inspect
  interaction for the 3 title-variant cards. Plan review caught a real consequence of
  the relocation: the export section's static "Checking export readiness…" text was
  previously invisible (nested inside `#content-wrap`, only shown once a package
  exists) but would become visible and misleading once permanently shown in the
  inspector — Codex proposed and PM approved the minimal fix, an honest static default
  ("Generate the YouTube package to check export readiness."), zero new JS logic since
  the existing `renderExportStatus()` already overwrites it once a package exists. 2
  new Playwright tests (`test_youtube_shell_browser.py`) directly exercise both the
  not-ready and ready export states, confirming the static-text fix and the real
  readiness computation. Same pre-authorized `test_step_nav_browser.py` extension
  (`current_step == 7`). **Zero real defects found on PM review** — PM independently
  re-ran every verification command, read the full diff (confirmed every required
  element id survived, no title-card selection state was added), and additionally
  verified against the real backend (`app/api/youtube.py:49-56`) that "no package yet"
  genuinely returns `200`/`null` (not `404`), confirming Codex's test mocks accurately
  model the real API contract rather than a convenient fiction. 562/562 full suite
  passes; PM's own run hit 1 known Gemini-retry timing flake
  (`test_generate_script_retries_on_429_then_succeeds`), confirmed passing in isolation
  at 0.71s, non-regressive (Task 4.2e touched zero backend code). See
  `tasks/task-4.2e.md` for the full record. 5/7 Task 4.2 pages now done.

- [x] **Music Library (`/music`) and Step 1 Config (`/step1`) — ✅ CLOSED
  (2026-09-16), no code change**: both were decided at the 2026-09-14 UI-redesign
  session to be deliberately NOT shell-based — Music Library is a shared utility page
  outside the 7-step pipeline, Step 1 Config is a pure form with no workspace concept.
  PM re-verified rather than rubber-stamping the standing decision: confirmed
  `music_library.js` has no `pane-sidebar`/shell wiring at all, and confirmed
  `step1_config.js`'s `StepNav.render()` call still uses the default `pills` variant,
  never `workflow`. No regression, formally closed as out-of-scope-by-design.

**Task 4.2 fully closed.** 5/7 pages redesigned into the shell (Learning, TTS, Video,
Thumbnail, YouTube — 4 of 5 delegated to and delivered by Codex per AR-06, 1
self-implemented by PM), 2/7 confirmed and closed as intentionally out of scope. Task
4.3 (Vietnamese UI localization) is now eligible to start per the explicit sequencing
decision in `docs/brainstorm/session-2026-09-15.md` — not started yet.

### 4.4 P0 navigation bug fixes (Dashboard Continue + Config duplicate-project) — ✅ DONE (2026-09-16)

Inserted ahead of Task 4.2d after a Codex read-only UI audit (`vp-auto` audit mode) of
the whole app found 2 real P0 bugs, both independently re-verified by PM against the
actual source before accepting the finding (not trusted on the audit report alone):

1. **Dashboard "Continue" button no-ops for 3 of 5 statuses.** The click handler
   (`dashboard.js:154-159`) only ever wired up `draft`/`script_generated` →
   `/step2` — added when only those 2 statuses existed (Task 1.4, see above). As the
   pipeline grew `audio_generated`/`video_generated`/`complete` were added to the status
   enum and dashboard filter but the Continue handler was never extended, so clicking it
   on those projects does nothing — no navigation, no error, no console output.
2. **Config page (`/step1`) always creates a new project, ignoring an existing
   `project_id` in the URL.** `step1_config.js` reads `project_id` only to render
   StepNav breadcrumbs; `handleSubmit` unconditionally calls `Api.createProject()`.
   Since `step_nav.js` makes "Config" a real clickable link from every other step for
   the current project, a user revisiting Config mid-workflow lands on a blank
   "new project" form and can silently spawn a duplicate project on submit — a
   dangerous mental-model mismatch, not a cosmetic issue.

Fix (implemented by Codex, accepted by PM per AR-06) uses only real, already-existing
backend capability: extended the Continue handler to a single `STATUS_TO_STEP` map
covering all 5 statuses (`audio_generated`→`/step4`, `video_generated`→`/step5`,
`complete`→`/step7`, matching the existing pattern of resuming to the step that
produced that status); and for Config, fetch+prefill via the existing
`GET /api/projects/{id}` for `draft` projects and submit via a new `Api.updateProject()`
(the already-implemented-but-previously-frontend-unused `PUT /api/projects/{id}`
endpoint) instead of create — locking every control read-only with a clear banner for
any later status rather than inventing new cascade/regenerate behavior. 5 new
Playwright tests (`test_step1_config_edit_browser.py`), including a double-submit
stress test asserting exactly 1 `PUT` and 0 `POST`, and a payload assertion confirming
a speaker's hidden TTS fields (engine/description/speed/pitch/volume) survive an edit
unchanged; 2 extended (`test_dashboard_browser.py`, now parametrized across all 5
statuses plus a defensive unknown-status no-op case). **Zero real defects found on PM
review** — PM independently re-ran every verification command, read the full diff, and
additionally ran its own disposable script + screenshot beyond what was asked
(confirmed a disabled genre chip truly can't be activated via a forced DOM click, not
just via Playwright's own actionability convenience check; confirmed the pre-existing
"Cancel" link — a plain `<a>`, untouched by the lock logic — correctly stays
functional). 558/558 full suite passes (up from 555). See `tasks/task-4.4.md` for the
full record. Resuming Task 4.2 with sub-task 4.2d (Thumbnail) next.

**P1/P2 findings from the same audit — logged as backlog, not actioned in Task 4.4**:
timeline clip width isn't proportional to real clip duration (Script/TTS/Video all
affected — a 3s and a 7s line render at nearly the same width); dashboard has no
pagination/virtualization and was observed rendering 176 project cards / 358 buttons
in one `innerHTML` pass (~17,000px page height); Learning's card click targets lack a
semantic role/`tabindex` for keyboard users; the timeline's horizontal resizer has
`tabindex="0"` but no keydown handler (only the vertical resizer does); Learning's
inspector starts empty (340px) instead of defaulting to the first item; header/nav
styling differs between shell-based pages and Config/Thumbnail/YouTube, and Step 6
still says "Daily Intel English" instead of "Daily Intel English Studio"; UI mixes
Vietnamese and English copy (was expected to be resolved by Task 4.3, but Task 4.3 was
dropped 2026-09-16 by explicit user decision — the app UI will stay English-only going
forward, this is now accepted, not a pending fix); Video's avatar section exposes a
not-yet-functional feature (LivePortrait lip-sync) without collapsing it.
None of these are regressions from Task 4.2's own work — they're either pre-existing
or inherent to the current dashboard's real project volume. **Picked up as Phase 5
(UI Polish Backlog) on 2026-09-16** after Phase 4 closed and Task 4.3 was dropped — see
below. 2 of the original 9 findings (Step 6's stale brand text, header/nav styling
inconsistency) turned out to already be fixed as side effects of Task 4.2d/4.2e; the
mixed Vietnamese/English copy finding is now permanently accepted (Task 4.3 dropped),
not a pending fix.

## Phase 5 Task Status

### 5.1 Dashboard scale (pagination) — ✅ DONE (2026-09-17)

Client-side pagination for the Dashboard's project grid — no backend change, since the
measured problem (176 real project cards / 358 buttons rendered in one `innerHTML`
pass, ~17,000px page height) is unbounded DOM rendering, not the data fetch (which
already returns the full list in one small payload, and stays that way). Fixed page
size of 24 (divides cleanly across the grid's common column counts); Prev/Next +
"Page X of Y" indicator, hidden entirely for a single page; filter/search changes
reset to page 1. The clamp logic that prevents an emptied last page from staying
visible lives centrally inside `render()` itself (recomputed fresh on every call,
before the loadFailed/empty checks) — this meant the delete handler needed **zero**
changes to satisfy that requirement, since `render()` already re-clamps on every
invocation including the one delete already triggers. A cleaner design than the
explicit post-delete clamp call the task card anticipated, confirmed correct by PM on
diff review, not a shortcut. Implemented by Codex, accepted by PM per AR-06. 4 new
Playwright tests (`test_dashboard_pagination_caps_dom_navigates_and_resets_on_reload`,
`test_dashboard_pagination_is_hidden_for_a_single_page`,
`test_dashboard_filter_and_search_reset_pagination_to_first_page`,
`test_dashboard_delete_last_card_on_last_page_clamps_to_valid_page`) using an isolated
`_pagination_projects(count)` factory — confirmed via diff that the pre-existing
shared `MOCK_PROJECTS` constant and its 6 existing consumers were left completely
untouched, satisfying PM's explicit plan-review requirement. **Zero real defects found
on PM review** — PM independently re-ran every verification command, read the full
diff, and separately investigated (via `git log -S`) an unrelated observation from the
verification screenshot: the Dashboard's Vietnamese hero text has been present since
the project's very first commit (2026-09-10), confirmed untouched by this task — it's
the concrete instance behind the already-accepted "mixed EN/VI copy" P2 finding, not a
new or in-scope defect. 566/566 full suite passes (up from 562); PM's independent run
hit 6 known Gemini-retry timing flakes (worse than usual because the run itself ran
markedly slower than baseline), all confirmed passing instantly in isolation together
— non-regressive, Task 5.1 touched zero backend code. See `tasks/task-5.1.md` for the
full record.

### 5.2 Timeline polish (proportional width + keyboard resizer) — ✅ DONE (2026-09-17)

PM's research before writing the task card corrected the original audit's scope:
Script's timeline has no timing data at any point in the pipeline (audio doesn't
exist yet when Script is on-screen) and is genuinely out of scope for proportional
width — forcing a fake/estimated duration there would violate the project's "no fake
features" precedent. Only Video (already computes real per-line timing via
`timingForLine()`, just never applies it to width) and TTS (already calls
`Api.getAudioStatus()` in `init()`, the fetched job just isn't stored to `state` —
a small state addition, not a new API call) get proportional clip width, only once
real timing exists; clips without timing keep today's auto-width behavior, never a
guessed duration. Formula: 16px/second, clamped 72-240px, derived from 78 real timing
samples (p90 5.97s, max 7.66s) — a 3s clip stays at the 72px floor, a 7s clip reaches
112px, giving a real visible difference for the audit's exact complaint case. TTS
also stores the job from **both** `Api.getAudioStatus()` and `Api.generateAudio()` —
an addition Codex proposed beyond the original plan and PM independently verified
before endorsing (`app/api/audio.py` confirmed both endpoints return the identical
job shape with real `timestamps`), so widths update immediately after a first
Generate All instead of requiring a reload. The shared shell's horizontal timeline
resizer (`shell.js`'s `makeHorizontalResizer()`) gained a keydown handler mirroring
the existing vertical-resizer pattern exactly (`ArrowUp`/`ArrowDown`, 12/40px step,
`max()` called fresh on every keypress since it's a function not a constant) — fixes
keyboard access on all 3 timeline pages (Script/TTS/Video) at once since they share
the same component. Implemented by Codex, accepted by PM per AR-06. 3 new/extended
Playwright tests, all using real bounding-box width measurements rather than
style-attribute presence checks — including one that cleverly reuses the existing
`line-3` script fixture with a truncated timestamps override to exercise the
"missing timing mid-list" case realistically, and a full 4-step keyboard round-trip
test (`ArrowUp`/`ArrowDown`/`Shift+ArrowUp`/`Shift+ArrowDown`). **Zero real defects
found on PM review** — PM independently re-ran every verification command, read the
full diff, and confirmed via `git diff --exit-code` that `step2_script.js` and
`style.css` were genuinely untouched. 569/569 full suite passes (up from 566; 1 known
Gemini-retry timing flake on PM's independent run, confirmed passing in isolation).
See `tasks/task-5.2.md` for the full record.

### 5.3 Small polish batch — ✅ DONE (2026-09-17)

Three independent, low-risk fixes bundled per the brainstorm session's decision
(mirrors Task 2.3's and Task 4.4's precedent of bundling related small items): (1)
Learning's item cards gain `role="button"`/`tabindex="0"` plus a `keydown` handler
for `Enter`/`Space` — they stay `<div>`s, not real `<button>`s, since they contain
other interactive inline-edit children (`commitField()`'s `.field` elements), which
cannot legally nest inside a native button per HTML content-model rules. A strict
`event.target === card` guard isolates the new handler from those nested elements'
own keyboard handling. (2) Learning's inspector auto-selects the first item of the
active tab whenever nothing is selected (first load, first generate, or after
`switchTab()`'s existing clear-on-switch), via a single well-guarded
`selectFirstActiveItem()` helper reused by both `render()` and `switchTab()` — never
overriding an existing user selection, including the specific edge case of
re-activating the tab that already owns the current selection. (3) Video's "Speaker
avatars (optional)" section (the already-honestly-disclosed, not-yet-functional
LivePortrait feature) moves into a native `<details>`/`<summary>`, collapsed by
default — reusing the exact pattern already established for Script's per-line
language notes (`step2_script.js:134-141`), no custom JS collapse widget needed.
Implemented by Codex, accepted by PM per AR-06. Mid-implementation, Codex correctly
stopped and reported per AR-06 rather than silently patching out of scope: a
pre-existing test in `tests/test_video_shell_browser.py` (from Task 4.2c, not in this
task's locked file list) broke because it waited for `.avatar-preview` to become
visible while now hidden inside the collapsed `<details>` — PM authorized a narrow
one-line fix (open the details before the existing flow), no assertion changed. 3
new/renamed Playwright tests, including a real keyboard walkthrough (natural Tab
order from an inline-edit field into the next card and from the last tab button into
the first card, Enter selecting a card, and an actual `event.defaultPrevented`
capture proving Space's `preventDefault()` really fired) and a direct
`element.open`/`#avatar-grid` visibility assertion for the collapse behavior itself
(added to the pre-existing avatar upload/remove test, not just a new file). **Zero
real defects found on PM review** — PM independently re-ran every verification
command, read the full diff for all 5 touched files, and confirmed `style.css` was
genuinely untouched. 571/571 full suite passes, 0 flakes — a fully clean run. See
`tasks/task-5.3.md` for the full record.

**This closes Task 5.3 — and Phase 5 (UI Polish Backlog) in full.** All 3 tasks done
(5.1 Dashboard pagination, 5.2 Timeline polish, 5.3 Small polish batch), all
implemented by Codex and accepted by PM per AR-06 with zero real defects found across
any of the 3 reviews.

## Phase 6 Task Status

### 6.1 Theme flash + dead-end error link + range slider styling — ✅ DONE (2026-09-17)

Three real, PM-verified findings from a user-commissioned deep-dive Gemini audit
(`C:\Users\Admin\Documents\audit_chuyensau_dailyintelenglish`), bundled per the
precedent set by Task 2.3/4.4/5.3: (1) 4 pages (`music_library`, `step1_config`,
`step6_thumbnail`, `step7_youtube`) hardcoded `<html data-theme="dark">`, causing a
real dark→light flash for any user without a stored preference, since `theme.js`'s
already-correct light-default logic only runs on `DOMContentLoaded`, after the
browser already painted the hardcoded state — fix removed the hardcoded attribute,
no JS change, verified via a real HTTP fetch of the raw response (not the post-JS
DOM state, which always has some `data-theme` value once `theme.js` runs). (2) All 6
pipeline pages' (step2-7) "Missing project" error state was plain text with no way
back to the Dashboard — fix added an identical, narrowly-scoped
`showMissingProjectError()` function per page rendering a real, fully-static
(non-interpolated) link via `innerHTML`, without touching the existing `showError()`
contract for any other message — verified by a real negative-control test proving
every other error path still renders plain text with zero links. (3) TTS's
speed/pitch/volume range sliders had zero color styling and rendered each browser's
own default — fix is CSS-only (`accent-color: var(--accent)`), no new JS state,
verified via a dynamic color-probe test rather than a hardcoded expected hex value.
**A 4th audit claim was independently traced and found to be a false positive, not
included**: "YouTube chapters always use an estimated timestamp" —
`youtube_service.py::generate_package()` already branches correctly and uses real
measured `start_sec` values whenever a completed audio job exists
(`real_chapters_from_timestamps()`, wired up via `app/api/youtube.py`); only a stale
docstring comment inside the fallback function is out of date, not a functional bug.
Implemented by Codex, accepted by PM per AR-06. **Zero real defects found on PM
review** — PM independently re-ran every verification command and read the full
diff for all 13 touched files, confirming each of the 4 theme-flash HTML files
changed by exactly one line, all 6 JS files following an identical pattern with no
scope creep, and `app/`/`theme.js`/`style.css` genuinely untouched. 583/583 full
suite passes, 0 flakes — a fully clean run. See `tasks/task-6.1.md` for the full
record.

**This closes Task 6.1 — and Phase 6 (Quick Wins Batch) in full**, since it was the
phase's only task.

## Phase 7 Task Status

### 7.1 Downgrade project status + surface staleness signal on script edit — ✅ DONE (2026-09-18)

Origin: `.viepilot/requests/BUG-013.md`, auto-logged by `/vp-audit` (2026-09-17) while
independently re-verifying a Gemini audit claim. PM's own trace found the gap was
worse than described: `app/api/projects.py`'s `generate_script`/`regenerate_script_line`/
manual-save endpoints had **zero status guard at all** — a project's script could be
fully regenerated, a single line edited, or manually saved even after audio/video
already existed, with nothing invalidating the now-stale downstream artifacts. Fix: a
new `project_service.mark_script_changed()` internal operation, accepting no
caller-supplied target status, downgrades project status back to `script_generated`
(non-destructive — no files/records deleted) whenever this happens, wired into all 3
real script-mutation call sites. During plan review, Codex correctly caught a real
error in PM's own task card (the public route is `PUT /{project_id}`, not `PATCH` as
originally written) and correctly identified that the manual-save route
(`PUT /{project_id}/script`, the Step 2 UI's normal autosave path) shares the exact
same bug as the two AI-driven endpoints — both approved as in-scope corrections, not
scope creep, since both files were already in the locked `allowed_files`. Mid-
implementation, Codex's own first full-suite run surfaced 3 failures in the
pre-existing `tests/test_projects_write_lock.py` suite (which calls the renamed
internal helper by name); rather than touching that out-of-scope test file, Codex
preserved the legacy private helper's name/signature and re-verified — reported
honestly in the evidence rather than hidden. Implemented by Codex, accepted by PM per
AR-06. **Zero real defects found on PM review** — PM independently re-ran every
verification command and read the full diff for all 5 production/test files,
confirming `config_json` never embeds `status` (so the narrow raw status update can't
desync it), a real disk-and-DB test proves audio/video files and job rows survive the
downgrade byte-for-byte unchanged, and the public `PUT /{project_id}` endpoint's
forward-only guarantee is fully intact (a new end-to-end test drives a project through
all 4 real forward transitions before proving `complete -> draft` still returns 422).
596/598 full suite passes — the 2 failures are the project's long-documented
Gemini-retry/backoff timing flake class (`tests/test_script_service.py`, unrelated to
this task's 6 touched files), confirmed passing instantly in isolation. See
`tasks/task-7.1.md` for the full record.

**This closes Task 7.1 — and Phase 7 (Script Edit Staleness) in full**, since it was
the phase's only task.

## Phase 8 Task Status

### 8.1 Reconcile disabled-button CSS drift (ENH-005); ENH-004 re-scoped — ✅ DONE (2026-09-18)

Opened at the user's explicit request to continue processing ENH-004/ENH-005 and to
self-implement rather than delegate to Codex, to save time — a one-time deviation
from the AR-06 PM/Codex split for this task only, held to the same doc-first plan,
independent re-verification, and git-persistence gates. ENH-004 re-investigated
before any code was touched: `app/api/projects.py` lines 20-36 (an existing code
comment) document that a connection-wide `asyncio.Lock` (`_write_lock`) already
serializes every route — reads included — precisely because there's one shared
`aiosqlite` connection with no per-request transaction isolation. Given that,
`PRAGMA journal_mode=WAL` would be purely cosmetic (WAL's benefit only manifests with
separate connections per reader); a real fix means replacing `_write_lock` with a
full connection-pool architecture, a genuinely large change this project has
consistently deferred. Marked `wontfix` in `.viepilot/requests/ENH-004.md` with full
reasoning, no code changed. ENH-005 (CSS fragmentation) traced to one real root
cause: the shared `.btn[disabled]` rule in `style.css` had no `aria-disabled`
variant, so `music_library.html`, `step7_youtube.html`, and `step6_thumbnail.html`
each independently invented a local fix and drifted (opacity 0.55 vs the shared 0.58,
3 different selector strategies). Fix: extended the shared rule to also match
`.btn[aria-disabled="true"]`; removed the resulting fully-redundant local overrides;
`step6_thumbnail.html` kept only its genuinely non-redundant `button[disabled]`
selector (confirmed needed for its bare `.template-option`/`.variant-card` buttons,
which have no `.btn` class — `step6_thumbnail.js:89,123,161`), corrected to the
shared value; its drifted `.btn-sm` padding override was also removed. 2 new
Playwright tests added to `tests/test_quick_wins_browser.py`, independently confirmed
meaningful via a real revert-and-confirm-failure check (`git stash` on the fix,
re-ran the test, got `AssertionError: assert '0.55' == '1'`, then restored and
re-confirmed the pass). Self-verified rather than skipped because there was no
separate Implementer: re-ran every verification command (31/31 targeted+regression,
ruff clean, `git diff --check` exit 0), and the full suite independently: 601 passed,
1 failed (the project's long-documented Gemini-retry/backoff timing flake class,
`tests/test_script_service.py`, unrelated to this task's 5 touched files), confirmed
passing instantly in isolation. **Zero real defects found.** See
`tasks/task-8.1.md` for the full record.

**This closes Task 8.1 — and Phase 8 (CSS Consolidation) in full**, since it was the
phase's only task. Of the 4 Gemini-audit-derived findings left open after Phase 6
(GEMINI_RATE_LIMIT_RPM, DB connection lock, forward-only status machine, CSS
fragmentation), all 4 are now resolved: 1 was a nuanced correction (not a defect), 1
is correctly `wontfix` with reasoning recorded, and 2 (BUG-013, ENH-005) are fixed.

## Phase 9 Task Status

### 9.1 Preserve prior job data on regeneration failure; downgrade status on voice-settings change — ✅ DONE (2026-09-18)

Origin: the user had Codex run its own independent, parallel read-only `/vp-audit`
pass alongside PM's own audit. Codex found 10 issues (0 critical, 1 high, 4 medium, 5
low) with zero source-code changes and no auto-logged requests of its own. PM
independently re-verified all 5 "important" findings (the 1 high + 4 medium) by
reading the actual source directly, not taking the report on faith — all 5 confirmed
real, no false positives, the most accurate parallel-AI scan this project has seen
(contrast with the earlier Gemini audit, which had 1 false positive out of 4 checked
claims). PM also independently re-scored 2 of the 5: BUG-016 (Codex: high) confirmed
accurate but found to have a real mitigating factor Codex's report didn't mention
(both "Listen" and "Generate All" always force fresh re-synthesis before playing/
mixing, so actual audio output is never wrong — only the status/staleness signal is
missing, identical in spirit to BUG-013); BUG-017 (Codex: medium) re-scored to high
after PM traced the actual UPSERT behavior and found it's an unconditional data-loss
scenario (every regeneration failure after any prior success wipes that success's
file references), not merely a metadata inconsistency. User chose to open this phase
for BUG-016 and BUG-017; BUG-018/BUG-019/ENH-007 logged but out of scope. Doc-first
task card written (`tasks/task-9.1.md`), handed to Codex per AR-06. Notably, this
task's design explicitly guards against a fix that would naively reuse Task 7.1's
`mark_script_changed()` unmodified for the speaker-settings case — that function's
`draft -> script_generated` advance branch is specific to a script being generated
for the first time, and would incorrectly advance a project's status just from
editing a speaker's voice at Step 1, before any script exists.

Codex's delivered plan matched every locked decision exactly: `mark_audio_job_failed`/
`mark_video_job_failed` narrowly update only `status`/`error_message`/`completed_at`,
falling back to an error-only `INSERT` only when no job row exists; `download_audio`/
`download_video`'s status gate correctly widened to `("complete", "error")` with a
non-null path check (a necessary consequence of the acceptance criteria, not scope
creep); a shared `_downgrade_downstream_to_script_generated()` helper lets
`mark_script_changed()` (unchanged externally) and a new, separate
`mark_speaker_voice_changed()` share logic without the naive-reuse trap. Real
end-to-end tests generate actual audio/video, save the real response bytes, force a
second attempt to fail, and confirm the download endpoint returns the identical bytes
afterward. A fully-parametrized 5-status regression guard confirms the speaker case.
PM independently re-verified rather than accepting the report on its word: read the
full diff for all 6 production files, re-ran every verification command (120/120
targeted including Task 7.1's unmodified `test_project_service.py`, ruff clean,
`git diff --check` exit 0), and ran the full suite independently: 613 passed, 2
failed. One is the known Gemini-retry flake class; the other
(`test_music_library_waveform_browser.py::test_waveform_renders_real_pixels_for_a_real_audio_file`)
is a newly-observed flake, never seen before this session, touching code Task 9.1
never modified (music library waveform rendering) — both confirmed passing instantly
in isolation, noted honestly as a distinct flake rather than folded into the known
class. **Zero real defects found on PM review.** This closes Task 9.1 — and Phase 9
(Regeneration Integrity) in full, since it was the phase's only task. BUG-016 and
BUG-017 are now resolved.

## Phase 10 Task Status

### 10.1 Clear stale per-line audio cache on line regenerate; stop deleting avatar files before commit is confirmed — ✅ DONE (2026-09-18)

Origin: `.viepilot/requests/BUG-018.md`/`BUG-019.md`, both confirmed real during the
2026-09-18 audits but left out of Phase 9's scope. Opened via `/vp-debug` at the
user's request to continue fixing the backlog. For BUG-019, PM researched a real,
low-risk fix design before writing the task card: switch avatar uploads to unique
per-file filenames (instead of a fixed `{speaker_id}{suffix}` name), update the DB
to reference the new file inside the existing transaction, and only delete the
*previous* file as a best-effort step in the API route strictly after the
transaction's commit is confirmed to succeed — removing the forced "delete-old,
then-commit" coupling that causes the bug, without introducing a new read-serving
race (confirmed `resolve_avatar_path` always resolves whatever path is currently in
the DB, never a glob/fixed-name lookup). Noted explicitly that this legitimately
changes the existing `test_finalize_avatar_file_replaces_old_extension` test's
expectations, since that test currently locks in the exact buggy behavior. Doc-first
task card written (`tasks/task-10.1.md`). Mid-task, the user made a standing policy
change — PM self-implements from now on instead of delegating to Codex. PM
implemented both fixes directly: `update_script_line` now clears
`audio_cache_path`/`duration_seconds`; `_finalize_avatar_file` writes unique
filenames and never touches the old file, with a new
`cleanup_previous_avatar_file()` doing the actual deletion only after the route's
`_write_transaction` block confirms success. Updated 2 existing tests whose
assertions encoded the old buggy behavior. Added a core regression test forcing a
real `db.commit()` failure (reusing the exact pattern already established in
`tests/test_projects_write_lock.py`) and independently confirmed it meaningful via
a revert-and-confirm-failure check (reverting the fix made the test fail exactly as
predicted, before restoring it). 101/101 targeted tests pass, ruff clean,
`git diff --check` exit 0. **Zero real defects found on PM's own independent
review.**

### 10.2 Documentation cleanup — stale task-card status fields, README, ARCHITECTURE.md — ✅ DONE (2026-09-18)

Origin: `.viepilot/requests/BUG-014.md`, `BUG-015.md`, `ENH-006.md`, `ENH-007.md` —
4 pure documentation/metadata findings, bundled per the Task 2.3/4.4/5.3/6.1
precedent. Before writing the task card, PM re-verified ENH-007's Mermaid-sidecar
claim by confirming `learning_service` (LCS) is genuinely wired into
`app/api/learning.py` with a real Gemini call, validating that the sidecar file
(which includes LCS) is the correct version and the embedded ARCHITECTURE.md block
(which omits it) is the one to fix. Doc-first task card written
(`tasks/task-10.2.md`). Self-implemented by PM per the same standing policy change:
fixed all 4 Phase 2 task cards' `Status` fields; rewrote README.md's Phase 4 section
to its real final state and added a new Phases 5-9 summary section; added a
status-downgrade note to ARCHITECTURE.md's Project data model (covering both Task
7.1's and Task 9.1's downgrade exceptions) and fixed a stale `tts_engine: omnivoice`
example value found in the same block; corrected the System Overview text diagram
(removed the WebSocket claim, Edge TTS shown as the real primary engine) and the
data-flow Mermaid diagram (renamed the OmniVoice node, marked LivePortrait lip-sync
"NOT implemented, deferred"); synced the embedded system-overview Mermaid block with
its sidecar byte-for-byte (confirmed via direct diff); and found + fixed the same
LivePortrait inaccuracy in the separate Module Dependencies diagram (both embedded
and sidecar copies), after confirming via a repo-wide grep that no `app/` code
references LivePortrait except docstrings explaining it's not built. No application
code touched — `git diff --check` clean. **Zero real defects found.**

**This closes Task 10.1 and Task 10.2 — and Phase 10 (Backlog Cleanup) in full.**
Every finding from both 2026-09-18 audits (Codex's parallel scan and PM's own
read-only pass) is now resolved: BUG-013 through BUG-019 all fixed; ENH-004
correctly `wontfix` with reasoning recorded; ENH-005 through ENH-007 all fixed.

## Phase 11 Task Status

### 11.1 Third-audit fixes — avatar delete, TTS engine contract, TTS lock-holding, global sleep-patch, docs — ✅ DONE (2026-09-18)

Origin: a third independent Codex `/vp-audit` pass, run at the user's request right
after Phase 10 closed. 7 findings (0 critical, 1 high, 4 medium, 2 low). PM
independently re-verified every one before acting — all 7 confirmed real, no false
positives across 3 separate Codex audits this session now.

**Finding 1 (high)**: `avatar_service.delete_avatar()` deleted the file before the
DB reference change was confirmed committed — the exact same root cause as BUG-019,
which Task 10.1 fixed for upload/replace but explicitly excluded from `delete_avatar`
with reasoning PM now recognizes was wrong ("no new file involved" doesn't matter —
the bug is about filesystem-mutation-before-commit-confirmation, which applies to a
plain delete too). Fixed the same way: `delete_avatar` now only clears the DB
reference and returns the file(s) to remove; the route deletes them via
`cleanup_previous_avatar_file` only after `_write_transaction` confirms success.
Removed the now-dead `_remove_existing_avatar_files` helper. New regression test
independently confirmed meaningful via a real revert-and-confirm-failure check.

**Finding 2 (medium)**: `TTS_ENGINES` accepted `piper`/`google`/`azure` as legal
speaker voice-engine values with zero actual synthesis implementation anywhere —
confirmed via grep. Selecting any of them silently used Edge TTS instead, no error.
Also confirmed `_synthesize_omnivoice()` is a hardcoded, unconditional-fail stub
(not a real check), yet `/api/tts/engines` reported it `available=true` from a mere
directory-existence check. Narrowed `TTS_ENGINES` to `["omnivoice", "edge_tts"]`;
`omnivoice` kept because it has a real, honestly-failing code path matching this
project's established fallback-pattern precedent. `/api/tts/engines` now
unconditionally reports `omnivoice: available=false` and drops `piper` entirely.

**Finding 3 (medium)**: `preview_line` (TTS preview) held the app's single
connection-wide write lock across the actual Edge TTS network call — directly
violating this project's own documented rule (already correctly followed for
Gemini calls and audio/video generation) that slow network/GPU work must never run
while holding that lock. Split `tts_service.synthesize_line` into
`synthesize_line_audio` (slow, no DB access) and `save_line_audio_cache` (fast DB
write); the route now calls them with no lock held in between, matching the
established pattern exactly. New concurrency regression test (a real
`asyncio.Event`-gated fake Edge TTS call plus a concurrent `_read_transaction`
under a timeout) independently confirmed meaningful via a real
revert-and-confirm-failure check — the old code genuinely timed out.

**Finding 4 (medium) — a plausible root cause for this project's long-documented
Gemini-retry flake class**: 4 test files' `no_real_sleep` fixtures
(`test_script_service.py`, `test_learning_service.py`, `test_tts_service.py`,
`test_youtube_service.py`) all did `monkeypatch.setattr(X.asyncio, "sleep",
fake_sleep)` — since each service module does a plain `import asyncio`, this patches
the *shared, process-wide* `asyncio.sleep`, not just that module's own retry calls.
Codex's audit observed ~5.5 million unexpected calls during a full run — plausibly
another library's internal poll-sleep loop (e.g. Playwright's) having its sleep
silently replaced by a no-op mid-poll, turning it into a tight busy-spin, during the
exact window one of these fixtures was active. All 4 service files now do
`from asyncio import sleep` and call the bare name; all 4 fixtures now patch that
module's own local `sleep` binding instead of the shared `asyncio` module. This may
well explain — and eliminate, or at least reduce — the "known Gemini-retry timing
flake" that has appeared in dozens of full-suite runs throughout this entire
session; the next several full-suite runs will show whether it recurs.

**Finding 5 (medium) — ENH-007 wasn't actually fully fixed in Task 10.2**: PM had
synced the system-overview and module-dependencies sidecars, and corrected the
embedded data-flow diagram, but never checked whether `data-flow.mermaid` had its
own sidecar file — it did, and still had the original OmniVoice/LivePortrait-as-active
content, fully diverged from the corrected embedded version. Separately, PM's own
Task 10.2 edit introduced a *new* inaccuracy: claiming OmniVoice "was built and
verified working in Phase 1" — false, confirmed by direct code read
(`_synthesize_omnivoice()` is an unconditional stub) and by this document's own
pre-existing, more accurate explanation elsewhere (OmniVoice's real API turned out
to be voice cloning, not the voice design originally envisioned — PM should have
found and deferred to that section before writing new, wrong content). Regenerated
`data-flow.mermaid` directly from the corrected embedded block (byte-for-byte
diffed). Rewrote the System Overview note to state facts accurately and point to
the correct existing explanation instead of duplicating a wrong one. Also found and
removed a now-fictional `Piper TTS` node from both diagrams (embedded + sidecars,
consequence of Finding 2), regenerating both sidecars directly from their corrected
embedded blocks.

**Finding 6 (low)**: `.viepilot/PROJECT-META.md`, never touched this entire
session, still said `Version: 0.1.0` (crystallize-time placeholder) and described
"TTS (OmniVoice + Edge TTS)" as if both were real. Corrected to `1.0.0-beta` and an
accurate one-line engine description.

**Finding 7 (low)**: README's Phases 5-9 summary section, written mid-Task-10.2
before Phase 10 itself was accepted, now omitted the completed Phase 10. Retitled
"Phases 5-10" with a new row.

**Tier 1 Low, acknowledged but not fixed**: Phase 8's entire doc-first plan +
implementation live in one commit (`f21bd60`), so git history alone can't prove the
plan predated the code (even though the task card's own content genuinely was
written first). Rewriting already-pushed shared history is out of scope for a
documentation finding — not done. Adopted going forward: self-implemented tasks
should commit a plan-only step before implementation when the design is knowable in
advance, so git history itself becomes the proof, matching the existing pattern for
every Codex-delegated task.

PM independently re-verified rather than accepting its own draft work as final:
re-ran every targeted test (207/207 across 11 files), ruff clean, `git diff --check`
clean, both new regression tests confirmed meaningful via real
revert-and-confirm-failure checks. Full suite run independently: 620 passed, 1
failed (`test_dashboard_delete_removes_card_after_confirm`, a newly-observed,
unrelated Playwright timing flake, confirmed passing instantly in isolation) in
330.31s — notably, **zero** occurrences of the long-documented Gemini-retry flake
class this run, and the fastest full-suite run in recent memory, a strong positive
signal that fix #4 addressed its actual root cause. **Zero real defects found on
PM's own review of this task.**

**This closes Task 11.1 — and Phase 11 (Third Audit Fixes) in full.** Every
finding from all 3 independent audits this session (PM's own 2026-09-18 read-only
pass, Codex's 2026-09-18 parallel scan, and this third Codex pass) is now resolved.

## Phase 12 Task Status

### 12.1 Settings page — Gemini API key stored in DB with `.env` fallback — ✅ DONE (2026-09-18)

Origin: new scope, requested directly by the user (not audit-derived) right after
being told the project was ready for trial — "sao không tạo một ô nhập API key
trong phần cài đặt". Scoped via `AskUserQuestion`: user chose a dedicated Settings
page saving to the database (over lighter alternatives).

New `app_settings` key/value DB table (migration `004_app_settings.sql`) and
`app/services/settings_service.py`: a DB-stored key always takes priority over
`.env`, applied immediately (no restart) by mutating the shared
`config.settings.GEMINI_API_KEY` singleton in place — the 4 existing Gemini-calling
services needed zero changes. `config.ENV_GEMINI_API_KEY` captures the original
`.env`-sourced value once at import time so "clear the stored key" correctly
reverts to it instead of going blank. New `/api/settings` router (`GET`/`PUT`/
`DELETE`) reusing `app/api/projects.py`'s existing `_write_transaction` lock
pattern, and never returning the raw key — only a masked preview (first 6 + last 4
chars). New Settings page linked from the dashboard topbar.

19 new tests (service + full HTTP round-trip), independently confirmed meaningful
via a real revert-and-confirm-failure check (`git stash` the whole implementation,
all 19 failed with `AttributeError` as predicted, restored). One real bug was
caught by the tests themselves during development: the first draft of a "clear
reverts to env" API test only isolated `settings.GEMINI_API_KEY`, not the separate
`config.ENV_GEMINI_API_KEY` constant — so it accidentally reverted to, and printed
into the test failure output, this machine's real live `.env` Gemini key. This was
a test-isolation bug, not a service bug (the service's real-revert behavior is
exactly correct); fixed by isolating both attributes in the test fixture.

Full suite: 640/640 passed (621 + 19 new), 293.22s, zero flakes. **Manually driven
end-to-end against the real running dev server with Playwright** (not just
unit-tested): opened `/settings`, confirmed the real key showed masked and
correctly labeled, saved a fake key, confirmed it took effect immediately and
survived a page reload (real DB persistence), toggled show/hide, cleared it back to
the real `.env` value, and confirmed the dashboard's new ⚙️ link navigates
correctly — then confirmed directly in `data/app.db` that no test data was left
behind and the user's real key was unaffected. **Zero real defects found on PM's
own review.**

### 12.2 Package as a standalone Windows `.exe` (PyInstaller) — ✅ DONE (2026-09-18)

New `app/core/paths.get_project_root()` centralizes what used to be 5 independent
`Path(__file__)`-walking constants across `app/main.py`,
`thumbnail_service.py`/`video_service.py`/`prompt_loader.py`/`database.py` — none
of that was guaranteed to survive being frozen into a PyInstaller build.
`Settings.DATA_DIR` switched to a frozen-aware `default_factory`
(`%LOCALAPPDATA%\DailyIntelEnglishStudio\data` when packaged, unchanged
otherwise, still fully overridable by `DIE_DATA_DIR`). New
`app/desktop_launcher.py`: programmatic `uvicorn.run(reload=False)` (the dev
`--reload` flag doesn't survive freezing), auto-opens the browser once the port
actually accepts connections (polled via a plain socket connect, not a fixed
sleep), and reuses an already-running instance instead of crashing if the exe is
launched a second time.

**Two real problems found and fixed during the actual build+run, not just
written to compile.** First: the initial build came out at **4.5GB** --
PyInstaller pulled in `torch` (2.11.0+cu128, ~4GB with bundled CUDA kernels),
`torchaudio`, `transformers`, `tensorflow`, `sklearn`, `librosa`, `numba` --
confirmed via a repo-wide grep that zero files under `app/` import any of them;
they're leftover packages from the long-abandoned OmniVoice GPU experimentation
(Phase 1), not real dependencies. Excluded them explicitly in the spec, rebuilt
to **169MB** (~27x smaller). Second: testing `DATA_DIR`'s frozen-aware default
by launching the exe from the project root picked up the real dev `.env`
(`DIE_DATA_DIR=data` explicitly set there) -- correct pydantic-settings
precedence, but an unrealistic test scenario that wrote a test project into the
shared dev database. Deleted it immediately, then correctly re-tested by
launching the exe from its own dist folder (no `.env` present, matching a real
user) -- confirmed `DATA_DIR` resolved to `%LOCALAPPDATA%` with a fresh, empty
database as intended.

Full suite: 639/640 passed, 322.79s -- 1 failure
(`test_youtube_browser.py::test_existing_package_loads_directly_without_generate_click`),
confirmed passing instantly in isolation, the third distinct one-off
Playwright-class flake observed this session (after Task 9.1's waveform test and
Task 11.1's dashboard-delete test), not a regression -- touches no file this task
modified.

**Actually built and run, twice** (per this project's "run it for real"
discipline, not just "verify it compiles"): ran `pyinstaller` directly, launched
the real `.exe` (not `python -m uvicorn`) from its own dist folder, confirmed
real startup logs and that the browser-auto-open thread fired for real, drove
the running packaged exe with Playwright across the dashboard/`/step1`/`/settings`
(all three loading and functioning correctly, including a real DB-backed
settings save on a fresh install with no `.env`), and confirmed a second launch
while the first was still running exits cleanly instead of crashing. Cleaned up
the accidental dev-database test project afterward. **Zero real defects found on
PM's own review.**

**This closes Task 12.2 -- and Phase 12 (Settings & Packaging) in full.** Both
tasks were new scope requested directly by the user, not audit-derived.

## Phase 13 Task Status

Phase 13 replaces the fragile long synchronous script/learning production path with
durable provider-neutral jobs, qualifies Qwen locally on the RTX 3060, retains one
visible stable Gemini fallback, and requires a real eight-minute Edge TTS/audio/video
trial before local-primary promotion. The controlling contract is
`docs/implementation/phase-13-local-first-ai-reliability.md`.

### 13.0 Baseline, ADR, backup, rollback contract — ✅ DONE (2026-09-18)

- Doc-first plan: 595 lines, 11 strict task contracts, independently reviewed for
  backend and operations risks before implementation.
- ADR and sanitized A2/B1/C1 golden inputs plus frozen legacy API/output fixtures added.
- Offline baseline verifier: 3 project fixtures and 4 endpoint contracts pass; ruff
  clean.
- Live `data/app.db` backed up with SQLite Online Backup API to ignored local storage,
  not raw file copy. Source and backup both report `integrity_check=ok`, zero foreign-
  key violations, 6 migrations, 293 projects, 573 script lines, and 157 learning packs.
  Backup is 1,290,240 bytes; SHA-256 is recorded in the Task 13.0 evidence card. It may
  contain the DB-stored Gemini key and must never be staged/uploaded.

### 13.1 Provision and qualify Ollama/Qwen (Gate A) — ✅ DONE (2026-09-18T23:31Z), PASS

Gate A required loopback-only Ollama, three valid nested-schema probes, full GPU
offload, ≥1.5 GiB free VRAM and ≥4 GiB free RAM at 16K, no OOM/TDR, and measured
cancel/down/model-missing behavior. **Result: PASS, all 9 gate checks true.** Before
the real run, reviewed the WIP `scripts/qualify_local_ai.py` (left over from a session
that stopped abruptly on quota) and fixed two real gaps rather than trusting
`ruff`/`--help` alone: the `ollama` CLI was resolved by bare command name, which fails
in a shell whose `PATH` predates a fresh winget install even though the binary is
genuinely present (`resolve_ollama_binary()`, prefers `PATH`, falls back to the
documented official install location via `Path.home()`); and evidence env vars were
read via `os.environ.get()`, which is empty in a process started before `setx`
persisted them, even though the real User-scope values were correctly set
(`resolved_env()`/`persisted_user_env()`, a controlled read-only PowerShell query).
Pulled `qwen3.5:9b` for real (digest `6488c96fa5faab64...`, prefix `6488c96fa5fa`
matching the plan's expected tag; `Q4_K_M`, 6.6 GB, 9.7B params). Real qualification run
against the live loopback server: 100% GPU offload at 16K context, minimum free VRAM
4,370 MiB (≥1,536 MiB required), minimum free RAM 17,504 MiB (≥4,096 MiB required),
peak VRAM used 7,741 MiB of 12,288 MiB, ~48.2 tokens/sec steady state, cold load
33.41s/warm ~6.3s, 3/3 nested-schema probes valid, model-missing (HTTP 404),
server-down (bounded `ConnectTimeout`), early-stream-close (server confirmed healthy
after), and unload (`keep_alive: 0`, confirmed empty `ollama ps`) all correctly
detected. No memory-headroom mitigation was needed. Evidence:
`data/quality_reviews/phase13/gate-a/ollama-20260918T233107Z.json` (gitignored, no
secrets — only prompt hashes and metrics). New `docs/operations/local-ai.md` covers
install/version/digest/location, loopback/cloud-disabled/concurrency config, all
lifecycle operations, an auto-update/digest-change requalification warning,
troubleshooting, and the local-vs-cloud privacy distinction. This PASS qualifies
`qwen3.5:9b` for Task 13.2+ integration; it does not by itself authorize local-primary
rollout — Gate B (Task 13.9) still decides local-primary versus
Gemini-primary/local-experimental. A second interactive Claude Code session was found
active on this same working directory mid-task and briefly wrote a duplicate summary
into `tasks/task-13.1.md`, de-duplicated by this session; no competing commit had
landed on `main` first. See `.viepilot/phases/13-local-first-ai-reliability/tasks/task-13.1.md`
for the full record.

### 13.2 Provider-neutral AI gateway — ✅ DONE (2026-09-19)

Built the typed provider contract layer product code will route through starting
Task 13.4/13.5: `app/services/ai/contracts.py` (`AIMode` enum, `GenerationRequest`/
`GenerationResult` Pydantic models, a `Provider` structural protocol),
`ollama_provider.py`/`gemini_provider.py` (each makes exactly **one** HTTP attempt,
no internal retry loop — the router owns all retry/fallback policy so it can't
multiply with a provider-internal one), `router.py` (`AIRouter`: routes by
`AI_MODE`, one same-provider retry on a retryable error class, one visible Gemini
fallback in hybrid mode, an in-process circuit breaker over the local provider,
and an overall `deadline_seconds` budget via `asyncio.wait_for`), `validation.py`
(`parse_and_validate`, the one shared JSON-parse-plus-Pydantic-validate primitive
Task 13.4/13.5 will reuse instead of each service's own ad hoc pair), and
`fake_provider.py` (a network-free double so router/provider tests never call a
real model). Live-reverified `gemini-3.8-flash` (real `models.list` call + the
official docs page) is still the current stable, non-preview Flash model before
locking the gateway's single Gemini adapter to it — no new model name introduced,
reuses the existing `constants.GEMINI_MODEL`. New settings: `AI_MODE` (kill switch,
default `"gemini"` — packaged-safe per ADR-001), `OLLAMA_BASE_URL`, `OLLAMA_MODEL`,
`OLLAMA_NUM_CTX`, `AI_REQUEST_DEADLINE_SECONDS`. New typed exceptions:
`ProviderError` and 6 subclasses plus `SchemaValidationError`, all logged with
model/purpose/prompt_hash/latency/tokens only — never the prompt or API key. 43 new
tests; a deliberate revert-and-confirm-failure check (temporarily added a 3rd
nested retry to the router) confirmed the "no nested retries" test coverage is
real — 4 tests failed for the right reason, then passed again after reverting.
Full suite: **683/683 pass**, 0 flakes, `ruff check .` clean, `git diff --check`
clean. Nothing outside this package's own tests calls the gateway yet — no legacy
route or service (`script_service.py`, `learning_service.py`, any `app/api/*.py`)
was touched, per this task's "no legacy service is switched before contract tests
pass" constraint. See
`.viepilot/phases/13-local-first-ai-reliability/tasks/task-13.2.md` for the full
plan and evidence record.

### 13.3 Shared transactions and durable AI jobs — ✅ DONE (2026-09-19)

Moved the app's single connection-wide `_write_lock`/`_read_transaction`/
`_write_transaction` out of `app/api/projects.py` (a router that 7 other routers
and 2 tests imported cross-router — the wrong shape) into a real shared home,
`app/db/transactions.py` (public names, no leading underscore). All 43 call
sites across `settings.py`/`tts.py`/`audio.py`/`video.py`/`youtube.py`/
`thumbnail.py`/`learning.py` plus `tests/conftest.py`'s reset fixture and 2
regression test files moved together in the same change — confirmed zero
dual-lock state at any point via a whole-repo grep. Added the durable job
schema (`006_ai_generation_jobs.sql`): `ai_generation_jobs` (full column set per
the controlling plan, CHECK constraints, cascade delete) and
`ai_generation_checkpoints`, with two indexes doing real work — a **partial**
unique index enforces one active job per project+operation at the DB level, and
a full unique index on `(project_id, operation, idempotency_key)` makes a
client's idempotent retry durable even after the job goes terminal. Built
`app/services/ai_job_service.py` (explicit legal-transition table; atomic
single-`UPDATE` claim, never SELECT-then-UPDATE; owner-checked heartbeat;
idempotent cancel; bounded abandoned-job recovery that forces `error` after
`AI_JOB_MAX_RECOVERY_ATTEMPTS` instead of retrying forever) and
`app/services/ai_worker.py` (claim/process loop that stays idle — touching no
DB row — until Task 13.4/13.5 register a "script"/"learning" handler; bounded
graceful shutdown that cancels rather than waits forever for a stuck handler).
New `app/api/ai_jobs.py`: `POST .../ai-jobs` (202 new / 200 existing, both
contract-legal), `GET .../ai-jobs/active` (`null` for "nothing yet", matching
this app's established style, never a bogus 404), `GET .../ai-jobs/{id}`/
`POST .../ai-jobs/{id}/cancel` (404 on cross-project access), and
`GET /api/ai/health` (mode/reachability/model/fallback-configured, confirmed to
never leak the Gemini key even under a forced-unreachable-Ollama test, and
never fails app startup). **Real bug found via API-level testing that
service/worker unit tests missed**: `AIWorker._stop_event` was constructed once
in `__init__` and reused across `start()`/`stop()` cycles — invisible to tests
using one raw `db` fixture and one event loop, but `TestClient(app)`'s real
FastAPI lifespan runs under a fresh loop per test, so the second test's
shutdown raised `RuntimeError: ... bound to a different event loop` (12/19 API
tests failed). Fixed by constructing a fresh `asyncio.Event()` inside `start()`
itself. Revert-and-confirm-failure: reverted, re-ran — the same 12 tests failed
identically; restored, re-ran — 19/19 pass. 90 new tests total (7 migration, 44
service, 6 worker, 19 API/health). Full suite: **753/753 pass**, 0 flakes,
`ruff check .` clean, `git diff --check` clean. No content pipeline registered
yet — nothing in production creates a real script/learning job through this
system until Task 13.4/13.5 land. See
`.viepilot/phases/13-local-first-ai-reliability/tasks/task-13.3.md` for the full
plan and evidence record.

### 13.4 Checkpointed script pipeline — ✅ DONE (2026-09-19)

Built `app/services/script_pipeline.py` implementing the controlling plan's exact
8-step script pipeline: a fresh project re-fetch (never trusting the job's
creation-time snapshot) with a hash/cancel check before any generation work;
`compute_target_words()`/`plan_sections()` (CEFR-WPM-based, matching the plan's
own worked example — B1 × 8 minutes = 800 words exactly); outline generation
(resumable from a `section_index=0` checkpoint); per-section generate → validate
→ one repair attempt on failure → checkpoint → progress/heartbeat; global merge
validation (±10% word budget, 35-65% two-speaker word-share balance, exact-
duplicate-line rejection, repeated normalized 8-gram ratio <1% — plus a topic-
relevance keyword-overlap **warning**, deliberately never a hard reject per the
plan); a second hash/cancel re-check immediately before the final save (closing
the race where inputs change or a cancel arrives during the last section); and
one atomic `write_transaction` covering the script save, `project_service.
mark_script_changed()` (reused unmodified — not in this task's allowed files, and
didn't need to be, since it already handles both the forward and downgrade status
transitions), and the job's `complete` transition together. New prompts
`outline.txt`/`section.txt`/`repair.txt` reuse the existing genre/CEFR
instruction-block loaders and the language-feature precedence rules already
proven in `script_base.txt`; line IDs are never requested from the model — the
merge step assigns them server-side via the existing `script_service.save_script()`.
`regenerate_line()` migrated onto the Task 13.2 `AIRouter` via a new
`_build_ai_router()` factory and an injectable `router` parameter — prompt,
schema, and the speaker-id-change check are byte-for-byte unchanged, and all 18
pre-existing `test_script_service.py` tests plus all 30 `test_script_api.py`
tests pass **unmodified**, proving the transport swap is invisible to every
existing caller. `generate_script()` (the legacy bulk path) was deliberately not
touched — it remains the synchronous compatibility route's implementation until
Task 13.7. 30 new/updated tests, including 6 full end-to-end handler tests
against a real in-memory DB with a `FakeProvider`-backed router: happy path
(→ `complete`, server-assigned UUIDs, `script_generated` status), one-repair-
then-succeed, repair-also-fails (→ `error`, prior — empty — script provably
unchanged), **interrupted-then-resumed** (a scripted exception simulates an
abrupt stop after section 1 checkpoints; a second, independent `FakeProvider`
scripted with only section 2 proves resumption skips regenerating the outline
and section 1), cancel-requested-before-start, and stale-on-project-change.
**Revert-and-confirm-failure**: disabled the checkpoint-skip condition —
the resume test failed with the same exception the interrupted run hit;
restored — 22/22 pipeline tests pass again. Full suite: **778/778 pass**, 0
flakes, `ruff check .`/`git diff --check` clean. `app/main.py` wiring of the new
handler onto the app's shared worker is deferred to Task 13.6 (not in this
task's allowed files) — recorded in `HANDOFF.json`, not dropped. See
`.viepilot/phases/13-local-first-ai-reliability/tasks/task-13.4.md` for the full
plan and evidence record.

### 13.5 Grounded learning pipeline — ✅ DONE (2026-09-19)

Built `app/services/learning_pipeline.py`: `validate_counts`/`validate_grounding`/
`validate_duplicates`/`validate_answers` (pure functions, sourced from the
existing `learning_pack.txt` prompt's own stated ranges — 1-2 grammar points,
3-5 questions — never invented thresholds) and a `make_handler(router)`
orchestration mirroring `script_pipeline.py`'s structure: initial project-hash
+ cancel check, a script-empty guard, one generation call at a low
(`LEARNING_GENERATION_TEMPERATURE = 0.2`) temperature per the plan, validation,
one repair pass through a new `prompts/learning/learning_repair.txt` on
failure, a second re-check immediately before saving, and one atomic
transaction for the final save + `complete` transition. **Real gap found and
honestly worked around**: `ai_generation_jobs.script_hash_at_start` (added in
Task 13.3's migration) is never populated by `create_job()`/`app/api/ai_jobs.py`
— neither file is in this task's allowed list either — so the pipeline
substitutes its own start-vs-final-save script-hash comparison
(`learning_service.compute_script_hash`, new, hashes only speaker_id/text) to
close the same race window functionally; recorded in the task card rather than
silently skipped, the same way Task 13.4 recorded the `app/main.py` wiring gap.
26 new tests: 5 labeled "fixture" tests for the deterministic pack-validation
cases the task card names (valid pack, ungrounded example, duplicate question,
MCQ answer not in options, too-few-questions), 4 more targeted validator
tests, and 7 full end-to-end handler tests against a real in-memory DB with a
`FakeProvider`-backed router (happy path, repair, repair-fails, script-empty,
cancel, stale-on-project-change, and **stale-on-script-change-during-
generation** — a monkeypatched `get_script` simulates a concurrent edit
landing mid-flight). **Revert-and-confirm-failure** on that last check:
disabling the script-hash-at-final-save comparison made the job complete on
now-stale content instead of failing; restoring it brought all 16 pipeline
tests back to green. All 20 pre-existing `test_learning_service.py` tests and
all 22 `test_learning_api.py` tests pass **unmodified**. Full suite:
**794/794 pass**, 0 flakes, `ruff check .`/`git diff --check` clean. Every
content pipeline Phase 13 planned (script + learning) now exists; neither is
wired into the running app yet (`app/main.py` deferred to Task 13.6). See
`.viepilot/phases/13-local-first-ai-reliability/tasks/task-13.5.md` for the
full plan and evidence record.

### 13.6 Settings, health, and Step 2/3 job UX — ✅ DONE (2026-09-19)

Exposed and validated the AI provider mode: `settings_service.get_ai_mode_status`/
`set_ai_mode`/`load_ai_mode_from_db` (mirroring the existing Gemini-key
functions' shape) and `PUT /api/settings/ai-mode`, merged into the existing
`GET /api/settings` payload. `app/main.py`'s lifespan now builds one real
`AIRouter` from settings and registers `script_pipeline.make_handler(router)`/
`learning_pipeline.make_handler(router)` on the `AIWorker` before starting it —
**both content pipelines built in Tasks 13.4/13.5 are reachable through the
running app for the first time**. Step 2 and Step 3's `handleGenerate` migrated
from one blocking `Api.generateScript()`/learning call onto a new shared
`frontend/static/js/ai_job.js` module (create-or-resume, 2s visible / 8s
hidden-tab polling backoff, keyboard-accessible cancel, terminal-state promise
settlement) with resume-on-load wired into each page's `init()` so a refresh
mid-generation reattaches instead of showing a false empty state. **Real
regression caught by running existing tests, not assumed safe**: the first
`GET /api/settings` merge used `"source"` as the AI-mode status key, silently
overwriting the Gemini-key status's own `"source"` — fixed by renaming to
`"ai_mode_source"`. **Two more real regressions found by actually running the
full pre-existing browser suite**: `tests/test_keyboard_shortcuts_browser.py`
and `tests/test_learning_shell_browser.py` both mocked the old synchronous
generate endpoints directly; fixed to mock the job-creation/polling endpoints
instead, preserving each test's actual intent. **A third regression found only
in a full-suite run**: the two new job browser test files'
`live_server_url` fixture (copied from the pre-existing keyboard-shortcuts
pattern) never stopped its background `uvicorn.Server` thread, leaking the
process-wide `Database`/`AIWorker` singletons into
`tests/test_settings_api.py` — confirmed by bisection (807/807 pass without
the two new files, the one failure with them) and fixed with an explicit
`server.should_exit = True` + `thread.join()` teardown. A non-obvious
JS Promise-auto-flattening bug in `ai_job.js` (`start()`/`resume()` returning
their internal promise would have made `await currentAiJob.start()` block for
the entire job lifecycle instead of just job creation) was found and fixed by
reasoning before it could ship, not by a failing test. 12 new browser tests
(`test_script_jobs_browser.py`/`test_learning_jobs_browser.py`: refresh-
resumes-active-job, duplicate-click-prevention, keyboard-accessible cancel,
fallback banner, terminal error shows retry and never a raw exception/error
code, `aria-live` present), 3 new in `test_ai_health_api.py`, 5 new each in
`test_settings_service.py`/`test_settings_api.py`. Full suite: **819/819
pass**, 0 flakes (345.22s), `ruff check .`/`git diff --check` clean. See
`.viepilot/phases/13-local-first-ai-reliability/tasks/task-13.6.md` for the
full plan and evidence record.

### 13.7 Cloud fallback and compatibility — ✅ DONE (2026-09-20)

Session continuation after a Codex-quota interruption/handoff. The handoff prompt
described Task 13.1 as still `in_progress`, which was stale -- `git log` and
`PHASE-STATE.md` both confirmed Tasks 13.0-13.6 were already `done` (through
commit `336a587`) before any action was taken; the real WIP was Task 13.7, not
13.1. Read every required doc plus the actual current `app/services/ai/**`,
all four Gemini-consumer service files, both legacy API routes, and all four
services' existing test files before writing the doc-first plan.
Live-reverified `gemini-3.8-flash` (real `models.list` call + official docs)
is still Google's current stable, non-preview Flash model, one day after Task
13.2's own check. Found Gemini's real Interactions-API background execution
(`ai.google.dev/gemini-api/docs/background-execution`) supports
`gemini-3.8-flash` -- but deliberately left it unwired: persisting/polling
`ai_generation_jobs.remote_interaction_id` (a column Task 13.3 added but
nothing reads/writes yet) needs `app/services/ai_worker.py`/
`ai_job_service.py`, neither in this task's allowed files; ADR-001 explicitly
permits the existing synchronous foreground call as valid whether or not
background is available, so this is a deliberate, documented deferral to a
future task, not a dropped requirement. Migrated all 4 direct Gemini
consumers (`script_service.generate_script`, `learning_service.
generate_learning_pack`, `thumbnail_service.generate_suggestions`,
`youtube_service.generate_package`) off their own duplicated
`_call_gemini`/`_attempt_model`/`_generate_with_retry`/`GEMINI_MODEL_FALLBACKS`
transport onto the shared `AIRouter` gateway via one new shared
`app/services/ai/router.py::build_ai_router_from_settings()` factory
(replacing 4 near-identical private copies). ADR-001's explicit rejection of
"multiple automatic fallback models" means the old 6-model quota-spreading
cascade is deliberately not preserved -- only response *shape* was promised
unchanged, not internal retry behavior. Each consumer's upfront
`GEMINI_API_KEY`-required guard became mode-aware (`AI_MODE=local`/`hybrid`
no longer needs a Gemini key), and each gained an injectable `router`
parameter mirroring `regenerate_line`'s existing Task 13.4 pattern. Both
legacy synchronous generate routes marked `deprecated=True` with a docstring
pointing at the durable-jobs API, response contract byte-for-byte unchanged;
`docs/api.md` regenerated (also closed a pre-existing drift gap from Tasks
13.3/13.6 never having triggered a regeneration). **Doc-first gate found two
real scope gaps, both recorded in `tasks/task-13.7.md` before code, matching
the precedent from 13.5/13.6**: (1) the migration meant
`tests/test_script_service.py`/`test_learning_service.py`/
`test_thumbnail_service.py`/`test_youtube_service.py` (none in the original
task-card test-file list) needed rewriting onto injected
`FakeProvider`-backed routers; (2) a **full**-suite run -- not just those four
files -- surfaced a second gap the doc-first review had missed:
`tests/test_thumbnail_api.py` and `tests/test_youtube_export_api.py`
independently monkeypatched the now-removed `_generate_with_retry` in their
own API-level `client` fixtures, fixed by mocking the public
`generate_suggestions`/`generate_learning_pack` functions instead (the same
pattern `test_script_api.py`/`test_learning_api.py` already use). One new
`tests/test_ai_router.py` test closes a real coverage gap against the
"disabled fallback yields a clear local error" verification criterion
(`AI_MODE=local` failing without ever touching Gemini); one new shared
`tests/test_ai_providers.py` wire-payload test protects the BUG-011
regression (`responseJsonSchema` not `responseSchema`) once, for all 4
migrated consumers, replacing 4 near-duplicate per-service versions of the
same check. Full suite: **801/801 pass**, 0 flakes,
`ruff check app tests scripts`/`git diff --check` clean. See
`.viepilot/phases/13-local-first-ai-reliability/tasks/task-13.7.md` for the
full plan and evidence record.

### 13.8 Automated regression and packaging gate — ✅ DONE (2026-09-20)

Audited every logger call site across the whole AI gateway/durable-job layer
before writing any test: only `app/services/ai/router.py` (4 sites) and one
line in `ai_worker.py` log anything today, all already using only safe
fields (provider/model/purpose/prompt_hash/latency/tokens/attempt/exception
class name) -- never a raw prompt, response, or API key. New
`tests/test_ai_logging.py` (7 tests) locks this down with `caplog`-captured
assertions across success, retry, hybrid-fallback, circuit-breaker-open,
total-failure, and auth-error paths through a real `AIRouter` -- broader
than the one pre-existing per-provider check
(`test_ai_providers.py::test_ollama_provider_never_logs_prompt_body`), which
covered only one provider's own output, not the router's, and not a
retry/fallback sequence. Ran the full verification matrix for real: `ruff
check app tests scripts` clean; `node --check` clean on every
`frontend/static/js/*.js` file; `scripts/check_dependencies.py` all 6 checks
GREEN; full suite **808/808 pass**, 0 flakes -- no pre-existing browser flake
occurred this run, so no isolated/group rerun was needed. Built the real
`.exe` via `scripts/build_exe.ps1` (clean, 169 MB dist, matching Task 12.2's
own confirmed size -- the `torch`/`tensorflow`/etc. exclusion list still
effective) and confirmed via the `.spec` file that Ollama/model are not
bundled. **Actually launched the packaged exe twice**, not just built it:
from its own `dist/` directory with no `.env` present, on an isolated port
so the existing dev server on 8000 was never touched -- once with Ollama
running (`ollama_reachable: true`) and once with Ollama genuinely stopped.
A real timing lesson surfaced and is recorded honestly: stopping only the
Ollama server process wasn't enough, since its tray watchdog
(`ollama app.exe`) auto-relaunched it within seconds (matching a Docker-
Desktop-style resilience pattern) -- both the server and the watchdog had to
be killed, confirmed via a real failed `curl` to `127.0.0.1:11434`, before
`GET /api/ai/health` genuinely reported `ollama_reachable: false`. Both
launches returned `GET /health` 200 immediately and `GET /api/ai/health`
degraded safely (no crash, no key leak) rather than blocking startup,
confirming the "app must still start when either is absent" invariant
against the real packaged build, not just the dev server. Environment
restored afterward (real Ollama server restarted, test exe stopped, stray
local log/pid files deleted). See
`.viepilot/phases/13-local-first-ai-reliability/tasks/task-13.8.md` for the
full plan and evidence record.

### 13.9 Real no-mock bake-off and operational trial (Gate B) — ✅ DONE (2026-09-21), **Gate B: FAIL**

> **Diagnosis superseded (2026-09-21, PM/Tester review):** the FAIL decision stands, but the
> "not an infrastructure defect / behaves exactly as designed" conclusion below was falsified
> — see `docs/operations/phase13-acceptance.md` §Correction, `docs/brainstorm/session-2026-09-21.md`,
> and Phase 14 below. Task 13.10 is blocked, not "next".

New `scripts/run_ai_operational_trial.py` drives a real in-process `uvicorn` server
(isolated port, `AI_MODE=local`, fallback genuinely OFF) over real HTTP only -- no
`TestClient`, no mocked provider, matching the controlling plan's explicit "live
uvicorn HTTP, no TestClient/mock/pytest" requirement for this one gate. Smoke-tested
first (`--smoke-test`, one abbreviated run) before committing to the real multi-hour
trial -- this caught a real infrastructure regression before it could taint results:
an earlier ad hoc Ollama restart during Task 13.8's packaged-exe verification had
started `ollama.exe serve` without the persisted `OLLAMA_MODELS` user environment
variable, silently pointing the server at an empty model directory (`qwen3.5:9b`
reported "missing" even though never uninstalled). Fixed by restarting Ollama with
every persisted env var explicitly set, then reconfirmed via a real `/api/tags` call
that the digest matched Task 13.1's Gate A evidence exactly (`6488c96fa5fa...`) before
running the real trial.

The full trial ran 5 consecutive B1-eight-minute script jobs, 4 samples (B1 5-min, B1
10-min, A2 8-min, C1 8-min), and 1 learning generation, all real local Qwen generation.
**Result: 8 of 9 script-generation attempts failed the exact same validator** --
`script_pipeline.py::validate_section`'s ±15% section word-count tolerance -- with
misses in both directions (from -74% to +56% of the section's target word count) and
across every CEFR level and duration tested, not isolated to one configuration; the
single allowed repair pass did not correct any of the 8 failures. This is a genuine
local-model instruction-following limitation, not an infrastructure defect: every
failed job transitioned to a clean `error` status with a safe `error_code`
(`section_validation_failed`) within 3 minutes, zero hangs, zero partial/corrupt
script writes, zero unhandled 5xx responses -- proving the durable-job architecture
built across Tasks 13.2-13.6 behaves exactly as designed under real, repeated failure,
not just under passing conditions. The one script that did complete (785 words, within
the 720-880-word global range) passed every content check except one -- disclosed
honestly as a false negative in the *trial runner's own* narrow keyword heuristic
(`has_outro` looked for a fixed phrase list; the actual last line, "Good luck with your
journey to better health and longer life ahead.", is a genuine but differently-phrased
closing line), not a real content defect in the generated script itself. Since the
primary B1-eight-minute set never reached even 1 of the 4 required content-passing
completions, the real Edge TTS -> audio -> video pipeline was correctly never run (no
"winning configuration" existed to run it against) -- honestly recorded in the report
as not-executed, not fabricated or assumed.

**Gate B decision: FAIL.** Per the controlling plan's own decision rule (section 8),
local stays experimental and Gemini remains the primary/default path -- already the
packaged default (`AI_MODE=gemini`), unchanged by this outcome. No threshold was
weakened to reach this decision. Full root-cause analysis and a threshold-by-threshold
table are in the new `docs/operations/phase13-acceptance.md`; raw machine-readable
evidence is at `data/quality_reviews/phase13/gate-b/gate-b-20260921T000903Z.json`
(gitignored, not committed, per the same evidence-handling precedent as Gate A). Task
13.10 proceeds with the Gemini-primary/local-experimental rollout path this outcome
designates -- this is not a setback for Phase 13 overall: the durable-job
architecture, provider gateway, and cloud-fallback compatibility work (Tasks 13.2-13.8)
all passed their own gates independently of this local-model-quality question and
remain in production use regardless of which provider is primary. See
`.viepilot/phases/13-local-first-ai-reliability/tasks/task-13.9.md` for the full plan
and evidence record.

## Phase 14 Task Status

**Status:** In progress | **Started:** 2026-09-21 | **Scope:** corrective (Gate B post-mortem)
**Controlling plan:** `docs/implementation/phase-14-ai-gateway-resilience.md` |
**Design record:** `docs/brainstorm/session-2026-09-21.md` (D1–D8) | **ADR:** ADR-001 amendment A1

Opened after the PM/Tester's independent review of Gate B found two independent root causes the
Coder's report missed: (A) the ±15%-per-section hard stop compounds a measured 66.7% per-section
pass rate into 13.2% predicted / 11% observed job success while the product gate is ±10% on the
total; (B) Task 13.7 removed the transient-error backoff with the cascade — Gemini (the primary
provider) died 0/2 on ordinary HTTP 503 with zero backoff anywhere in the gateway; plus (C)
`repair_count`/`fallback_used`/`actual_provider`/`model` are never written to the job row. Governance
constraint recorded in the plan: **no tolerance value changes** (`SCRIPT_GLOBAL_WORD_TOLERANCE`
0.10, `SCRIPT_SECTION_WORD_TOLERANCE` 0.15 pinned by test). Task 13.10 blocked until 14.4.

### 14.0 Doc-first gate — ✅ DONE (2026-09-21, PM)

- [x] Controlling plan (543 lines: invariants 13–19, designs §4.1–4.4, explicit allowed files per
  task, declared Gate B-2 decision rules PASS / FAIL-CONTENT / FAIL-INFRA, stop conditions,
  two-session partition), SPEC, PHASE-STATE, task cards 14.1–14.6, ADR-001 amendment A1 (Decision 3
  capped infrastructure retry at one — amended explicitly, not silently violated). Commit `ed02eb5`.
- [x] PM re-verified the checkpoint statistics from the trial DB before writing (18 sections,
  mean 145.9, σ 19.5; all job-row telemetry columns empty).

### 14.1 Bounded exponential backoff for transient errors — ✅ DONE (2026-09-21, Coder; PM-accepted)

- [x] `AIRouter._attempt`: transient class (`ProviderUnavailableError`/`RateLimit`/`Timeout`) →
  up to `AI_TRANSIENT_MAX_ATTEMPTS = 4` attempts, sleeps 1 s → 2 s → 4 s (capped 4.0) via
  module-local `sleep`, each sleep gated by `remaining < delay + AI_BACKOFF_MIN_REMAINING_SECONDS`
  against a `deadline_at` computed once in `generate()`; content class keeps one immediate retry;
  auth never retried; hybrid shape and circuit-breaker accounting unchanged; no second model.
  `GenerationResult` gains `attempts`, `backoff_seconds`, `transient_errors` (class names only).
  Commits `2bd203c` (design), `2384578` (code), `990a6b7` (Amendment A tests).
- [x] **Amendment A** (PM, `378bf4d`): four pre-existing `*_wraps_provider_error*` tests in
  `test_learning_service.py`/`test_script_service.py`/`test_youtube_service.py` scripted two
  transient outcomes for the old policy and ran `FakeProvider` dry under four attempts. PM reproduced
  the 4 failures (12.8 s runtime = real 1 s + 2 s sleeps per test — incidental proof the backoff
  waits), then added the three files test-only; fix = four scripted outcomes + patched `router.sleep`.
- [x] **PM acceptance review (independent):** production diff limited to `router.py`,
  `contracts.py`, `constants.py` (all in the allowed list); 6 new router tests cover the six
  declared verifications (`[1.0, 2.0, 4.0]` delay sequence, exhaustion + `ai_router_exhausted`
  log, deadline stop at `[1.0]`, content-class no-sleep, auth no-retry, hybrid exhaustion → Gemini);
  Coder's revert-and-confirm-failure recorded in the task card; PM ran the 88 targeted tests in
  1.13 s (no real sleeps) and `ruff` clean. Coder-reported full suite **814 passed** (808 + 6 new);
  PM will re-run the full suite itself before 14.4b.

### 14.2 Job telemetry (repair/fallback/provider/attempts/error codes) — ✅ DONE (2026-09-21, Coder; PM-accepted)

- [x] `ai_job_service.record_generation_call` (one UPDATE, `COALESCE` so an error-outcome call
  never nulls a prior provider/model, bounded `metrics_json.calls` at 64, refuses terminal jobs)
  and `provider_error_code` (`provider_unavailable|timeout|rate_limited|auth|invalid_response`,
  base → `provider_error`). Both pipelines route every router call through a `_call_router`
  wrapper that calls the router with **no transaction open** and records telemetry in its own
  short `write_transaction` afterwards; `ProviderError` → `_fail_provider` with a specific code
  instead of the worker's blanket `handler_exception`. Section checkpoints carry
  `target_nominal/target_effective/words/deviation_pct/repaired/words_before_repair/
  errors_before_repair`. `AIJobOut.metrics` via `model_validator` (no route change). Commits
  `73e5e6b` (design), `cde8e79` (code). Coder-reported full suite 848.
- [x] **Amendment B / 14.2-b** (PM review finding, plan commit `c93d152`; fix `ba086d5`):
  `SchemaValidationError` is a `ProviderError` subclass but a *content* failure; the outline
  path's `except ProviderError` recorded it as `provider_error`, which the Gate B-2 rule would
  count as infrastructure. Now maps to `schema_validation_failed` (classified `content` in
  §4.4); one service test + one e2e test (unparseable outline → `schema_validation_failed`,
  never `provider_*`/`handler_exception`). Coder-reported full suite 850.
- [x] **PM acceptance review (independent):** diff limited to the allowed files; wrapper
  verified to never hold a transaction across inference; call record contains only safe fields;
  129 + 9 targeted tests pass, `ruff` clean. Accepted as documented: `fallback_reason` is not
  populated (router does not expose the local failure class; neither Gate B-2 matrix uses
  fallback) — candidate for a later task, not a Phase 14 gate.

### 14.3 Running section budget; hard gate only at global ±10% — ✅ DONE (2026-09-21, Coder; PM-accepted)

- [x] `validate_section` split into `validate_section_structure` + `validate_section_word_budget`;
  non-last sections target `clamp(nominal + carry, nominal × [0.65, 1.35])`, the last section
  targets the real remaining budget clamped to `nominal_last × [0.5, 1.5]`; after the one repair,
  a surviving structural error still fails (`section_validation_failed`), a surviving word-budget
  miss is accepted and its drift carried (`script_section_accepted_off_target`); `validate_global`
  ±10% unchanged as the only hard word-count gate; one final-section budget repair gated on the
  total word count specifically (`SCRIPT_PIPELINE_MAX_GLOBAL_BUDGET_REPAIRS = 1`); resume recomputes
  carry from checkpoint `target_effective` with a nominal fallback. Prompts untouched. Commits
  `a530be3` (design), `039bc8d` (code). Coder-reported full suite 865.
- [x] **Governance verified by the PM:** `SCRIPT_SECTION_WORD_TOLERANCE = 0.15` and
  `SCRIPT_GLOBAL_WORD_TOLERANCE = 0.10` byte-unchanged; constants-pin test present; Coder's
  revert-and-confirm-failure on both the pin (0.15→0.25) and the accept-and-carry behaviour recorded.
- [x] **PM acceptance review (independent):** diff limited to `script_pipeline.py`, `constants.py`,
  `test_script_pipeline.py`; the `n + 1` repair bound is asserted (`call_count == 4`,
  `repair_count <= num_sections + 1`); resume-equivalence pure-function test present; 121 targeted
  tests pass in 1.27 s, `ruff` clean. One harmless observation recorded (resume loop also adds the
  last section's delta to `carry`, which is unused after the last section). One 13.4 test changed
  fixture from a pure word-count miss to an unknown-speaker error, with justification — correct,
  since a pure word miss no longer reaches `section_validation_failed` by design.

### 14.4 Gate B second run, both providers — ✅ 14.4a DONE; 14.4b EXECUTED (2026-09-21, PM) — **local FAIL 3/5 (media duration/A-V fail), Gemini FAIL-INFRA 0/5**

- [x] 14.4a runner prep (`scripts/run_ai_operational_trial.py` only; commits `377f140`, `153aa16`):
  `classify_failure` (infra/content/other; `schema_validation_failed` = content), `call_stats`
  from `metrics.calls[]`, per-section checkpoint table read from the trial DB, §4.4 aggregates,
  `--matrix local|gemini`, `--with-samples/--with-media`, `--resume-evidence` (two-day split),
  `--reaggregate` (offline), `has_outro` fix verified against the real Phase 13 false negative
  (outline objective "concludes the show" now counts); evidence/trial-data moved to
  `data/quality_reviews/phase14/gate-b2/` so Phase 13 data is never overwritten.
- [x] **Amendment C** (PM, plan `92baabf`, before any Gate B-2 run): the declared Gemini rule
  "5/5 complete ∧ ≤1 infra death" was self-contradictory and would have mislabelled one transient
  death as FAIL-CONTENT. Clarified: PASS-cloud ⇔ infra ≤ 1 ∧ content_pass ≥ 4 ∧ completed + infra
  == 5; FAIL-INFRA ⇔ infra ≥ 2; else FAIL-CONTENT. Coder fixed `gemini_matrix_decision` (`153aa16`)
  and honestly noted the old evidence files do not exercise the fixed branch.
- [x] **PM acceptance review (independent):** re-ran `--reaggregate` on both Phase 13 files
  (local FAIL 0/5 content, Gemini DIAGNOSTIC_ONLY + 2 `handler_exception` flags — unchanged);
  exercised the fixed branch directly with 7 synthetic run sets (5 pass; 4 pass + 1 content-fail
  complete; 1 infra + 4 pass → PASS-cloud; 1 infra + 3 pass + 1 bad → FAIL-CONTENT; 2 infra →
  FAIL-INFRA; 1 content death + 4 pass → FAIL-CONTENT; 1 handler_exception → flagged) — all match
  Amendment C; `ruff` clean.
- [x] 14.4b executed by the PM on 2026-09-21 (user confirmed Coder idle; full suite 865/865 at
  HEAD `64bab3b`; Gemini preflight `200 → 503 → 200`). Report:
  `docs/operations/phase14-gate-b2.md`; evidence `data/quality_reviews/phase14/gate-b2/` (gitignored).
  - **Local: FAIL** by the unchanged Phase 13 rule — **3/5 complete** (817/780/722 words, all 3
    pass every content check), run 3 `section_validation_failed` (>5 consecutive lines,
    structural), run 4 `global_validation_failed` (1053/800 — the ±10% hard gate caught a final
    section that came back at 426 words for an effective 173, twice). 0 infra, 0
    `handler_exception`; one Ollama timeout absorbed by backoff. First measured telemetry: 21
    repairs, repair success 44% (8/18); per-section σ 55.7% (outliers), mean +4.0% vs nominal
    → the −9% undershoot question is closed on evidence (variance, not bias). Learning 2/3.
    Samples B1-5/10-min and C1 complete and inside ±10% of their own targets.
  - **Gemini: FAIL-INFRA** — **0/5**, 5 infra deaths (3 × 503 exhaustion after 4 attempts / 7 s
    backoff, 2 × 429). Two outlines survived on attempt 4; three section calls did not — the
    1+2+4 s window (≈ 20 s incl. response times) is shorter than the real 503 storms while ≈
    100 s of the 120 s deadline went unused. Post-run probe: **free tier, 20 requests/day/model**
    (`GenerateRequestsPerDayPerProjectPerModel-FreeTier`, `retryDelay 21s`); every attempt
    counts, so the matrix (~30 requests) exhausted the day's quota during run 3.
  - **Two runner defects found and fixed** (Coder 14.4a-c, `dec4913`; not pipeline defects): the
    media step called `/audio/generate` without first synthesizing lines via `/tts/preview`
    (latent since 13.9); `word_count_in_range` used 720–880 for every sample instead of each
    run's own ±10% range (samples are informational; re-aggregated: B1-10min and C1 now pass).
  - **Media step (second pass, `--media-only` on the 817-word run-1 script): the real pipeline
    ran end to end with zero server errors** — 59/59 lines through Edge TTS, mix 200 (361.88 s,
    −16.01 LUFS), ffmpeg render 200, MP3 7.24 MB / MP4 5.28 MB, h264/aac, hashed and ffprobed.
    **Media gate FAIL** on the declared thresholds: audio 361.9 s and video 364.4 s ∉ [432, 528]
    (817 words play at ≈ 135 wpm vs the planned `CEFR_WORDS_PER_MINUTE["B1"] = 100` — a
    product pace-calibration finding, not a Phase 14 change), and A/V diff 2.52 s > 1.0 s
    (renderer padding). First time these were measurable at all.
  - **Stop conditions fired (plan §8):** "Gate B-cloud returns FAIL-INFRA after 14.1" and "the
    Gemini account's live quota cannot accommodate the declared matrix even split across two
    days". Per the 14.6 table (FAIL / FAIL-INFRA): **Task 13.10 stays blocked.** PM stopped and
    reported; the next decisions (14.1-b backoff redesign incl. `retryDelay` and per-day-quota
    non-retry; Gemini billing tier) are the user's.

### 14.5 Correct the Phase 13 acceptance report — ✅ DONE (2026-09-21, PM)

- [x] Additive-only correction (61 lines added, 0 removed; script-verified every original line
  survives in order): dated §Correction after §Decision with findings A/B/C and consequences;
  `> Superseded` annotations on §Root cause and §Recommendation; threshold table untouched; the
  781-vs-785 word-count discrepancy between checkpoints and runner disclosed rather than hidden.

### Amendment D (2026-09-21) — owner drops Gemini; local-only release path

The owner decided after Gate B-2 (D9–D12, brainstorm §Addendum; ADR-001 A2; plan §12): Gemini is
switched off everywhere (config-first, code retained dormant, re-enable only via the new
`DIE_AI_ALLOW_CLOUD=true`); the packaged EXE requires Ollama + `qwen3.5:9b` and shows guidance
when absent; local is the primary path **by owner override of the Gate B promotion rule**
(recorded as an override, not a threshold change); 14.1-b (Gemini backoff redesign) dropped.
PM assessed the owner's alternatives on evidence: an API-key pool does not help (quota is
per Google project; multiple projects break the API terms; 503s killed 3/5 before quota ran
out); finer chunking already exists and burns the per-request quota faster; the UI costs no
quota; local text quality was never the failing factor.

### 14.7 Local-only mode, config-first — ✅ DONE (2026-09-21, Coder; PM-accepted)

- [x] `AI_MODE` default `local`; `set_ai_mode` rejects `gemini`/`hybrid` unless the new
  `DIE_AI_ALLOW_CLOUD=true` (only new switch); Settings mode selector + API-key form replaced by a
  read-only status line; `/api/ai/health` drops `gemini_fallback_configured`, adds `cloud_enabled`;
  Step 2/3 gate the generate button on live health with inline install/pull guidance;
  `check_dependencies.py` treats Ollama + `qwen3.5:9b` as required (verified live); README/CHANGELOG
  updated; FakeProvider tests prove thumbnail and YouTube run under `AI_MODE=local`. Commits
  `1661708` (design), `518dd0a` (code), `d623b29` (Amendment F fix-up). Coder-reported full suite
  **879 passed**.
- [x] **Amendments E/F** (PM): E added the thumbnail/YouTube test files omitted from the allowed
  list and settled the selector (read-only line) and health-field (drop + `cloud_enabled`) choices;
  F added `tests/test_ai_jobs_api.py` (one stale assertion) and `frontend/pages/step6_thumbnail.html`
  (stale "Pillow + Gemini text" badge) and required the missing YouTube local-mode test, which the
  Coder had not flagged.
- [x] **PM acceptance review (independent):** diff limited to the allowed list; a case-insensitive
  grep for "gemini" across `frontend/` returns 0 lines; 97 targeted tests pass; `ruff` clean.
  PM-side docs: `docs/api.md` regenerated (no route-doc change), `docs/operations/local-ai.md`
  rewritten for the local-only runtime contract, HANDOFF `tech_stack.thumbnail` corrected.
### 14.8 Local hardening: over-length sections + consecutive-lines rule — ✅ DONE (2026-09-21, Coder; PM-accepted)

- [x] Section prompt states the budget as a hard range computed in Python from
  `SCRIPT_SECTION_WORD_TOLERANCE` (14.8-b removed the 0.85/1.15 literals the first cut had put in
  the template — CR-02) and requires alternating speakers; repair prompt receives measured
  words + signed delta and, for over-length, instructs trimming specific lines (the Gate B-2 340→426
  rewrite finding); consecutive-lines errors name the offending speaker/line range. One
  **length-only** repair pass gated by the new `SCRIPT_PIPELINE_MAX_LENGTH_REPAIRS = 1`, triggered
  only when a section is still over `effective × 1.35` after the semantic repair (under-length keeps
  14.3's accept-and-carry). Checkpoint `metrics_json` gains `length_repaired`/
  `words_before_length_repair`. Commits `824cc67` (design), `ac61cf8` (code), `4542b58` (14.8-b).
- [x] **Governance verified by the PM:** `SCRIPT_SECTION_WORD_TOLERANCE = 0.15`,
  `SCRIPT_GLOBAL_WORD_TOLERANCE = 0.10`, `SCRIPT_MAX_CONSECUTIVE_LINES_PER_SPEAKER = 5` byte-unchanged;
  pin test extended to all three with revert-and-confirm-failure recorded.
- [x] **PM acceptance review (independent):** diff limited to the allowed files; trigger/bound read
  in code (`repair_count ≤ 2n + 1` asserted, hit exactly 5 in the e2e test); 52 pipeline tests pass;
  `ruff` clean; template contains no tolerance literal; a rendered-prompt test guards the range
  against constant drift. Coder-reported full suite 883 (before 14.8-b; 14.8-b adds 1 test).

### 14.9 Gate B-3, local only — ✅ EXECUTED (2026-09-22, PM) — **script gate PASS 5/5; overall FAIL on learning 4/5 + media**

- [x] Preflight at HEAD `71e1464` (code `4542b58`): full suite **884/884**, ruff clean, Ollama digest
  `6488c96fa5fa`, health `cloud_enabled: false`. Report `docs/operations/phase14-gate-b3.md`.
- [x] **Script gate PASS for the first time:** 5/5 complete (733/744/792/782/800 words), 5/5 pass all
  seven content checks, 148–169 s per job, 0 infra, 0 `handler_exception`, max attempts 1. Per-section
  σ 22.9% (Gate B-2 55.7%); within ±15% of nominal 52% (34.8%); the 14.8 length-only repair fired 3×
  and cut every over-length section (217→80, 291→161, 411→151).
- [x] Learning **4/5** (one `pack_validation_failed`: idiom not in transcript) → learning gate FAIL.
  Media ran end to end (43 lines TTS, MP3 301.5 s, MP4 304.0 s, h264/aac, −16 LUFS) but **FAIL as
  declared**: duration ∉ [432, 528] (≈ 146 wpm vs planned 100 — pace question still open with the
  owner) and A/V diff 2.48 s.
- [x] Real Ollama probes on the winning script: thumbnail suggestions OK (8.5 s, 3 schema-valid
  variants), YouTube package OK (7.3 s, 3 titles / 13 tags / description / chapters) — both former
  Gemini consumers work local-only.
- [x] Samples: B1-5min and A2 pass; B1-10min structural (consecutive lines); C1 8-gram ratio 1.05%.
- **Consequence (plan §12 14.9):** D11 stays an owner override, recorded as such; 13.10 resumes under
  D11 (14.6). Open owner decisions unchanged: pace calibration, A/V padding; new: learning 4/5 bar.
### 14.6 Resume Task 13.10, local-only (revised) — ✅ DONE (2026-09-22; Coder `4a7383e`/`1c89b6a`, PM-accepted; one README copy nit assigned)

- [x] Live rollback drill (real uvicorn on a throwaway `DIE_DATA_DIR`, free port, real Ollama stop/start
  with all six env vars, Playwright without route mocks): Ollama stopped → health `ollama_reachable: false`,
  non-AI project create/list work, Step 2/3 show the disabled button + install guidance with no "Gemini"
  text; Ollama started → digest `6488c96fa5fa` confirmed via health and `/api/tags`, a real script job and
  a real learning job complete with `actual_provider: ollama`, guidance gone on reload. No DB repair.
- [x] Packaged smoke build rebuilt with today's code (pyinstaller invoked directly; `build_exe.ps1` hit the
  machine's default execution policy — README gained a `-ExecutionPolicy Bypass` note): starts with Ollama
  stopped, `GET /` 200, health reflects Ollama down, non-AI create works, Step 2 shows guidance.
- [x] `.viepilot/ARCHITECTURE.md`, `AI-GUIDE.md`, `PROJECT-CONTEXT.md`: every AI-engine mention now says
  Ollama local by default, Gemini dormant (bounded to those mentions; unrelated pre-Phase-13 staleness
  recorded, not silently expanded). README/.env.example/check_dependencies/spec re-verified from 14.7.
- [x] PM: `docs/operations/local-ai.md` (14.7), `docs/api.md` regenerated, state files. Full suite 884.
- **Task 13.10 is therefore complete under owner decision D11** (plan §13 D16). Phase 13 closes with an
  explicit decision record: local is the primary and only runtime by owner decision; Gate B-3 script gate
  passed 5/5 under the unchanged rule; learning/media residuals are Phase 14 tasks 14.10/14.11 and are
  re-measured in Gate B-4.

### Amendment G (2026-09-22) — owner delegated the open decisions to the PM; D13–D16

PM measured before deciding (real Edge TTS on the Gate B-3 winning script, five speeds): 111 / 125 /
132 / 145 / 159 wpm incl. silences at speed 0.75 / 0.85 / 0.9 / 1.0 / 1.1 — the 1.0 point reproduces
the media run exactly; even the floor speed cannot reach 432 s with 730 words. Decisions: **D13** planned
pace = measured pace (per-level default speed + measured WPM table; B1 8-min target → 1,000 words;
prompts updated in sync; thresholds unchanged); **D14** A/V padding: investigate first, fix if
unintentional, else re-declare ≤ 3.0 s with the reason; **D15** learning repair-by-removal bounded by the
existing minimums, dropped items recorded; **D16** 13.10 closes under D11.

### 14.10 Pace calibration (D13/D14) — ✅ DONE (2026-09-22, Coder `0db62e9`/`ec26846`; PM-accepted)

- [x] `CEFR_WORDS_PER_MINUTE = {A1 111, A2 111, B1 125, B2 132, C1 145, C2 159}` paired with
  `CEFR_DEFAULT_TTS_SPEED = {0.75, 0.75, 0.85, 0.90, 1.00, 1.10}` (the PM's measured table); six
  `prompts/script/cefr_*.txt` "Pace" lines updated in sync; `compute_target_words("B1", 8) == 1000` and
  `plan_sections == [200]*5` asserted; pin test + revert-and-confirm-failure.
- [x] Speed default: no UI speed control exists; `SpeakerConfig.speed` is now `Optional` (UI sends `null`),
  `project_service._resolve_speaker_speeds` fills `None` from the level default once before both the
  `config_json` snapshot and the DB write; stored speeds are never overwritten (3 new service tests).
- [x] **D14 resolved by evidence:** root cause reproduced against the real ffmpeg command shape —
  `-shortest` flushes B-frame-buffered frames after the audio input ends (≈ 2.5 s at ~300 s, 0 at 10 s).
  Fix: `-t <measured audio_jobs.duration_seconds>` replaces `-shortest` (301.520000 == 301.520000 in the
  reproduction). `AV_DIFF_MAX_SECONDS` stays 1.0 — the threshold was right, the renderer was wrong.
- [x] Nine pipeline tests relied on the old B1 wpm via a 1-minute default test project; fixed at one point
  of control (test config default duration 1.0 → 0.8 min so the same 100-word target is reached) with the
  reasoning recorded. PM review: diff in the allowed files, 125 targeted tests pass, `ruff` clean;
  Coder-reported full suite 888.
### 14.11 Learning repair by removal (D15) — ✅ DONE (2026-09-22, Coder `3f99f08`/`394a794`; PM-accepted)

- [x] After the one repair, items still failing grounding/answer checks are dropped (structured per-item
  view over the same validators); the unchanged `validate_pack` re-runs on the reduced pack; publish only
  if counts/duplicates still pass, else `pack_validation_failed` with the drop summary; `dropped_items`
  recorded in `metrics_json`. Minimums 1/1/1/3 unchanged. 2 new e2e tests; revert-and-confirm-failure;
  44 learning tests pass; Coder-reported full suite 891.
- Noted for a cleanup task (not blocking): `_record_dropped_items` writes SQL from the pipeline because
  `ai_job_service.py` was outside the allowed files — belongs in `ai_job_service` as a metrics setter.

### 14.12 Gate B-4, local only — ✅ EXECUTED (2026-09-22, PM) — **FAIL 3/5; word count solved at 1,000 words; repetition is the new failure class; A/V fixed; media duration blocked by a runner defect**

- [x] Preflight at `394a794`: full suite 891/891, ruff clean, targets 1000 = 5×200; two orphaned
  `llama-server.exe` runners left by the 14.6 drill held 11.7 GB VRAM until the owner cleared them.
  Report `docs/operations/phase14-gate-b4.md`.
- [x] Script 3/5 (991/984/915, all content checks); both deaths `global_validation_failed` on the
  **repeated 8-gram ratio** (1.02%, 4.32%) — no word-count death; 0 infra; repair success 65%.
  Samples: B1-10min complete (1,245 words); A2/C1 also 8-gram; B1-5min hallucinated speaker id.
- [x] Learning 3/3. Media: **A/V diff 0.00 s (D14 confirmed)**, codecs pass, duration 376.8 s ✘ —
  the runner hard-codes speaker `speed: 1.0`, so 14.10's B1 default 0.85 never applied (≈ 438 s
  predicted at 0.85; not credited until measured).
- **D17** repetition repair (14.13), **D18** runner speed (14.4a-d), Gate B-5 (14.14); Phase 14 closes
  after B-5 regardless of verdict (plan §14).

### 14.4a-d Runner applies the level default speed — ✅ DONE (2026-09-22, Coder `9b8d0be`; PM-accepted)

- [x] `_speaker_payload()` no longer sends `speed`, so the API applies `CEFR_DEFAULT_TTS_SPEED` exactly
  as the UI does; evidence records `speaker_speeds` from the server's resolved project (B-5 shows
  0.85/0.75/1.00 for B1/A2/C1). `--reaggregate` on the B-4 file unchanged.

### 14.13 Repetition repair (D17) — ✅ DONE (2026-09-22, Coder `256ba01`/`a6169a6`; PM-accepted)

- [x] `find_repeated_8grams_by_section` attributes each repeated window to the section it starts in;
  when every remaining global hard error is the repeated-8-gram check, the single worst section is
  regenerated once through the repair prompt with the phrases named (`SCRIPT_PIPELINE_MAX_REPETITION_REPAIRS
  = 1`), its checkpoint overwritten by `section_index`, `validate_global` re-run; mixed failures never
  trigger it. Section prompt gains an "avoid these phrases" note capped by `SCRIPT_SECTION_AVOID_PHRASES_MAX
  = 8`. `SCRIPT_MAX_REPEATED_8GRAM_RATIO = 0.01` unchanged, pinned. Bound ≤ 2n+2 asserted. 11 new
  tests; revert-and-confirm-failure on pin and trigger; PM: 64 pipeline tests pass, ruff clean; full
  suite 902.

### 14.14 Gate B-5, local only — ✅ EXECUTED (2026-09-22, PM) — **script 5/5, samples 4/4, learning 5/5 PASS; media duration FAIL (413.3 s)**

- [x] Preflight at `a6169a6`: full suite 902/902, ruff clean, VRAM 1.2 GB, no orphaned runners.
  Report `docs/operations/phase14-gate-b5.md`.
- [x] Script **5/5 complete, 5/5 pass** at 1,000 words (933/969/981/1,002/1,046); samples **4/4**;
  learning **5/5**; 0 infra; σ 18.9%. The repetition repair fired 3× (run 5, B1-10min, C1) and every
  one of those jobs completed — the B-4 killer is neutralised.
- [x] Media at the level default 0.85 (now measured): A/V 0.00 s ✔, codecs ✔, **413.3 s ✘** — the
  winning script sat at −6.7% of target and its real pace was ≈ 135 wpm vs the single-script
  calibration of 125 (≈ +8%); runs 4/5 would have played ≈ 445–465 s but are not credited unmeasured.
- **Overall FAIL on media duration only; Phase 14 closes here per plan §14.** D11 stays an owner
  override, recorded as such.

### Phase 14 close-out — ✅ CLOSED 2026-09-22

Delivered: bounded backoff (14.1), job telemetry (14.2), running section budget (14.3), Gate B-2
(14.4), Phase 13 report correction (14.5), local-only release + Task 13.10 (14.6/14.7), local hardening
(14.8), Gate B-3 (14.9), measured pace calibration + A/V root-cause fix (14.10), learning repair by
removal (14.11), Gate B-4 (14.12), repetition repair (14.13), Gate B-5 (14.14). Phase 13 Gate B →
Gate B-5: B1 8-min completion 1/5 → 5/5 with every content check passing; samples 0/4 → 4/4; learning
1/1 → 5/5; infra failures 0; cloud dependency removed; media pipeline runs end to end with exact A/V.
Residual, for a future phase (not started): multi-script pace calibration and a declared media-gate
protocol change; deterministic consecutive-lines fix; `_record_dropped_items` layering cleanup.

## Phase 15 Task Status

**Status:** In progress | **Opened:** 2026-09-22 | **Scope:** structural-failure robustness for the local
script pipeline. Trigger: the owner's first real run after Phase 14 (A2 / small_talk / 10 min / 2 speakers)
died at section 3 with `unknown speaker_id(s): ['ff5f20e0-417b-8d9f-752e844d46f0']` — the model dropped
one group of the real UUID `ff5f20e0-4082-417b-8d9f-752e844d46f0` (Alex). Same class as the Gate B-4
B1-5min sample. Plan `docs/implementation/phase-15-local-robustness.md` (invariants 20–23: no invented
speaker, no server-invented content, thresholds unchanged).

### 15.1 Speaker aliases in the section contract + deterministic id resolution — ✅ DONE (2026-09-22, Coder `d1efe4f`/`ebd79e2`; PM-accepted)

- [x] New `SectionLineWire` (alias `speaker`) is what the model parses against; `resolve_section_lines`
  converts to the unchanged `SectionLineOut` (UUID) before any validation, so validators/checkpoints/
  `save_script` and old checkpoints are untouched. Resolution order: exact alias → normalized alias →
  unique display name → exact UUID → UUID-shaped near-miss with ratio ≥ `SCRIPT_SPEAKER_ID_MATCH_MIN_RATIO
  = 0.85` matching exactly one id → else unknown (repair → fail as before). Section/repair prompts list
  `S1`/`S2` aliases. `regenerate_line` untouched. 13 new tests incl. the literal owner-run case;
  revert-and-confirm-failure on the pin and on the safety net at 1.0. Coder-reported full suite 915.
- [x] **PM acceptance:** called `resolve_speaker` directly on the real trigger —
  `ff5f20e0-417b-8d9f-752e844d46f0 → Alex (uuid_near_miss, ratio 0.925)`; alias/name/UUID rules and the
  unknown fallbacks behave as specified; `script_service.py` diff empty; 90 targeted tests pass; ruff clean.

### 15.2 Deterministic consecutive-lines fix — ✅ DONE (2026-09-22, Coder `bf872da`/`3381c21`; PM-accepted)

- [x] `merge_consecutive_lines(lines, limit)` splits an over-limit same-speaker run into exactly `limit`
  contiguous groups (divmod distribution), joining text with a space; `language_notes` unioned (dedup,
  first-seen), `grammar_point` from the first line. Fires only when the sole post-repair structural error
  is the consecutive-lines one; a section with fewer than two distinct speakers is unfixable and still
  fails. Bounded by `SCRIPT_PIPELINE_MAX_STRUCTURAL_FIXES = 1`; checkpoint metrics gain
  `structural_fix/lines_before_fix/lines_after_fix`. `SCRIPT_MAX_CONSECUTIVE_LINES_PER_SPEAKER = 5`
  unchanged. 11 new tests; revert-and-confirm-failure on the constant's gating; Coder-reported 926.
  Reasoned deviation accepted: repair-budget constants are not in the threshold pin test (precedent
  14.8/14.13) — the pin is for quality thresholds.
- [x] **PM acceptance:** exercised the merge directly — 8 lines/52 words → 6 lines/52 words, text order
  identical, no re-attribution, structural check clean; ruff clean; 88 pipeline tests pass.

### 15.3 Runner per-gate evidence path; `set_job_metric` layering cleanup — ✅ DONE (2026-09-22, Coder `ccc160d`/`d2c0d20`; PM-accepted)

- [x] `ai_job_service.set_job_metric(db, job_id, key, value)` replaces `learning_pipeline._record_dropped_items`
  (behaviour unchanged; all 26 Task 14.11 tests pass unmodified; 6 new tests). Runner `--gate NAME` writes
  evidence and trial data under `data/quality_reviews/phase15/<name>/` (default path byte-identical via
  `--reaggregate` on the B-4 file). Coder-reported full suite 932; PM: 93 targeted tests, ruff clean.

### 15.4 Gate B-6, local only, incl. the owner's configuration — ✅ EXECUTED (2026-09-22, PM) — **0 structural failures; media PASS (first time); script 3/5 on repetition**

- [x] Preflight at `d2c0d20`: full suite 932/932, ruff clean, VRAM 1.8 GB, no orphaned runners; fresh trial
  DB under `phase15/gate-b6/`. Report `docs/operations/phase15-gate-b6.md`.
- [x] Script 3/5 (1,056/1,079/1,053, all content checks); both deaths `repeated 8-gram ratio` (1.00%,
  1.42%) after one repetition repair each; **no unknown-speaker or consecutive-lines death in 11 jobs**.
  Samples 4/4; learning 3/3; 0 infra.
- [x] **Owner's configuration (A2/small_talk/10 min/2 speakers) — the one that died in real use — completed
  2/2** (1,100 and 1,073 words vs 1,110 target), learning 2/2.
- [x] **Media PASS for the first time:** 487.3 s ∈ [432, 528], A/V 0.00 s, codecs — D13 confirmed end to end.
- Verdict: FAIL on the script gate only (repetition, variable run-to-run: B-5 5/5 vs B-6 3/5 on identical
  code). Phase 15's objective (structural robustness) achieved; **Phase 15 closes**. 15.5 optional/not needed
  for B1 media.

### Phase 15 close-out — ✅ CLOSED 2026-09-22

Delivered: speaker aliases + deterministic id resolution (15.1), consecutive-lines merge (15.2),
`set_job_metric` + runner `--gate` (15.3), Gate B-6 (15.4). Remaining single failure class: repetition
(options recorded in the report §7 for the owner: second bounded repetition repair; stronger avoid-list;
or accept 3–5/5 with in-app Retry).

## Phase 16 Task Status

Plan `docs/implementation/phase-16-stability-hardening.md`; state `.viepilot/phases/16-stability-hardening/PHASE-STATE.md`.
Opened 2026-09-23 via `/vp-audit` → `/vp-evolve` (BUG-022, ENH-008, ENH-009, BUG-023). Baseline 932/932, `ruff` clean.

| Task | Owner | Status |
|---|---|---|
| 16.1 Worker loop guard + `worker_alive` (BUG-022) | Coder | ✅ done (`56bb74b`) |
| 16.2 ffmpeg timeouts (ENH-008) | Coder | ✅ done (`95d8b29`+`4baa840`) |
| 16.3 Test-data leak + cleanup script + CHANGELOG Phase 15 (BUG-023) | Coder → PM | ✅ done (`22100d0`; PM cleanup 447 deleted) |
| 16.4 Repetition avoid list, evidence-driven (ENH-009 A) | Coder | ✅ done (`d6ecbb7`) |
| 16.5 Gate B-7 | PM | ✅ executed: FAIL on word count (2 jobs), repetition 0.00% in 9/9 completed |
| 16.6 Second repetition repair (conditional) | Coder | ⛔ not run (D20) |
| 16.7 Gate B-8 (conditional) | PM | ⛔ not run (D20) |

PM review log (one line per verdict: task, commit, APPROVED/CHANGES/ACCEPTED, suite count):

- 16.1 design `f925ea5` — **APPROVED** (PM, 2026-09-23) with two notes: (N1) the backoff constant must be read at call time / monkeypatchable so test (a) doesn't sleep 5 s; (N2) record in the card as a known residual: if the guarded error-transition itself fails for a transient reason (e.g. `database is locked`), the job stays `running` until its lease expires and is only reclaimed by `recover_abandoned_jobs` at the next `start()` — acceptable for this task (the loop survives and logs the job id), not in scope to fix.
- 16.1 impl `56bb74b` — **ACCEPTED** (PM, 2026-09-23). Diff matches the approved design + N1/N2. PM re-verification: targeted 19/19; **PM's own revert-and-confirm-failure** (loop guard removed → `test_loop_survives_a_transient_claim_error_and_processes_a_later_job` + `test_loop_logs_and_backs_off_on_an_unhandled_iteration_error` FAIL, restored → 12/12); full single-process suite **940 passed**; `ruff` clean. Nit N3 (non-blocking, folded into 16.2 by plan Amendment A): `test_health_reports_worker_alive_false_when_the_worker_task_is_dead` sets `_task=None` via monkeypatch, so the `client` teardown's `stop()` returns early and the real loop task is orphaned until the portal loop closes — restore the real task before the client exits.
- **16.3 evidence (PM, 2026-09-23):** a full **single-process** `pytest -q` leaks exactly **4 rows per run** into the real `data/app.db` — one each "Learning / Script / YouTube / Export API Test Episode" — reproduced twice today (Coder's run 00:44–00:51Z, PM's run 00:55–01:01Z; count 426 → 434). Split runs (non-browser, then `-k browser`) leak nothing. So the leak is order-dependent, one test per API file.
- 16.1 housekeeping + N3 fix `17cb199` — accepted (N3 test fix landed in the same commit as the 16.2 design; test-only and pre-specified by Amendment A, so this is accepted as a process note, not a violation).
- 16.2 design `17cb199` — **CHANGES** (PM, 2026-09-23): the draft unlinks the "partial" output at the final `video.mp4` path on timeout. Because `-y` already truncated the previous good video at start, the BUG-017 row (kept pointing at the prior video) would then point at a missing file. Plan **Amendment B**: render to a `*.rendering.mp4` temp sibling and `os.replace` it in on success; on timeout or failure remove only the temp file. Add a test that a prior `video.mp4` survives a timed-out re-render. The rest of the design (constants, shared helper, duration param, `from None`, real-subprocess sleep test, revert target) is approved as is.
- 16.2 impl `95d8b29` — **CHANGES (small, N4)** (PM, 2026-09-23). Diff matches Amendment B; targeted 20/20. PM's own revert check: `timeout=` dropped → 4 timeout/prior-video tests FAIL, restored → 20/20. One gap (N4): on Windows `os.replace` raises `PermissionError` if the final `video.mp4` is open elsewhere (e.g. the Video Studio preview is streaming it via `FileResponse`, which opens it without `FILE_SHARE_DELETE`). The temp file is then left behind and the user sees a generic "Video rendering failed: [WinError 5]". Required: wrap both `os.replace` calls in `except OSError` → unlink the temp → `VideoRenderError("… could not replace the previous video (is it open in a player?) — close it and retry")`, plus one test (patched `os.replace` raises `PermissionError`: error raised, temp removed, prior video bytes intact). Full suite on the final sha before acceptance.
- 16.2 final `4baa840` — **ACCEPTED** (PM, 2026-09-23). N4 lands as a shared `_publish_rendered_output` helper used by both passes. PM re-verification: PM revert check (helper reduced to a bare `os.replace` → `test_render_video_sync_raises_actionable_error_when_replace_fails` FAILS, restored → 21/21); full single-process suite **945 passed**; `ruff` clean. ENH-008 closed at close-out.
- 16.3 design `48e52b6` — **APPROVED with CHANGES** (PM, 2026-09-23; plan **Amendment C**). Root cause accepted: 21 of 24 copy-pasted browser `live_server_url` fixtures never isolate `DATA_DIR`, so the real lifespan opens the singleton on the real `data/app.db`, and `Database.connect()` reuses that stale connection for the next `TestClient`. Required: (1) one shared live-server helper in `tests/conftest.py` (isolate `DATA_DIR`, bounded join, **fail loudly** if the thread survives or the singleton is still connected, restore), with all 24 files migrated to it; (2) the guard also fails on stale-connection reuse (open connection's path ≠ current `settings.db_path`), not only on the literal real path. Cleanup script and CHANGELOG as designed. The investigation's own diagnostic runs leaked 8 more rows (4 names only), to be cleaned with the rest.
- 16.3 stop report (Coder, 2026-09-23): implementation complete; the final full run was 951 passed / **1 failed**: the new guard tripped on `test_ai_health_api.py::test_health_response_has_no_extra_undeclared_fields` (bare `TestClient(app)`, real DB since Task 13.6, GET-only so never visibly leaked). The Coder correctly stopped rather than widen scope. PM ruling: **Amendment D**, the file is added to 16.3's allowed files for that one test only. Evidence that the guard works on a real case.
- 16.3 code `22100d0` — **ACCEPTED** (PM, 2026-09-23). The shared `live_server` helper covers all 24 browser files; guard (a) real path + (b) stale reuse, both with committed tests; cleanup script uses exact names and the service-layer delete; CHANGELOG Phase 15 entry added. PM re-verification: PM revert check (isolation line removed from `live_server` → `test_dashboard_browser.py` 18 errors in 2.8 s, restored); full single-process suite **954 passed**; `ruff` clean; **real DB count 454 → 454** across both the revert run and the full run. Dry-run (PM, read-only): 447 matches (Learning 133 / YouTube 114 / Export 105 / Script 95); 7 real projects survive. Awaiting the owner's OK for `--apply` (D19). Residual N5 (non-blocking): the script's backup uses `shutil.copy2`, not the SQLite backup API; mitigated operationally, since the PM takes an extra `sqlite3 .backup()` copy before `--apply` and no dev server is running.
- 16.3 real-DB cleanup — **DONE** (PM, 2026-09-23, owner OK per D19). PM SQLite-API backup `app-pm-sqlite-backup-20260923T032200Z.db` + script backup `app-before-cleanup-20260923T032201Z.db`; 447 deleted; 7 real projects remain; integrity ok, FK check 0, no orphans; re-dry-run total 0. **Task 16.3 DONE; BUG-023 resolved.**
- 16.4 design `e5be873` — **APPROVED with one change** (PM, 2026-09-23). Evidence reconstruction verified against the gate's own verdicts (1.0000% / 1.4156%); the classification (2 generic framing templates, 0 content terms) and the rejection of `count >= 1` loosening are both accepted. Change N6: the new rules must **not quote the forbidden phrase verbatim** (e.g. "That's exactly right, I truly believe that..."). With a 9B local model, quoted examples in the prompt prime reuse. Describe the pattern abstractly instead (e.g. "a fixed agreement phrase followed by 'I believe'"). The card's "selection-logic unit tests" verification item is N/A (no code change); the prompt-contract tests carry it.
- 16.4 impl `d6ecbb7` — **ACCEPTED** (PM, 2026-09-23). Rules 4–6 in `section.txt` plus one `repair.txt` line, abstract with no quoted phrase (N6 met, with an "I truly believe" regression assertion); no code change. PM re-verification: PM revert check (rules 4–6 removed → `test_pipeline_section_prompt_always_includes_the_static_anti_repetition_rules` FAILS, restored); full single-process suite **956 passed**; `ruff` clean; real DB 7 → 7. Next: **16.5 Gate B-7** (PM, Coder idle).
- 16.5 Gate B-7 — **EXECUTED** (PM, 2026-09-23), report `docs/operations/phase16-gate-b7.md` (`ce6eff0`). Runner FAIL (3/5 content, 4/5 complete); plan criterion 5/5 FAIL. Repetition 0.00% in **9/9** completed scripts (B-6: 2 repetition-only deaths). The 2 failures are global word-count overshoots (1,124/1,000 mixed with rep 1.07%; 703/625). Learning 4/4 + owner 2/2, media PASS 491.1 s, 0 structural, no regression. 16.6 would not have saved either failure (repetition-only mechanism).

### Phase 16 close-out — ✅ CLOSED 2026-09-23

Delivered: worker loop guard + `worker_alive` (16.1); ffmpeg timeouts + temp-render/atomic replace, which fixes BUG-017's file-level gap (16.2); the test-DB leak root cause (24 copy-pasted live-server fixtures) replaced by one shared helper + a real-DB/stale-reuse guard, with the 447 leaked projects cleaned up after a backup (16.3); evidence-driven anti-repetition rules (16.4); Gate B-7 (16.5). Suite 932 → 956. Open follow-ups: **ENH-010** (global word-count repair) and the outro/rule-5 watch item.

## Phase 17 Task Status

Plan `docs/implementation/phase-17-global-length-repair.md`; state `.viepilot/phases/17-global-length-repair/PHASE-STATE.md`. Baseline 956/956.

| Task | Owner | Status |
|---|---|---|
| 17.1 Budget-aware global stage (ENH-010) | Coder | not started |
| 17.2 Final-section sign-off + `has_outro_last3` | Coder | not started |
| 17.3 Gate B-8 | PM | not started |

PM review log:

- 17.1 design `caab2e2` — **CHANGES** (PM, 2026-09-23; plan Amendment A). The single ordered two-slot loop is approved (clear, bounded, 2 extra calls max, reuses the existing caps). Required: (C1, **blocking**) the budget-error match uses `"total episode word count"`, which is the repair-message text; `validate_global` emits `"total word count …"` (script_pipeline.py:472), so the budget branch would never fire. Share one prefix constant, and drive the tests through the real `validate_global`. (C2) Choose the section by deviation from its **nominal** target, not the effective one (Amendment A.1); the 5-min test must use the real B-7 numbers and expect section 2. (C3) Evidence-based shrink method (Amendment A.2): 36/103 repaired sections ended more than 15% over and the only global shrink request failed, so the design must say how an over-budget fix actually shrinks. The length item in the repetition repair and the item 4 view are accepted.
- 17.1 design rev `b265221` — **APPROVED with C4** (PM, 2026-09-23; plan Amendment B). C1 (shared prefix constant) and C2 (nominal selection, real 5-min numbers → section 2) are accepted. C3's bare fresh regeneration is rejected on evidence: first-pass generation has a median of 0.60× target (15/118 within ±15%), so it would overshoot into "too short". C4: rerun the chosen section through the **full per-section path** (generation + in-loop length repair; median 1.02×, 65/118 within ±15%) via a behaviour-preserving helper extraction; worst case is 3 extra calls; `avoid_phrases` comes from the other sections. The "under" direction stays a plain repair.

## Phase 18 Task Status (queued behind Phase 17)

Plan `docs/implementation/phase-18-cloud-first-ai.md`; state `.viepilot/phases/18-cloud-first-ai/PHASE-STATE.md`.

| Task | Owner | Status |
|---|---|---|
| 18.1 `OpenAICompatProvider` | Coder | not started |
| 18.2 Router roles/modes/budgets; Gemini removed | Coder | not started |
| 18.3 Settings + health + privacy note | Coder | not started |
| 18.4 Fallback-rate readout + runner | Coder | not started |
| 18.5 Gate B-9 A/B | PM | not started |

PM review log:

- (none yet)

## Decision Log

| Date | Decision | Rationale |
|------|----------|-----------|
| 2026-09-23 | **Phase 18 planned** (`/vp-evolve ENH-011`) from D21–D24: generic OpenAI-compatible provider, router primary/fallback roles with **separate per-provider time budgets** and a circuit breaker, modes `local`/`cloud`/`cloud_first`, Gemini provider removed (comment sweep out of scope), Settings key/URL/model, fallback-rate readout, Gate B-9 A/B against B-8. Queued behind Phase 17 so B-8 records the local baseline; version → 1.1.0-beta at close | Smoke evidence: cloud quality far better, free tier flaky; both smoke jobs died on the shared router deadline, so separate budgets are a hard requirement |
| 2026-09-23 | **D21–D24 (owner, brainstorm `docs/brainstorm/session-2026-09-23.md`):** D21 cloud first with local qwen as automatic fallback, superseding D9/D11 as the default (the `DIE_AI_ALLOW_CLOUD` kill switch stays); D22 start on the free tier (Nemotron 3 Super), measure the fallback rate, consider paid later; D23 replace the dedicated Gemini provider with one generic OpenAI-compatible provider; D24 key/base URL/model in the Settings page (DB, write-only) with `.env` defaults. Planned as Phase 18 after Phase 17 closes | ENH-011 smoke test: cloud models hit word targets ~0.99× vs qwen's 0.60× first pass, but the free tier is unreliable, so a fallback is mandatory; the router already has hybrid + circuit breaker, needing role generalisation and separate per-provider time budgets |
| 2026-09-23 | **Phase 17 opened** (`/vp-evolve ENH-010`). PM **erratum** to the Gate B-7 report and ENH-010: a global budget repair already exists (Task 14.3 item 6, last section only). The real failure mechanics: run 1 = a length-inflating repetition repair with no re-check; 5-min = the last-section-only repair can't absorb a middle-section overshoot. Plan: targeted budget repair + length-aware repetition repair + mixed-failure path (17.1), final-section sign-off (17.2), Gate B-8 (17.3). Thresholds pinned; no server-side content deletion | Evidence from the B-7 checkpoints (read-only) contradicted the B-7 report's own §3.2; the plan targets the observed mechanism, not the reported one |
| 2026-09-23 | **D20 (owner): Phase 16 closed after Gate B-7.** ENH-009 resolved on evidence (repetition 0.00% in 9/9 completed scripts). 16.6/16.7 not run, since the second repetition-only repair would not have saved either B-7 failure. New ENH-010 (bounded global word-count repair, incl. the mixed case) plus an outro/rule-5 watch item logged for a future phase; interim is the in-app Retry | Gate B-7 moved the failure class from repetition to global length overshoot, which is a different mechanism; building 16.6 would chase the old class |
| 2026-09-23 | **Phase 16 opened** (`/vp-evolve`) for BUG-022, ENH-008, ENH-009, BUG-023. Owner decisions: **D18** ENH-009 → strengthen the section prompt's avoid list from Gate B-6 evidence first (16.4), measure with Gate B-7 (16.5), build a second bounded repetition repair (16.6) only if the script gate is still < 5/5; threshold stays 1%. **D19** BUG-023 → delete the 4 known leaked fixture names from the real `data/app.db`, backup first, dry-run shown to the owner first, PM runs `--apply`. Execution: two parallel sessions, PM Claude Opus + Coder Claude Sonnet, plan §6 partition with `SendMessage` as the live channel | `/vp-audit` 2026-09-23: 932/932 green, but a silently-dying worker loop, un-timed ffmpeg calls, a 3/5 repetition gate, and 419 leaked test projects stand between "works" and "stable" |
| 2026-09-22 | Gate B-6: 0 structural failures in 11 jobs, owner's configuration 2/2, media PASS (487 s, A/V 0.00); script 3/5 on repetition. **Phase 15 closed**; repetition options recorded for the owner, none started | The phase's objective is met on evidence; the residual is a variable content-quality class with a bounded repair already in place |
| 2026-09-22 | Phase 15 opened (delegated authority): section contract switches to speaker aliases (S1/S2) resolved server-side, with a ≥ 0.85-similarity safety net for echoed UUIDs; consecutive-lines runs merged deterministically (never re-attributed); thresholds unchanged | The owner's first real run lost 3 minutes to a copied-UUID slip the server can resolve without inventing anything; the two structural checks were the only ones without a repair path |
| 2026-09-22 | Gate B-5: script/samples/learning all PASS at 1,000 words; media duration 413.3 s FAIL (−4.3%). **Phase 14 closed** as declared in plan §14; D11 remains an owner override; multi-script pace calibration and a declared media-gate protocol change are proposed for a future phase | The phase must not chase gates indefinitely; every other gate passes under unchanged thresholds; the remaining miss is a single-script calibration spread, measured and documented |
| 2026-09-22 | Gate B-4: FAIL 3/5 — both deaths on the repeated-8-gram check at 1,000 words; A/V fixed (0.00 s); media duration blocked by the runner's hard-coded speed. D17 bounded repetition repair (threshold unchanged), D18 runner applies the level default speed, Gate B-5 then closes Phase 14 regardless of verdict | Word count is solved; repetition is the next measurable failure class and has no repair path today; the phase must not chase gates indefinitely |
| 2026-09-22 | Owner delegated the open decisions to the PM → D13 measured pace calibration (per-level default speed + measured WPM table, B1 8-min = 1,000 words), D14 A/V rule declared before investigation, D15 learning repair-by-removal bounded by existing minimums, D16 Task 13.10 complete under D11 and Phase 13 closed | Real Edge TTS measurement at five speeds; two gates each lost one learning pack to a single ungrounded item; thresholds unchanged throughout |
| 2026-09-22 | Gate B-3 (local-only): script gate PASS 5/5 for the first time; overall FAIL on learning 4/5 and media duration/A-V; D11 remains an owner override; 13.10 resumes under D11 | Unchanged Phase 13 thresholds applied to real evidence; the remaining failures are a learning grounding miss and two undecided product questions (pace, A/V padding), not the script pipeline |
| 2026-09-21 | **Owner: drop Gemini** — `AI_MODE=local` default, cloud fallback OFF, key UI hidden, code dormant behind `DIE_AI_ALLOW_CLOUD`; EXE requires Ollama; local primary by explicit owner override of the Gate B promotion rule (D9–D12, ADR-001 A2) | Gate B-2: Gemini 0/5 (503 storms + free-tier 20 requests/day exhausted by retries) vs local 3/5 with every completed script passing all content checks and zero infra failures; key pools violate the API terms and do not address 503s |
| 2026-09-21 | Gate B-2 verdicts recorded without threshold changes: local FAIL (3/5), Gemini FAIL-INFRA (0/5). Stop condition: Task 13.10 stays blocked; 14.1 reopened (14.1-b) | Declared rules applied to real evidence; the Gemini failure has two independent causes (503 window too short inside an under-used 120 s deadline; free-tier 20 requests/day exhausted by retries) — the second is an account decision, not code |
| 2026-09-21 | Task 13.10 rollout **blocked**; Phase 14 opened as a corrective phase (D1/D2) | Gate B post-mortem: Gemini (primary) 0/2 on transient 503 with no backoff anywhere in the gateway — shipping would regress 503 handling below the pre-Phase-13 baseline; the local failure is a compounding per-section gate, not only model precision |
| 2026-09-21 | ADR-001 amendment A1: transient errors retried against the same model up to 4 attempts with 1s→2s→4s backoff inside the single deadline; cascade ban, single fallback, no-preview rules unchanged (D3) | ADR Decision 3 literally capped infrastructure retry at one; amended explicitly rather than violated silently. Task 13.7 had removed backoff together with the cascade; only the cascade was intended |
| 2026-09-21 | Per-section ±15% becomes the repair trigger + drift signal; the only hard word-count gate is the global ±10% (D4). **Neither tolerance value changes** — both pinned by test | 66.7% per-section pass rate compounds to 13.2% predicted / 11% observed job success; the completed job passed the product gate at −2.4% while sections were individually off-target. Removing an internal stop that was stricter than the product requirement is not a relaxation |
| 2026-09-21 | Gate B-2 decision rules declared before any run: local = Phase 13 rule verbatim; Gemini = PASS-cloud / FAIL-CONTENT / FAIL-INFRA with infra and content failures reported separately (D6) | The original Gate B never tested the provider it recommended shipping; declaring rules first prevents post-hoc threshold movement |
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
| 2026-09-14 | Codex ran out of quota again mid-Task 2.1a; user handed coding back to PM (Claude Code)
  for the rest of this session. PM independently verified Codex's already-complete
  `scripts/generate_cefr_review_samples.py`/test file (task card had stayed at "not started"
  — same recurring pattern as Task 1.8b/2.3): 499/499 full suite, ruff clean, real 18-call
  campaign run — only 1/18 succeeded, 17 failed on real Gemini `503`/`429`. User then shared
  real Google AI Studio dashboard screenshots showing `gemini-3.8-flash`'s actual limit on
  this account is **5 RPM / 20 RPD** (not the unverified `15 RPM` the code assumed), and that
  `3.7`/`3.6` Flash sat completely unused (0/5, 0/20) — separate quota buckets per model
  version. User proposed a model-downgrade-on-quota-exceeded mechanism; PM implemented a
  `GEMINI_MODEL_FALLBACKS` chain (`3.8 → 3.7 → 3.6`, verified live via `models.list` that all
  three are real callable IDs first) across all 4 Gemini-calling services, plus 503 becoming
  retryable alongside 429 (closing the resilience gap flagged earlier this session), plus
  correcting `GEMINI_RATE_LIMIT_RPM` 15→5 (fixes Task 2.1a's CLI throttle 4.1s→12.1s).
  Live-verified end-to-end against the real API while 3.8 was still quota-exhausted: 3.8
  failed 429 x3, fell back to 3.7, which failed 503 x2 then succeeded on attempt 3 — a real
  generation that would have failed outright before this fix. 12 new/updated tests across
  the 4 services' test files, 86/86 passing, zero regressions. Also flagged 2 unrelated
  structural risks found via a fresh Tier-3-style audit, not yet fixed: `google-generativeai`
  is an unused dependency in `requirements.txt` (never imported, dead since the httpx-REST
  switch), and `requirements.txt` has zero pinned versions (`>=` everywhere) despite installed
  versions already running far ahead of the declared floors. | User; PM (Claude Code) |
| 2026-09-14 | User proposed tiering models by content difficulty (harder CEFR levels → a
  stronger/more-accurate model, easier levels → a lighter one). PM checked live via
  `models.list` before agreeing to anything: the only available "stronger" model is
  `gemini-3.1-pro-preview` (no GA/stable Pro tier exists on this account at all) — a real
  instability risk, the same class that forced the earlier `gemini-2.0-flash` migration.
  PM asked the user to clarify intent via AskUserQuestion before building anything; **user
  confirmed the actual goal is spreading quota load, not a quality upgrade for hard content**.
  Decision: extended `GEMINI_MODEL_FALLBACKS` with two more real GA models
  (`gemini-3.5-flash`, `gemini-3.5-flash-lite`, verified live, no `-preview` suffix) instead of
  building CEFR-based model routing — same mechanism as the same-day fallback-chain fix, just
  a longer chain (5 models now), no new architecture needed. Deliberately did NOT add
  `gemini-3.1-pro-preview` anywhere. 92/92 tests pass on the affected files after the change. | User; PM (Claude Code) |
| 2026-09-14 | User asked PM to handle the 2 flagged structural risks and run a deep
  bug-hunting audit. Risks: removed unused `google-generativeai` dependency (confirmed via
  whole-repo grep, zero imports anywhere), pinned every `requirements.txt` entry to its
  exact installed/tested version (was unbounded `>=` everywhere), and added `playwright`
  (was missing entirely despite 12 `test_*_browser.py` files depending on it directly —
  confirmed a fresh install would fail to collect those tests). Audit: dispatched a
  research agent with explicit context on what NOT to re-flag (already-reviewed patterns),
  then independently re-verified every one of its 5 findings against the real code (and,
  for the path-traversal one, with a live pathlib repro) before fixing anything — PM does
  not act on a subagent's claim without checking it first. 4 real bugs fixed: (1) HIGH —
  `audio_service.mix_project`'s `background_music_filename` had zero validation before
  being joined onto `music_library/`, letting an absolute path silently discard the base
  directory or a `../` sequence escape it entirely (confirmed live); fixed with the same
  guard `music.py` already uses. (2) MEDIUM — `youtube.py`'s export route ran synchronous
  `build_export_zip` (real disk reads + zip compression of a multi-MB video) directly on
  the event loop, same bug class as Task 2.2, missed because this route was added
  separately; wrapped in `asyncio.to_thread`. (3) MEDIUM — `delete_project` never cleaned
  up any of the 5 per-project data directories, an unbounded storage leak; new
  `cleanup_project_artifacts()`, called only after the DB transaction commits. (4) LOW —
  `tts_service.get_cached_audio_path` was the one file-resolver in the app skipping the
  containment/existence check its siblings use; brought in line. 16 new tests, full suite
  re-run green. See Known Issues for the one finding deliberately left open. | User; PM (Claude Code) |
| 2026-09-14 | User separately asked to add "3.1" specifically, believing it stable with no
  announced retirement. PM checked the live `ai.google.dev/gemini-api/docs/deprecations` page
  before adding anything (not just `models.list`, which carries no lifecycle metadata): the
  only real, non-preview "3.1" model for this use case, `gemini-3.1-flash-lite`, **does**
  already have an announced shutdown date (2027-05-07), and Google's own recommended
  replacement for it is `gemini-3.5-flash-lite` — already in the chain from the entry above.
  PM disclosed this plainly rather than silently complying or silently refusing. User chose to
  add it anyway ("tôi thích dùng 3.1 vì nó rất ổn định"). Added as the 6th and last entry in
  `GEMINI_MODEL_FALLBACKS` (an extra quota bucket, explicitly documented in the constants.py
  comment as a known-tradeoff addition, not a technical recommendation). 92/92 tests still
  pass, ruff clean. | User; PM (Claude Code) |
| 2026-09-14 | Task 2.4 (UI Redesign Slice 1) shipped: Dashboard → light high-contrast
  launcher, Step 2 → CapCut-style resizable Script workspace (new `shell.js`
  `WorkspaceShell`, inspector, 3-track timeline), shared tokens flipped light-by-default.
  New scope beyond the original Phase 2 ROADMAP plan, from an approved UI direction
  (`.viepilot/ui-direction/2026-09-14/`). Doc-first plan flagged 2 real brief
  contradictions before coding — PM resolved both explicitly rather than letting the
  Implementer guess (see task-2.4.md). All existing selectors/behavior retained
  (list/filter/search/delete on Dashboard; inline-edit/autosave/regenerate on Script); no
  app/API/schema/state-machine file touched. 49 new/updated Playwright tests; full suite
  515/516 pass (1 pre-existing tracked Gemini-retry flake, confirmed via isolated re-run,
  not a regression). `ruff`/`node --check` clean. Live-verified with real Playwright
  screenshots at 1440×900, both pages, both themes. | User; PM (Claude Code) |
| 2026-09-14 | At a `/vp-auto` control point, user decided Task 2.1's Quality Testing
  campaign (4 ROADMAP items) is reviewed by PM as an automated-proxy pass first, flagging
  anything that genuinely needs the user's own judgment, rather than the user reviewing
  every artifact personally. First item closed under this approach: CEFR accuracy
  testing. Re-ran Task 2.1a's CLI (`scripts/generate_cefr_review_samples.py`) for a clean
  run — 18/18 succeeded this time (prior run was 11/18 on real `httpx.RequestError`
  connection failures, not a code defect; the `GEMINI_MODEL_FALLBACKS` chain absorbed
  heavy 429 rate-limiting throughout). PM then read all 18 real generated scripts in
  full and recorded a traceable per-case verdict in `tasks/task-2.1b.md`: **14 PASS, 4
  BORDERLINE, 0 FLAG**. The 4 BORDERLINE cases (A2/B1/B2 × `news`) share one pattern —
  the `news` genre consistently pulls idiom/grammar sophistication about half a level
  higher than `small_talk`/`interview` at the same CEFR level, while A1/C1/C2 × `news`
  stay well-calibrated; no grammar errors, misused idioms, off-topic drift, or
  safety/factual issues found anywhere in the batch. Nothing required the user's own
  read this round; the news-genre calibration pattern is logged as an optional future
  prompt-tuning task, not acted on (this was a read-only review, no `prompts/script/`
  change). | User; PM (Claude Code) |
| 2026-09-14 | At a second `/vp-auto` control point, user confirmed PM should continue
  Task 2.1's remaining 3 Quality Testing items (multi-accent TTS, audio quality, video)
  using real technical measurement (LUFS, silence gaps, subtitle-timestamp sync) rather
  than subjective listening, which PM cannot do. Task 2.1c: 20/20 real Edge TTS
  syntheses across all 10 accents × 2 genders succeeded; no-music audio mixes measured
  -16.01 LUFS (0.01dB off the -16 target, well within tolerance); real video render
  confirmed exact subtitle-timestamp sync against `mix_project`'s own measured data. 3
  real findings surfaced and logged (not fixed, per this task's read-only scope — see
  Known Issues below): `scottish` accent duplicates `british`'s Edge TTS voice ids (a
  real upstream limitation — Microsoft's neural catalog has no dedicated Scottish voice,
  confirmed via the real `edge-tts --list-voices` output); background-music mixes drift
  to -17.12 LUFS, 1.12dB outside the ROADMAP-declared ±1dB tolerance, with the root
  cause identified (voice normalized before the music overlay, never re-normalized
  after); and no 9:16 video output exists anywhere in the codebase (a missing feature,
  not a QA gap — all 3 background templates and the rendered MP4 confirmed 1280×720
  only). This closes Task 2.1's full 4-item Quality Testing campaign at the
  automated-proxy-review level the user approved. See `tasks/task-2.1c.md` for the full
  measurement record. | User; PM (Claude Code) |
| 2026-09-14 | User asked PM to research and fix all 3 real findings from Task 2.1c
  strictly. Research: EBU R128 confirms loudness normalization must target the final
  complete mix, not an isolated stem (root cause of the LUFS drift); ffmpeg's blurred-
  background-pad is the real industry convention for 16:9→9:16 conversion; live-confirmed
  via the actual `edge-tts` package that no Scottish voice exists upstream. Fixed all 3:
  (1) `_mix_project_sync` normalizes the final mixed signal once, after the music overlay;
  (2) new `_render_vertical_sync` second ffmpeg pass + `aspect_ratio` field/column/
  download-format/Step 5 UI toggle, real `ffprobe`-confirmed 720×1280 output, default
  16:9 unchanged; (3) a `title` tooltip discloses the Scottish/British voice limitation.
  While verifying #2 against the real app, found and fixed 2 more real, blocking bugs
  (disclosed, needed to actually prove the feature worked): the `.hidden`-on-`.btn` CSS
  trap already flagged in Known Issues, and a real `init_db()` migration-replay crash on
  any second real app restart (fixed with a `schema_migrations` tracking table). 530/530
  full suite passes (up from 515), zero flakes. See `tasks/task-2.5.md`. | User; PM
  (Claude Code) |
| 2026-09-14 | User ran `/vp-audit` before starting Phase 3. PM found 6 real findings
  (self-review of Task 2.4/2.5's own code, not just a docs check): stale `ARCHITECTURE.md`
  API docs, `mp4_path_vertical` orphaning on a 16:9-only regenerate, `escapeHtml()` unsafe
  for attribute-value contexts (already-exploitable for `speaker.name`, pre-existing),
  `save_video_job`'s error path wiping previous successful paths to NULL (pre-existing),
  no `die-vp-p1-complete` tag (tag hygiene), and a single-statement assumption in
  `init_db()`'s new migration fallback (design note). User chose to fix the first 3 now
  (Task 2.6), leave the other 3 noted-only. All 3 fixes real-verified — the
  `escapeHtml()` fix specifically via revert-and-confirm-failure (a real quote-breakout
  payload broke a rendered attribute without the fix) before restoring it. 532/533 full
  suite passes (1 pre-existing tracked flake). See `tasks/task-2.6.md`. | User; PM
  (Claude Code) |
| 2026-09-15 | At a `/vp-auto` control point, PM presented the remaining open question from
  `HANDOFF.json` (declare Phase 2 done and move to Phase 3, or scope "progress
  cancellation"/LivePortrait lip-sync as real tasks first) via `AskUserQuestion` rather
  than picking silently — both remaining items are genuinely large architectural/research
  efforts, not quick fixes, so which one (if either) to prioritize next is a real product
  call. **User chose: close Phase 2, start Phase 3.** Re-ran the full suite clean before
  closing: **533/533 pass** (the previously-tracked Gemini-retry timing flake did not
  recur this run) — Phase 2 formally closed with zero known app-code regressions.
  "Progress cancellation" (Task 2.2) and real LivePortrait lip-sync (Task 1.7) remain
  logged as deferred future work, not blocking. Phase 3 (Review & Documentation) opened:
  `.viepilot/phases/03-review-documentation/` scaffolded, Task 3.1 (Documentation)
  doc-first plan written and delivered in the same session — `README.md` updated for
  Phase 2; new `docs/prompt-guide.md`, `docs/tts-setup.md`; new `docs/api.md`
  auto-generated via new `scripts/generate_api_docs.py` (49 routes, reads the real
  `app.openapi()` schema so it can't drift like `ARCHITECTURE.md` once did — see Task
  2.6a). Also fixed a real doc-sync gap found while closing out Phase 2: Task 2.6 had
  never been added to `CHANGELOG.md`'s `[Unreleased]` section despite being done and
  tagged — added retroactively. | User; PM (Claude Code) |
| 2026-09-15 | User chose to continue with Task 3.2 (Demo & Review) over Task 3.3 (Final
  Cleanup) at a `/vp-auto` control point. Delivered all 3 ROADMAP items with real,
  verifiable artifacts rather than placeholders: `scripts/generate_sample_episodes.py`
  produced 3 real sample episodes (A1/B1/C1, real Gemini scripts + real Edge TTS/ffmpeg
  audio); `scripts/record_demo_video.py` produced a real 223.9-second end-to-end
  pipeline recording (`ffprobe`-verified), catching and fixing 2 real bugs along the way
  (Step 1's speaker-name fields blocking submission when left empty; Step 4's wait
  timeout too tight for ~29 sequential real TTS calls); `docs/product-review.md`
  cross-checked its feature checklist against ROADMAP.md rather than restating from
  memory. This closes Task 3.2 — Phase 3 now stands at 7/11 discrete ROADMAP items done.
  | User; PM (Claude Code) |
| 2026-09-15 | User chose to continue with Task 3.3 (Final Cleanup) at a `/vp-auto`
  control point, closing Phase 3. Audited all 4 ROADMAP items before assuming any needed
  work: 2 already satisfied (zero `print()` in `app/`; `requirements.txt` already fully
  pinned), 2 real gaps fixed (`.env.example` was stale, advertising 5 dead `Settings`
  fields with zero real usages — `GOOGLE_TTS_API_KEY`/`AZURE_TTS_API_KEY`/
  `AZURE_TTS_REGION` from the pre-decision multi-engine TTS design, plus
  `OMNIVOICE_DEVICE`/`OMNIVOICE_MAX_CONCURRENT` — removed from both
  `app/core/config.py` and `.env.example`). Verification hit 2 abnormally slow full-suite
  runs (real system load — a Chrome Remote Desktop session active on this machine, same
  resource-contention pattern documented earlier this session); each hit the project's
  pre-existing, tracked Gemini-retry timing flake exactly once, confirmed non-regressive
  via isolated re-run. Git tag `v1.0.0-beta` applied after push. **This closes Task 3.3
  and Phase 3 in full (11/11 discrete ROADMAP items done) — all 3 planned phases now
  complete on Day 6 of a 21-day target.** | User; PM (Claude Code) |
| 2026-09-15 | User ran `/vp-audit` after Phase 3 closed, asking to find and fix real
  errors before continuing. Full 4-tier pass (Tier 4 skipped — this is not the ViePilot
  framework repo): Tier 1/2 found 3 real, pre-existing drift issues, all fixed. (1)
  `ROADMAP.md`'s Task 1.1 "Verify ffmpeg & OmniVoice" checklist item was still unchecked
  with stale "not yet" text describing a blocked state from 2026-09-11, even though
  TRACKER.md has recorded all 3 blockers resolved since 2026-09-12/13 and Task 1.1 closed
  — re-ran `scripts/check_dependencies.py` live to confirm all 6 checks are still GREEN
  before flipping the checkbox. (2) `CHANGELOG.md` had no version section for the new
  `v1.0.0-beta` tag — everything sat under `[Unreleased]` — and its `[0.1.0]` compare
  link pointed at a tag (`v0.1.0`) that was never actually created; renamed the section to
  `## [1.0.0-beta] - 2026-09-15`, added a fresh empty `[Unreleased]`, and repointed the
  `[0.1.0]` link at the real initial commit (`3fc1cb8`). (3) `HANDOFF.json`'s top-level
  `version` field was still `"0.1.0"`, not updated alongside the new tag — bumped to
  `"1.0.0-beta"`. Tier 3: `ruff check scripts/ app/` clean, `pip check` clean, no new
  code-quality findings — the codebase has already been through several deep audit passes
  this session (Task 2.6, the 2026-09-14 structural-risk audit). Verified the
  `.viepilot/architecture/*.mermaid` sidecar files still match `ARCHITECTURE.md`'s
  diagram matrix exactly (3 required, 3 optional/N/A with no stray files) and that
  `ARCHITECTURE.md` doesn't reference the Task 3.3 dead-settings cleanup (nothing to
  sync). | User; PM (Claude Code) |
| 2026-09-15 | User ran `/vp-brainstorm` to plan post-v1.0.0-beta work. PM reviewed known
  deferred items (progress cancellation, LivePortrait lip-sync, remaining UI redesign
  pages, CEFR calibration) and presented a risk/value table; user approved 2 low-risk,
  clear-value tasks as Phase 4 (CEFR `news` tuning, UI Redesign Slice 2 — 7 pages, split
  per-page), keeping progress cancellation and LivePortrait lip-sync deferred. See
  `docs/brainstorm/session-2026-09-15.md`. Scaffolded Phase 4 directly within the
  following `/vp-auto` invocation (same established pattern as opening Phase 3): added
  `## Phase 4` to `ROADMAP.md`, created
  `.viepilot/phases/04-post-beta-polish/PHASE-STATE.md`, wrote `tasks/task-4.1.md`
  doc-first before implementing. Delivered Task 4.1 (see Phase 4 Task Status above) with
  an honest partial-improvement result, not overclaimed. | User; PM (Claude Code) |
| 2026-09-15 | User said "tiếp tục" (continue) to start Task 4.2 (UI Redesign Slice 2).
  Delivered sub-task 4.2a (Learning, `/step3`) first, per the brainstorm session's
  suggested pipeline order. Wrapped in the same 3-panel shell as Script (Task 2.4), no
  timeline (Learning has no sequential-items concept). Inspector design was a real PM
  judgment call, disclosed: read-only detail view only, no per-item action buttons,
  since no backend endpoint exists to regenerate a single vocabulary/idiom/grammar/quiz
  item (only whole-pack regenerate) — building fake per-item actions would violate this
  project's own "no fake features" precedent. First browser test coverage this page has
  ever had (3 new tests). Found and fixed a real regression during verification:
  `test_step_nav_browser.py` assumed only Script used the shell layout, and
  `step3_learning.js`'s new `StepNav.render()` call was missing `variant: "workflow"` —
  fixed both at the root cause rather than only loosening the test. 536/536 full suite
  passes (up from 533). Remaining 6 pages (TTS, Video, Thumbnail, YouTube, Music
  Library, Step1-Config) not started. | User; PM (Claude Code) |
| 2026-09-15 | User ran `/vp-audit` after Task 4.2a, before starting the next page.
  Tier 1 (state consistency across TRACKER/ROADMAP/PHASE-STATE/HANDOFF/git tags for
  Phase 4) clean. Tier 2 found one real doc-drift gap: `README.md` had no mention of
  Phase 4 at all despite Tasks 4.1/4.2a already shipping — added a "Post-v1.0.0-beta
  Polish (Phase 4)" section matching the existing Phase 2/3 format. Tier 3 (re-reading
  Task 4.2a's own new code, not just re-trusting the prior session) found one real bug:
  `commitField()` in `step3_learning.js` never called `renderInspector()`, so editing
  the currently-selected item's field left the inspector showing stale text until
  re-selected — confirmed real via revert-and-confirm-failure (a new inspector
  assertion in the existing inline-edit test failed for the right reason before the
  fix, matching Task 2.6c's verification discipline). Compared against Script's
  equivalent `commit()` (Task 2.4) and confirmed it already calls `renderInspector()`
  on every path — this was a Learning-specific oversight, not a systemic pattern
  worth auditing elsewhere. Both findings fixed; 536/536 full suite passes. Tier 4
  skipped (not the ViePilot framework repo). | User; PM (Claude Code) |
| 2026-09-15 | User reported Codex's quota restored, asked PM to shift into pure PM
  role and delegate Task 4.2b (TTS Audio Studio) to Codex as Implementer, per the
  existing AR-06 PM-Implementer contract. PM wrote the doc-first task card
  (`tasks/task-4.2b.md`) and a ready-to-send Codex prompt; also fixed a real doc-drift
  bug found while preparing it — `docs/CODEX_CODE_PROMPT.md` hard-coded the Phase 1
  tasks path, which could misdirect Codex now that the project has 4 phases. Separately,
  scoped a new Task 4.3 (Vietnamese UI localization — full replace, no EN/VI toggle,
  technical terms like CEFR levels/genre/accent codes stay in English since they're API
  values) in the brainstorm session, explicitly sequenced to start only after Task 4.2's
  remaining pages are done (avoids touching the same files twice). See
  `docs/brainstorm/session-2026-09-15.md`. | User; PM (Claude Code) |
| 2026-09-16 | Codex delivered Task 4.2b. PM reviewed in 2 real rounds rather than
  trusting the report outright: round 1 approved Codex's presented plan and
  pre-authorized a narrow, already-anticipated `test_step_nav_browser.py` fix Codex
  correctly flagged instead of touching outside its scope; round 2 (after Codex's
  first delivery) PM's own independent screenshot — not the test suite — caught a real
  bug (`renderTimeline()` never cleared the Music timeline lane, accumulating duplicate
  clips on every re-render), sent back with the exact fix requested rather than
  patching it personally or accepting with a known defect. Codex's fix was independently
  re-verified (including a disposable 5-interaction stress-test script) before
  acceptance. 541/541 full suite passes. This is the first task fully delegated to
  Codex since Phase 4 opened, and the delegation contract worked as designed — Codex
  correctly escalated instead of guessing on both real issues it hit. | User; PM
  (Claude Code); Codex (Implementer) |
| 2026-09-16 | User asked to delegate Task 4.2c (Video Studio) to Codex, same as 4.2b.
  PM researched the real current-state gap first (Video never fetched the script's
  lines, unlike TTS) and wrote a doc-first task card explicitly citing both of 4.2a/
  4.2b's real regressions so they wouldn't recur a third time, plus pre-authorizing the
  now-well-understood `test_step_nav_browser.py` one-line fix in advance. Codex
  delivered: shell + real timeline built from a new `Api.getScript()` call site
  correlated to the audio job's real timestamps; honest "Synced" Voice-track labeling
  (not TTS's in-progress language, since audio already exists by this stage); a
  `/script`-fetch failure that degrades gracefully rather than blocking the core
  workflow (deliberately designed around the pre-existing `test_video_studio_
  browser.py`'s fake-project-ID real-404 risk, without needing to touch that
  out-of-scope file); and `renderTimeline()` proactively clearing all 3 lanes from the
  start, directly informed by 4.2b's post-mortem. Codex and PM also jointly decided to
  skip an optional "Play this segment" playback button, judging the seek/race
  complexity not worth it for a non-required feature. **Zero real defects found on PM
  review this round** — PM still independently re-verified everything (full diff read,
  re-ran the pre-existing `test_video_studio_browser.py` at 34/34, and a disposable
  6-interaction stress-test screenshot of the Music lane) before accepting. 544/544
  full suite passes. This is the second task fully delegated to Codex, and the
  accumulated task-card guidance from 4.2a/4.2b's regressions appears to be working —
  the delegation loop is improving with each round rather than repeating the same
  mistakes. | User; PM (Claude Code); Codex (Implementer) |
| 2026-09-16 | User had Codex run a read-only UI audit (`vp-auto` audit mode) across the
  whole app after Task 4.2c shipped. It found 2 P0 behavior bugs (Dashboard's Continue
  button no-ops for `audio_generated`/`video_generated`/`complete` statuses; Config page
  always creates a new project instead of editing the one named by an existing
  `project_id` in the URL) plus several P1/P2 polish items (timeline clip width not
  proportional to real duration, dashboard has no pagination and was observed rendering
  176 cards/358 buttons in one pass, some accessibility gaps, mixed EN/VI copy, an
  unused-feature disclosure on Video's avatar section). PM independently re-verified
  both P0 claims against the actual source (not accepted on the audit report's word
  alone) — both confirmed real and reachable via normal navigation, not edge cases. PM
  proposed and user approved inserting a new Task 4.4 ahead of Task 4.2d (Thumbnail) to
  fix the 2 P0 bugs immediately, on the reasoning that they affect navigation
  reliability across every already-shipped page and one of them (silent duplicate
  project creation) carries real data-integrity risk, outweighing the value of staying
  in page-redesign order. User again chose to delegate the fix to Codex, continuing the
  same AR-06 PM-Implementer pattern used for 4.2b/4.2c. P1/P2 items logged as backlog
  above (Task 4.2 section) rather than actioned now — not urgent, no confirmed user
  impact reported, and P2's mixed-language item is already covered by the planned
  Task 4.3. See `tasks/task-4.4.md`. | User; PM (Claude Code); Codex (read-only auditor,
  then Implementer) |
| 2026-09-16 | Codex delivered Task 4.4. PM independently re-verified rather than
  accepting the report on its word: read the full diff for all 4 touched files
  (confirmed the `STATUS_TO_STEP` map, the new `Api.updateProject()`, and — most
  importantly — that the Config load-error path never unhides the form, closing the
  exact bug this task exists to fix), reviewed the new test file
  (`test_step1_config_edit_browser.py` — a double-submit stress test asserting exactly
  1 `PUT`/0 `POST` plus exact hidden-TTS-field preservation, and a 4-status-parametrized
  test asserting 0 enabled controls in locked mode), re-ran every verification command
  independently (22/22 targeted, 25/25 regression, ruff/node/git-diff-check clean), and
  additionally ran its own disposable script + screenshot beyond what was asked —
  confirmed a disabled genre chip truly can't be activated via a forced DOM click (not
  just Playwright's own convenience check) and that the pre-existing "Cancel" link (a
  plain `<a>`, untouched by the lock logic) correctly stays functional. Full suite run
  independently: 558/558 passed, 263s, zero flakes — faster and cleaner than the
  Implementer's own 1375s run (which hit the known Gemini-retry flake 3 times, all
  confirmed passing in isolation), confirming that slow run was system load, not a code
  issue. **Zero real defects found.** This is the third task delegated to Codex overall
  and the first non-UI-redesign task in the AR-06 pattern — closes Task 4.4; Task 4.2
  resumes with sub-task 4.2d (Thumbnail) next. | User; PM (Claude Code); Codex
  (Implementer) |
| 2026-09-16 | User confirmed continuing to delegate to Codex for sub-task 4.2d
  (Thumbnail Generator). PM wrote the doc-first task card citing every prior
  sub-task's StepNav `variant:"workflow"` regression and flagging the one real
  difference from prior pages up front: Thumbnail already has a genuine write-path
  editor (headline+palette, debounced autosave, 409 conflict handling), so its
  inspector should host that real editor as-is rather than a new read-only view.
  Codex's pre-code plan correctly identified and cited the exact shared-shell
  constraints (inspector hidden below 1050px, resizer clamped to 260-480px, no
  inspector-collapse API) rather than guessing — PM independently verified both
  claims against `style.css`/`shell.js` before approving. PM also flagged one open
  risk without blocking approval: relocating the live preview into a 260-480px
  inspector is a real width reduction for a page whose whole purpose is visual
  judgment, and asked for a screenshot in the evidence to judge legibility rather
  than re-litigating the stage/inspector split. Codex delivered exactly per plan —
  diff review confirmed every required element id survived unrenamed, and confirmed
  the CSS custom-property renames Codex used were true pre-existing aliases in
  `style.css`, not a functional change. New `test_thumbnail_shell_browser.py` (2
  tests) directly proves the relocated editor's write path still works end-to-end
  (a combined headline+color edit within one debounce window fires exactly 1
  `PATCH`). PM's own screenshot verification in both themes confirmed the preview
  stays usable at the default and expanded inspector widths — resolving the tracked
  risk satisfactorily, no follow-up needed. PM additionally confirmed keyboard-driven
  resize works on this page's resizers (not just mouse drag), beyond what was asked.
  **Zero real defects found.** 560/560 full suite passes. This is the third task
  delegated to Codex end-to-end — closes Task 4.2d; Task 4.2 now at 4/7 pages done.
  | User; PM (Claude Code); Codex (Implementer) |
| 2026-09-16 | User confirmed continuing to delegate to Codex for sub-task 4.2e
  (YouTube Package, /step7) — the next natural step since it uses the same
  shell-without-timeline pattern, with Learning's and Thumbnail's precedent reducing
  regression risk. PM wrote the doc-first task card, flagging a real design question
  unique to this page: unlike every prior sub-task, there is no per-item selection
  concept at all (titles/description/chapters/tags are all fully shown at once, not
  click-to-select), so there's no natural "selected item" for an inspector. Decision:
  the inspector hosts the "Full Package Export" section instead — a real, already
  dynamic workflow-status panel (ready/not-ready + exactly what's missing, computed
  from real video/thumbnail readiness state) — rather than inventing a
  click-to-inspect interaction for the 3 title-variant cards, which would be a new
  feature outside this structural-only task's scope. Pre-authorized the same
  `test_step_nav_browser.py` one-line extension. Handed to Codex per AR-06; awaiting
  its pre-code plan. | User; PM (Claude Code) |
| 2026-09-16 | Codex delivered Task 4.2e. Plan review had already caught a real
  consequence of relocating "Full Package Export" into the always-visible inspector:
  its static "Checking export readiness…" text was previously invisible (nested
  inside `#content-wrap`, hidden until a package exists) and would become visible and
  misleading once permanently shown — PM confirmed this by reading `render()`'s
  early-return logic before approving Codex's proposed fix (an honest static default,
  zero new JS). Codex implemented exactly per plan and delivered 2 new tests directly
  exercising both export states and the text fix. PM independently re-verified rather
  than accepting the report on its word: read the full diff (confirmed every element
  id survived, no title-card selection state was added), re-ran every verification
  command (28/28 targeted+regression, ruff/node/git-diff-check clean), and
  additionally checked the real backend (`app/api/youtube.py:49-56`) to confirm "no
  package yet" genuinely returns `200`/`null` rather than `404` — validating that
  Codex's test mocks model the real API contract, not a convenient fiction PM's own
  first-draft verification script had wrongly assumed (a 404). Full suite run
  independently: 562 passed, 1 failed
  (`test_generate_script_retries_on_429_then_succeeds`, the known Gemini-retry timing
  flake, confirmed passing in isolation at 0.71s) in 1147.57s — a genuinely slow run
  (19 minutes vs. the ~250-450s baseline), consistent with the documented pattern that
  slow runs trigger this flake; Task 4.2e touched zero backend code. **Zero real
  defects found.** This is the fourth task delegated to Codex end-to-end — closes Task
  4.2e; Task 4.2 now at 5/7 pages done, with only Music Library and Step1-Config
  remaining (both deliberately NOT shell-based). | User; PM (Claude Code); Codex
  (Implementer) |
| 2026-09-16 | User asked PM to formally close out the last 2 items in Task 4.2's
  7-page split (Music Library, Step1-Config) rather than leave them open indefinitely
  now that all 5 shell-eligible pages were done. PM did not rubber-stamp the
  standing 2026-09-14 decision — re-verified it still held before closing: grepped
  `music_library.js` for any `pane-sidebar`/shell wiring (none found) and confirmed
  `step1_config.js`'s `StepNav.render()` call still passes no `variant` (defaults to
  `pills`, never `workflow`) — both consistent with "deliberately NOT shell-based."
  No code change needed or made. This formally closes Task 4.2 in full: 5/7 pages
  redesigned into the shell, 2/7 confirmed and closed as intentionally out of scope.
  Task 4.3 (Vietnamese UI localization) is now eligible to start per the explicit
  sequencing decision in `docs/brainstorm/session-2026-09-15.md` — not started yet,
  awaiting the user's decision on whether/when to begin it. | User; PM (Claude Code) |
| 2026-09-16 | User ran `/vp-auto` to proceed with the next Phase 4 work — Task 4.3
  (Vietnamese UI localization), the only remaining item. PM read the brainstorm
  session's locked decisions (full replace, no toggle, technical terms stay English,
  split per page) and did preliminary research: grepped all 9 pages' JS files for
  hardcoded UI strings (~39-201 candidate string literals per file depending on page
  size) and identified 3 shared cross-page components with their own hardcoded
  strings (`step_nav.js`'s 7 step labels + progress text, `shell.js`'s collapse
  button, `save_indicator.js`'s 4 status labels) that would need translating once,
  centrally, before any per-page work to avoid inconsistent terminology across pages.
  Before writing any task card, PM asked the user a real, consequential style
  question — how to handle common creator-vocabulary English loanwords (Video,
  Thumbnail, Podcast, Template) when translating, since this sets precedent for
  dozens of strings across all 9 pages and getting it wrong would mean redoing work.
  **User's answer: drop the localization plan entirely** rather than choose a style,
  and asked PM to switch to `/vp-brainstorm` instead. No task card was written, no
  code was touched — the question surfaced the user's actual preference (not wanting
  this feature at all) before any implementation cost was sunk, which is exactly what
  asking early is for. Task 4.3 marked DROPPED (not deferred) across
  ROADMAP.md/TRACKER.md/PHASE-STATE.md/HANDOFF.json; the mixed Vietnamese/English UI
  copy noted in the 2026-09-16 Codex UI audit's P2 backlog is now accepted as
  permanent, not a pending fix. **Phase 4 formally closed** at 3 pursued tasks
  (4.1/4.2/4.4), all done. | User; PM (Claude Code) |
| 2026-09-16 | User ran `/vp-brainstorm` to plan what's next after Phase 4 closed. PM
  reviewed known deferred items (progress cancellation, LivePortrait lip-sync) plus
  the 2026-09-16 UI audit's P1/P2 backlog — re-verifying each backlog finding against
  the *current* codebase rather than trusting the original audit text, which surfaced
  that 2 of 9 findings (Step 6's stale "Daily Intel English" brand text, header/nav
  styling inconsistency between shell and non-shell pages) were already fixed as side
  effects of Task 4.2d/4.2e's shell redesign work. PM presented a risk/value table;
  user chose to open a new Phase 5 addressing all 6 remaining real findings, split
  into 3 tasks by technical relatedness (5.1 Dashboard pagination, standalone,
  highest measured value; 5.2 timeline polish, bundles 2 findings that both touch the
  shared timeline component used by Script/TTS/Video; 5.3 a small bundled batch of 3
  low-effort items, mirroring Task 2.3's and Task 4.4's precedent of bundling related
  small items rather than creating one task per finding). PM scaffolded Phase 5
  directly (`.viepilot/phases/05-ui-polish-backlog/`, same pattern as opening Phase 3
  and Phase 4) and wrote the doc-first task card for Task 5.1, researching the real
  current `dashboard.js`/`dashboard.html` structure first (confirmed
  `Api.listProjects()`/`GET /api/projects` has no `limit`/`offset` support at all, and
  `render()` slices nothing — every filtered result renders every time) and locking
  in the key design decision: client-side pagination only, no backend change, since
  176 projects is a small fetch payload and the real problem is unbounded DOM
  rendering. Continuing to delegate to Codex as Implementer per AR-06, same pattern
  used throughout Phase 4. See `docs/brainstorm/session-2026-09-16.md` and
  `tasks/task-5.1.md`. | User; PM (Claude Code) |
| 2026-09-17 | Codex delivered Task 5.1. PM independently re-verified rather than
  accepting the report on its word: read the full diff and found the clamp logic lives
  centrally inside `render()` (recomputed on every call), which meant Codex needed
  zero changes to the delete handler to satisfy "clamp after delete" — a cleaner
  design than the explicit post-delete clamp PM's own task card anticipated, confirmed
  correct rather than assumed. Confirmed the pre-existing shared `MOCK_PROJECTS`
  fixture and its 6 existing consumers were left completely untouched, satisfying the
  plan-review requirement PM had explicitly raised. Re-ran every verification command
  (18/18 dashboard, 1/1 responsive, ruff/node/git-diff-check clean) and reviewed the
  verification screenshot, which surfaced an unrelated observation: the Dashboard's
  hero text is in Vietnamese — investigated via `git log -S` and confirmed it's been
  there since the project's very first commit (2026-09-10), untouched by this task,
  and is the concrete instance behind the "mixed EN/VI copy" P2 finding already
  accepted as permanent when Task 4.3 was dropped — not a new or in-scope defect.
  Full suite run independently hit 6 known Gemini-retry timing flakes (more than the
  usual 1, because this particular run was slower than baseline) — all 6 confirmed
  passing instantly together in isolation, non-regressive since Task 5.1 touched zero
  backend code. **Zero real defects found.** This closes Task 5.1; Phase 5 continues
  with Task 5.2 (timeline polish) next. | User; PM (Claude Code); Codex (Implementer) |
| 2026-09-17 | Codex delivered Task 5.2. PM independently re-verified rather than
  accepting the report on its word: read the full diff for all 5 touched files,
  confirming the width-clamp helpers correctly return `null` (no inline style set) for
  missing/non-finite/zero/negative durations in both TTS and Video, applied
  consistently to matching Script/Voice clips for the same line, and confirming via
  `git diff --exit-code` that `step2_script.js` was genuinely untouched. Confirmed the
  endorsed `Api.generateAudio()`-storage addition was implemented at both call sites
  exactly as agreed at plan review. Reviewed the new/extended tests and found them
  unusually rigorous for width-comparison coverage — real bounding-box measurements
  rather than style-attribute presence checks, one test cleverly reusing the existing
  `line-3` script fixture with a truncated timestamps override to realistically
  exercise the missing-timing-mid-list case, and a full 4-step keyboard round-trip
  test for the horizontal resizer. Re-ran every verification command independently
  (48/48 targeted+regression, ruff/node/git-diff-check clean) and reviewed the
  verification screenshot, confirming the measured 72px/112px width difference is
  visually obvious. Full suite run independently: 568 passed, 1 failed (the known
  Gemini-retry timing flake class), confirmed passing in isolation at 0.54s —
  non-regressive since Task 5.2 touched zero backend code. **Zero real defects
  found.** This closes Task 5.2; Phase 5 now at 2/3 tasks done, continuing with Task
  5.3 (small polish batch) next. | User; PM (Claude Code); Codex (Implementer) |
| 2026-09-17 | Codex delivered Task 5.3, the final Phase 5 task. Mid-implementation,
  Codex correctly stopped and reported per AR-06 rather than silently patching out of
  scope: a pre-existing test in `test_video_shell_browser.py` (from Task 4.2c, not in
  this task's locked file list) broke because it waited for `.avatar-preview` to
  become visible while now hidden inside the newly-collapsed `<details>` — PM
  independently confirmed the diagnosis (`.avatar-preview` genuinely lives inside
  `#avatar-grid`, inside the now-collapsed section) before authorizing a narrow
  one-line fix (open the details before the existing flow continues), no assertion
  changed. PM then independently re-verified the full delivery rather than accepting
  the report on its word: read the full diff for all 5 touched files, traced the
  `selectFirstActiveItem()`/`render()`/`switchTab()` refactor by hand through every
  case (different-tab switch, same-tab reactivation, empty section) and confirmed
  each behaves correctly, confirmed the `event.target === card` keydown guard
  correctly isolates the new handler from nested interactive children, and confirmed
  `style.css` was genuinely untouched. Reviewed the new/renamed tests and found them
  unusually rigorous — a real keyboard walkthrough tracing natural Tab order through
  the DOM, and an actual `event.defaultPrevented` capture proving Space's
  `preventDefault()` really fired rather than just inferring it from the visible
  outcome. Re-ran every verification command independently (20/20 targeted, 29/29
  regression, ruff/node/git-diff-check clean) and reviewed the verification
  screenshot. Full suite run independently: 571 passed, 0 failed, 324.96s — a fully
  clean run with zero flakes, faster than the Implementer's own 1217.99s run (which
  hit the known Gemini-retry flake twice, both confirmed passing in isolation).
  **Zero real defects found.** This closes Task 5.3 and Phase 5 in full — all 3 tasks
  done (5.1/5.2/5.3), all delegated to Codex per AR-06, zero real defects found on any
  of the 3 PM reviews. | User; PM (Claude Code); Codex (Implementer) |
| 2026-09-17 | User separately commissioned an independent deep-dive UI/architecture
  audit from Gemini (`C:\Users\Admin\Documents\audit_chuyensau_dailyintelenglish`),
  covering 8 findings beyond the original Codex audit's scope. PM read the full
  report and independently verified 4 of the most concrete claims against the actual
  source before presenting anything — 3 confirmed real (theme flash on 4 pages via
  hardcoded `data-theme="dark"` racing `theme.js`'s correct-but-late light default; a
  dead-end plain-text "Missing project" error on 6 pages with no link back to the
  Dashboard; TTS range sliders with zero accent-color styling), and 1 confirmed a
  **false positive**: the report claimed YouTube chapters always use a fixed-WPM
  estimate, but tracing `youtube_service.py::generate_package()` and
  `app/api/youtube.py` showed the real-measurement path (`real_chapters_from_
  timestamps()`) already exists and is already correctly wired up whenever a
  completed audio job exists — only a stale docstring comment inside the fallback
  function is out of date, not a functional gap. This is a concrete example of the
  project's "trust but verify" discipline catching a plausible-sounding but
  ultimately incorrect audit finding before any work was scoped around it. User chose
  to proceed with Phase 6, addressing the 3 verified real findings bundled into one
  task per the Task 2.3/4.4/5.3 precedent; the 4 remaining unverified findings (DB
  connection lock, unused rate-limiter constant, forward-only status machine, CSS
  fragmentation) were not scoped in, consistent with this project's standing
  preference to defer large architectural changes for a solo local-use app (same
  reasoning as Progress cancellation/LivePortrait). PM scaffolded Phase 6 directly
  (`.viepilot/phases/06-quick-wins-batch/`) and wrote the doc-first task card for
  Task 6.1, handed to Codex per AR-06. See `docs/brainstorm/session-2026-09-17.md`
  and `tasks/task-6.1.md`. | User; PM (Claude Code) |
| 2026-09-17 | Codex delivered Task 6.1, the only Phase 6 task. PM independently
  re-verified rather than accepting the report on its word: read the full diff for
  all 13 touched files, confirming each of the 4 theme-flash HTML files changed by
  exactly one line, byte-for-byte identical across all 4; all 6 JS files following
  an identical `showMissingProjectError()` pattern (a single-quoted, fully static
  string literal with no template interpolation, only the one "no project_id" call
  site replaced, every other `showError` call site confirmed untouched); the TTS
  slider CSS change limited to exactly the one `accent-color` line; and confirmed via
  `git diff --exit-code` that `app/`, `theme.js`, and `style.css` were genuinely
  untouched. Reviewed the new `test_quick_wins_browser.py` and found it correctly
  uses `page.request.get()` — a real HTTP fetch, not a browser navigation — to check
  the raw served HTML for the theme fix, avoiding the exact methodological trap both
  the plan and PM had flagged at review time; its negative-control test mocks a real
  500 error and asserts zero `<a>` tags in the resulting banner, empirically proving
  every other `showError` call site's safety rather than just asserting it. The
  extended TTS slider test uses a dynamic color-probe element to resolve
  `var(--accent)` at runtime instead of hardcoding an expected hex value that would
  break if the token ever changed. Re-ran every verification command independently
  (19/19 targeted, 47/47 regression, ruff/node/git-diff-check clean). Full suite run
  independently: 583 passed, 0 failed, 345.53s — a fully clean run with zero flakes
  at all. **Zero real defects found.** This closes Task 6.1 and Phase 6 in full,
  since it was the phase's only task. | User; PM (Claude Code); Codex (Implementer) |
| 2026-09-17 | User asked PM to run `/vp-audit` for a deep independent re-verification of the 4 Gemini audit findings left unverified after Phase 6 (DB single-connection lock, unused rate-limiter constant, forward-only status machine, CSS fragmentation). PM read the actual source for each rather than trusting the original report: (1) `GEMINI_RATE_LIMIT_RPM` is NOT unused — it's referenced by 2 standalone CLI sample-generation scripts (`scripts/generate_sample_episodes.py`, `scripts/generate_cefr_review_samples.py`) for proactive client-side throttling; the production FastAPI runtime instead relies on reactive retry/backoff on HTTP 429/503 (`GEMINI_MAX_RETRIES`/`GEMINI_RETRY_BASE_DELAY` in `script_service.py`) — a nuanced correction, not a clean false positive. (2) DB single-connection write lock CONFIRMED REAL: `Database` is a true singleton around one shared `aiosqlite.Connection`, no pool, no WAL mode — logged as ENH-004. (3) Forward-only status machine CONFIRMED REAL and worse than the original claim suggested: `POST /{id}/script/generate` and `/script/regenerate` have zero status guard at all, so a user can edit the script after audio/video are already generated with no downgrade or staleness warning — logged as BUG-013 (high priority, a real data-integrity gap, not just a missing feature). (4) CSS fragmentation CONFIRMED REAL with concrete new evidence beyond the original claim: 992 lines of per-page inline CSS vs 227 in the shared stylesheet, and 3 different disabled-button selector strategies with 2 different opacity values (0.55 vs 0.58) plus a `.btn-sm` padding mismatch on `step6_thumbnail.html` — logged as ENH-005. All 3 real findings auto-logged as request files per vp-audit's ENH-070 default behavior; none auto-fixed (per AR-06/routing guard, report-only — routes to `/vp-evolve` on user request). | User; PM (Claude Code) |
| 2026-09-17/18 | User chose to open Phase 7 to fix BUG-013 now (ENH-004/ENH-005 stay in the backlog). PM scaffolded Phase 7 and wrote the doc-first task card for Task 7.1, handed to Codex per AR-06. Codex's pre-code plan caught a real error in the task card (public route is `PUT /{project_id}`, not `PATCH`) and correctly identified a 3rd affected call site (`PUT /{project_id}/script`, manual script save) sharing the same bug — both approved by PM as in-scope corrections. Task 7.1 delivered 2026-09-18: new `project_service.mark_script_changed()` (no caller-supplied target status) downgrades a project's status back to `script_generated` whenever script is generated/regenerated/manually saved on a project already past that status, non-destructively (no files/records touched); `_validate_status_transition` and the public `PUT /{project_id}` endpoint's forward-only guarantee left fully intact. Mid-implementation, Codex's own full-suite run surfaced a real coupling with the pre-existing `tests/test_projects_write_lock.py` suite (calls the renamed helper by name) — resolved by preserving the legacy private helper's name/signature rather than touching the out-of-scope test, reported honestly. Zero real defects found on PM's independent review (full diff read, all commands re-run, a disk-and-DB test confirmed real audio/video files and job rows survive byte-for-byte unchanged). 596/598 full suite passes (2 known Gemini-retry flakes, confirmed non-regressive in isolation). **This closes Task 7.1 and Phase 7 in full.** | User; PM (Claude Code); Codex (Implementer) |
| 2026-09-18 | User asked PM to continue processing ENH-004/ENH-005 and to self-implement to save time — a one-time deviation from the AR-06 PM/Codex split, held to the same doc-first/verification/git-persistence standard. PM re-investigated ENH-004 before writing any plan: found `app/api/projects.py`'s existing `_write_lock` (a connection-wide `asyncio.Lock`, already documented in a code comment PM had not read closely enough the first time) already serializes every route because there's one shared connection — meaning `PRAGMA journal_mode=WAL` alone would be purely cosmetic, and a real fix needs a full connection-pool redesign, out of proportion to a quick win. Marked `wontfix` in ENH-004.md with full reasoning, no code changed. ENH-005 traced to a real root cause: the shared `.btn[disabled]` rule had no `aria-disabled` variant, so 3 pages each invented an inconsistent local fix. Extended the shared rule, removed the resulting redundant local overrides, kept only step6_thumbnail.html's genuinely non-redundant `button[disabled]` selector (verified needed for its bare `.template-option`/`.variant-card` buttons). Self-verified via a real revert-and-confirm-failure check on the new tests. 601/602 full suite passes (1 known Gemini-retry flake, confirmed non-regressive). **This closes Task 8.1 and Phase 8 in full.** All 4 Gemini-audit-derived findings left open after Phase 6 are now resolved. | User; PM (Claude Code) |
| 2026-09-18 | User asked PM to run a read-only `/vp-audit` pass (no source-code changes), noting Codex would scan the codebase in parallel. PM ran Tier 1 (state consistency), Tier 2 (docs drift), and a Tier 3 spot-check sweep. Tier 1: all 8 phases' PHASE-STATE.md status, ROADMAP.md status, and `die-vp-p{N}-complete` git tags cross-checked and consistent; found 1 real drift — 4 Phase 2 task cards (2.1b/2.1c/2.5/2.6) still show `Status: in_progress` despite each having its own PM Acceptance section confirming they were done (task-2.1a.md's distinct `code_complete_pending_real_run` status was checked and confirmed intentional, not drift) — logged BUG-014 (low). Tier 2: found README.md's Phase 4 section stale since early Phase 4 ("In Progress", 1/7 pages), with Phases 4(remainder)/5/6/7/8 entirely undocumented in README.md despite the project's own workflow requiring README updates on milestone complete — logged BUG-015 (low); and ARCHITECTURE.md's Project data model documents the status enum but not Task 7.1's new script-edit downgrade behavior — logged ENH-006 (low). Confirmed the 3 required architecture diagram sidecars (system-overview, data-flow, module-dependencies) all exist, and that ARCHITECTURE.md's Projects API section already correctly documents `PUT /api/projects/{id}` (not PATCH) — this doc could have caught PM's own Task 7.1 task-card error earlier had it been checked first. Tier 3 spot-check: no `TODO`/`FIXME`/`print()`/bare `except:` found in `app/`; spot-checked `lineCardHtml()` in step2_script.js confirms Gemini-generated text is consistently passed through `escapeHtml()` before `innerHTML` interpolation (matching the established CR-05 discipline from Phase 2's BUG-005/Task 2.6c work — not re-audited exhaustively); the 2 f-string-built SQL statements in `project_service.py` build only column names from a fixed, code-defined schema (never user input) with all values still parameterized, confirmed not an injection risk; `requirements.txt`'s 19 real dependency lines are all version-pinned. 3 new findings auto-logged as request files; none auto-fixed (report-only per the routing guard). No source code was touched by this audit. | User; PM (Claude Code) |
| 2026-09-18 | User shared Codex's own independent, parallel read-only `/vp-audit` results (10 findings, 0 critical/1 high/4 medium/5 low, no source changes, no auto-log). PM independently re-verified all 5 "important" findings by reading the actual source directly rather than trusting the report -- all 5 confirmed real, an excellent, false-positive-free scan. Re-scored 2: BUG-016 (voice settings not invalidating downstream status) confirmed real but found a genuine mitigating factor (Listen and Generate All both force fresh re-synthesis, so actual audio output is never wrong -- only the status signal is missing, same family as BUG-013); BUG-017 (failed regeneration wipes prior job data) re-scored from medium to high after tracing the exact UPSERT behavior and confirming it's unconditional real data loss, not just metadata drift. Logged all 5 as BUG-016 through BUG-019 and ENH-007. User chose to open Phase 9 to fix BUG-016 and BUG-017 now; the other 3 logged but out of scope. PM scaffolded Phase 9 and wrote the doc-first task card for Task 9.1, explicitly designing around the trap of naively reusing Task 7.1's `mark_script_changed()` for the speaker-settings case (its draft-advance branch would wrongly fire from a Step-1 voice edit). Handed to Codex per AR-06. | User; PM (Claude Code); Codex (parallel auditor) |
| 2026-09-18 | Task 9.1 delivered by Codex and accepted by PM per AR-06 with zero real defects found on independent review -- `mark_audio_job_failed`/`mark_video_job_failed` preserve prior job data on failure; download endpoints widened to keep a preserved success downloadable; a shared downstream-downgrade helper lets `mark_script_changed()` (Task 7.1, unchanged externally) and a new `mark_speaker_voice_changed()` cooperate without the naive-reuse trap. Real end-to-end tests verify actual MP3/MP4 byte identity before/after a forced failure. 613/615 full suite passes -- 1 known Gemini-retry flake plus 1 newly-observed, unrelated browser-timing flake in the music library waveform test (first occurrence this session, confirmed non-regressive in isolation, tracked honestly rather than folded into the known class). This closes Task 9.1 and Phase 9 in full -- BUG-016 and BUG-017 resolved. | User; PM (Claude Code); Codex (Implementer) |
| 2026-09-18 | User invoked `/vp-debug` asking to continue fixing bugs. All 6 remaining backlog items (BUG-014, BUG-015, BUG-018, BUG-019, ENH-006, ENH-007) were already fully diagnosed from the 2026-09-18 audits, so PM skipped a new debug-session investigation and went straight to scoping fixes. Opened Phase 10 with 2 tasks: 10.1 bundles the 2 remaining real code bugs (BUG-018: stale per-line audio cache after single-line regenerate; BUG-019: avatar filesystem mutation not rolled back if the DB transaction later fails -- PM designed a unique-filename + commit-then-cleanup fix before writing the task card, avoiding a new read-serving race). 10.2 bundles the 4 pure documentation findings (BUG-014, BUG-015, ENH-006, ENH-007) per the established small-fixes-bundling precedent. Both doc-first task cards written and handed to Codex per AR-06. | User; PM (Claude Code) |
| 2026-09-18 | Mid-Phase-10, user invoked `/vp-auto` with a standing policy change: PM self-implements directly from now on instead of delegating to Codex, to avoid errors from mixing 2 different models. PM self-implemented Task 10.1 (BUG-018/BUG-019 fixes, including a revert-and-confirm-failure check on the new avatar regression test) and Task 10.2 (4 documentation fixes, plus finding and fixing the same LivePortrait inaccuracy in the Module Dependencies diagram along the way). 617/619 full suite passes (2 known Gemini-retry flakes, confirmed non-regressive). This closes Task 10.1, Task 10.2, and Phase 10 in full -- every finding from both 2026-09-18 audits now resolved. | User; PM (Claude Code) |
| 2026-09-18 | User shared a third independent Codex `/vp-audit` pass, run after Phase 10 closed (7 findings: 0 critical/1 high/4 medium/2 low). PM independently re-verified all 7 -- all confirmed real. Opened Phase 11, self-implemented Task 11.1: fixed `delete_avatar()`'s BUG-019-class bug (a real miss in PM's own Task 10.1 scoping, incorrectly excluded at the time); narrowed `TTS_ENGINES` to only real engines, removing 3 that were accepted but never implemented; stopped `preview_line` from holding the app's shared DB lock across a live Edge TTS network call; fixed 4 test files' `no_real_sleep` fixtures to patch their own module's local `sleep` name instead of the shared `asyncio` module (a plausible root cause of this project's long-documented Gemini-retry flake class); synced the previously-missed `data-flow.mermaid` sidecar and corrected a new self-contradiction PM's own Task 10.2 had introduced about OmniVoice; updated stale `PROJECT-META.md` and README. Acknowledged (not fixed) that Phase 8's doc-first history lives in one commit, not git-provably sequenced -- adopted committing plan-then-implementation separately going forward. Both new regression tests independently confirmed meaningful via real revert-and-confirm-failure checks. Full suite independently: 620 passed, 1 failed (a newly-observed, unrelated Playwright flake, confirmed non-regressive in isolation) in 330.31s -- zero Gemini-retry flakes this run, the first fully clean run on that front in a long time, and notably the fastest recent full-suite run, a strong signal the sleep-patching fix addressed the flake class's actual root cause. This closes Task 11.1 and Phase 11 in full -- every finding from all 3 independent audits this session is now resolved. | User; PM (Claude Code); Codex (parallel auditor) |
| 2026-09-18 | User asked PM to run `/vp-audit` a 4th time as final confirmation after Phase 11 closed. Tier 1 (state consistency): all 11 phases' PHASE-STATE.md status, TRACKER.md, HANDOFF.json, and all 12 `die-vp-p{N}-complete`/`-t*` git tags cross-checked and fully consistent -- zero drift found. Tier 2 (docs drift): found 2 real, low-severity gaps -- (1) `README.md`'s "Post-Beta Bug Fixes & Polish" section header and phase table still said "Phases 5-10", entirely omitting Phase 11 (logged BUG-020); (2) `.viepilot/ARCHITECTURE.md`'s Diagram Applicability Matrix still had an `event-flows | optional | WebSocket streaming TTS` row that directly contradicted the corrected System Overview text 35 lines above it in the same file ("no WebSocket/SSE anywhere in the app") -- confirmed via direct grep that the codebase has zero WebSocket usage and that even the polling `/status` routes explicitly disclaim real SSE in their own docstrings; the ENH-007 fix that corrected the System Overview text never updated this row to match (logged BUG-021). Verified all 3 architecture diagram sidecars still byte-for-byte match their embedded Mermaid blocks (programmatic extraction + diff, zero drift). Tier 3 spot-check on Phase 11's touched files (`avatar_service.py`, `tts_service.py`, `tts.py`, `projects.py`, plus the 4 sleep-patched service files): no bare `except:`/`print()`, zero dead references to the removed `piper`/`google`/`azure` engines anywhere in `app/` or `frontend/`, all 4 sleep-patched files confirmed consistently using `from asyncio import sleep` with no leftover `asyncio.sleep(...)` calls. Both findings fixed immediately given their triviality (self-implemented, doc-only, no runtime behavior change) rather than opening a new phase -- proportionate to their size, unlike Phase 11's substantive code fixes. Full suite independently re-run one more time: **621/621 passed, zero failures, 294.35s** -- faster than Phase 11's already-clean run, zero Gemini-retry-class flakes, and neither of the two previously-observed one-off Playwright flakes (Task 9.1's waveform test, Task 11.1's dashboard-delete test) recurred either, further supporting that both were genuine one-off infrastructure flakes rather than real regressions. **This is the cleanest full-suite run recorded all session.** All findings from all 4 independent audit passes this session (Codex x3, PM x1) are now resolved. | User; PM (Claude Code) |
| 2026-09-18 | User asked directly (not audit-derived) why the app has no Settings UI for the Gemini API key, and to package the app "professionally". Scoped via `AskUserQuestion`: Settings page saving to the DB (over lighter alternatives), and a standalone `.exe` via PyInstaller (over a simple install script or Docker). Opened Phase 12, wrote and committed the doc-first plan for Task 12.1 before touching any implementation file. Self-implemented Task 12.1: new `app_settings` DB table, `settings_service.py` resolving a DB-stored key over `.env` at runtime (reverting cleanly to the original `.env` value on clear), new `/api/settings` router, new Settings page linked from the dashboard topbar. 19 new tests, independently confirmed meaningful via a real revert-and-confirm-failure check -- one of which caught a real test-isolation bug during development (an early draft accidentally reverted to, and printed, this machine's real `.env` Gemini key instead of the test's fake one; fixed by isolating `config.ENV_GEMINI_API_KEY` too, not a service defect). Full suite 640/640 passed, zero flakes. Manually driven end-to-end against the real running dev server with Playwright (not just unit-tested), then confirmed no test data was left in the real local database afterward. **This closes Task 12.1** -- Task 12.2 (packaging) planned next. | User; PM (Claude Code) |
| 2026-09-18 | Self-implemented Task 12.2: centralized 5 independent `Path(__file__)`-walking path constants into `app/core/paths.get_project_root()`, a frozen-aware `DATA_DIR` default, and a new `app/desktop_launcher.py` entrypoint. Two real problems found and fixed during the actual build+run: (1) the first PyInstaller build came out at 4.5GB from leftover OmniVoice-experimentation ML packages (torch/tensorflow/sklearn/librosa/transformers) with zero real usage anywhere in `app/` -- excluded, rebuilt to 169MB; (2) testing `DATA_DIR` from the project root picked up the real dev `.env`'s explicit `DIE_DATA_DIR=data` (correct precedence, unrealistic test) -- re-tested properly from the exe's own dist folder, confirmed it resolves to `%LOCALAPPDATA%` as intended. Actually built and ran the real `.exe` twice, driven end-to-end with Playwright (dashboard/`/step1`/`/settings` all working on a fresh install with no `.env`), confirmed a second launch reuses the running instance instead of crashing. Full suite 639/640 passed (1 confirmed one-off Playwright-class flake, non-regressive in isolation). **This closes Task 12.2 -- and Phase 12 (Settings & Packaging) in full.** | User; PM (Claude Code) |
| 2026-09-18/19 | Phase 13 opened (user-approved post-beta scope: replace the fragile long synchronous script/learning request path with durable local-first jobs). Task 13.0 (doc-first plan, ADR, baseline verifier, real SQLite Online Backup) done 2026-09-18. A session pursuing Task 13.1 (install/qualify Ollama+Qwen, Gate A) stopped abruptly on quota mid-task, after installing Ollama 0.34.2 and persisting its User-scope env config, but before pulling the model or running the real gate; a handoff checkpoint committed the WIP runner and a continuation prompt rather than losing the work. This session resumed per that checkpoint: reviewed the WIP `scripts/qualify_local_ai.py` line-by-line rather than trusting `ruff`/`--help` alone, and fixed two real gaps -- `ollama` CLI PATH resolution (a shell open before a fresh winget install never sees the updated `PATH`; added `resolve_ollama_binary()`) and evidence env vars read from a stale `os.environ` instead of the real persisted User-scope values (added a controlled, read-only PowerShell `resolved_env()`/`persisted_user_env()`). Pulled `qwen3.5:9b` for real (digest `6488c96fa5fa`, `Q4_K_M`, 6.6 GB, matching the plan's expected tag) and ran the real qualification: **Gate A PASS, all 9 checks true** -- 100% GPU offload at the plan's default 16K context, minimum free VRAM 4,370 MiB and minimum free RAM 17,504 MiB (both comfortably above the 1,536 MiB/4,096 MiB floors), ~48.2 tokens/sec steady state, 3/3 nested-schema probes valid, and correct detection of model-missing/server-down/early-stream-close/unload. No memory-headroom mitigation was needed. Wrote `docs/operations/local-ai.md` (install/config/lifecycle/troubleshooting/privacy/evidence). **This closes Task 13.1.** This PASS qualifies the model for Task 13.2+ integration only -- Gate B (Task 13.9) still decides local-primary versus Gemini-primary/local-experimental. A second interactive Claude Code session was found active on the same working directory mid-task and briefly wrote a duplicate Gate A summary into the task card before this session de-duplicated it; no competing commit had landed first. See `.viepilot/phases/13-local-first-ai-reliability/tasks/task-13.1.md` and `docs/operations/local-ai.md` for the full record. | User; PM (Claude Code) |

## Known Issues

- ~~BUG-013~~ **RESOLVED 2026-09-18** under Task 7.1 — see Phase 7 Task Status above and `.viepilot/requests/BUG-013.md`.
- ~~ENH-004~~ **WONTFIX 2026-09-18** under Task 8.1 — the single shared connection is already protected by an existing, well-reasoned connection-wide lock (`app/api/projects.py`'s `_write_lock`); WAL mode alone would be a no-op given that lock, and a real fix requires a connection-pool redesign this project defers per its standing precedent. See `.viepilot/requests/ENH-004.md`.
- ~~ENH-005~~ **RESOLVED 2026-09-18** under Task 8.1 (concrete drift only — the broader 992-line inline-CSS-volume observation was not fully audited, see the request file) — see Phase 8 Task Status above and `.viepilot/requests/ENH-005.md`.
- ~~BUG-014~~ **RESOLVED 2026-09-18** under Task 10.2 — see Phase 10 Task Status above and `.viepilot/requests/BUG-014.md`.
- ~~BUG-015~~ **RESOLVED 2026-09-18** under Task 10.2 — see Phase 10 Task Status above and `.viepilot/requests/BUG-015.md`.
- ~~ENH-006~~ **RESOLVED 2026-09-18** under Task 10.2 — see Phase 10 Task Status above and `.viepilot/requests/ENH-006.md`.
- ~~BUG-016~~ **RESOLVED 2026-09-18** under Task 9.1 — see Phase 9 Task Status above and `.viepilot/requests/BUG-016.md`.
- ~~BUG-017~~ **RESOLVED 2026-09-18** under Task 9.1 — see Phase 9 Task Status above and `.viepilot/requests/BUG-017.md`.
- ~~BUG-018~~ **RESOLVED 2026-09-18** under Task 10.1 — see Phase 10 Task Status above and `.viepilot/requests/BUG-018.md`.
- ~~BUG-019~~ **RESOLVED 2026-09-18** under Task 10.1 for upload/replace — **a real miss found by a third audit**: the same root cause also applied to `delete_avatar()`, incorrectly excluded from the original fix ("no new file involved" reasoning was wrong — the bug is about filesystem-mutation-before-commit-confirmation, which applies to a plain delete too). Fixed under Task 11.1. See `.viepilot/requests/BUG-019.md`.
- ~~ENH-007~~ **RESOLVED 2026-09-18** under Task 10.2 — **found still incomplete by a third audit**: the `data-flow.mermaid` sidecar was never checked/synced (only system-overview and module-dependencies were), and PM's own Task 10.2 edit introduced a new inaccuracy claiming OmniVoice was "built and verified working." Both fully fixed under Task 11.1. See `.viepilot/requests/ENH-007.md`.
- **Newly-observed flake (2026-09-18, first occurrence)**: `tests/test_music_library_waveform_browser.py::test_waveform_renders_real_pixels_for_a_real_audio_file` failed once during Task 9.1's independent full-suite verification, alongside the known Gemini-retry flake. Confirmed passing instantly in isolation; touches no file Task 9.1 modified (real-audio Web Audio API decode + canvas pixel read in a headless browser — a timing/resource-sensitive shape, similar in kind to the Gemini-retry class but a distinct cause). Not the known documented flake class — tracked separately here for honesty. Not investigated further; watch for recurrence before deciding whether it needs its own fix.
- **Task 11.1 (2026-09-18) fixes not previously logged as their own findings** (surfaced directly by a third Codex `/vp-audit` pass, no separate request files created since they were fixed same-day): (1) `avatar_service.delete_avatar()` had BUG-019's exact bug, see above; (2) `TTS_ENGINES` accepted `piper`/`google`/`azure` with zero synthesis implementation — narrowed to `["omnivoice", "edge_tts"]`, `/api/tts/engines` now honestly reports `omnivoice: available=false`; (3) `preview_line` held the app's shared write lock across a live Edge TTS network call — fixed to match the established "no lock across slow work" pattern; (4) 4 test files' `no_real_sleep` fixtures patched the shared `asyncio.sleep` globally instead of their own module's local binding — a plausible root cause of the long-documented Gemini-retry flake class below, now fixed; watch upcoming full-suite runs for whether that flake class recurs. All 4 independently verified fixed by PM, 2 with real revert-and-confirm-failure checks. See `.viepilot/phases/11-third-audit-fixes/tasks/task-11.1.md` for the full record.
- **Process note (2026-09-18, acknowledged, not retroactively fixed)**: Phase 8's entire doc-first plan + implementation live in a single commit (`f21bd60`), so git history alone can't prove the plan was recorded before the code (found by a third audit; the task card's own content genuinely was written first, but that isn't git-provable). Rewriting already-pushed shared history is out of scope for a documentation finding. Adopted going forward: self-implemented tasks commit a plan-only step before implementation when the design is knowable in advance, matching the existing pattern for Codex-delegated tasks (a `docs(review):`-style commit before `fix(...)`).
- **Newly-observed flake (2026-09-18, first occurrence)**: `tests/test_dashboard_browser.py::test_dashboard_delete_removes_card_after_confirm` failed once during Task 11.1's independent full-suite verification (a Playwright selector-wait timeout). Confirmed passing instantly in isolation; touches no file Task 11.1 modified. Notably, this run had **zero** occurrences of the long-documented Gemini-retry flake class (see Task 11.1 finding #4's sleep-patching fix) — the first fully clean run on that front in a long time, suggesting that class may finally be resolved, while occasional unrelated Playwright timing flakes (this one, plus the Task 9.1 waveform one) remain a separate, lower-frequency phenomenon of browser-test infrastructure under system load. Not investigated further; watch for recurrence.
- ~~BUG-020~~ **RESOLVED 2026-09-18** same-day, self-implemented — see the 4th `/vp-audit` pass Decision Log entry above and `.viepilot/requests/BUG-020.md`.
- ~~BUG-021~~ **RESOLVED 2026-09-18** same-day, self-implemented — see the 4th `/vp-audit` pass Decision Log entry above and `.viepilot/requests/BUG-021.md`.
- **4th audit full-suite confirmation (2026-09-18)**: 621/621 passed, 294.35s, zero flakes of any kind (neither the Gemini-retry class nor either of the two previously-observed one-off Playwright flakes recurred). The cleanest full-suite run recorded all session — strong further confirmation Task 11.1's sleep-patching fix resolved the Gemini-retry class for good, and that the two Playwright flakes were genuine one-offs, not new regressions.

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
  **2026-09-14 update:** 2 more full-suite runs while verifying the Gemini model-fallback fix
  (both unusually slow: 781.34s then 695.93s, vs the ~257s same-day baseline) each hit this
  same flake class, now also reaching the new fallback-chain tests (same
  monkeypatched-`asyncio.sleep`-and-assert-exact-sequence shape as the pre-existing ones): run
  1 failed `test_script_service.py::test_generate_script_exhausts_one_model_then_falls_back_to_next`
  only; run 2 failed 3 *different* tests
  (`test_script_service.py::test_generate_script_retries_on_429_then_succeeds`,
  `test_script_service.py::test_generate_script_backoff_sequence_is_1s_2s_4s`,
  `test_youtube_service.py::test_generate_package_retries_on_503_then_succeeds`) — a different
  set each run is itself evidence this is the same nondeterministic timing class, not a fixed
  logic bug in the new fallback code. A targeted bisected run of the 6 files that precede
  `test_script_service.py` in collection order plus `test_script_service.py` itself passed
  clean (72/72) at normal speed, and all 3 of run 2's failing tests passed instantly in
  isolation immediately after — consistent with the existing pattern, not a new root cause.
  Root cause still not fixed (this was flagged `wontfix` in 2026-09-13, a real fix would mean
  no longer sharing one global patched `asyncio.sleep` across the whole test process) — noting
  here only because it now reaches more tests than before, purely because there are more
  Gemini-retry-shaped tests to be caught by it after today's fallback-chain work.
  **2026-09-14, third occurrence, different root cause identified:** a third full-suite run
  (after the security/correctness audit fixes) took 884.83s — the slowest yet — and failed 8
  tests: 3 of the known Gemini-retry-pattern class, plus for the first time 5 real Playwright
  browser tests (`test_music_library_browser.py`, `test_music_library_waveform_browser.py`
  x2, `test_responsive_layout_browser.py` x2). Investigated *why* the machine was unusually
  slow this time instead of just re-running blind: `tasklist` showed 17 `chrome.exe`
  processes and the UI-preview dev server (`uvicorn`, port 8000) still running from earlier
  in this same session — real accumulated resource contention, not just the existing
  sleep-mock-leak theory. Stopped the dev server (confirmed via `netstat` it was mine before
  killing it). Deliberately did NOT kill the 17 Chrome processes — could not confirm via
  `tasklist`/`wmic` (PowerShell was also temporarily unavailable) whether all of them were
  orphaned Playwright test browsers or included a real user window, and killing a real
  browser window without that certainty was judged not worth the risk; left for the user to
  clean up if desired. All 8 failing tests passed instantly/cleanly when re-run in isolation
  immediately after (3 Gemini tests instant, all 5 browser tests in 31s total) — consistent
  with resource contention, not a regression from the same session's bug fixes.
  **2026-09-15, Task 3.3 verification:** 2 more full-suite runs (1285.10s and 1054.27s —
  both far above the ~250-450s baseline) each hit exactly
  `test_generate_script_backoff_sequence_is_1s_2s_4s` once. Checked for the same resource-
  contention cause before re-running blind: `tasklist /V` found 15 `chrome.exe` processes,
  but one of them was a real, active Chrome Remote Desktop window (the user's own remote
  session into this machine) — deliberately did NOT kill any of them (same reasoning as
  the entry above: cannot safely tell orphaned Playwright browsers apart from a real user
  session, and this time a real one is confirmed present). Confirmed via isolated re-run:
  passed instantly (0.56s) both times. The change under test (Task 3.3's removal of 5
  dead `Settings` fields from `app/core/config.py`) has zero code-path relationship to
  `script_service.py`'s retry timing — consistent with resource contention, not a
  regression.

- **Known, deliberately deferred race (found 2026-09-14 by PM audit, not fixed):**
  `app/api/audio.py`, `video.py`, and `youtube.py`'s `/generate`/export routes each snapshot
  the project in a `_read_transaction`, do slow unlocked work (mix/render/zip), then
  re-acquire `_write_transaction` to insert/update a job row keyed on `project_id` — without
  re-checking the project still exists. If `DELETE /api/projects/{id}` completes in that
  window, the subsequent `INSERT` violates the `ON DELETE CASCADE` foreign key (`PRAGMA
  foreign_keys = ON`), raising an unhandled `sqlite3.IntegrityError` that surfaces as a raw
  500 instead of a clean 404, and leaves whatever files were already rendered as further
  orphans (on top of the orphan class already fixed today for the delete-then-nothing-
  running case). Real, but requires this app's single local user to run two conflicting
  actions on the *same* project from separate sessions/tabs simultaneously — a narrow
  trigger, not a remotely-exploitable or data-corrupting one (the FK constraint itself
  still holds; nothing inconsistent is ever persisted). A clean fix means catching
  `sqlite3.IntegrityError` around the final write in 3 files (audio/video/youtube), 2 write
  blocks each (the error branch and the success branch) — deliberately not rushed into this
  session's fix batch; pick up as its own small task later if it's ever hit in practice.

- ~~Background-music mix loudness drifts outside the ±1dB tolerance~~ **RESOLVED
  2026-09-14 (Task 2.5a):** found 2026-09-14 via Task 2.1c's real audio-quality
  measurement — `audio_service._mix_project_sync` normalized the voice track *before*
  overlaying ducked background music and never re-normalized the combined signal,
  measuring -17.12 LUFS with music vs the -16 target (1.12dB outside ROADMAP.md's
  declared ±1dB tolerance). Fixed by moving the single `_normalize_to_target` call to
  run on the *final* mixed signal (voice + music) instead of the voice stem alone — per
  EBU R128 guidance that loudness normalization must target the complete final mix.
  `test_mix_project_with_background_music_caps_at_ducking_ceiling` tightened to assert
  the real `±1dB` bound (was a loose `< target+3` check that would have missed this).
- ~~No 9:16 (vertical) video output exists~~ **RESOLVED 2026-09-14 (Task 2.5b):** found
  2026-09-14 via Task 2.1c — `video_service.py` had zero resolution/aspect-ratio
  handling anywhere, all 3 background templates and every render were 1280×720 (16:9)
  only. Fixed with a real second ffmpeg pass (`_render_vertical_sync`, blurred-
  background-pad technique — the real industry convention for 16:9→9:16 conversion),
  wired through a new `aspect_ratio` request field (default `"16:9"`, byte-for-byte
  unchanged), a new `video_jobs.mp4_path_vertical` column (migration 005), a new
  download format, and a Step 5 UI toggle. Real `ffprobe` confirms the output is
  genuinely 720×1280 (reusing the existing-but-previously-unwired `VIDEO_WIDTH_SHORTS`/
  `VIDEO_HEIGHT_SHORTS` constants). See `tasks/task-2.5.md`.
- ~~`.hidden` silently ignored on `.btn`-classed elements~~ **RESOLVED 2026-09-14 (Task
  2.5b):** this was flagged 2026-09-13 (found while building Task 1.7c) as "likely
  present" on `step6_thumbnail.js`'s `retry-save-btn` but not yet fixed. It resurfaced
  for real 2026-09-14 on Task 2.5b's new `#download-mp4-vertical` link (caught by a real
  Playwright test failure, not by inspection). Fixed with the one real `[hidden] {
  display: none !important; }` rule this entry itself already recommended — resolves the
  bug everywhere in the app, including the still-unfixed-in-its-own-right
  `retry-save-btn` call site (not touched, no longer silently broken either).
- **Real, reproducible `init_db()` migration-replay crash — RESOLVED 2026-09-14 (Task
  2.5b, found while verifying it):** `init_db()` re-executed every migration file on
  every app startup with no tracking of what was already applied. Harmless for
  migrations 001-003 (`CREATE TABLE/INDEX IF NOT EXISTS`), but migrations 004 and 005
  both use `ALTER TABLE ADD COLUMN` (SQLite has no `ADD COLUMN IF NOT EXISTS`) — a real
  `sqlite3.OperationalError: duplicate column name` crash on any second real app restart
  after either landed. Reproduced for real against the actual persisted `data/app.db`
  (not a hypothetical) via `test_video_studio_browser.py`'s real-server fixture failing
  to start. Fixed with a `schema_migrations` tracking table so each migration file runs
  exactly once, with a defensive fallback for databases that already have 004/005's
  columns applied from before this fix existed. New `tests/test_database.py` proves
  `init_db()` called twice against the same on-disk file no longer raises. Re-verified
  by running `test_video_studio_browser.py` three times in a row against the real,
  already-migrated `data/app.db` — 10/10 pass every time (was failing to start at all
  before this fix).

- ~~No `die-vp-p1-complete` git tag despite Phase 1 being marked done~~ **RESOLVED
  2026-09-15**: found 2026-09-14 by a `/vp-audit` pass before Phase 3 (pure tag-hygiene
  gap, no functional impact, user chose not to act on it immediately); applied
  retroactively while closing Phase 2, alongside the new `die-vp-p2-complete` tag.
- **`save_video_job`'s error path wipes `mp4_path`/`srt_path`/`mp4_path_vertical`/
  `background_image` to NULL on a failed regenerate (found 2026-09-14, `/vp-audit` pass,
  pre-existing, not fixed):** `app/api/video.py`'s `except Exception` handler calls
  `save_video_job(db, project_id, status="error", error_message=str(exc), commit=False)`
  without passing through the previous successful values — the UPSERT's
  `ON CONFLICT DO UPDATE SET x = excluded.x` then sets all of them to `NULL`/default,
  even though the actual files from the last successful render likely still exist on
  disk. Real but narrow (only triggers if a user explicitly re-triggers generation and
  it fails after a prior success) and pre-existing (Task 2.5b's `mp4_path_vertical` just
  inherited the same already-existing pattern for the other 3 fields, not a new
  introduction) — user chose not to act on it now.
- **`init_db()`'s migration-idempotency fallback assumes single-statement migrations
  (found 2026-09-14, `/vp-audit` pass, design note, not fixed):** the `duplicate column
  name`/`already exists` fallback in `app/db/database.py::init_db()` (added 2026-09-14,
  see the resolved entry above) treats a caught error as "this whole migration file was
  already applied." Correct for migrations 004/005 (each exactly one `ALTER TABLE ADD
  COLUMN` statement) but would silently skip the *rest* of a hypothetical future
  migration file that mixed one already-applied non-idempotent statement with a genuinely
  new one. Not exploitable today — logged so a future migration author keeps each
  migration file to one non-idempotent statement, or the fallback gets upgraded to
  per-statement tracking if that stops being true.
- **Newly-observed flake (2026-09-18, first occurrence)**: `tests/test_youtube_browser.py::test_existing_package_loads_directly_without_generate_click` failed once during Task 12.2's full-suite verification run. Confirmed passing instantly in isolation (3.25s); touches no file Task 12.2 modified. The third distinct one-off Playwright-class flake observed this session (after Task 9.1's waveform test and Task 11.1's dashboard-delete test) — consistent with the already-documented pattern of occasional unrelated browser-test infrastructure timing flakes, not a regression. Not investigated further; watch for recurrence.
- **Packaging limitation (2026-09-18, Task 12.2, documented not fixed)**: the standalone `.exe` build does not bundle ffmpeg or the OmniVoice model directory — both still need to be present on the machine exactly as for a source install. Deliberate scope decision (ffmpeg bundling has real licensing considerations and adds ~80MB+; OmniVoice has no real GPU inference implementation to bundle regardless). `scripts/check_dependencies.py` and the in-app `/health` endpoint report ffmpeg's presence honestly either way. See README's "Packaging as a standalone .exe" section.

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
| BUG-013 | Bug | Editing an earlier pipeline step after later steps are generated does not invalidate downstream audio/video | high | done |
| ENH-004 | Enhancement | Single shared aiosqlite connection serializes all DB operations across concurrent requests | medium | wontfix |
| ENH-005 | Enhancement | Per-page inline CSS fragmentation causes verified visual drift from the shared stylesheet | medium | done |
| BUG-014 | Bug | 4 Phase 2 task cards carry a stale in_progress Status field despite being accepted/done | low | done |
| BUG-015 | Bug | README.md's Phase 4 section is stale and Phases 4(remainder)/5/6/7/8 are entirely undocumented | low | done |
| ENH-006 | Enhancement | ARCHITECTURE.md doesn't document the script-edit status-downgrade behavior (Task 7.1) | low | done |
| BUG-016 | Bug | Changing a speaker's voice settings doesn't invalidate already-generated audio/video status | high | done |
| BUG-017 | Bug | A failed audio/video regeneration attempt destroys the DB record of a still-valid previous success | high | done |
| BUG-018 | Bug | Regenerating a single script line leaves its old audio_cache_path/duration_seconds in place | medium | done |
| BUG-019 | Bug | Avatar upload's filesystem mutation isn't rolled back if the surrounding DB transaction later fails | medium | done |
| ENH-007 | Enhancement | ARCHITECTURE.md describes dropped/deferred features as active and diverges from its own Mermaid sidecar | medium | done |
| BUG-020 | Bug | README omits Phase 11 | low | done |
| BUG-021 | Bug | ARCHITECTURE.md event-flows row contradicts overview | low | done |
| BUG-022 | Bug | AIWorker poll loop has no top-level guard — silent death | high | done (Phase 16) |
| ENH-008 | Enhancement | ffmpeg subprocess calls have no timeout | medium | done (Phase 16) |
| BUG-023 | Bug | Leaked test projects in real app.db; CHANGELOG missing Phase 15 | low | done (Phase 16) |
| ENH-009 | Enhancement | Script repetition gate variable (B-5 5/5 → B-6 3/5) | medium | done (Phase 16, 16.4; B-7 rep 0.00%) |
| ENH-010 | Enhancement | Global script word-count repair is not budget-aware (incl. mixed case) | medium | planned (Phase 17) |
| ENH-011 | Enhancement | OpenAI-compatible cloud provider (Nemotron via OpenRouter), local qwen fallback | medium | planned (Phase 18, queued after Phase 17) |
