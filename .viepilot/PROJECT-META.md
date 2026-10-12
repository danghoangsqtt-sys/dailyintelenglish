# PROJECT-META.md — Daily Intel English Studio

## Project Information

| Field | Value |
|-------|-------|
| **Project Name** | Daily Beyond English Studio (brand since Phase 27; technical name Daily Intel English Studio) |
| **Slug** | DailyIntelEnglish |
| **Version** | 1.2.0-beta (released 2026-10-05; Phases 22 and 25–32 unreleased) |
| **Inception Year** | 2026 |
| **License** | MIT |
| **Type** | AI-powered Local Web Application |
| **Status** | Active Development |

## Description

Daily Beyond English Studio là một ứng dụng web local (chạy trên máy tính cá nhân) dành cho content creator muốn sản xuất video podcast tiếng Anh cho YouTube — tất cả trong một quy trình 7 bước liền mạch. Stack hiện tại (2026-10-12):

- **AI:** gateway cloud-first (Gemini 3.1 Flash-Lite → OpenRouter free → Ollama `qwen3.5:9b` local fallback) cho kịch bản, nội dung học, storyboard, thumbnail và gói YouTube.
- **TTS:** Edge TTS là engine duy nhất (D56); OmniVoice, Kokoro, StyleTTS 2 đã thử và bỏ.
- **Audio:** pydub + ffmpeg + pyloudnorm, nhạc nền thông minh từ Music Library.
- **Video:** Remotion (`video-renderer/`, mặc định "Enhanced") với ffmpeg làm fallback "Standard".
- **Hình ảnh:** thư viện nhân vật/bối cảnh/shot/sprite/activity; sinh ảnh local trên GPU bằng diffusers + RealVisXL V5.0 trong `venv-image`.

## Organization

| Field | Value |
|-------|-------|
| **Owner** | Solo Developer |
| **User Scope** | Single User (localhost) |
| **Target Platform** | Windows (localhost web app) |

## Developer Info

| Field | Value |
|-------|-------|
| **GPU** | NVIDIA GeForce RTX 3060 12GB VRAM |
| **OS** | Windows |
| **Python** | 3.11+ |

## Repository

```
d:\DataAdmin\Daily_Intel_English\
```

## Package Structure

```
DailyIntelEnglish/
├── app/                    # FastAPI backend
│   ├── api/               # API routes
│   ├── services/          # Business logic
│   ├── models/            # Data models
│   └── core/              # Config, DB, utils
├── frontend/              # HTML/CSS/JS frontend
│   ├── pages/             # Page templates
│   ├── static/            # CSS, JS, assets
│   └── components/        # Reusable HTML components
├── data/                  # Local data storage
│   ├── projects/          # Project JSON files
│   ├── audio/             # Generated audio files
│   ├── video/             # Generated video files
│   ├── thumbnails/        # Generated thumbnails
│   ├── music_library/     # User's background music
│   └── tts_cache/         # TTS audio cache
├── video-renderer/        # Remotion (React/TypeScript) Enhanced video renderer
├── prompts/               # AI prompt templates (shared by every provider)
│   ├── script/            # Script generation prompts
│   └── learning/          # Learning content prompts
├── models/                # Local AI model files (OmniVoice, etc.)
├── scripts/               # Setup & utility scripts
├── .viepilot/             # ViePilot project artifacts
├── docs/                  # Documentation
└── tests/                 # Test suite
```

## File Header Template

```python
# ==============================================================================
# Daily Intel English Studio
# File: {filename}
# Description: {description}
# Author: Daily Intel English
# Created: 2026-09-10
# License: MIT
# ==============================================================================
```

## ViePilot Profile

profile_id: none / not configured
