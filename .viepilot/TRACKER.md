# TRACKER.md — Daily Intel English Studio

## Current Status

**Phase:** 1 — Full Feature Build  
**Day:** 1 / 21  
**Started:** 2026-09-10  
**Target:** 2026-09-30  

## Progress Overview

| Phase | Status | Tasks Done | Tasks Total |
|-------|--------|-----------|-------------|
| Phase 1 — Build | 🔄 In Progress | 6 | 40 |
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
- [ ] Dashboard UI — cards/search/filter/theme render, but "New Project" and "Continue" are still placeholders (Step 1 wizard not built yet) and there is no automated UI test. Not marking done.

### 1.3 Script Config Wizard
- [x] Config API route — `POST/GET/PUT/DELETE /api/projects[/{id}]`, `ScriptConfig`/`SpeakerConfig`/`ProjectUpdate` validated, invalid CEFR/genre/accent/status rejected with 422 in the standard envelope
- [ ] Script Config UI

### 1.4 AI Script Generation
- [ ] Prompt templates (10 genres × CEFR)
- [ ] ScriptService
- [ ] Script Generation UI

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
