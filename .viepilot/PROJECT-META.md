# PROJECT-META.md — Daily Intel English Studio

## Project Information

| Field | Value |
|-------|-------|
| **Project Name** | Daily Intel English Studio |
| **Slug** | DailyIntelEnglish |
| **Version** | 1.0.0-beta |
| **Inception Year** | 2026 |
| **License** | MIT |
| **Type** | AI-powered Local Web Application |
| **Status** | Active Development |

## Description

Daily Intel English Studio là một ứng dụng web local (chạy trên máy tính cá nhân) dành cho content creator muốn sản xuất video podcast tiếng Anh cho YouTube. Ứng dụng kết hợp AI (Gemini API) để tạo kịch bản, TTS (Edge TTS — kỹ sư duy nhất thực sự chạy được; OmniVoice từng dự tính làm engine chính nhưng API thật của nó là voice cloning chứ không phải voice design như hình dung ban đầu, nên không được triển khai) để tạo giọng đọc, và công cụ chỉnh sửa audio/video để xuất bản lên YouTube — tất cả trong một quy trình 7 bước liền mạch.

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
├── prompts/               # Gemini prompt templates
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
