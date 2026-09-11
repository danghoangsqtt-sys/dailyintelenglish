# Daily Intel English Studio

> 🎙️ AI-powered podcast production studio for English learning YouTube content

[![Python 3.11+](https://img.shields.io/badge/Python-3.11+-blue)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-latest-green)](https://fastapi.tiangolo.com)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![GPU: RTX 3060](https://img.shields.io/badge/GPU-RTX%203060-76b900)](https://nvidia.com)

## What is Daily Intel English Studio?

**Daily Intel English Studio** là công cụ sản xuất nội dung tiếng Anh hỗ trợ bởi AI dành cho content creator YouTube. Ứng dụng tự động hóa toàn bộ pipeline từ ý tưởng → kịch bản → giọng đọc → video → YouTube description.

### ✨ Key Features

#### Shipped / Implemented (Phase 1, Tasks 1.1–1.5)

| Feature | Description | Status |
|---------|-------------|--------|
| 📊 **Dashboard & Project Management** | Quản lý dự án podcast, trạng thái pipeline forward-only, lưu trữ SQLite bất đồng bộ (`aiosqlite`) | ✅ Shipped (Task 1.1–1.2) |
| ⚙️ **Script Config Wizard** | Cấu hình chủ đề, trình độ CEFR (A1–C2), thời lượng, 1–6 người nói, 10 thể loại, 10 giọng vùng miền, toggles tính năng ngôn ngữ | ✅ Shipped (Task 1.3) |
| 🤖 **AI Script Generation & Inline Editor** | Gemini API (`gemini-3.8-flash`) tạo kịch bản chuẩn CEFR với JSON Schema validation, chỉnh sửa inline, re-generate từng câu, coalesced autosave | ✅ Shipped (Task 1.4) |
| 📚 **Learning Content Generation & Editor** | Tự động trích xuất từ vựng (IPA, định nghĩa song ngữ Anh-Việt), thành ngữ, cấu trúc ngữ pháp, trắc nghiệm đọc hiểu kèm đáp án và giải thích | ✅ Shipped (Task 1.5) |

#### Planned / In Development (Phase 1, Tasks 1.6–1.10)

| Feature | Description | Status |
|---------|-------------|--------|
| 🎙️ **Multi-voice TTS Studio** | OmniVoice (GPU cục bộ RTX 3060) + Edge TTS (dự phòng đám mây miễn phí) + Piper TTS, phân vai giọng đọc | ⏳ Planned (Task 1.6) |
| 🎵 **Audio Mixing & Music Library** | Nối audio, chèn nhạc nền bản quyền an toàn, ducking âm lượng, chuẩn hóa âm thanh | ⏳ Planned (Task 1.7) |
| 🎬 **Video Studio** | Xuất MP4 với phụ đề tự động (SRT/burned-in), LivePortrait lips-sync avatar theo từng nhân vật | ⏳ Planned (Task 1.8) |
| 🖼️ **Thumbnail Generator** | Template + AI gợi ý nội dung + Pillow editor, xuất biến thể A/B (16:9 & 9:16 Shorts) | ⏳ Planned (Task 1.9) |
| 📋 **YouTube Package** | Sinh trọn bộ YouTube metadata: tiêu đề, mô tả chuẩn SEO, timestamps/chapters, tags, transcript | ⏳ Planned (Task 1.10) |

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
# Edit .env — set your DIE_GEMINI_API_KEY
# (All application settings use the DIE_ prefix, e.g. DIE_GEMINI_API_KEY)

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
1️⃣  Dashboard        → Create new project (Implemented)
2️⃣  Script Config    → Topic, CEFR level, duration, speakers, genre, accent (Implemented)
3️⃣  AI Script        → Generate, preview, inline edit, per-line regenerate (Implemented)
4️⃣  Learning Content → Vocabulary, idioms, grammar, comprehension questions (Implemented)
5️⃣  TTS Audio Studio → Voice assignment, preview, mix, music library (Planned)
6️⃣  Video Studio     → Background/avatar, subtitle, export MP4 (Planned)
7️⃣  YouTube Package  → Description, chapters, tags, full transcript (Planned)
```

## Tech Stack

- **Backend**: Python 3.11+ / FastAPI / Uvicorn / aiosqlite
- **Frontend**: Vanilla HTML5 / CSS3 / JavaScript
- **AI**: Google Gemini API (`gemini-3.8-flash`) with strict structured JSON schema
- **TTS**: OmniVoice (local GPU) + Edge TTS + Piper TTS
- **Audio**: pydub + ffmpeg
- **Video**: ffmpeg + LivePortrait (lips-sync)
- **Thumbnail**: Pillow
- **Database**: SQLite (aiosqlite async transactions)

## Project Structure

```
Daily_Intel_English/
├── app/                    # FastAPI backend
├── frontend/               # HTML/CSS/JS pages
├── data/                   # Runtime data (gitignored)
├── prompts/                # Gemini prompt templates
├── models/                 # Local AI models
├── scripts/                # Setup utilities
├── tests/                  # Automated test suite (pytest)
├── .viepilot/              # Project architecture & governance docs
└── docs/                   # Developer & user documentation
```

## License

MIT License — see [LICENSE](LICENSE)

---

*Built with ViePilot | Crystallized: 2026-09-10*
