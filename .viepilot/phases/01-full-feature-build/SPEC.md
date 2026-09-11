# Phase 1: Full Feature Build

## Overview
Phase 1 delivers the full feature build for Daily Intel English Studio, creating an end-to-end AI podcast generation pipeline across 10 primary tasks.

- **Phase Number:** 1
- **Slug:** 01-full-feature-build
- **Timeline:** Days 1–7 (2026-09-10 to 2026-09-17)
- **Target Platform:** Local Web App (FastAPI + HTML/CSS/JS)
- **Hardware:** NVIDIA RTX 3060 12GB VRAM

## Task List & Acceptance Matrix

| Task | Title | Description | Status |
|---|---|---|---|
| 1.1 | Project Setup & Infrastructure | Python environment, FastAPI skeleton, SQLite DB, dependency check | In Progress |
| 1.2 | Dashboard & Project Management | ProjectService CRUD, atomic speaker updates, state machine, dashboard UI | In Progress |
| 1.3 | Step 1 — Script Config Wizard | Config API route, CEFR/genre/accent options, sanitized form UI | Done |
| 1.4 | Step 2 — AI Script Generation | Jinja2 templates, Gemini REST service, line regen, concurrency lock, script UI | Done |
| 1.5 | Step 3 — Learning Content | LearningContentService, vocab/idiom/grammar/quiz tabs, autosave, learning UI | Done |
| 1.6 | Step 4 — TTS Audio Studio | OmniVoice local GPU + Edge TTS backup, AudioService, TTS UI | Planned |
| 1.7 | Step 5 — Video Studio | VideoService with background + burned subtitle & SRT, LivePortrait, Video UI | Planned |
| 1.8 | Step 6 — Thumbnail Generator | ThumbnailService, Pillow templates + Gemini Vision, Thumbnail UI | Planned |
| 1.9 | Step 7 — YouTube Package | YouTubePackageService (metadata, tags, chapters), Package UI | Planned |
| 1.10 | Music Library | Background music management and audio mix integration UI | Planned |

## Subtask Breakdown (29 Total Items)
- **1.1 Setup (5 items)**: Python env (done), Directory structure (done), FastAPI skeleton (done), SQLite setup (done), Dependency check script (pending ffmpeg/env/model on local machine).
- **1.2 Dashboard (2 items)**: ProjectService CRUD (done, 30 tests), Dashboard UI (pending automated E2E test).
- **1.3 Script Config (2 items)**: Config API route (done), Script Config UI (done, Playwright verified).
- **1.4 Script Generation (4 items)**: Prompt templates (done, 101 tests), ScriptService (done), Script UI (done), Concurrency lock & FIX2/2B/2C gate (done, 166 tests).
- **1.5 Learning Content (3 items)**: Prompt templates (done), LearningContentService (done, 20 tests), Learning Content UI (done, 196 tests total).
- **1.6 TTS Audio Studio (4 items)**: TTSService OmniVoice, TTSService Edge TTS, AudioService, TTS UI.
- **1.7 Video Studio (3 items)**: VideoService Background+Subtitle, VideoService LivePortrait, Video UI.
- **1.8 Thumbnail Generator (3 items)**: ThumbnailService, 5 templates, Thumbnail UI.
- **1.9 YouTube Package (2 items)**: YouTubePackageService, YouTube Package UI.
- **1.10 Music Library (1 item)**: Music Library UI.
