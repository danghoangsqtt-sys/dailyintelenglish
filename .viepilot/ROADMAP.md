# ROADMAP.md — Daily Intel English Studio

## Overview

**Timeline:** 21 ngày (10/09/2026 → 30/09/2026)  
**GPU:** NVIDIA RTX 3060 12GB  
**Stack:** Python FastAPI + HTML/CSS/JS + OmniVoice + Gemini API

---

## Phase 1 — Full Feature Build (Day 1–7)

> **Goal:** Tất cả tính năng hoạt động end-to-end — từ config đến export YouTube package

### 1.1 Project Setup & Infrastructure

- [x] **Setup Python environment**
  - `python -m venv venv` + `pip install fastapi uvicorn pydub aiosqlite python-dotenv pillow jinja2 httpx`
  - Verify: `uvicorn app.main:app --reload` starts without error
  
- [x] **Directory structure creation**
  - Tạo đầy đủ: `app/`, `frontend/`, `data/`, `prompts/`, `models/`, `tests/`
  - Verify: all dirs exist

- [x] **FastAPI app skeleton**
  - `app/main.py` với CORS, lifespan, routers mount
  - `app/core/config.py` — Settings (DATA_DIR, GEMINI_API_KEY, etc.), namespaced under `DIE_` prefix
  - `app/core/constants.py` — Magic numbers
  - Verify: `GET /health` returns 200

- [x] **SQLite setup (aiosqlite)**
  - `app/db/init.sql` — projects, speakers, scripts, audio_jobs tables
  - `app/db/database.py` — async connection pool
  - Verify: DB created on startup

- [x] **Verify ffmpeg & OmniVoice**
  - `scripts/check_dependencies.py` — check ffmpeg, OmniVoice model, GPU
  - Verify: script reports all GREEN — resolved 2026-09-13 (ffmpeg installed via
    `winget`, `DIE_GEMINI_API_KEY` filled in, OmniVoice model downloaded and GPU-load
    verified; see TRACKER.md Known Issues for the full resolution record). Re-confirmed
    live 2026-09-15 (`/vp-audit`): all 6 checks (Python, ffmpeg, GPU, Gemini key,
    OmniVoice model, data dirs) still report GREEN on this machine.

### 1.2 Dashboard & Project Management

- [x] **ProjectService CRUD**
  - `app/services/project_service.py` — create, get, list, update, delete, auto-save
  - Verify: unit tests pass for all CRUD — 30 automated tests (service-level + full HTTP via TestClient) pass; includes validation, atomic speaker updates, config_json sync, and forward-only status transitions

- [x] **Dashboard UI** (`frontend/pages/dashboard.html`)
  - Project cards grid với status badges
  - "New Project" button → Step 1 wizard
  - Search + filter (by CEFR, genre, status)
  - Dark/Light mode toggle
  - Verify: 7 automated Playwright browser tests (`tests/test_dashboard_browser.py`) — listing with status badges, filter, search, empty state, "New Project" → `/step1`, "Continue" → `/step2?project_id=...` for draft projects, delete removes card after confirm. 230 total tests pass.

### 1.3 Step 1 — Script Config Wizard

- [x] **Config API route** (`app/api/projects.py`)
  - `POST /api/projects` — create with config
  - Pydantic models: `ScriptConfig`, `SpeakerConfig`
  - Verify: API accepts valid config, rejects invalid CEFR level — tested via `tests/test_projects_api.py`

- [x] **Script Config UI** (`frontend/pages/step1_config.html`)
  - Form fields: Project Name, Topic (required), CEFR level (dropdown), Duration (presets + custom), Num speakers (integer 1–6, sanitized live)
  - Genre selector (10 options với icon), Accent selector (10 regions + flag)
  - Language features toggles (collocation, idiom, slang, etc.)
  - Speaker cards: name, gender, accent per speaker — count always kept in sync with `num_speakers`
  - Verify: form saves config via `POST /api/projects`, advances to the Step 2 entry point (placeholder — full UI is Task 1.4) with the created `project_id` preserved. Verified in a real headless browser (Playwright): dashboard → Step 1 → valid submit → 200 → Step 2 placeholder → project reappears on Dashboard; invalid payload blocks submit client-side (0 requests) with a friendly banner; dark/light mode works. API errors never leak raw backend text into the UI (logged to console instead, per CR-05).

### 1.4 Step 2 — AI Script Generation

- [x] **Prompt templates** (`prompts/script/`)
  - Base template: `script_base.txt`
  - Per-genre: `debate.txt`, `instructions.txt`, `interview.txt`, `small_talk.txt`, etc. (10 files)
  - CEFR constraint blocks: `cefr_a1.txt` → `cefr_c2.txt`
  - Verify: prompts load via Jinja2, variables inject correctly — 101 automated tests, incl. solo-speaker mode, duplicate-name/UUID disambiguation, CEFR-ceiling-vs-toggle precedence, and path-traversal rejection

- [x] **ScriptService** (`app/services/script_service.py`)
  - `generate_script(project_id, config)` → calls Gemini (REST via httpx, not the SDK), parses JSON response
  - `regenerate_line(project_id, config, line_id, current_text, speaker_id)` → re-generates single line
  - Retry with backoff on Gemini rate limit (1s → 2s → 4s, HTTP 429 only)
  - Verify: 22 automated tests (mocked Gemini) — success, retry/backoff, non-429 no-retry, invalid JSON, schema failure, hallucinated/non-UUID speaker_id rejected, missing API key. Exposed via `POST/PUT` routes in `app/api/projects.py` (`app/models/script.py`), all errors routed through the existing global `AppError` handler

- [x] **Script Generation UI** (`frontend/pages/step2_script.html`)
  - "Generate" button → progress spinner → script display
  - Script viewer: each line as card (speaker chip, text, language notes expandable)
  - Inline text editor for each line
  - "Re-generate this line" button per line
  - Verify: generate script, edit a line, re-generate a line — all work. Also: loads a persisted script on init (`GET /api/projects/{id}/script`) so it survives reload/revisit, drives `draft → script_generated`, "Regenerate All" (confirm-gated), and Dashboard's "Continue" button. Verified end-to-end in a real headless browser, including an actual SQLite reload check. 7 new API tests, 160 total pass.

- [x] **1.4D-FIX2/FIX2B/FIX2C gate** — PM-required hardening before Sprint 1.5A, three rounds:
  - **FIX2**: autosave resyncs line ids from the `PUT .../script` response and serializes overlapping saves; Regenerate disabled while a save is in flight; Generate panel stays hidden when loading the existing script fails; script save + status-advance merged into one transaction with rollback; `GEMINI_MODEL` moved off the shut-down `gemini-2.0-flash` to `gemini-3.8-flash`.
  - **FIX2B**: the whole app shares one `aiosqlite` connection with exactly one implicit transaction at a time, so a per-project lock still let an unrelated concurrent write interleave into (and get wiped out by) another request's rollback. Replaced with one connection-wide `_write_lock` (`app/api/projects.py::_write_transaction`) covering every write route (create/update/delete project, script generate/regenerate/save); `db.commit()` moved inside the `try` so a commit failure also rolls back.
  - **FIX2C**: the same connection-wide lock now also guards every **read** (`_read_transaction`) — `list_projects`, `get_project`, `GET /api/projects/{id}/script`, and the pre-read steps of generate/regenerate/save — so a read can never dirty-read an uncommitted write or phantom-read a write that later rolls back. The lock is never held across a Gemini call (network + retries would otherwise stall every other request): generate/regenerate take a short read lock to snapshot what they need, call Gemini unlocked, then take a separate write lock to persist.
  - Test count: 160 → 163 (FIX2) → 165 (FIX2B) → 166 (FIX2C, deterministic read-vs-write regression in `tests/test_projects_write_lock.py`, asyncio.Event-synchronized — no sleep-based timing). `ruff check` clean, `pytest -x` all green, `node --check` clean, browser E2E (Playwright) green every round.

### 1.5 Step 3 — Learning Content

- [x] **Prompt templates** (`prompts/learning/`)
  - `prompts/learning/learning_pack.txt` rendered async via `app/core/prompt_loader.py`
  - Verify: Jinja2 injection works with project topic, CEFR level, and script lines

- [x] **LearningContentService** (`app/services/learning_service.py`)
  - `generate_learning_content(script, cefr_level)` → `LearningPackOut` with vocabulary, idioms, grammar, quiz
  - Gemini REST via `httpx.AsyncClient`, `gemini-3.8-flash`, 429 exponential backoff 1s→2s→4s
  - SQLite persistence in `learning_contents` table with UPSERT
  - Verify: 20 automated tests in `tests/test_learning_api.py` pass; committed (`b06eb07`)

- [x] **Learning Content UI** (`frontend/pages/step3_learning.html`)
  - `frontend/pages/step3_learning.html` + `step3_learning.js` served at `/step3`
  - 4 tabs: Vocabulary (IPA, PoS, definition, example), Idioms, Grammar, Quiz (with answer toggle)
  - Coalesced trailing autosave (`PUT /api/projects/{id}/learning`) with dirty section queue
  - Regenerate Pack confirm dialog, and Next Step navigation
  - Verify: 223 automated tests pass (218 unit/integration + 5 browser E2E), browser E2E verified; committed (`b57428e`)

### 1.6 Step 4 — TTS Audio Studio

- [x] **TTSService — OmniVoice** (`app/services/tts_service.py`) — **Won't do, by user
  decision 2026-09-13.** Real GPU inference will not be integrated: OmniVoice's actual
  API is zero-shot voice *cloning* from a reference audio sample, not the
  text-described "voice design" this bullet originally assumed
  (`generate_line(text, voice_description, ...)`), and closing that gap doesn't clearly
  improve on the already-working Edge TTS enough to justify the voice-cloning
  consent/rights questions a reference-sample source would raise. **Edge TTS is the sole
  official TTS engine.**
  - Semaphore(2) for concurrent limit — **done**, `asyncio.Semaphore(MAX_CONCURRENT_TTS)` wraps the call site (left in place, harmless)
  - VRAM overflow → auto-fallback to Edge TTS — **done and tested** (any exception from the OmniVoice path falls back, not just OOM specifically)
  - Real model loading / cache / generation — **not pursued**; `_synthesize_omnivoice()` honestly and permanently raises "model not loaded" rather than faking success, exercised by `test_omnivoice_synthesis_always_raises_unavailable_for_now`. The Step 4 UI does not offer OmniVoice as a selectable engine (no real behavior difference to choose between)

- [x] **TTSService — Edge TTS**
  - `generate_line_edge(text, voice_name, speed)` → mp3 (via `edge_tts.Communicate`, streamed to bytes)
  - List available English accents per region — `EDGE_TTS_VOICE_MAP` in `app/core/constants.py`, all 10 accents x 3 genders, voice ids verified live against `edge_tts.list_voices()`
  - Verify: generates speech for all 10 accent regions — live-smoke-tested all 10 accents x 2 genders (20/20 real Edge TTS calls succeeded); one transient "no audio received" response was caught and recovered by the new retry-once-on-empty-audio logic, not silently ignored

- [x] **AudioService** (`app/services/audio_service.py`) — Sub-task 1.6b, done 2026-09-13
  - `mix_project(project, lines, background_music_filename)` → single MP3 + WAV from all lines — done
  - Add silence gaps between lines — done, 300ms same-speaker / 500ms different-speaker
  - Background music ducking (if music selected) — done, static-level cap at `MUSIC_DUCKING_MAX_DBFS` (not dynamic speech-reactive ducking)
  - Normalize to -16 LUFS — done, real ITU-R BS.1770 measurement via `pyloudnorm`, not a dBFS approximation
  - Generate timestamps JSON — done, real measured per-line start/end seconds
  - Verify: 25 dedicated tests against a real ffmpeg pipeline (not mocked) — silence-gap timing, loudness within tolerance of target, ducking ceiling respected both directions, timestamps monotonic and duration-accurate; 375 total tests pass

- [x] **TTS Audio Studio UI** (`frontend/pages/step4_tts.html`) — Sub-task 1.6c, done 2026-09-13
  - Speaker voice assignment panel (engine + voice per speaker) — done, autosaved per speaker via new `PATCH /api/projects/{id}/speakers/{speaker_id}` (a narrow in-place update added specifically because the existing `PUT /{id}` speakers-replace path would cascade-delete script_lines once a script exists — see task-1.6.md)
  - "Preview" button per line → plays audio inline — done
  - Background music selector (from music_library folder) — done
  - Speed/pitch/volume sliders per speaker — done
  - "Generate All" button → progress text (plain polling, not SSE streaming — see task-1.6.md's documented deviation from the ARCHITECTURE.md SSE label, same reasoning as `/audio/status`)
  - Final player — done as a plain `<audio controls>` element; waveform *visualization* not done (visual-only, no task assigned anywhere yet, same standing gap as the Music Library page)
  - Download MP3 / WAV buttons — done
  - Verify: 13 new tests (6 API + 7 Playwright E2E with network mocking), plus a real end-to-end smoke script (real project → real script → real speaker patch → real TTS synthesis → real ffmpeg mix → real download) — 388 total tests pass

### 1.7 Step 5 — Video Studio

- [x] **VideoService — Background + Subtitle** (`app/services/video_service.py`) — Sub-task 1.7a, done 2026-09-13
  - `generate_video(project_id, audio_job, template_id)` — real completed audio mix (Task 1.6) + one of 3 fixed background templates + burned-in subtitles (ffmpeg) — done
  - SRT file generation from timestamps — done, from AudioService's real *measured* per-line timestamps (not estimated), including actual dialogue text
  - Burned-in subtitles (ffmpeg subtitles filter) — done, verified the installed ffmpeg build has `--enable-libass` before relying on it, and worked out the Windows path-escaping rule the filter needs
  - Verify: MP4 generates correctly with synced subtitles — 20 new tests (real ffmpeg pipeline, not mocked) + a live end-to-end smoke run with a real extracted video frame visually confirming the correct speaker name + dialogue text burned in

- [ ] **VideoService — LivePortrait lips-sync** (Phase 1 primary if time allows) — the
  avatar-sourcing question that used to block this is resolved (user decision 2026-09-13:
  upload only, see Sub-task 1.7c, done); the actual lip-sync inference pipeline itself
  remains not started
  - `generate_video_avatar(project_id, avatar_images)` — per-speaker avatar lip-sync
  - Side-by-side layout: speaker1 left, speaker2 right
  - Active speaker highlight (border glow on speaking turn)
  - Verify: lips-sync avatar video generates for 2-speaker dialogue

- [x] **Video Studio UI** (`frontend/pages/step5_video.html`) — Sub-task 1.7b, done 2026-09-13
  - Background selector — done, choose from the 3 fixed templates (no custom upload yet, matches 1.7a's own scope decision)
  - Avatar uploader per speaker — done, Sub-task 1.7c (2026-09-13): upload/preview/remove
    per speaker at `/step5`, `app/services/avatar_service.py`, never wired into video
    generation since the lip-sync pipeline itself doesn't exist yet
  - Subtitle style picker / Mode toggle / "Copy prompt to generate avatar image" — not
    built: still belong to Level 3 (LivePortrait), which isn't implemented; building UI
    controls for a backend path that always fails would be a fake feature
  - Progress bar → a plain "Rendering…" status text instead (ffmpeg render is well under a second per the 1.7a live smoke test — a fake animated progress bar for a near-instant operation was rejected) + preview player — done
  - Download MP4 + SRT buttons — done
  - Verify: 7 new Playwright tests (network-mocked) + a live end-to-end smoke run through the real API + a real screenshot confirming visual consistency

### 1.8 Step 6 — Thumbnail Generator

- [x] **ThumbnailService** (`app/services/thumbnail_service.py`) — Sub-task 1.8a, by Codex, PM-accepted 2026-09-12
  - Load template PNG + Jinja2 text overlay config — done
  - Gemini fills: title text, accent color, topic keywords — done, `responseJsonSchema` + Pydantic, exact-count + duplicate-rejection validation
  - Pillow renders 3-5 A/B variants — done, hash-verified distinct pixels per variant
  - Export 1280×720 + 720×1280 versions — done, both PNG (lossless) and JPEG
  - Verify: generates 3 variants, all differ meaningfully — 27 new tests (6 prompt + 11 service + 10 API); PM independently re-rendered all 5 templates and visually confirmed quality

- [x] **Thumbnail template files** (`frontend/static/thumbnail_templates/`) — Sub-task 1.8a
  - 5 templates: `modern_split.png`, `gradient_bold.png`, `minimal_clean.png`, `dynamic_wave.png`, `podcast_classic.png` — done, deterministically generated by `scripts/generate_thumbnail_template_assets.py`
  - JSON config per template: text zones, color zones, font specs — done (font is Pillow's embedded scalable default, not a system/hardcoded path)
  - Verify: all templates render correctly — PM independently rendered and viewed all 5

- [x] **Thumbnail UI** (`frontend/pages/step6_thumbnail.html`) — Sub-task 1.8b, by Codex (completed/verified by PM after Codex's session ran out of quota mid-task), PM-accepted 2026-09-12
  - Template gallery (5 options, hover preview) — done
  - Generate button → 3-5 A/B variants display — done, confirm-gated when replacing an existing batch
  - Click to select favorite — done, atomic single-UPDATE exclusive selection
  - In-app editor: change title text, colors, add/remove elements — done for text+colors (optimistic-concurrency re-render); add/remove elements and drag/drop explicitly out of scope (see task-1.8.md "Layout-tweak scope decision")
  - Download selected variant (16:9 + 9:16) — done, PNG+JPG both aspects, cache-busted via revision token
  - Verify: select template, generate, edit, download — all work — 17 new tests (11 service/API + 6 real-browser Playwright), 314 total tests pass

### 1.9 Step 7 — YouTube Package

- [x] **YouTubePackageService** (`app/services/youtube_service.py`) — Sub-tasks 1.9a + 1.9b, by Claude Code (acting as PM + Implementer), PM-accepted; 1.9b closed 2026-09-13
  - `generate_package(project, script_lines, timestamps=None)` → titles + description + tags + chapters — done
  - Description: Gemini-generated summary — done
  - Chapters: **measured** from AudioService's real per-line timestamps once a project's audio exists (`real_chapters_from_timestamps()`, Sub-task 1.9b), otherwise **estimated** from script word count (Sub-task 1.9a's original behavior); `chapters_estimated` says which, clearly labelled in API + UI
  - Tags: 5-15 relevant tags (Gemini), joined string capped at `YOUTUBE_TAGS_MAX_CHARS` (500)
  - Full `.zip` export (`GET .../youtube/export`) — done, Sub-task 1.9b: video.mp4 + subtitles.srt (Task 1.7) + thumbnail.png (Task 1.8 favorite) + metadata.txt, in-memory zip, requires all three prerequisites
  - Full transcript/vocabulary/grammar formatting inside the export — done, Sub-task 1.9c (2026-09-13, by Codex): 5th zip file `transcript_and_vocabulary.txt` with the full script transcript plus Learning Content (vocabulary/idioms/grammar/comprehension questions) when generated; Learning Content stays optional, never a new export prerequisite
  - Verify: 30 tests (1.9a) + 13 tests (1.9b) + 10 tests (1.9c, including a real end-to-end pipeline test with real Unicode content); real bugs caught and fixed before landing each time (1.9a: tag whitespace on DB round-trip; 1.9b: frontend defaulting to "Measured" on an undefined flag, caught by a browser test)

- [x] **YouTube Package UI** (`frontend/pages/step7_youtube.html`) — Sub-tasks 1.9a + 1.9b
  - Sections: Title options (3 variants) | Description | Chapters (labelled Estimated/Measured accurately) | Tags — done
  - "Copy to clipboard" button per section — done
  - "Download full package (.zip)" — done, Sub-task 1.9b: disabled with an explanatory status note until video + favorite thumbnail both exist
  - Edit fields inline — out of scope (read-only display + Regenerate, matching the original plan's explicit scope decision)
  - Verify: 6 (1.9a) + 2 (1.9b) real-browser Playwright tests; real bugs caught by browser testing both times, not by unit tests alone

### 1.10 Music Library Management

- [x] **Music Library UI** (`frontend/pages/music_library.html`) — Sub-task 1.10a (ffmpeg-independent), by Codex, PM-accepted 2026-09-12
  - Drag-and-drop upload to `data/music_library/` — done, plus file-picker fallback, 50MB limit, magic-byte validation, atomic no-clobber duplicate naming
  - List tracks with player preview — done, native browser `<audio>` preview (not a waveform visualization)
  - Delete track — done, confirm-gated
  - Verify: upload, preview, delete work — 19 dedicated tests (15 API incl. a real concurrency test, 4 Playwright browser E2E), PM independently re-ran all; 271 total tests pass (1 unrelated pre-existing flaky test confirmed passing in isolation)
  - Volume leveling + Step 4/5 background-track selection/ducking — delivered in Task 1.6
    Sub-task 1.6b (`app/services/audio_service.py`), 2026-09-13
  - Waveform visualization — done, Sub-task 1.10c, 2026-09-13: `frontend/static/js/waveform.js`
    (Web Audio API decode, canvas rendering, played/unplayed tinting, click-to-seek),
    verified with real decodable audio and a real Playwright pixel-content check. **Closes
    Task 1.10.**

---

## Phase 2 — Testing & Polish (Day 8–14)

### 2.1 Quality Testing

- [x] **CEFR accuracy testing** — done 2026-09-14 (Task 2.1a + 2.1b). Task 2.1a: a
  standalone CLI (`scripts/generate_cefr_review_samples.py`) generates the 18-case matrix
  (6 CEFR levels × 3 genres) via the real production `generate_script()` path, no fake
  success path. Task 2.1b (user-approved at a `/vp-auto` control point: PM does an
  automated-proxy review first): PM read all 18 real Gemini-generated scripts in full
  and recorded a traceable per-case verdict — **14 PASS, 4 BORDERLINE, 0 FLAG**. The 4
  BORDERLINE cases (A2/B1/B2 × `news`) share one pattern: the `news` genre pulls
  idiom/grammar sophistication about half a level higher than `small_talk`/`interview`
  at the same CEFR level; A1/C1/C2 × `news` stay well-calibrated. No grammar errors,
  no misused idioms, no off-topic drift, no safety/factual issues found across all 18.
  Nothing required the user's own read; the news-genre calibration pattern is logged as
  an optional future prompt-tuning task, not acted on here (read-only review). See
  `tasks/task-2.1a.md` and `tasks/task-2.1b.md` for the full record.

- [x] **Multi-accent TTS testing** — done 2026-09-14 (Task 2.1c). OmniVoice voice-design
  testing is moot (real OmniVoice integration decided not-pursued 2026-09-13; Edge TTS is
  the sole official engine). All 10 accents × male/female (20 combinations) real-tested
  against the actual Edge TTS voice map: 20/20 succeeded. 9 of 10 accents resolve to a
  distinct real neural voice; `scottish` resolves to the same voice ids as `british`
  (confirmed against the real `edge-tts --list-voices` catalog: Microsoft's neural
  lineup has no dedicated Scottish-accented voice at all) — a known upstream limitation,
  not a code defect.
- [x] **Audio quality testing** — done 2026-09-14 (Task 2.1c). Real `mix_project` runs
  on 2 real script lengths (8 lines/66s, 12 lines/91s): no-music loudness measured
  -16.01 LUFS both times (0.01dB from the -16 target, well within ±1dB), silence gaps
  measured exactly 500ms between different-speaker lines as designed. **With background
  music, measured loudness drifted to -17.12 LUFS (1.12dB off target) — outside the
  declared ±1dB tolerance**, a real reproducible finding: the voice track is normalized
  to -16 LUFS *before* the ducked music overlay, and the combined signal is never
  re-normalized afterward. Root cause identified, not yet fixed (see TRACKER.md Known
  Issues) — a small, scoped follow-up task, not done in this read-only QA pass.
- [x] **Video testing** — done 2026-09-14 (Task 2.1c). LivePortrait avatar testing is
  moot (LivePortrait lip-sync integration remains not-started, a separate deferred
  effort — see Task 1.7 notes). Real end-to-end render (TTS → mix → video) confirmed
  subtitle sync is exact (generated SRT content byte-for-byte matches
  `mix_project`'s own measured timestamps). **9:16 output: does not exist.** All 3
  background templates and the rendered MP4 are confirmed 1280×720 (16:9) only — a full
  code search found zero resolution/aspect-ratio handling anywhere in
  `video_service.py`. This ROADMAP line's "both 16:9 and 9:16" can't be tested until
  9:16 support is built — logged as a missing feature, not a QA gap (see TRACKER.md
  Known Issues).

### 2.2 Bug Fixes & Performance

- [x] Fix any blocking API calls → move to executor — done 2026-09-13 (Task 2.2). A
  research-agent audit + direct file review found 4 real gaps (not the ~25 already-correct
  usages elsewhere): `video_service.generate_video()`'s background-check/mkdir/SRT-write,
  `tts_service.synthesize_line()`'s model-exists-check/mkdir/audio-write (a per-line hot
  path), `audio_service.mix_project()`'s background-music existence check, and
  `app/api/tts.py`'s `list_engines()` (model-exists + `shutil.which("piper")`). All 4
  wrapped in `asyncio.to_thread`; 55 pre-existing tests across the touched files pass
  completely unmodified, proving zero behavior change
- [ ] Optimize OmniVoice batch: generate 5 lines per batch instead of sequential — moot,
  per the user's 2026-09-13 decision (TRACKER.md Known Issues) real OmniVoice integration
  will not be pursued
- [ ] Add progress cancellation (stop mid-generation) — audited 2026-09-13: every
  generation route is a synchronous request/response call with no background-job/cancel
  mechanism anywhere in the app; building real cancellation is a genuinely large
  architectural change, not a bug fix — deferred as its own future task
- [x] Fix Gemini retry logic for 429 rate limit errors — already done during Phase 1 (all
  4 Gemini-calling services have 1s→2s→4s exponential backoff on 429 only); this line
  predated that work and was never updated. Closed via audit 2026-09-13, no code needed

### 2.3 UX Polish

- [x] **Step progress indicator**: header bar shows "Step 2 of 7" — done 2026-09-13, by
  Codex, PM-accepted: `frontend/static/js/step_nav.js` (`StepNav.render()`), mounted on
  all 7 step pages. 15 new Playwright tests, 452 total pass.
- [x] **Breadcrumb navigation**: jump back to any previous step — done alongside the item
  above (same component): 7 clickable pills, missing `project_id` degrades to a clean
  bare URL rather than a broken link
- [x] **Auto-save indicator**: "Saved" / "Saving..." in header — done 2026-09-13 (Task
  2.3e, closes Task 2.3 entirely). New shared `frontend/static/js/save_indicator.js`
  (`SaveIndicator.mount()`, same pattern as `StepNav`/`KeyboardShortcuts`) mounted in the
  header of `/step2`, `/step3`, `/step6` — the 3 pages with an existing page-level
  autosave state machine — as an addition alongside each page's existing inline
  `#save-status` element, not a replacement. `/step4` (per-speaker-field autosave, no
  single "document" concept), `/step1`/`/step5`/`/step7`/Dashboard/Music Library (no
  page-level autosave concept at all) intentionally excluded
- [x] **Keyboard shortcuts**: `Ctrl+Enter` to generate, `Esc` to cancel — done 2026-09-13
  (Task 2.3b): a new shared `KeyboardShortcuts.init({ primaryButtonId })` (same pattern as
  `StepNav`) mounted on all 7 step pages triggers each page's real primary button, only
  when it's genuinely visible and not disabled. `Esc` needed no code — every confirm-gated
  action already uses native `window.confirm()` (Escape-cancelable for free), and the two
  pages with inline-edit-then-commit fields (`/step2`, `/step3`) already revert on Escape
- [x] **Empty states**: helpful messages when no projects / no music library — audited
  2026-09-13 (Task 2.3c) and found already satisfied: Dashboard's `#empty-state` and Music
  Library's `#empty-state` both already show a helpful message when their list is
  genuinely empty (distinct from a load *failure*, fixed separately under "Error toasts"
  above); `/step1` is a pure form with no "empty" concept and `/step7`'s `#generate-panel`
  already serves as its own empty/call-to-action state. No code change needed
- [x] **Error toasts**: user-friendly error messages (not stack traces) — done 2026-09-13
  (Task 2.3c). Audited first: all 7 step pages and `music_library.js` already had a
  working friendly-error system; the Dashboard was the one real gap (a failed project
  load silently rendered the misleading "No projects yet" empty state, and a failed
  delete used a raw `alert(err.message)`). Both fixed with the same `#error-banner`
  pattern used everywhere else — no new UI paradigm introduced
- [x] **Responsive layout**: works at 1024px width minimum — closed 2026-09-13 (Task 2.3d)
  via a real Playwright audit before any planning: all 9 pages already have zero
  horizontal overflow at 1024px, thanks to the consistent `repeat(auto-fit, minmax(...))`
  grid pattern used everywhere plus `/step6`'s existing `@media (max-width: 1180px)`
  stacking rule. No code change needed; a permanent 9-page regression suite
  (`tests/test_responsive_layout_browser.py`) now pins this so it can't silently regress

### 2.4 UI Redesign Slice 1 — Dashboard + Script Workspace

New scope added 2026-09-14 (not in the original Phase 2 plan above), from an approved
CapCut-style UI direction (`.viepilot/ui-direction/2026-09-14/`).

- [x] **Dashboard → light, high-contrast project launcher** — done 2026-09-14 (Task 2.4):
  new hero + toolbar + light project-card shell while retaining every existing
  list/filter/search/delete/new-project behavior and selector
- [x] **Step 2 → CapCut-style Script workspace** — done 2026-09-14 (Task 2.4): new
  `frontend/static/js/shell.js` (`WorkspaceShell`) drives a resizable/collapsible
  workflow sidebar, central script stage (original inline editor untouched), a
  selected-line inspector (speaker/text/language notes, Listen via the existing
  `previewTtsLine` endpoint, Regenerate via the existing guarded path), and a three-track
  Script/Voice/Music timeline
- [x] **Light-by-default theme migration** — done 2026-09-14 (Task 2.4): shared CSS
  tokens moved to light-first `:root` with dark values under `[data-theme="dark"]`;
  `theme.js`'s stored-preference fallback changed from `"dark"` to `"light"`
  (byte-for-byte otherwise unchanged); legacy variable aliases kept so untouched pages
  render unaffected
  49 new/updated Playwright tests, 515/516 passing (1 pre-existing tracked Gemini-retry
  flake, confirmed via isolated re-run — Task 2.4 touched zero backend code). See
  `.viepilot/phases/02-testing-polish/tasks/task-2.4.md` for the full record.

### 2.5 Fix the 3 real findings from Task 2.1c

New scope added 2026-09-14 (not in the original Phase 2 plan above), per explicit user
request to research + plan + fix all 3 real findings from Task 2.1c's QA pass.

- [x] **Background-music LUFS drift** — fixed: `audio_service._mix_project_sync` now
  normalizes the final mixed signal (voice + ducked music) once, after the overlay,
  instead of only the pre-music voice stem — per EBU R128 guidance that loudness
  normalization must target the complete final mix. Real measured result: within the
  declared ±1dB tolerance (was 1.12dB off before the fix).
- [x] **No 9:16 video output** — fixed: new `_render_vertical_sync` (blurred-background-
  pad ffmpeg technique, the real industry convention for 16:9→9:16 conversion) as a
  second pass over the existing 16:9 render; new `aspect_ratio` request field, DB column,
  download format, and Step 5 UI toggle. Default (16:9) is byte-for-byte unchanged. Real
  `ffprobe` confirms the vertical output is genuinely 720×1280.
- [x] **Scottish/British voice duplication** — disclosed, not code-fixable (confirmed
  live against the real `edge-tts` package that no Scottish neural voice exists
  upstream): a `title` tooltip on Step 1's Scottish accent option/chip explains the
  limitation.

**2 additional real bugs found and fixed while verifying 9:16 video** (disclosed, needed
to actually prove the feature works against the real app): the `.hidden`-on-`.btn` CSS
trap pre-flagged in TRACKER.md Known Issues (fixed with the one real `[hidden]` rule
recommended there), and a real `init_db()` migration-replay crash on any second real app
restart once a non-idempotent migration exists (fixed with a `schema_migrations`
tracking table). 530/530 full suite passes (up from 515), zero flakes. See
`.viepilot/phases/02-testing-polish/tasks/task-2.5.md` for the full record.

### 2.6 Fix 3 findings from the post-Task-2.5 audit pass

New scope added 2026-09-14: user ran `/vp-audit` before starting Phase 3 and selected 3
of 6 real findings to fix immediately (the other 3 are pre-existing/low-severity, noted
only in TRACKER.md Known Issues).

- [x] **ARCHITECTURE.md doc drift** — fixed: the `### Video` API docs now mention
  `aspect_ratio` and the `mp4_vertical` download format (stale since Task 2.5b).
- [x] **Orphaned `mp4_path_vertical` on regenerate** — fixed: `generate_video()` now
  deletes a stale vertical file left over from an earlier `"9:16"` call when a later
  regenerate doesn't request it again. Real bug in Task 2.5b's own design, found by
  self-review during this audit pass.
- [x] **`escapeHtml()` unsafe for attribute-value contexts** — fixed: now also escapes
  `"`/`'`, not just `&`/`<`/`>`. Verified as a real bug (not just theoretical) by
  reverting the fix, watching a real Playwright test fail for the right reason (a quote
  breaking out of a rendered `value="..."` attribute), then restoring it.

532/533 full suite passes (1 pre-existing tracked Gemini-retry flake, confirmed via
isolated re-run). See `.viepilot/phases/02-testing-polish/tasks/task-2.6.md`.

---

## Phase 3 — Review & Documentation (Day 15–21)

### 3.1 Documentation — ✅ DONE (2026-09-15)

- [x] **README.md** — installation guide, quick start, features overview — updated with a
  Phase 2 summary table, corrected stale LivePortrait status lines, and a new
  Documentation table linking the 3 docs below
- [x] **Prompt Engineering Guide** (`docs/prompt-guide.md`) — how to customize prompts —
  covers script genre/CEFR blocks, the CEFR-ceiling-vs-language-toggle precedence rule,
  solo-speaker override, learning content, thumbnail, and YouTube prompts
- [x] **TTS Setup Guide** (`docs/tts-setup.md`) — Edge TTS voice map + known
  Scottish/British limitation, and the full OmniVoice investigation record (real model
  downloaded/GPU-verified, decided against integrating — see key_decisions)
- [x] **API Reference** (`docs/api.md`) — auto-generated from FastAPI OpenAPI via new
  `scripts/generate_api_docs.py` (reads the real `app.openapi()` schema, 49 routes
  documented) — re-run the script after any route change instead of hand-editing

### 3.2 Demo & Review — ✅ DONE (2026-09-15)

- [x] **Demo video**: Record full workflow from project creation to YouTube package — a
  real 223.9-second Playwright screen recording (`docs/demo/demo-video.webm`, see
  `docs/demo-video.md`) of the actual running app: real Gemini calls, real Edge TTS,
  real ffmpeg. Shorter than the original "10 min" figure because the real pipeline is
  genuinely this fast, not because footage was cut
- [x] **Sample outputs**: 3 sample podcast scripts (A1, B1, C1) with audio —
  `docs/samples/{A1,B1,C1}/` via new `scripts/generate_sample_episodes.py`: real Gemini
  script generation + real Edge TTS/ffmpeg audio mix per level, same topic/genre/speakers
  held constant so CEFR level is the only variable
- [x] **Product review report**: feature checklist, known issues, future improvements —
  `docs/product-review.md`, assembled from and cross-checked against ROADMAP.md/
  TRACKER.md rather than restated from memory

### 3.3 Final Cleanup — ✅ DONE (2026-09-15)

- [x] Remove all `print()` debug statements → use `logging` — audited: `grep -rn
  "print(" app/` returns zero matches, every service already uses
  `logging.getLogger(__name__)`. Already satisfied, no code needed
- [x] Add `.env.example` file — existed since crystallization, but was stale: removed 5
  dead `Settings` fields with zero real usages anywhere (`GOOGLE_TTS_API_KEY`,
  `AZURE_TTS_API_KEY`, `AZURE_TTS_REGION` — vestiges of the pre-decision multi-engine TTS
  design; `OMNIVOICE_DEVICE`/`OMNIVOICE_MAX_CONCURRENT` — the real concurrency limit is
  the unrelated hardcoded `MAX_CONCURRENT_TTS` constant) from both `app/core/config.py`
  and `.env.example`
- [x] Verify `requirements.txt` is complete and pinned — audited: every entry already
  uses `==` (done during Phase 2's structural-risk audit, 2026-09-14). Already satisfied
- [x] Git tag: `v1.0.0-beta` — applied after this task's changes were verified and pushed

---

## Acceptance Criteria (Phase 1 Complete)

- [x] Can create a new project with full configuration — Task 1.3
- [x] AI generates a grammatically correct, level-appropriate script for any genre + CEFR combination — Task 1.4
- [x] TTS generates audio for all speakers, mixes into single MP3/WAV — Tasks 1.6
- [x] Video exports as MP4 with synced subtitles + SRT file — Task 1.7
- [x] Thumbnail generates 3+ A/B variants — Task 1.8
- [x] YouTube package includes complete description + chapters + transcript + vocabulary —
  Sub-task 1.9c (2026-09-13, by Codex): the `.zip` export's 5th file,
  `transcript_and_vocabulary.txt`, adds the full script transcript plus Learning Content
  (vocabulary/idioms/grammar/comprehension questions) when generated for the project
- [x] All steps persist data (auto-save) — refresh doesn't lose progress — verified across
  Tasks 1.3-1.9 (each step's `GET` route restores state; audio/video/thumbnail/youtube
  jobs are all re-fetched on page load, not just held in memory)
- [x] Dark mode works across all pages — `data-theme="dark"` default + `theme.js` toggle,
  present on every page since Task 1.1/1.2

---

## Phase 4 — Post-v1.0.0-beta Polish

New phase, not in the original 21-day/3-phase plan — scoped in the 2026-09-15 brainstorm
session (`docs/brainstorm/session-2026-09-15.md`) after all 3 original phases closed.
PM presented a risk/value review of known deferred items (progress cancellation,
LivePortrait lip-sync, remaining UI redesign pages, CEFR calibration); user approved 2
low-risk, clear-value tasks. Progress cancellation and real LivePortrait lip-sync remain
explicitly deferred, not part of this phase.

### 4.1 CEFR `news`-genre prompt tuning — ✅ DONE (2026-09-15), partial improvement

- [x] **Tune `prompts/script/news.txt`** — Task 2.1b's real 18-sample review (2026-09-14)
  found A2/B1/B2 × `news` BORDERLINE (idiom/grammar sophistication ~half a CEFR level
  higher than `small_talk`/`interview` at the same level; A1/C1/C2 × `news` were already
  well-calibrated). Added explicit register-vs-complexity guidance so the genre's formal
  tone doesn't push Gemini past the CEFR ceiling set elsewhere in the prompt.
  - Verified: re-ran `scripts/generate_cefr_review_samples.py --levels A2 B1 B2 --genres
    news` (3/3 real Gemini calls) and re-reviewed against Task 2.1b's exact rubric.
    **Honest result: partial, mixed improvement, not a full fix** — A2's specific
    "indefinite pronoun + modal" pattern didn't recur but Future Simple usage persists;
    B1's exact flagged idiom ("a breath of fresh air") recurred verbatim; B2's idiom
    choice became more solidly B2-appropriate but grammar (Past Perfect Continuous)
    still borders C1. See `tasks/task-4.1.md` for the full before/after evidence.
    Consistent with tuning a probabilistic model — a real, measured, disclosed effect,
    not overclaimed as solved. None of the original cases were unusable, only slightly
    harder than nominal, so this closes at the honest result rather than iterating
    further on a low-priority item.

### 4.2 UI Redesign Slice 2 (7 remaining pages) — ✅ 7/7 CLOSED (2026-09-16)

- [x] **Learning** (`/step3`) — ✅ DONE (2026-09-15). Applied the 3-panel shell (no
  timeline, confirmed decision); inspector is a read-only detail view of the selected
  vocabulary/idiom/grammar/quiz item (quiz inspector always shows the answer). 3 new
  Playwright tests (first browser coverage this page has had). Found+fixed a real
  regression in `test_step_nav_browser.py`'s shell-layout assumption and a missing
  `variant: "workflow"` on the page's own `StepNav.render()` call. 536/536 full suite
  passes. See `.viepilot/phases/04-post-beta-polish/tasks/task-4.2a.md`.
- [x] **TTS Audio Studio** (`/step4`) — ✅ DONE (2026-09-16), implemented by Codex
  (Implementer), accepted by PM per AR-06. Shell + 3-track timeline (Script/Voice/Music);
  read-only inspector with an honest session-only preview-state badge, a real Listen
  action, and a real scroll-to-speaker-card "Voice settings" affordance. Existing
  per-speaker autosave and Generate-All order unchanged. 5 new Playwright tests. 2 real
  review rounds: a pre-authorized `test_step_nav_browser.py` fix (same class as 4.2a's),
  and a PM-caught real bug (`renderTimeline()` never cleared the Music lane, causing
  duplicate clips on re-render) that Codex fixed and PM independently re-verified,
  including a 5-interaction stress-test screenshot. 541/541 full suite passes. See
  `.viepilot/phases/04-post-beta-polish/tasks/task-4.2b.md`.
- [x] **Video Studio** (`/step5`) — ✅ DONE (2026-09-16), implemented by Codex,
  accepted by PM per AR-06. Shell + real 3-track timeline (Script read-only reference;
  Voice honestly labeled "Synced" since audio already exists at this stage; Music shows
  the real background-music filename) built from a new `Api.getScript()` call
  correlated to the audio job's real per-line timestamps. Read-only inspector shows
  real `M:SS – M:SS` measured timing (no playback — a disclosed, considered scope cut).
  A `/script`-fetch failure degrades gracefully rather than blocking the core
  avatar/template/generate workflow. 4 new Playwright tests. Zero real defects found on
  PM review — proactively avoided Task 4.2b's Music-lane bug and included the
  pre-authorized `test_step_nav_browser.py` extension. 544/544 full suite passes. See
  `.viepilot/phases/04-post-beta-polish/tasks/task-4.2c.md`.
- [x] **Thumbnail Generator** (`/step6`) — shell, no timeline — ✅ DONE (2026-09-16),
  implemented by Codex, accepted by PM per AR-06. One difference from prior sub-tasks:
  this page already had a real write-path editor (headline + palette, debounced
  autosave, 409 conflict handling) for the selected variant — the inspector hosts this
  real editor as-is, not a new read-only view, since it already existed. Every existing
  element id preserved. 2 new browser tests. Zero real defects found on PM review —
  independently re-verified including its own screenshots in both themes. 560/560 full
  suite passes. See `tasks/task-4.2d.md`.
- [x] **YouTube Package** (`/step7`) — shell, no timeline — ✅ DONE (2026-09-16),
  implemented by Codex, accepted by PM per AR-06. Real design question different from
  prior sub-tasks: this page has no per-item selection concept, so the inspector hosts
  the "Full Package Export" readiness panel (real dynamic state) rather than an item
  detail view. A real consequence of the relocation (a previously-invisible "Checking
  export readiness…" placeholder would become visible and misleading) was caught at
  plan review and fixed with an honest static default, zero new JS logic. 2 new
  browser tests. Zero real defects found on PM review. 562/562 full suite passes. See
  `tasks/task-4.2e.md`.
- [x] **Music Library** (`/music`) — ✅ CLOSED (2026-09-16), no code change —
  deliberately NOT shell-based (shared utility page, not part of the 7-step pipeline,
  no `StepNav` at all — decision made 2026-09-14, re-confirmed by PM before closing:
  page still has no `pane-sidebar`/shell wiring, consistent with the decision).
- [x] **Step 1 Config** (`/step1`) — ✅ CLOSED (2026-09-16), no code change beyond
  Task 4.4's — deliberately NOT shell-based (pure form, no workspace concept; `StepNav`
  stays in `pills` variant, never `workflow` — confirmed correct, since this page was
  never meant to use the shell layout).

**Task 4.2 fully closed 2026-09-16** — 5 of 7 pages redesigned into the shell
(Learning, TTS, Video, Thumbnail, YouTube), 2 of 7 formally confirmed and closed as
intentionally out of scope (Music Library, Step1-Config). Each shell page is its own
sub-task (task cards written individually, doc-first, per the 2026-09-15 brainstorm
session's explicit pacing decision) — not one large task, per Task 2.4's precedent (2
pages needed 49 new/updated tests).

**Task 4.3 (Vietnamese UI localization) — DROPPED 2026-09-16.** Became eligible once
Task 4.2 finished, per the explicit sequencing decision in
`docs/brainstorm/session-2026-09-15.md`. At the first real planning question (how to
handle common creator-vocabulary loanwords like Video/Thumbnail/Podcast when
translating), the user decided not to pursue UI localization at all and asked to drop
the plan instead of answering it. No task card was written, no code was touched.
**Phase 4 formally closed 2026-09-16** at 3 pursued tasks (4.1, 4.2, 4.4), all done;
Task 4.3 dropped by explicit user decision, not deferred.

### 4.4 P0 navigation bug fixes — ✅ DONE (2026-09-16)

- [x] **Dashboard "Continue" button** — no-ops for `audio_generated`/`video_generated`/
  `complete` project statuses (only `draft`/`script_generated` were wired up). Fixed:
  a single `STATUS_TO_STEP` map now covers all 5 statuses
  (`draft`/`script_generated`→`/step2`, `audio_generated`→`/step4`,
  `video_generated`→`/step5`, `complete`→`/step7`).
- [x] **Config page (`/step1`) duplicate-project bug** — ignored an existing
  `project_id` in the URL and always created a new project on submit, even though
  StepNav makes Config a real reachable link from every other step. Fixed: fetches +
  prefills via `Api.getProject()` and saves via a new `Api.updateProject()`
  (the existing-but-previously-frontend-unused `PUT /api/projects/{id}` endpoint) for
  `draft` projects; renders every control disabled with a locked-configuration banner
  for any later status — no cascade/regenerate logic invented.

Found via a Codex read-only UI audit (`vp-auto` audit mode) on 2026-09-16, both bugs
independently confirmed by PM before the task was created, implemented by Codex,
accepted by PM per AR-06 with zero real defects found on review — PM independently
re-ran every verification command and ran its own disposable script + screenshot
beyond what was asked. 5 new browser tests, 2 extended. 558/558 full suite passes (up
from 555). See `.viepilot/phases/04-post-beta-polish/tasks/task-4.4.md` for the full
record. P1/P2 findings from the same audit (timeline duration not proportional,
dashboard doesn't scale past ~150 projects, accessibility gaps, EN/VI mixed copy)
logged as backlog, not part of this task — see TRACKER.md Decision Log, 2026-09-16.

---

## Phase 5 — UI Polish Backlog

**Status:** ✅ Complete | **Started:** 2026-09-16 | **Closed:** 2026-09-17

New phase, scoped in `docs/brainstorm/session-2026-09-16.md` after Phase 4 closed.
Addresses the real, still-current P1/P2 findings from the 2026-09-16 Codex UI audit
(2 of the original 9 findings turned out to already be fixed as side effects of Task
4.2d/4.2e's shell redesign — re-verified before scoping, not assumed).

### 5.1 Dashboard scale (pagination) — ✅ DONE (2026-09-17)

- [x] Client-side pagination for the Dashboard's project grid — no backend change,
  since the measured problem is unbounded DOM rendering (176 real project cards / 358
  buttons in one `innerHTML` pass, ~17,000px page height), not the data fetch itself.
  Fixed page size of 24; Prev/Next + page indicator; controls hidden for a single
  page; filter/search resets to page 1; delete clamps back automatically (the clamp
  logic lives centrally in `render()`, no special-case delete code needed). Implemented
  by Codex, accepted by PM per AR-06 with zero real defects found. 4 new browser tests
  using an isolated fixture — the pre-existing shared `MOCK_PROJECTS` and its 6
  consumers were left untouched. 566/566 full suite passes. See
  `.viepilot/phases/05-ui-polish-backlog/tasks/task-5.1.md` for the full record.

### 5.2 Timeline polish (proportional width + keyboard resizer) — ✅ DONE (2026-09-17)

- [x] Timeline clip width made proportional to real clip duration — **scope corrected
  during planning**: only Video (already had real per-line timing) and TTS (already
  fetched the audio job, just needed to store it — no new API calls for either) got
  this; Script has no timing data at any point and stayed out of scope. Formula:
  16px/second, clamped 72-240px, derived from 78 real timing samples. TTS also stores
  the job from a first `Api.generateAudio()` call, not just `Api.getAudioStatus()`, so
  widths update immediately after Generate All without a reload.
- [x] The shared shell's horizontal timeline resizer (`#resizer-top`) gets a keydown
  handler — previously had `tabindex="0"` but only the vertical sidebar/inspector
  resizers in `shell.js` handled keyboard input. Fixed once in `shell.js`, covering
  all 3 timeline pages (Script/TTS/Video) at once. Implemented by Codex, accepted by
  PM per AR-06 with zero real defects found. 569/569 full suite passes. See
  `.viepilot/phases/05-ui-polish-backlog/tasks/task-5.2.md` for the full record.

### 5.3 Small polish batch — ✅ DONE (2026-09-17)

- [x] Learning's card click targets get a semantic role/`tabindex` for keyboard users
  (stay `<div>`s with `role="button"`, not real `<button>`s, since they contain other
  interactive inline-edit children) plus a strictly-guarded keydown handler for
  `Enter`/`Space`.
- [x] Learning's inspector defaults to the first item of the active tab instead of
  starting empty — never overriding an existing selection, including on a same-tab
  reactivation.
- [x] Video's avatar section (not-yet-functional LivePortrait feature) moved into a
  native `<details>`/`<summary>`, collapsed by default — reusing the same pattern
  already used for Script's language notes. Implemented by Codex, accepted by PM per
  AR-06 with zero real defects found. 571/571 full suite passes, 0 flakes. See
  `.viepilot/phases/05-ui-polish-backlog/tasks/task-5.3.md` for the full record.

**Phase 5 fully closed 2026-09-17.** All 3 tasks done — 5.1 Dashboard pagination, 5.2
Timeline polish, 5.3 Small polish batch — all delegated to Codex per AR-06, zero real
defects found across any of the 3 PM reviews.

Task order: 5.1 (highest measured value) → 5.2 → 5.3, per the risk/value review in
`docs/brainstorm/session-2026-09-16.md`. Continuing to delegate to Codex as
Implementer per AR-06, same pattern as Phase 4.

---

## Phase 6 — Quick Wins Batch

**Status:** ✅ Complete | **Started:** 2026-09-17 | **Closed:** 2026-09-17

New phase, scoped in `docs/brainstorm/session-2026-09-17.md` after Phase 5 closed and
a user-commissioned deep-dive Gemini audit
(`C:\Users\Admin\Documents\audit_chuyensau_dailyintelenglish`) surfaced 8 findings
beyond the original Codex audit. PM independently verified 4 of them before scoping —
3 real, bundled here; 1 (YouTube chapters "always estimated") confirmed a **false
positive** and explicitly excluded (the real-measurement code path already exists and
is already correctly wired up). Deeper architectural findings from the same audit
(single-connection DB lock, unused rate-limiter constant, forward-only status
machine, inline CSS fragmentation) remain deferred, consistent with this project's
Progress-cancellation/LivePortrait precedent.

### 6.1 Theme flash + dead-end error link + range slider styling — ✅ DONE (2026-09-17)

- [x] Removed hardcoded `data-theme="dark"` from 4 pages (`music_library`,
  `step1_config`, `step6_thumbnail`, `step7_youtube`) — `theme.js` already applied
  the correct default, this just stops the pre-JS flash.
- [x] Added a real "Go to Dashboard" link to the "Missing project" error state on all
  6 pipeline pages (step2-7) via a narrowly-scoped `showMissingProjectError()`
  function per page — every other `showError()` call site verified unchanged.
- [x] Styled the TTS speed/pitch/volume range sliders with the app's accent color
  (`accent-color: var(--accent)`) instead of each browser's default appearance —
  CSS-only, no new JS state. Implemented by Codex, accepted by PM per AR-06 with
  zero real defects found. 583/583 full suite passes, 0 flakes. See
  `.viepilot/phases/06-quick-wins-batch/tasks/task-6.1.md` for the full record.

**Phase 6 fully closed 2026-09-17** — its one task (6.1) done, delegated to Codex per
AR-06, zero real defects found on PM review.

## Phase 7 — Script Edit Staleness

**Status:** ✅ Complete | **Started:** 2026-09-17 | **Closed:** 2026-09-18

Opened after user ran `/vp-audit` (2026-09-17) for deep independent re-verification of
the 4 Gemini audit findings left unscoped after Phase 6. Result: `GEMINI_RATE_LIMIT_RPM`
is not actually unused (used by 2 CLI sample scripts, not the runtime — nuanced
correction, not logged as a defect); DB single-connection lock (ENH-004) and CSS
fragmentation (ENH-005) confirmed real but left in the backlog per user decision — low
risk for a solo local-use app. BUG-013 — a project's script could be edited/regenerated
after audio/video were already generated with **zero** status guard and no invalidation
signal — confirmed real and more serious than originally described, so the user chose
to open this phase to fix it now rather than defer it.

### 7.1 Downgrade project status + surface staleness signal on script edit — ✅ DONE (2026-09-18)

- [x] Generating/regenerating a script, or manually saving edits, on a project
  already at `audio_generated`, `video_generated`, or `complete` downgrades its
  status back to `script_generated` (non-destructive — no files/records deleted) via
  a new `mark_script_changed()` internal operation that accepts no caller-supplied
  target status, so the Dashboard's existing status badge and "Continue" routing
  honestly reflect that downstream steps are stale. The public `PUT /{project_id}`
  endpoint (corrected from the task card's original "PATCH" during plan review)
  still rejects any arbitrary caller-supplied backward transition exactly as before.
  Implemented by Codex, accepted by PM per AR-06 with zero real defects found.
  596/598 full suite passes (2 known Gemini-retry flakes, confirmed non-regressive).
  See `.viepilot/phases/07-script-edit-staleness/tasks/task-7.1.md` for the full
  record.

**Phase 7 fully closed 2026-09-18** — its one task (7.1) done, delegated to Codex per
AR-06, zero real defects found on PM review.

## Phase 8 — CSS Consolidation

**Status:** ✅ Complete | **Started:** 2026-09-18 | **Closed:** 2026-09-18

Opened at the user's explicit request to continue processing ENH-004/ENH-005 and to
save time by having PM self-implement rather than delegate to Codex, a one-time
deviation from the AR-06 split for this task only. Re-investigation found ENH-004 (DB
single-connection lock) already has a deliberate, well-reasoned fix in place — a
connection-wide `asyncio.Lock` (`app/api/projects.py`) already serializes every route
precisely because there is one shared connection — so `PRAGMA journal_mode=WAL` alone
would be purely cosmetic; a real fix would need a full connection-pool redesign,
deferred per the project's standing precedent. Marked `wontfix` with reasoning
recorded, no code changed. ENH-005 (CSS fragmentation) had a real, minimal fix: the
shared stylesheet was missing a `.btn[aria-disabled="true"]` disabled-link variant,
so 3 pages had each invented their own inconsistent local override — reconciled to
one shared rule.

### 8.1 Reconcile disabled-button CSS drift (ENH-005); ENH-004 re-scoped — ✅ DONE (2026-09-18)

- [x] Extended the shared `.btn[disabled]` rule to also match
  `.btn[aria-disabled="true"]`; removed the resulting redundant local overrides in
  `music_library.html`, `step7_youtube.html`, and (partially) `step6_thumbnail.html`
  (which kept only its genuinely page-specific `button[disabled]` selector, corrected
  to the shared value); removed `step6_thumbnail.html`'s drifted `.btn-sm` padding
  override. CSS-only, no JS changed. Self-implemented and self-verified by PM
  (including a revert-and-confirm-failure check proving the new tests are
  meaningful). 601/602 full suite passes (1 known Gemini-retry flake, confirmed
  non-regressive). See
  `.viepilot/phases/08-css-consolidation/tasks/task-8.1.md` for the full record.

**Phase 8 fully closed 2026-09-18** — its one task (8.1) done, self-implemented by
PM per explicit user request, zero real defects found on PM's own independent
re-review.

## Phase 9 — Regeneration Integrity

**Status:** ✅ Complete | **Started:** 2026-09-18 | **Closed:** 2026-09-18

Opened after the user had Codex run its own independent, parallel read-only
`/vp-audit` pass alongside PM's own audit. Codex found 10 issues (0 critical, 1 high,
4 medium, 5 low); PM independently re-verified all 5 "important" ones by reading the
source directly — all 5 confirmed real, no false positives, an excellent scan. User
chose to fix the 2 most serious now: a failed audio/video regeneration attempt
destroyed the DB record of a still-valid previous success (BUG-017, real data loss),
and changing a speaker's voice settings didn't invalidate downstream project status
(BUG-016, the same bug class as BUG-013, reached via a mutation path Task 7.1's
scoping missed). 3 other findings (stale per-line audio cache, avatar filesystem/DB
rollback mismatch, ARCHITECTURE.md diagram staleness) are logged but out of scope
for this phase.

### 9.1 Preserve prior job data on regeneration failure; downgrade status on voice-settings change — ✅ DONE (2026-09-18)

- [x] A failed audio/video regeneration attempt no longer wipes a prior successful
  job's file paths/metadata — only status/error/completed_at change, the previous
  file stays downloadable (verified at the actual byte level). Editing a speaker's
  voice settings when the project is already at audio_generated/video_generated/
  complete downgrades status back to script_generated (non-destructive), sharing a
  downstream-only helper with Task 7.1's `mark_script_changed()` without affecting
  draft/script_generated projects. Implemented by Codex, accepted by PM per AR-06
  with zero real defects found. 613/615 full suite passes (2 flakes, both confirmed
  non-regressive in isolation). See
  `.viepilot/phases/09-regeneration-integrity/tasks/task-9.1.md` for the full record.

**Phase 9 fully closed 2026-09-18** — its one task (9.1) done, delegated to Codex per
AR-06, zero real defects found on PM review.

## Phase 10 — Backlog Cleanup

**Status:** ✅ Complete | **Started:** 2026-09-18 | **Closed:** 2026-09-18

Opened via `/vp-debug` at the user's request to continue fixing the remaining
backlog findings from the 2026-09-18 audits — all 6 already fully diagnosed, no new
investigation needed. Mid-phase, the user made a standing policy change: PM
self-implements directly from now on instead of delegating to Codex. Task 10.1
fixed the 2 remaining real code bugs (BUG-018, BUG-019). Task 10.2 fixed the 4 pure
documentation/metadata findings (BUG-014, BUG-015, ENH-006, ENH-007).

### 10.1 Clear stale per-line audio cache on line regenerate; stop deleting avatar files before commit is confirmed — ✅ DONE (2026-09-18)

- [x] Regenerating a single script line clears its stale `audio_cache_path`/
  `duration_seconds`. Avatar re-uploads no longer delete the previous file before
  the surrounding DB transaction's commit is confirmed to succeed — a forced commit
  failure now leaves the original avatar intact instead of orphaning it, verified
  by a real regression test (and a revert-and-confirm-failure check on it).
  Self-implemented by PM, zero real defects found on PM's own independent review.
  See `.viepilot/phases/10-backlog-cleanup/tasks/task-10.1.md` for the full record.

### 10.2 Documentation cleanup — stale task-card status fields, README, ARCHITECTURE.md — ✅ DONE (2026-09-18)

- [x] 4 Phase 2 task cards' stale `Status` fields corrected; README.md's Phase 4
  section and Phases 5-9 brought up to date; ARCHITECTURE.md's status-downgrade
  behavior documented and its WebSocket/OmniVoice/LivePortrait/Mermaid-sidecar
  inaccuracies corrected (plus the same LivePortrait inaccuracy found and fixed in
  the separate Module Dependencies diagram). Self-implemented by PM. See
  `.viepilot/phases/10-backlog-cleanup/tasks/task-10.2.md` for the full record.

**Phase 10 fully closed 2026-09-18** — both tasks done, self-implemented by PM per
the user's standing policy change, zero real defects found on PM's own review.
Every finding from both 2026-09-18 audits (Codex's parallel scan and PM's own
read-only pass) is now resolved.

## Phase 11 — Third Audit Fixes

**Status:** ✅ Complete | **Started:** 2026-09-18 | **Closed:** 2026-09-18

Opened after the user shared a third independent Codex `/vp-audit` pass (run after
Phase 10 closed). 7 findings, all independently re-verified and confirmed real by
PM — including a real miss in PM's own Phase 10 work (`delete_avatar()` had the
same root cause as BUG-019 but was incorrectly excluded from that fix) and a
plausible root cause for this project's long-documented Gemini-retry timing flake
class (a shared test fixture pattern that monkeypatched `asyncio.sleep`
process-wide instead of module-scoped).

### 11.1 Third-audit fixes — avatar delete, TTS engine contract, TTS lock-holding, global sleep-patch, docs — ✅ DONE (2026-09-18)

- [x] `delete_avatar()` no longer deletes a file before its DB reference change is
  confirmed committed (same fix pattern as BUG-019). `TTS_ENGINES` narrowed to only
  engines that actually work (`omnivoice`, `edge_tts`) — `piper`/`google`/`azure`
  removed, they were accepted as valid input but had zero synthesis
  implementation. TTS preview no longer holds the app's shared database lock
  across a live network call. 4 test files' `no_real_sleep` fixtures now patch
  their own module's local `sleep` name instead of the shared `asyncio` module —
  a plausible fix for the project's long-standing Gemini-retry flake class.
  Architecture diagram sidecars fully synced; `PROJECT-META.md` and README
  brought up to date. Self-implemented by PM, zero real defects found on PM's own
  review (including 2 revert-and-confirm-failure checks). See
  `.viepilot/phases/11-third-audit-fixes/tasks/task-11.1.md` for the full record.

**Phase 11 fully closed 2026-09-18** — its one task done, self-implemented by PM,
zero real defects found on PM's own review. Every finding from all 3 independent
audits this session (2 on 2026-09-18, this being the 3rd) is now resolved.

## Phase 13 — Local-First AI Reliability

**Status:** In progress | **Started:** 2026-09-18 | **Scope:** user-approved post-beta

Replace synchronous long-running script/learning requests with durable SQLite jobs;
centralize Ollama/Gemini provider policy; generate long scripts through validated,
resumable sections; expose refresh/cancel/fallback state in Step 2/3; and promote local
Qwen only after RTX 3060 qualification plus five real eight-minute runs and a complete
real Edge TTS → audio → ffmpeg video trial.

Execution is split into Tasks 13.0–13.10 with two immutable evidence gates. Gate A
qualifies local runtime/security/memory. Gate B decides local-primary versus
Gemini-primary/local-experimental; either decision retains durable jobs and a
configuration-only Gemini rollback path. See
`docs/implementation/phase-13-local-first-ai-reliability.md`.
