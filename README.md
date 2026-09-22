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
| **Task 1.1** | 🏗️ **Project Setup & Dependencies** | FastAPI skeleton, SQLite (`aiosqlite`), `scripts/check_dependencies.py` báo GREEN toàn bộ (Python, ffmpeg, GPU, Gemini key, OmniVoice model, thư mục data) | ✅ Shipped |
| **Task 1.6** | 🎙️ **TTS Audio Studio** (`/step4`) | Edge TTS (10 giọng vùng miền × 3 giới tính) cho preview từng dòng; `AudioService` nối audio + ducking + chuẩn hóa loudness thật (-16 LUFS, ITU-R BS.1770); phân giọng/tốc độ/cao độ/âm lượng theo speaker, chọn nhạc nền, "Generate All" + xuất MP3/WAV | ✅ Shipped |
| **Task 1.9** | 📋 **YouTube Package** (`/step7`) | 3 title variants + description + tags qua Gemini; chapters **đo thật** từ audio khi đã có (hoặc ước tính nếu chưa); export `.zip` đầy đủ (video + thumbnail + SRT + metadata.txt + transcript/từ vựng/ngữ pháp nếu đã tạo Learning Content) | ✅ Shipped |
| **Task 1.7** | 🎬 **Video Studio** (`/step5`) | `VideoService` xuất MP4 thật từ audio mix + 1 trong 3 background template + phụ đề burned-in (ffmpeg/libass) từ timestamp thật; chọn template, xem trước, tải MP4/SRT. LivePortrait lips-sync avatar chưa có (cần ảnh avatar per-speaker, chưa có tính năng upload/tạo ảnh) | ✅ Shipped |
| **Task 1.10** | 🎵 **Music Library** (`/music`) | Upload/list/preview/delete nhạc nền (giới hạn 50MB, kiểm tra magic-byte, chống trùng tên); volume leveling + chọn nhạc nền cho Step 4 (qua Task 1.6); waveform visualization thật (Web Audio API, click-to-seek) | ✅ Shipped |

All 10 Phase 1 major tasks are now shipped. Two follow-up product decisions were made
2026-09-13: real OmniVoice GPU voice cloning will not be pursued (Edge TTS is the sole
official TTS engine — OmniVoice's real API turned out to be voice *cloning* from a
reference sample, not the text-described voice design first planned); Level 3
LivePortrait avatar lip-sync stays deferred as a separate future research effort, but its
avatar-upload groundwork (user supplies their own image per speaker) is in scope now.

#### Testing & Polish (Phase 2) — ✅ Done 2026-09-14

| Task | Feature | Status |
|------|---------|--------|
| **Task 2.1** | 🔍 **Quality Testing** — CEFR accuracy across 18 real generated samples (14 PASS / 4 BORDERLINE, a genre-specific calibration note, 0 FLAG), real technical measurement of multi-accent TTS (20/20), audio loudness, and video/subtitle sync | ✅ Done |
| **Task 2.2** | 🐛 **Bug Fixes & Performance** — moved 4 blocking calls off the event loop; progress cancellation deliberately deferred as a separate architectural task | ✅ Done (buildable scope) |
| **Task 2.3** | ✨ **UX Polish** — step progress/breadcrumbs, `Ctrl+Enter` shortcuts, error toasts, responsive layout (1024px+), auto-save indicator, across all 7 step pages | ✅ Done |
| **Task 2.4** | 🎨 **UI Redesign Slice 1** — light, high-contrast Dashboard launcher; CapCut-style resizable Script workspace (`/step2`) with a line inspector and 3-track timeline; light-by-default theme | ✅ Done |
| **Task 2.5** | 🔧 **Fix Task 2.1's findings** — background-music loudness now stays within tolerance, real 9:16 vertical video export added, Scottish/British voice overlap disclosed in-UI | ✅ Done |
| **Task 2.6** | 🧹 **Post-audit fixes** — doc drift, an orphaned vertical-video file on regenerate, and an unsafe HTML-attribute escaping bug | ✅ Done |

532/533 automated tests pass (1 pre-existing, tracked timing flake — always passes in
isolation). See `.viepilot/TRACKER.md` for the full evidence trail.

#### Review & Documentation (Phase 3) — ✅ Done 2026-09-15

| Task | Feature | Status |
|------|---------|--------|
| **Task 3.1** | 📖 **Documentation** — README, [Prompt Engineering Guide](docs/prompt-guide.md), [TTS Setup Guide](docs/tts-setup.md), auto-generated [API Reference](docs/api.md) | ✅ Done |
| **Task 3.2** | 🎬 **Demo & Review** — [3 sample episodes](docs/samples/) (A1/B1/C1, real script+audio), a real [223.9s end-to-end demo recording](docs/demo-video.md), and a [product review report](docs/product-review.md) | ✅ Done |
| **Task 3.3** | 🧹 **Final Cleanup** — removed 5 dead `Settings` fields and synced `.env.example`; `print()`/`logging` and pinned `requirements.txt` already satisfied | ✅ Done |

All 3 planned phases (Full Feature Build, Testing & Polish, Review & Documentation) are
complete as of Day 6 of a 21-day target. Tagged `v1.0.0-beta`.

#### Post-v1.0.0-beta Polish (Phase 4) — ✅ Done 2026-09-16

New scope beyond the original 3-phase plan, scoped in the
[2026-09-15 brainstorm session](docs/brainstorm/session-2026-09-15.md) after v1.0.0-beta
shipped.

| Task | Feature | Status |
|------|---------|--------|
| **Task 4.1** | 🎯 **CEFR `news`-genre prompt tuning** — targeted the 3 patterns Task 2.1b flagged as BORDERLINE; honest result was a partial, mixed improvement, not a full fix | ✅ Done |
| **Task 4.2** | 🎨 **UI Redesign Slice 2** — CapCut-style shell for the 7 remaining pages; 5/7 redesigned (Learning, TTS, Video, Thumbnail, YouTube Package), 2/7 (Music Library, Step1-Config) confirmed and closed as deliberately not shell-based | ✅ Done (5/7 redesigned, 2/7 closed as out of scope) |
| **Task 4.4** | 🐛 **P0 navigation bug fixes** — Dashboard "Continue" silently no-op'd for 3 of 5 project statuses; Config page silently duplicated a project instead of resuming it — both found by a Codex UI audit, fixed and verified | ✅ Done |

Task 4.3 (Vietnamese UI localization) was scoped but **dropped by explicit user
decision** before any code was written — see `.viepilot/TRACKER.md`. Progress
cancellation and real LivePortrait lip-sync remain deliberately deferred.

#### Post-Beta Bug Fixes, Polish & New Features (Phases 5-12) — ✅ Done 2026-09-18

8 more phases beyond the original plan — most scoped from an independent audit
(including multiple separate AI-assisted read-only `/vp-audit` passes), the last
two (Phase 12) from a direct user feature request. Each closed with zero real
defects found on PM review. Full evidence trail in `.viepilot/ROADMAP.md` and
`.viepilot/TRACKER.md`.

| Phase | Feature | Status |
|-------|---------|--------|
| **Phase 5** | 📊 **UI Polish Backlog** — client-side Dashboard pagination (176 project cards were rendering unbounded), proportional TTS/Video timeline clip widths, small accessibility/UX fixes | ✅ Done |
| **Phase 6** | ✨ **Quick Wins Batch** — fixed a pre-JS-paint dark-theme flash on 4 pages, added a real "Go to Dashboard" link to a dead-end error state on 6 pages, styled TTS range sliders with the app's accent color | ✅ Done |
| **Phase 7** | 🔒 **Script Edit Staleness** — editing a script after its audio/video were already generated silently left the project marked "complete"; now correctly downgrades status to signal the downstream steps need regenerating | ✅ Done |
| **Phase 8** | 🎨 **CSS Consolidation** — reconciled a disabled-button styling drift across 3 pages back to one shared rule | ✅ Done |
| **Phase 9** | 🔁 **Regeneration Integrity** — a failed audio/video regeneration attempt used to wipe the database's record of a still-valid previous success; changing a speaker's voice settings now also correctly signals stale downstream audio/video | ✅ Done |
| **Phase 10** | 🧹 **Backlog Cleanup** — the same regeneration-integrity fix as Phase 9 also applied to deleting an avatar; stale per-line TTS cache clearing; an honest `/api/tts/engines` contract (removed 3 engine choices that were accepted but never actually implemented); no more holding the app's shared database lock across a live TTS network call; documentation cleanup | ✅ Done |
| **Phase 11** | 🔍 **Third Audit Fixes** — the same avatar-file bug found in Phase 10 was still present in avatar *delete* (not just upload); root-caused and fixed the project's long-standing "Gemini-retry" test flake class (a shared fixture was patching a process-wide `asyncio.sleep` instead of a module-local one); TTS preview no longer holds the app's write lock across a live synthesis call; corrected a self-introduced documentation inaccuracy about OmniVoice from Phase 10 | ✅ Done |
| **Phase 12** | ⚙️ **Settings & Packaging** — a Settings page to enter the Gemini API key in-app instead of hand-editing `.env` (database-backed, live-applied, never displays the full key once saved); a standalone Windows `.exe` build via PyInstaller so trying the app doesn't need a manual `venv` setup | ✅ Done |

## Quick Start

### Requirements

- Python 3.11+
- NVIDIA GPU (recommended: RTX 3060+ with 8GB+ VRAM)
- ffmpeg (in PATH, or set `DIE_FFMPEG_PATH` to its absolute exe path — e.g. on Windows if it was installed via `winget` and the shell's PATH hasn't picked it up yet)
- **[Ollama](https://ollama.com/download)**, running, with the `qwen3.5:9b` model pulled
  (`ollama pull qwen3.5:9b`) — the app is **local-only** as of Phase 14 (see
  [docs/operations/local-ai.md](docs/operations/local-ai.md)); it still *starts*
  without Ollama, but AI generation needs it running
- ~~Google Gemini API key~~ not needed for normal use — Gemini is dormant (unsupported
  rollback path, see [Tech Stack](#tech-stack) below)

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
# Defaults are already local-only (DIE_AI_MODE=local) -- no key needed for normal use.
# (All application settings use the DIE_ prefix, e.g. DIE_OLLAMA_MODEL)

# 5. Check dependencies (verifies Ollama is running and the model is pulled)
python scripts/check_dependencies.py

# 6. Run the app
uvicorn app.main:app --reload --port 8000
```

### Open the app

```
http://localhost:8000
```

### Packaging as a standalone `.exe` (Windows)

For trying the app without a manual `venv`/`pip install` setup, it can be built
into a self-contained folder with `PowerShell -File scripts\build_exe.ps1` (installs
`pyinstaller` if missing, then builds `daily_intel_english_studio.spec`) — if your
system's PowerShell execution policy blocks running the script
(`UnauthorizedAccess`/"running scripts is disabled on this system"), run
`PowerShell -ExecutionPolicy Bypass -File scripts\build_exe.ps1` instead. The result
lands in `dist\DailyIntelEnglishStudio\` — double-click `DailyIntelEnglishStudio.exe`
there; it opens your browser to the app automatically once the server is ready, and
launching it again while it's already running just reopens the browser instead of
starting a second instance.

The packaged app stores its database and generated files under
`%LOCALAPPDATA%\DailyIntelEnglishStudio\data` (not next to the exe — that folder
isn't guaranteed writable depending on where it's installed). It is local-only
(Ollama, `qwen3.5:9b`) by default — see Requirements above; it still starts and lets
you use every non-AI feature without Ollama running, showing install/pull guidance on
the AI screens instead.

**Rollback (unsupported):** Gemini stays in the codebase, dormant. Re-enabling it is
an explicit configuration change, never a migration: set `DIE_AI_ALLOW_CLOUD=true` and
`DIE_AI_MODE=hybrid` (or `gemini`) in `.env`, and provide a key via the in-app
**Settings** page (⚙️ on the dashboard) or `DIE_GEMINI_API_KEY`.

**Not bundled**: ffmpeg and the OmniVoice model directory still need to be present
on the machine exactly as for the source install (see Requirements above) —
bundling a real ffmpeg binary was left out of scope (licensing + ~80MB size), and
OmniVoice has no real GPU inference implementation to bundle in the first place
(see the TTSService note further down). `scripts/check_dependencies.py` and the
in-app `/health` status still report ffmpeg's presence honestly either way.

## Production Pipeline Workflow

```
1️⃣  Step 1: Script Config    → Topic, CEFR level, duration, speakers, genre, accent (Shipped - Task 1.3)
2️⃣  Step 2: AI Script        → Generate, preview, inline edit, per-line regenerate (Shipped - Task 1.4)
3️⃣  Step 3: Learning Content → Vocabulary, idioms, grammar, comprehension quiz (Shipped - Task 1.5)
4️⃣  Step 4: TTS Audio Studio → Voice assignment, per-line preview, real audio mix + loudness normalization, MP3/WAV export (Shipped - Task 1.6)
5️⃣  Step 5: Video Studio     → Template selector, real MP4 with burned-in subtitles/SRT, 16:9 + 9:16 export, per-speaker avatar upload, preview + downloads (Shipped - Task 1.7/2.5b); LivePortrait lips-sync inference itself remains a deferred, not-yet-started effort
6️⃣  Step 6: Thumbnail        → AI-assisted templates, A/B variants, manual editor, export (Shipped - Task 1.8)
7️⃣  Step 7: YouTube Package  → Titles/description/tags/chapters (measured once audio exists) + full .zip export (Shipped - Task 1.9)
```
Music Library (Task 1.10, `/music`) is a standalone background-music management feature, not a numbered pipeline step — upload/list/preview/delete, volume leveling, Step 4 background-track selection, and waveform visualization are all shipped.

## Tech Stack

- **Backend**: Python 3.11+ / FastAPI / Uvicorn / aiosqlite
- **Frontend**: Vanilla HTML5 / CSS3 / JavaScript
- **AI**: Local Ollama (`qwen3.5:9b`) with strict structured JSON schema — the only
  supported path as of Phase 14 (see
  [docs/architecture/adr-001-local-first-ai.md](docs/architecture/adr-001-local-first-ai.md)).
  Google Gemini API (`gemini-3.8-flash`) remains in the codebase, dormant, as an
  unsupported rollback (`DIE_AI_ALLOW_CLOUD=true`) — never re-enabled by default.
- **TTS**: Edge TTS (sole engine — OmniVoice GPU cloning considered, dropped 2026-09-13; see [docs/tts-setup.md](docs/tts-setup.md))
- **Audio**: pydub + ffmpeg (real ITU-R BS.1770 loudness normalization via `pyloudnorm`)
- **Video**: ffmpeg (background templates + burned-in subtitles, 16:9 and 9:16 export). LivePortrait lip-sync avatar remains a deferred, not-yet-started research effort
- **Thumbnail**: Pillow + AI (local Ollama by default) text/palette suggestions
- **Database**: SQLite (aiosqlite async transactions)

## Documentation

| Doc | Purpose |
|-----|---------|
| [docs/prompt-guide.md](docs/prompt-guide.md) | How to customize the AI prompt templates (script genres, CEFR blocks, learning content, thumbnails, YouTube package) — shared by Ollama (default) and the dormant Gemini path |
| [docs/tts-setup.md](docs/tts-setup.md) | Edge TTS voice map and known limitations; why OmniVoice was investigated but not integrated |
| [docs/api.md](docs/api.md) | Full API reference, auto-generated from the app's real FastAPI OpenAPI schema (`scripts/generate_api_docs.py`) — also live at `/docs` while the app is running |
| [.viepilot/ARCHITECTURE.md](.viepilot/ARCHITECTURE.md) | System design, services, data models |
| [.viepilot/ROADMAP.md](.viepilot/ROADMAP.md) | Phase/task plan with acceptance criteria |
| [.viepilot/TRACKER.md](.viepilot/TRACKER.md) | Full progress and decision log |

## Project Structure

```
Daily_Intel_English/
├── app/                    # FastAPI backend
├── frontend/               # HTML/CSS/JS pages
├── data/                   # Runtime data (gitignored)
├── prompts/                # AI prompt templates (Ollama default, Gemini dormant)
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
