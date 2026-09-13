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

- [ ] **Verify ffmpeg & OmniVoice**
  - `scripts/check_dependencies.py` — check ffmpeg, OmniVoice model, GPU
  - Verify: script reports all GREEN — **not yet**: ffmpeg not on PATH, `.env`/`DIE_GEMINI_API_KEY` not set, OmniVoice model not downloaded on this machine (see TRACKER Known Issues). Script logic itself is done and tested, but the task's verify condition (all-GREEN) is not met.

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

- [ ] **TTSService — OmniVoice** (`app/services/tts_service.py`)
  - Load OmniVoice model at startup (singleton)
  - `generate_line(text, voice_description, speed, pitch)` → WAV file
  - Semaphore(2) for concurrent limit — **done**, `asyncio.Semaphore(MAX_CONCURRENT_TTS)` wraps the call site
  - VRAM overflow → auto-fallback to Edge TTS — **done and tested** (any exception from the OmniVoice path falls back, not just OOM specifically)
  - Cache: check `data/tts_cache/` before generating
  - Verify: generates speech for sample lines, cache works, fallback works — **blocked**: no OmniVoice model weights on this machine (`models/omnivoice/` empty, see Known Issues); `_synthesize_omnivoice()` honestly raises "model not loaded" rather than faking success, exercised by `test_omnivoice_synthesis_always_raises_unavailable_for_now`

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

- [ ] **VideoService — LivePortrait lips-sync** (Phase 1 primary if time allows) — deferred,
  blocked on a real user decision: no speaker has an avatar image
  (`speakers.avatar_image_path` is null for every speaker, no upload/generation feature
  exists) — same class of blocker as OmniVoice's `ref_audio` requirement
  - `generate_video_avatar(project_id, avatar_images)` — per-speaker avatar lip-sync
  - Side-by-side layout: speaker1 left, speaker2 right
  - Active speaker highlight (border glow on speaking turn)
  - Verify: lips-sync avatar video generates for 2-speaker dialogue

- [ ] **Video Studio UI** (`frontend/pages/step5_video.html`)
  - Background selector (upload image / choose from templates)
  - Avatar uploader per speaker (for lips-sync mode)
  - Subtitle style picker (font, size, color, position)
  - Mode toggle: "Background + Subtitles" vs "Avatar + Lips-sync"
  - AI prompt export: "Copy prompt to generate avatar image"
  - Progress bar + preview player
  - Download MP4 + SRT buttons
  - Verify: both modes work, downloads correct

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
  - Full transcript/vocabulary/grammar formatting inside the export: not implemented — not part of the ROADMAP acceptance criterion (video+thumbnail+SRT+metadata.txt only)
  - Verify: 30 tests (1.9a) + 13 tests (1.9b, including a real end-to-end pipeline test, not mocked); real bugs caught and fixed before landing each time (1.9a: tag whitespace on DB round-trip; 1.9b: frontend defaulting to "Measured" on an undefined flag, caught by a browser test)

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
  - Not done: waveform visualization (visual UI only — no task assigned yet)

---

## Phase 2 — Testing & Polish (Day 8–14)

### 2.1 Quality Testing

- [ ] **CEFR accuracy testing**
  - Generate 1 script per level (A1 → C2) × 3 genres = 18 test scripts
  - Manual review: vocabulary, grammar, collocation accuracy
  - Document issues → fix prompt templates

- [ ] **Multi-accent TTS testing**
  - Test OmniVoice voice design for 10 accent regions
  - Test Edge TTS voice selection per region
  - Record best voice IDs per region → `prompts/tts/voice_presets.json`

- [ ] **Audio quality testing**
  - Check mix for: silence gaps, volume consistency, music ducking
  - Test with short (30s), medium (10min), long (20min) scripts
  - Verify MP3 loudness: -16 LUFS ±1dB

- [ ] **Video testing**
  - Test subtitle sync for multiple content lengths
  - Test LivePortrait with 5 different avatar images
  - Test both 16:9 and 9:16 outputs

### 2.2 Bug Fixes & Performance

- [ ] Fix any blocking API calls → move to executor
- [ ] Optimize OmniVoice batch: generate 5 lines per batch instead of sequential
- [ ] Add progress cancellation (stop mid-generation)
- [ ] Fix Gemini retry logic for 429 rate limit errors

### 2.3 UX Polish

- [ ] **Step progress indicator**: header bar shows "Step 2 of 7"
- [ ] **Breadcrumb navigation**: jump back to any previous step
- [ ] **Auto-save indicator**: "Saved" / "Saving..." in header
- [ ] **Keyboard shortcuts**: `Ctrl+Enter` to generate, `Esc` to cancel
- [ ] **Empty states**: helpful messages when no projects / no music library
- [ ] **Error toasts**: user-friendly error messages (not stack traces)
- [ ] **Responsive layout**: works at 1024px width minimum

---

## Phase 3 — Review & Documentation (Day 15–21)

### 3.1 Documentation

- [ ] **README.md** — installation guide, quick start, features overview
- [ ] **Prompt Engineering Guide** (`docs/prompt-guide.md`) — how to customize prompts
- [ ] **TTS Setup Guide** (`docs/tts-setup.md`) — OmniVoice + Edge TTS installation
- [ ] **API Reference** (`docs/api.md`) — auto-generated from FastAPI OpenAPI

### 3.2 Demo & Review

- [ ] **Demo video**: Record full workflow from project creation to YouTube package (10 min video)
- [ ] **Sample outputs**: 3 sample podcast scripts (A1, B1, C1) with audio
- [ ] **Product review report**: feature checklist, known issues, future improvements

### 3.3 Final Cleanup

- [ ] Remove all `print()` debug statements → use `logging`
- [ ] Add `.env.example` file
- [ ] Verify `requirements.txt` is complete and pinned
- [ ] Git tag: `v1.0.0-beta`

---

## Acceptance Criteria (Phase 1 Complete)

- [ ] Can create a new project with full configuration
- [ ] AI generates a grammatically correct, level-appropriate script for any genre + CEFR combination
- [ ] TTS generates audio for all speakers, mixes into single MP3/WAV
- [ ] Video exports as MP4 with synced subtitles + SRT file
- [ ] Thumbnail generates 3+ A/B variants
- [ ] YouTube package includes complete description + chapters + transcript + vocabulary
- [ ] All steps persist data (auto-save) — refresh doesn't lose progress
- [ ] Dark mode works across all pages
