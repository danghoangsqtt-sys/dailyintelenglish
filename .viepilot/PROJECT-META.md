# PROJECT-META.md — Daily Intel English Studio

## Project Information

| Field | Value |
|-------|-------|
| **Project Name** | Daily Beyond English Studio (brand since Phase 27; technical name Daily Intel English Studio) |
| **Slug** | DailyIntelEnglish |
| **Version** | 1.7.0 (2026-10-23, tag v1.7.0; audience setting; Full and Lite packages, hand-over by USB/Drive); 1.6.0 (2026-10-22, Lite edition); 1.5.0 (2026-10-22); previous 1.4.0-rc.1 trial (2026-10-15), 1.3.0 stable (2026-10-13) |
| **Next Feature Target** | 1.5.0 unreleased (2026-10-16): Phase48 and49.1–49.9 technically verified;49.10 code/package verified, real owner art/V49 pending. Published1.4.0-rc.1 predates these additions. Phase51 tracks the separate local Desktop update and build identity; SPEC.md / PLAN.md / PHASE-STATE control progress |
| **Inception Year** | 2026 |
| **License** | MIT |
| **Type** | AI-powered Local Web Application |
| **Status** | Active Development |

## Description

Daily Beyond English Studio là một ứng dụng web local (chạy trên máy tính cá nhân) dành cho content creator muốn sản xuất video podcast tiếng Anh cho YouTube — tất cả trong một quy trình 7 bước liền mạch. Stack hiện tại (2026-10-15):

- **AI:** gateway cloud-first (Gemini 3.1 Flash-Lite → OpenRouter free → Ollama `qwen3.5:9b` local fallback) cho kịch bản, nội dung học, storyboard, thumbnail và gói YouTube.
- **TTS:** Edge TTS là engine duy nhất (D56); OmniVoice, Kokoro, StyleTTS 2 đã thử và bỏ.
- **Audio:** pydub + ffmpeg + pyloudnorm, nhạc nền thông minh từ Music Library.
- **Video:** Remotion (`renderer/`) dựng video ngang, video dọc và Shorts với ba chế độ: nhân vật nói chuyện, một bối cảnh tĩnh, màn hình đen. ffmpeg dùng cho âm thanh và kiểm tra media.
- **Hình ảnh:** thư viện profile nhân vật, sprite, bối cảnh và Activity Library; Qwen-Image-2.1-Turbo tạo ảnh minh họa/bối cảnh, Qwen-Image-Edit-2511 tạo thumbnail AI scene trong `.venv-image`. SDXL và thư viện shot hai người đã được gỡ ở Phase 44.

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
│   ├── library/           # characters, scenes, sprites, activities, storyboard
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
