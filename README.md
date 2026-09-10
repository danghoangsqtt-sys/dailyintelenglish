# Daily Intel English Studio

> ðŸŽ™ï¸ AI-powered podcast production studio for English learning YouTube content

[![Python 3.11+](https://img.shields.io/badge/Python-3.11+-blue)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-latest-green)](https://fastapi.tiangolo.com)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![GPU: RTX 3060](https://img.shields.io/badge/GPU-RTX%203060-76b900)](https://nvidia.com)

## What is Daily Intel English Studio?

**Daily Intel English Studio** lÃ  cÃ´ng cá»¥ sáº£n xuáº¥t ná»™i dung tiáº¿ng Anh há»— trá»£ bá»Ÿi AI dÃ nh cho content creator YouTube. á»¨ng dá»¥ng tá»± Ä‘á»™ng hÃ³a toÃ n bá»™ pipeline tá»« Ã½ tÆ°á»Ÿng â†’ ká»‹ch báº£n â†’ giá»ng Ä‘á»c â†’ video â†’ YouTube description.

### âœ¨ Key Features

| Feature | Description |
|---------|-------------|
| ðŸ¤– **AI Script Generation** | Gemini API táº¡o ká»‹ch báº£n chuáº©n CEFR (A1-C2), 10 thá»ƒ loáº¡i, 10 giá»ng vÃ¹ng miá»n |
| ðŸŽ™ï¸ **Multi-voice TTS** | OmniVoice (local GPU) + Edge TTS, 2-6 ngÆ°á»i nÃ³i, voice design |
| ðŸ“š **Learning Content** | Auto-generate vocabulary, idioms, grammar notes, comprehension questions |
| ðŸŽ¬ **Video Export** | MP4 vá»›i subtitle, avatar lips-sync (LivePortrait), background templates |
| ðŸ–¼ï¸ **Thumbnail Generator** | Template + AI fill + manual editor, A/B variants |
| ðŸ“‹ **YouTube Package** | Complete description, chapters, tags, full transcript |
| ðŸŽµ **Music Library** | User-managed copyright-safe background music |

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
# Edit .env â€” add your GEMINI_API_KEY

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
1ï¸âƒ£  Dashboard        â†’ Create new project
2ï¸âƒ£  Script Config    â†’ Topic, CEFR level, duration, speakers, genre, accent
3ï¸âƒ£  AI Script        â†’ Generate, preview, inline edit
4ï¸âƒ£  Learning Content â†’ Vocabulary, idioms, grammar, comprehension questions
5ï¸âƒ£  TTS Audio Studio â†’ Voice assignment, preview, mix, music library
6ï¸âƒ£  Video Studio     â†’ Background/avatar, subtitle, export MP4
7ï¸âƒ£  YouTube Package  â†’ Description, chapters, tags, full transcript
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
â”œâ”€â”€ app/                    # FastAPI backend
â”œâ”€â”€ frontend/               # HTML/CSS/JS pages
â”œâ”€â”€ data/                   # Runtime data (gitignored)
â”œâ”€â”€ prompts/                # Gemini prompt templates
â”œâ”€â”€ models/                 # Local AI models
â”œâ”€â”€ scripts/                # Setup utilities
â”œâ”€â”€ tests/                  # Test suite
â”œâ”€â”€ .viepilot/              # Project architecture docs
â””â”€â”€ docs/                   # User documentation
```

## License

MIT License â€” see [LICENSE](LICENSE)

---

*Built with ViePilot | Crystallized: 2026-09-10*

