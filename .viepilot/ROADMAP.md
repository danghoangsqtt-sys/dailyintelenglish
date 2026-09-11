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
  - Semaphore(2) for concurrent limit
  - VRAM overflow → auto-fallback to Edge TTS
  - Cache: check `data/tts_cache/` before generating
  - Verify: generates speech for sample lines, cache works, fallback works

- [ ] **TTSService — Edge TTS**
  - `generate_line_edge(text, voice_name, speed)` → WAV
  - List available English accents per region
  - Verify: generates speech for all 10 accent regions

- [ ] **AudioService** (`app/services/audio_service.py`)
  - `mix_project(project_id)` → single MP3 + WAV from all lines
  - Add silence gaps between lines
  - Background music ducking (if music selected)
  - Normalize to -16 LUFS
  - Generate timestamps JSON
  - Verify: mixed audio sounds natural, timestamps accurate

- [ ] **TTS Audio Studio UI** (`frontend/pages/step4_audio.html`)
  - Speaker voice assignment panel (engine + voice per speaker)
  - "Preview" button per line → plays audio inline
  - Background music selector (from music_library folder)
  - Speed/pitch/volume sliders per speaker
  - "Generate All" button → progress bar (SSE streaming)
  - Final player with waveform visualization
  - Download MP3 / WAV buttons
  - Verify: full flow — assign voices, preview lines, generate mix, download

### 1.7 Step 5 — Video Studio

- [ ] **VideoService — Background + Subtitle** (`app/services/video_service.py`)
  - `generate_video_basic(project_id)` — audio + background image + subtitle overlay (ffmpeg)
  - SRT file generation from timestamps
  - Burned-in subtitles (ffmpeg subtitles filter)
  - Verify: MP4 generates correctly with synced subtitles

- [ ] **VideoService — LivePortrait lips-sync** (Phase 1 primary if time allows)
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

- [ ] **ThumbnailService** (`app/services/thumbnail_service.py`)
  - Load template PNG + Jinja2 text overlay config
  - Gemini fills: title text, accent color, topic keywords
  - Pillow renders 3-5 A/B variants
  - Export 1280×720 + 720×1280 versions
  - Verify: generates 3 variants, all differ meaningfully

- [ ] **Thumbnail template files** (`frontend/static/thumbnail_templates/`)
  - 5 templates: `modern_split.png`, `gradient_bold.png`, `minimal_clean.png`, `dynamic_wave.png`, `podcast_classic.png`
  - JSON config per template: text zones, color zones, font specs
  - Verify: all templates render correctly

- [ ] **Thumbnail UI** (`frontend/pages/step6_thumbnail.html`)
  - Template gallery (5 options, hover preview)
  - Generate button → 3-5 A/B variants display
  - Click to select favorite
  - In-app editor: change title text, colors, add/remove elements
  - Download selected variant (16:9 + 9:16)
  - Verify: select template, generate, edit, download — all work

### 1.9 Step 7 — YouTube Package

- [ ] **YouTubePackageService** (`app/services/youtube_service.py`)
  - `generate_package(project_id)` → full YouTube upload package
  - Description: hook + overview + chapters + CTA (Gemini generated)
  - Chapters: formatted from timestamps
  - Tags: 20 relevant tags (Gemini + CEFR + genre tags)
  - Verify: package text fits YouTube limits, chapters correct

- [ ] **YouTube Package UI** (`frontend/pages/step7_youtube.html`)
  - Collapsible sections: Description | Chapters | Tags | Full Transcript | Vocabulary | Grammar
  - "Copy to clipboard" button per section
  - "Export as .txt" for full package
  - Edit fields inline
  - Verify: all sections populated, copy works, export works

### 1.10 Music Library Management

- [ ] **Music Library UI** (`frontend/pages/music_library.html`)
  - Drag-and-drop upload to `data/music_library/`
  - List tracks with player preview
  - Delete track
  - Verify: upload, preview, delete work

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
