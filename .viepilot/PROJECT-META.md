# PROJECT-META.md — Daily Intel English Studio

## Project Information

| Field | Value |
|-------|-------|
| **Project Name** | Daily Beyond English Studio (brand since Phase 27; technical name Daily Intel English Studio) |
| **Slug** | DailyIntelEnglish |
| **Version** | 1.3.0 (released 2026-10-13, project close-out; 1.2.0-beta 2026-10-05) |
| **Inception Year** | 2026 |
| **License** | MIT |
| **Type** | AI-powered Local Web Application |
| **Status** | Active Development |

## Description

Daily Beyond English Studio là một ứng dụng web local (chạy trên máy tính cá nhân) dành cho content creator muốn sản xuất video podcast tiếng Anh cho YouTube — tất cả trong một quy trình 7 bước liền mạch. Stack hiện tại (2026-10-12):

- **AI:** gateway cloud-first (Gemini 3.1 Flash-Lite → OpenRouter free → Ollama `qwen3.5:9b` local fallback) cho kịch bản, nội dung học, storyboard, thumbnail và gói YouTube.
- **TTS:** Edge TTS là engine duy nhất (D56); OmniVoice, Kokoro, StyleTTS 2 đã thử và bỏ.
- **Audio:** pydub + ffmpeg + pyloudnorm, nhạc nền thông minh từ Music Library.
- **Video:** Remotion (`renderer/`, mặc định "Enhanced") với ffmpeg làm fallback "Standard".
- **Hình ảnh:** thư viện nhân vật/bối cảnh/shot/sprite/activity; sinh ảnh local trên GPU bằng diffusers + RealVisXL V5.0 trong `.venv-image`.

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
Daily_Intel_English/       # Phase 38 layout (D115) -- map: docs/structure/STRUCTURE.md
├── backend/               # FastAPI package (main.py, desktop_launcher.py)
│   ├── api/ core/ db/     # routes; config, paths, settings; SQLite + migrations
│   ├── schemas/           # Pydantic models
│   ├── ai/                # llm/, image/, tts/, prompts/, models/ (weights, gitignored)
│   ├── content/           # projects, scripts, learning, YouTube, Shorts
│   ├── media/             # audio, music, video (Remotion bridge), thumbnails, brand
│   ├── library/           # characters, scenes, shots, sprites, activities, storyboard
│   └── channel/           # channel plan, dashboard
├── frontend/              # pages/ + static/
├── renderer/              # Remotion (React/TypeScript) video renderer
├── scripts/               # maintenance CLIs and benchmarks
├── tests/                 # pytest suite
├── docs/                  # user/, operations/, implementation/, report/, structure/
├── data/                  # runtime data (gitignored)
└── .venv/ .venv-image/    # Python environments (gitignored)
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
