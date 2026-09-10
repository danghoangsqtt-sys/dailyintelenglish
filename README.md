# Daily Intel English Studio

> 🎙️ AI-powered podcast production studio for English learning YouTube content

[![Python 3.11+](https://img.shields.io/badge/Python-3.11+-blue)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-latest-green)](https://fastapi.tiangolo.com)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![GPU: RTX 3060](https://img.shields.io/badge/GPU-RTX%203060-76b900)](https://nvidia.com)

## What is Daily Intel English Studio?

**Daily Intel English Studio** là công cụ sản xuất nội dung tiếng Anh hỗ trợ bởi AI dành cho content creator YouTube. Ứng dụng tự động hóa toàn bộ pipeline từ ý tưởng → kịch bản → giọng đọc → video → YouTube description.

### ✨ Key Features

| Feature | Description |
|---------|-------------|
| 🤖 **AI Script Generation** | Gemini API tạo kịch bản chuẩn CEFR (A1-C2), 10 thể loại, 10 giọng vùng miền |
| 🎙️ **Multi-voice TTS** | OmniVoice (local GPU) + Edge TTS, 2-6 người nói, voice design |
| 📚 **Learning Content** | Auto-generate vocabulary, idioms, grammar notes, comprehension questions |
| 🎬 **Video Export** | MP4 với subtitle, avatar lips-sync (LivePortrait), background templates |
| 🖼️ **Thumbnail Generator** | Template + AI fill + manual editor, A/B variants |
| 📋 **YouTube Package** | Complete description, chapters, tags, full transcript |
| 🎵 **Music Library** | User-managed copyright-safe background music |

## Quick Start

### Requirements

- Python 3.11+
- NVIDIA GPU (recommended: RTX 3060+ with 8GB+ VRAM)
- ffmpeg in PATH
- Google Gemini API key

### Installation

```bash
# 1. Clone / copy to your machine
cd d:\DataAdmin\Daily_Intel_English

# 2. Create virtual environment
python -m venv venv
venv\Scripts\activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Setup environment
copy .env.example .env
# Edit .env — add your GEMINI_API_KEY

# 5. Check dependencies
python scripts/check_dependencies.py

# 6. Run the app
uvicorn app.main:app --reload --port 8000
```

### Open the app

```
http://localhost:8000
```

## Workflow (7 Steps)

```
1️⃣  Dashboard        → Create new project
2️⃣  Script Config    → Topic, CEFR level, duration, speakers, genre, accent
3️⃣  AI Script        → Generate, preview, inline edit
4️⃣  Learning Content → Vocabulary, idioms, grammar, comprehension questions
5️⃣  TTS Audio Studio → Voice assignment, preview, mix, music library
6️⃣  Video Studio     → Background/avatar, subtitle, export MP4
7️⃣  YouTube Package  → Description, chapters, tags, full transcript
```

## Tech Stack

- **Backend**: Python 3.11+ / FastAPI / Uvicorn / aiosqlite
- **Frontend**: Vanilla HTML5 / CSS3 / JavaScript
- **AI**: Google Gemini API (gemini-2.0-flash)
- **TTS**: OmniVoice (local GPU) + Edge TTS + Piper TTS
- **Audio**: pydub + ffmpeg
- **Video**: ffmpeg + LivePortrait (lips-sync)
- **Thumbnail**: Pillow
- **Database**: SQLite

## Project Structure

```
Daily_Intel_English/
├── app/                    # FastAPI backend
├── frontend/               # HTML/CSS/JS pages
├── data/                   # Runtime data (gitignored)
├── prompts/                # Gemini prompt templates
├── models/                 # Local AI models
├── scripts/                # Setup utilities
├── tests/                  # Test suite
├── .viepilot/              # Project architecture docs
└── docs/                   # User documentation
```

## License

MIT License — see [LICENSE](LICENSE)

---

*Built with ViePilot | Crystallized: 2026-09-10*
