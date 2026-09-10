# TRACKER.md — Daily Intel English Studio

## Current Status

**Phase:** 1 — Full Feature Build  
**Day:** 1 / 21  
**Started:** 2026-09-10  
**Target:** 2026-09-30  

## Progress Overview

| Phase | Status | Tasks Done | Tasks Total |
|-------|--------|-----------|-------------|
| Phase 1 — Build | 🔄 In Progress | 0 | 40 |
| Phase 2 — Testing | ⏳ Not Started | 0 | 10 |
| Phase 3 — Review | ⏳ Not Started | 0 | 6 |

## Phase 1 Task Status

### 1.1 Project Setup
- [ ] Python environment
- [ ] Directory structure
- [ ] FastAPI skeleton
- [ ] SQLite setup
- [ ] Dependency check script

### 1.2 Dashboard
- [ ] ProjectService CRUD
- [ ] Dashboard UI

### 1.3 Script Config Wizard
- [ ] Config API route
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

## Known Issues

*None yet — project just started*

## Version

- App version: 0.1.0
- crystallize_version: 0.8.0
- crystallized_at: 2026-09-10T07:55:00+07:00
