# Daily Intel English Studio

> 🎙️ AI-powered podcast production studio for English learning YouTube content

[![Python 3.11+](https://img.shields.io/badge/Python-3.11+-blue)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-latest-green)](https://fastapi.tiangolo.com)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![GPU: RTX 3060](https://img.shields.io/badge/GPU-RTX%203060-76b900)](https://nvidia.com)

## What is Daily Intel English Studio?

**Daily Intel English Studio** là công cụ sản xuất nội dung tiếng Anh hỗ trợ bởi AI dành cho content creator YouTube. Ứng dụng tự động hóa toàn bộ pipeline từ ý tưởng → kịch bản → giọng đọc → video → YouTube description.

### ✨ Key Features

#### Shipped Features (Phase 1)

| Task | Feature | Description | Status |
|------|---------|-------------|--------|
| **Task 1.2** | 📊 **Dashboard & Project Management** (`/`) | `ProjectService` full CRUD, state machine tiến trình forward-only, dashboard project cards, filter/search, delete-with-confirm | ✅ Shipped |
| **Task 1.3** | ⚙️ **Script Config Wizard** (`/step1`) | Cấu hình chủ đề, trình độ CEFR (A1–C2), thời lượng, 1–6 người nói, 10 thể loại, 10 giọng vùng miền, toggles ngôn ngữ, speaker cards | ✅ Shipped |
| **Task 1.4** | 🤖 **AI Script Generation & Inline Editor** (`/step2`) | Gemini API (`gemini-3.8-flash`) tạo kịch bản với `responseJsonSchema`, chỉnh sửa inline, per-line regenerate, autosave an toàn | ✅ Shipped |
| **Task 1.5** | 📚 **Learning Content Generation & Editor** (`/step3`) | Trích xuất từ vựng (IPA, định nghĩa song ngữ), thành ngữ, ngữ pháp, trắc nghiệm đọc hiểu với đáp án/giải thích, autosave | ✅ Shipped |
| **Task 1.8** | 🖼️ **Thumbnail Generator** (`/step6`) | 5 template Pillow, Gemini sinh headline/bảng màu, chọn template + generate 3-5 biến thể, favorite selection, chỉnh sửa thủ công headline/màu (optimistic concurrency), xuất PNG/JPG 16:9 & 9:16 | ✅ Shipped |

#### Core Foundation & In Progress

| Task | Feature | Description | Status |
|------|---------|-------------|--------|
| **Task 1.1** | 🏗️ **Project Setup & Dependencies** | FastAPI skeleton, SQLite (`aiosqlite`), kiểm tra môi trường (`scripts/check_dependencies.py`) — chưa GREEN toàn bộ (chờ `ffmpeg`/`.env`/model OmniVoice trên máy) | 🔄 In Progress |
| **Task 1.6** | 🎙️ **TTS Audio Studio** (`/step4`) | Edge TTS (10 giọng vùng miền × 3 giới tính) đã xong cho preview từng dòng; OmniVoice (GPU cục bộ) và AudioService (nối audio/ducking/chuẩn hóa LUFS) chờ `ffmpeg` | 🔄 In Progress |
| **Task 1.9** | 📋 **YouTube Package** (`/step7`) | 3 title variants + description + tags qua Gemini, chapters ước tính (chưa đo thật vì chưa có audio); export `.zip` (video+thumbnail+SRT) chờ Task 1.7 | 🔄 In Progress |
| **Task 1.10** | 🎵 **Music Library** (`/music`) | Upload/list/preview/delete nhạc nền (giới hạn 50MB, kiểm tra magic-byte, chống trùng tên) đã xong; waveform/volume leveling/chọn nhạc nền cho Step 4-5 chờ `ffmpeg` | 🔄 In Progress |

#### Planned Features (Phase 1, Task 1.7)

| Task | Feature | Description | Status |
|------|---------|-------------|--------|
| **Task 1.7** | 🎬 **Video Studio** | Xuất MP4 với phụ đề tự động (SRT/burned-in), LivePortrait lips-sync avatar — chờ `ffmpeg` | ⏳ Planned |

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

## Production Pipeline Workflow

```
1️⃣  Step 1: Script Config    → Topic, CEFR level, duration, speakers, genre, accent (Shipped - Task 1.3)
2️⃣  Step 2: AI Script        → Generate, preview, inline edit, per-line regenerate (Shipped - Task 1.4)
3️⃣  Step 3: Learning Content → Vocabulary, idioms, grammar, comprehension quiz (Shipped - Task 1.5)
4️⃣  Step 4: TTS Audio Studio → Voice preview (Edge TTS shipped); full mix + normalization pending ffmpeg (In Progress - Task 1.6)
5️⃣  Step 5: Video Studio     → Background, burned-in subtitles/SRT, LivePortrait lips-sync (Planned - Task 1.7)
6️⃣  Step 6: Thumbnail        → AI-assisted templates, A/B variants, manual editor, export (Shipped - Task 1.8)
7️⃣  Step 7: YouTube Package  → Titles/description/tags (shipped); zip export pending Task 1.7 (In Progress - Task 1.9)
```
Music Library (Task 1.10, `/music`) is a standalone background-music management feature, not a numbered pipeline step — upload/list/preview/delete shipped, mixing features pending ffmpeg.

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
