# AI-GUIDE.md — Daily Intel English Studio

## Quick Context for AI Agents

**Project:** Daily Intel English Studio  
**Type:** Local web app — AI podcast production tool  
**Stack:** Python FastAPI + HTML/JS + Gemini API + OmniVoice TTS + ffmpeg  
**GPU:** RTX 3060 12GB (OmniVoice, LivePortrait)  

## File Map

| File | Purpose |
|------|---------|
| `.viepilot/ARCHITECTURE.md` | System design, services, API endpoints, data models |
| `.viepilot/PROJECT-CONTEXT.md` | Domain rules, CEFR system, business logic, conventions |
| `.viepilot/SYSTEM-RULES.md` | Coding standards, async rules, style guide |
| `.viepilot/ROADMAP.md` | Phase tasks with acceptance criteria |
| `.viepilot/TRACKER.md` | Current progress, decision log |
| `app/` | FastAPI backend source |
| `frontend/` | HTML/CSS/JS pages |
| `prompts/` | Gemini prompt Jinja2 templates |
| `data/` | Runtime data (audio, video, projects) |

## Context Loading Strategy

For **script generation tasks** → read:
1. `PROJECT-CONTEXT.md` (CEFR rules, genre rules, accent rules)
2. `prompts/script/` templates
3. `app/services/script_service.py`

For **TTS/audio tasks** → read:
1. `ARCHITECTURE.md` (TTSService, AudioService sections)
2. `SYSTEM-RULES.md` (OmniVoice rules, async rules)
3. `app/services/tts_service.py`, `app/services/audio_service.py`

For **UI/frontend tasks** → read:
1. `ARCHITECTURE.md` (API endpoints)
2. `SYSTEM-RULES.md` (frontend conventions)
3. `frontend/pages/` relevant page

For **new feature tasks** → read:
1. `ROADMAP.md` (which phase/task)
2. `TRACKER.md` (current status)
3. Relevant service file

## Key Relationships

```
Project (SQLite)
  ├── config → ScriptConfig (Pydantic)
  ├── speakers[] → SpeakerConfig
  ├── script[] → ScriptLine
  ├── learning_content → LearningContent
  ├── audio → AudioJob
  ├── video → VideoJob
  ├── thumbnails[] → ThumbnailVariant
  └── youtube_package → YouTubePackage
```

## Profile

profile_id: none / not configured
