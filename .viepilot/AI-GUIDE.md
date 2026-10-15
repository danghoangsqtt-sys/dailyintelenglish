# AI-GUIDE.md — Daily Intel English Studio

## Quick Context for AI Agents

**Project:** Daily Intel English Studio  
**Type:** Local web app — AI podcast production tool  
**Stack:** Python FastAPI + HTML/JS + cloud-first AI gateway (Gemini/OpenRouter, local Ollama fallback) + Edge TTS + Remotion
**GPU:** RTX 3060 12GB (Qwen images and local Ollama, leased sequentially)

## File Map

| File | Purpose |
|------|---------|
| `.viepilot/ARCHITECTURE.md` | System design, services, API endpoints, data models |
| `.viepilot/PROJECT-CONTEXT.md` | Domain rules, CEFR system, business logic, conventions |
| `.viepilot/SYSTEM-RULES.md` | Coding standards, async rules, style guide |
| `.viepilot/ROADMAP.md` | Phase tasks with acceptance criteria |
| `.viepilot/TRACKER.md` | Current progress, decision log |
| `backend/` | FastAPI backend source (domain packages; every AI part in `backend/ai/`) |
| `frontend/` | HTML/CSS/JS pages |
| `backend/ai/prompts/` | AI prompt Jinja2 templates (cloud-first gateway, local fallback) |
| `data/` | Runtime data (audio, video, projects) |

## Context Loading Strategy

For **script generation tasks** → read:
1. `PROJECT-CONTEXT.md` (CEFR rules, genre rules, accent rules)
2. `backend/ai/prompts/script/` templates
3. `backend/content/script_service.py`

For **TTS/audio tasks** → read:
1. `ARCHITECTURE.md` (TTSService, AudioService sections)
2. `SYSTEM-RULES.md` (async and media rules)
3. `backend/ai/tts/tts_service.py`, `backend/media/audio_service.py`

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
