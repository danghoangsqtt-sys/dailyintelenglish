# Daily Beyond English Studio

> 🎙️ AI-powered podcast production studio for English learning YouTube content

The product brand is **Daily Beyond English** (Phase 27). The repository, the Python package and
the packaged `DailyIntelEnglishStudio.exe` keep the original technical name *Daily Intel English*.

## Windows Desktop trial — 1.4.0-rc.1 (2026-10-15)

Open **Daily Beyond English Studio** from the Desktop icon (the channel logo). It starts the local app and opens its browser interface without a command window. The installed EXE is `dist/DailyIntelEnglishStudio/DailyIntelEnglishStudio.exe`; keep its complete folder together. The trial links to the existing repository's Node/Remotion, ffmpeg, image environment/models and `data` folder.

[Download the Windows trial](https://github.com/danghoangsqtt-sys/dailyintelenglish/releases/tag/v1.4.0-rc.1) · [Launch, build and rollback guide](docs/operations/exe-trial-20261015.md) · [Render performance findings](docs/operations/render-performance-20261015.md). This is an owner-authorized usage trial; outstanding visual gates remain pending. The last stable release remains 1.3.0.

[![Python 3.11+](https://img.shields.io/badge/Python-3.11+-blue)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-latest-green)](https://fastapi.tiangolo.com)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![GPU: RTX 3060](https://img.shields.io/badge/GPU-RTX%203060-76b900)](https://nvidia.com)

## What is Daily Beyond English Studio?

**Daily Beyond English Studio** là công cụ sản xuất nội dung tiếng Anh hỗ trợ bởi AI dành cho content creator YouTube. Ứng dụng tự động hóa toàn bộ pipeline từ ý tưởng → kịch bản → giọng đọc → video → YouTube description.

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
| **Task 3.1** | 📖 **Documentation** — README, [Prompt Engineering Guide](docs/user/prompt-guide.md), [TTS Setup Guide](docs/user/tts-setup.md), auto-generated [API Reference](docs/api.md) | ✅ Done |
| **Task 3.2** | 🎬 **Demo & Review** — [3 sample episodes](docs/samples/) (A1/B1/C1, real script+audio), a real [223.9s end-to-end demo recording](docs/report/demo-video.md), and a [product review report](docs/report/product-review.md) | ✅ Done |
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

15 more phases beyond the original plan — most scoped from independent audits (including
multiple separate AI-assisted read-only `/vp-audit` passes), with major AI-architecture
work in Phases 13–18. Each closed with zero real defects found on PM review. Full evidence
trail in `.viepilot/ROADMAP.md` and `.viepilot/TRACKER.md`.

**Current trial:** `1.4.0-rc.1` (2026-10-15). **Last stable version:** `1.3.0` (2026-10-13, project close-out — see the
[final report](docs/report/final-report.md)). `1.2.0-beta` (2026-10-05) made the Remotion video the default. AI writes are
**cloud-first with local fallback** — Gemini 3.1 Flash-Lite is the primary, with an
automatic chain through OpenRouter free models and finally local `qwen3.5:9b` on the
RTX 3060. Real Gate B-11 measurement: **~45s B1 8-min script generation median, vs. ~127s
local — 2.8× faster** (`docs/operations/phase18-gate-b11.md`,
`docs/report/benchmark-chart.png`). Kill switch `DIE_AI_ALLOW_CLOUD=false` (or `DIE_AI_MODE=
local`) reverts to 100% offline immediately.

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
| **Phase 13** | 🏠 **Local-First AI Reliability** — real qualified Ollama + `qwen3.5:9b` install as an offline AI option; durable job system (`ai_generation_jobs`) with per-project checkpoints so a crash mid-generation resumes cleanly instead of losing work; provider-neutral AI gateway | ✅ Done |
| **Phase 14** | 🛠️ **AI Gateway Resilience** — real Gate B-2 comparison of Ollama vs. Gemini, then owner decision to ship local-only after Gemini free tier proved too flaky (superseded by Phase 18); per-section script generation with bounded budget/repetition repairs; measured WPM calibration per CEFR level | ✅ Done |
| **Phase 15** | 🔧 **Local Script Robustness** — speaker aliases (S1/S2) in the section contract instead of raw UUIDs; deterministic same-speaker line merging; per-gate evidence path organization | ✅ Done |
| **Phase 16** | 🩹 **Stability Hardening** — worker loop guard + `worker_alive` health signal; ffmpeg subprocess timeouts + atomic render; test-data leak fix + `conftest` guard; evidence-driven repetition avoid list | ✅ Done |
| **Phase 17** | 📏 **Budget-Aware Global Validation** — global word-count repair covering the mixed section-over/section-under case with a length-aware repetition repair path | ✅ Done |
| **Phase 18** | ☁️ **Cloud-First AI with Local Fallback** — the current default. Generic `OpenAICompatProvider`; multi-provider cloud chain (Gemini 3.1 Flash-Lite → Gemini Flash-Lite latest → OpenRouter Nemotron/Gemma/Dots3 → local qwen); per-provider circuit breaker and time budget; kill switch `DIE_AI_ALLOW_CLOUD=false`. Gate B-11 real measurement: **~45s median vs. ~127s local (2.8× faster)**. **v1.1.0-beta** shipped at close | ✅ Done |
| **Phase 19** | 🎬 **Animated Learning Videos (Remotion)** — word-level karaoke captions from per-word Edge TTS timings, active-speaker chip, timed vocabulary/idiom cards, intro/outro and a chapter/progress bar. Remotion became the default in 1.2.0-beta and the sole video renderer in Phase 35. Gate B-12 media and visual PASS; the voice complaint was an Edge TTS issue (D38) | ✅ Done |

#### Visual studio, publishing and the channel (Phases 20–37)

Phases 20, 23 and 24 shipped in `1.2.0-beta`; Phases 22 and 25–37 ship in `1.3.0` (see [CHANGELOG.md](CHANGELOG.md)). Gates B-14 to B-21 were closed by owner decision D109 (2026-10-13): their features are part of every episode
accepted at Gates B-22 to B-24.

| Phase | Feature | Status |
|-------|---------|--------|
| **Phase 20** | 🖼️ **AI Visuals** — local GPU image generation in a separate `.venv-image` worker (diffusers), one GPU arbiter for the RTX 3060, a Character Library and Scene Library, and per-project shots used by the Enhanced video ([plan](docs/implementation/phase-20-ai-visuals.md)) | ✅ Done (gate closed by D109) |
| **Phase 21** | 🗣️ **Better TTS engine** — Kokoro (D36) and StyleTTS 2 (D38) spikes both failed the owner listening test; Edge TTS stays, and the spike engines were removed (D56) ([plan](docs/implementation/phase-21-tts-kokoro.md)) | ⛔ Closed, won't fix |
| **Phase 22** | 🎵 **Background music** — AI music generation was dropped (D50); free library tracks instead, with automatic pace/mood classification, auto-select by topic and length, a bed fitted to the episode and ducked under the voice, and a music credit in the YouTube description ([plan](docs/implementation/phase-22-ai-music.md), [free sources](docs/user/free-music-sources.md)) | ✅ Done (gate closed by D109) |
| **Phase 23–24** | 🗺️ **Scene Library v2 and storyboard** — a 55-place scene library; the AI proposes story beats, the owner reviews them in Step 5, and approved beats become the shots that drive the video timeline ([plan](docs/implementation/phase-23-24-scenes-and-storyboard.md)) | ✅ Done (gate closed by D109) |
| **Phase 25** | 🎬 **Branded intro and outro** — logo morph and a spoken greeting and farewell in every Enhanced video, with the music ducked under the voice ([plan](docs/implementation/phase-25-branded-intro-outro.md)) | ✅ Done |
| **Phase 26** | ✨ **UI polish** — interim polish before the layout redo ([plan](docs/implementation/phase-26-ui-polish.md)) | ✅ Done |
| **Phase 27** | 🎨 **Rebrand and studio layout** — Daily Beyond English name, logo and palette in the app and video; collapsible sidebar; image grids for characters and scenes; all seven steps share one studio frame ([plan](docs/implementation/phase-27-rebrand-and-layout.md)) | ✅ Done (gate closed by D109) |
| **Phase 28** | 📷 **Semi-realistic picture style** — RealVisXL V5.0 editorial look, approved character sheets, outfit-colour and extra-person checks with a "check this shot" mark in Step 5 ([plan](docs/implementation/phase-28-semi-realistic-style.md)) | ✅ Done (gate closed by D109) |
| **Phase 29** | 🗂️ **Shot Library** (`/shots`) — reviewed, reusable pictures of the cast by scene, framing, action and mood; new episodes reuse approved matches and draw only what is missing; natural gaze and cleaner cuts ([plan](docs/implementation/phase-29-shot-library.md)) | ✅ Done (gate closed by D109) |
| **Phase 30** | 🎧 **Podcast picture modes** — Step 5 "Video pictures": with characters, black screen, or one still scene with a slow zoom ([plan](docs/implementation/phase-30-podcast-visuals.md)) | ✅ Done |
| **Phase 31** | 👥 **Alex and Lina** — the owner's own characters replace the earlier pair; the owner's pictures import into the Shot Library from an inbox folder ([55-scene list](docs/operations/scene-list-55.md)) | ✅ Done |
| **Phase 32** | 🗨️ **Talking characters** — Step 5 mode "Podcast: talking characters": visual-novel style sprites whose mouths follow the speech, with expressions, blinks, gestures and turn-taking; an Activity Library of reviewed pictures (upload with an owner-entered name per image) that become full-screen cutaways on storyboard insert beats ([plan](docs/implementation/phase-32-talking-sprites.md), [sprite spec](docs/operations/sprite-asset-spec.md), [activity upload](docs/operations/activity-library-manual-upload.md)) | ✅ Done (Gate B-22 PASS) |
| **Phase 33** | 🎮 **Character profiles v2** — game-style character selection in Steps 1 and 5, profiles with 29 talking-sprite slots filled from outside-AI pictures (prompts per slot, automatic renaming and alignment), man left / woman right facing each other, 3–6 speakers; Gate B-23 fixes: storyboard inserts named from the Activity Library, missing illustrations drawn on the local GPU or made with an outside AI | ✅ Done (Gate B-23 PASS) |
| **Phase 34** | 🧾 **Project hygiene** — phase records reconciled, checkpoint tags, README / architecture / API reference refreshed, Ruff clean | ✅ Done |
| **Phase 35** | 🧹 **Legacy cleanup** — the old app name in the AI prompts, one-off scripts and prompt files, the "Generate locally" tab, the sprite inbox import, speaker avatars and the Standard ffmpeg renderer removed (D89) | ✅ Done |
| **Phase 36** | 📦 **YouTube publishing package** — collocations, phrasal verbs and sentence patterns; an SEO description with hashtags and the transcript as the pinned comment; thumbnails with the episode's characters or an outside-AI picture; a **Channel plan** (topics → series → numbered episodes, AI channel map, rotating 2-week calendar) and a **channel cockpit dashboard** (stats, Today, 5-stage roadmap, Kanban board) | ✅ Done (Gate B-24 PASS) |
| **Phase 37** | 📱 **Shorts & TikTok** — the whole episode in vertical 1080x1920 (picture on top, big karaoke captions, both characters below) and 1–3 AI-proposed, owner-approved 30–90 s highlight clips opening on a hook banner, each with a 9:16 cover, a Shorts title/description and a TikTok caption | ✅ Built, owner Gate B-25 pending |

## Quick Start

### Requirements

- Python 3.11+
- NVIDIA GPU (recommended: RTX 3060+ with 8GB+ VRAM — needed only for the local fallback
  path; the cloud-first default runs on any machine that can reach the internet)
- ffmpeg (in PATH, or set `DIE_FFMPEG_PATH` to its absolute exe path — e.g. on Windows if it was installed via `winget` and the shell's PATH hasn't picked it up yet)
- **Cloud AI keys** (recommended, this is the default since Phase 18): a
  [Google AI Studio](https://aistudio.google.com/) API key (`DIE_GEMINI_API_KEY`) and/or an
  [OpenRouter](https://openrouter.ai) key (`DIE_OPENAI_COMPAT_API_KEY`). Both providers
  have free tiers that are enough to try the app end-to-end. Enter either through the
  in-app Settings page (Phase 12) or the `.env` file.
- **[Ollama](https://ollama.com/download)** with the `qwen3.5:9b` model — the local
  fallback when cloud is unreachable, rate-limited, or explicitly disabled
  (`DIE_AI_ALLOW_CLOUD=false`). See
  [docs/operations/local-ai.md](docs/operations/local-ai.md). Not strictly required if you
  always have working cloud keys, but it's what makes the app resilient — a Gemini outage
  degrades a generation instead of failing it.

### Installation

```bash
# 1. Clone / copy to your machine
cd d:\DataAdmin\Daily_Intel_English

# 2. Create virtual environment
python -m venv .venv
.venv\Scripts\activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Setup environment
copy .env.example .env
# Fill in DIE_GEMINI_API_KEY and/or DIE_OPENAI_COMPAT_API_KEY for the cloud-first default.
# Leave them empty to run local-only (Ollama + qwen3.5:9b required).
# (All application settings use the DIE_ prefix, e.g. DIE_AI_MODE, DIE_OLLAMA_MODEL)

# 5. Check dependencies (verifies Ollama is running and the model is pulled)
python scripts/check_dependencies.py

# (optional) Local image generation: a separate Python for torch + diffusers
#   py -3.14 -m venv .venv-image   then follow backend/ai/image/requirements.txt

# 6. Run the app
uvicorn backend.main:app --reload --port 8000
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
isn't guaranteed writable depending on where it's installed). It runs
**cloud-first** by default since Phase 18 (`DIE_AI_MODE=cloud_first`), with local
Ollama as automatic fallback — see Requirements above. A no-key install collapses
transparently to local-only (invariant I32 from Phase 18); every non-AI feature
works either way.

**Full offline / kill switch:** set `DIE_AI_ALLOW_CLOUD=false` (or `DIE_AI_MODE=local`)
to force 100% local. No cloud calls are made at all, verified by a real test in
`tests/test_ai_router.py`. Requires Ollama + `qwen3.5:9b`.

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
3️⃣  Step 3: Learning Content → Vocabulary, idioms, collocations, phrasal verbs, sentence patterns, grammar, listening quiz (Tasks 1.5, 36.1)
4️⃣  Step 4: TTS Audio Studio → Voice assignment, per-line preview, real audio mix + loudness normalization, MP3/WAV export (Shipped - Task 1.6)
5️⃣  Step 5: Video Studio     → The Remotion episode (the only renderer since Phase 35): cast through the character selector, storyboard review, shots from the Shot/Scene libraries, picture modes (story pictures, black screen, one still, talking characters), activity illustrations (drawn on the local GPU or made with an outside AI when missing); MP4 + SRT; a vertical episode and Shorts/TikTok highlight clips with covers and texts (Phases 1, 19–37)
6️⃣  Step 6: Thumbnail        → The episode's characters over a topic picture with a headline, CEFR badge and logo (3–5 variants, 16:9 + 9:16), or your outside-AI picture; manual editor, export (Tasks 1.8, 36.3–36.4)
7️⃣  Step 7: YouTube Package  → Titles, an SEO description within 5,000 characters (chapters, learning items with Vietnamese meanings, listening questions, hashtags), the transcript as the pinned comment, tags, copy buttons + full .zip export (Tasks 1.9, 36.2)
```
Music Library (Task 1.10, `/music`) is a standalone background-music management feature, not a numbered pipeline step — upload/list/preview/delete, volume leveling, Step 4 background-track selection, and waveform visualization are all shipped. The Character Library (`/characters`: character profiles with their talking-sprite slots, and the scenes) and the Shots page (`/shots`: the Activity Library of generic pictures and the scene-background import) are also standalone pages that feed Step 5.

## Tech Stack

- **Backend**: Python 3.11+ / FastAPI / Uvicorn / aiosqlite
- **Frontend**: Vanilla HTML5 / CSS3 / JavaScript
- **AI**: **Cloud-first with local fallback** since Phase 18 (v1.1.0-beta). Chain:
  Gemini 3.1 Flash-Lite → Gemini Flash-Lite latest → OpenRouter free (Nemotron 3 Super
  → Gemma 4 26B → Dots3-Note) → local Ollama `qwen3.5:9b` on the RTX 3060. Per-provider
  circuit breaker + separate time budgets. Kill switch `DIE_AI_ALLOW_CLOUD=false` reverts
  to 100% local. Structured JSON output enforced across all providers via a generic
  `OpenAICompatProvider`. See
  [docs/operations/phase18-gate-b11.md](docs/operations/phase18-gate-b11.md) for real
  measurement (median 45s cloud vs. 127s local, 2.8× faster).
- **TTS**: Edge TTS (sole engine — OmniVoice GPU cloning considered, dropped 2026-09-13; see [docs/user/tts-setup.md](docs/user/tts-setup.md))
- **Audio**: pydub + ffmpeg (real ITU-R BS.1770 loudness normalization via `pyloudnorm`)
- **Video**: Remotion 4 + React 19 + TypeScript in the separate [`renderer/`](renderer/) Node workspace, run locally as a subprocess from FastAPI — the only renderer since Phase 35 (the Standard ffmpeg renderer was removed; the vertical 1080x1920 layout and highlight clips are Remotion too, Phase 37). Node.js, `npm install` in `renderer/` and Chrome Headless Shell are required
- **Images**: local GPU image generation in its own `.venv-image` environment — Qwen-Image-2.1-Turbo (illustrations with ordinary people, never a cast face; plates; topic pictures) and Qwen-Image-Edit-2511 (the AI-scene thumbnails); RealVisXL/SDXL and the two-person shots were removed in Phase 44 (D123); see [the benchmark](docs/operations/phase39-image-benchmark.md) — and worker process (`backend/ai/image/requirements.txt`, `backend/ai/image/image_worker.py`); optional — every library also accepts the owner's own pictures
- **Thumbnail**: Pillow composition of the cast's talking sprites over the episode's pictures (Montserrat headline, CEFR badge, logo) + AI headline suggestions
- **Database**: SQLite (aiosqlite async transactions)

## Documentation

| Doc | Purpose |
|-----|---------|
| [docs/user/prompt-guide.md](docs/user/prompt-guide.md) | How to customize the AI prompt templates (script genres, CEFR blocks, learning content, thumbnails, YouTube package) — shared by every provider in the cloud-first chain (Gemini, OpenRouter models, local qwen) |
| [docs/user/tts-setup.md](docs/user/tts-setup.md) | Edge TTS voice map and known limitations; why OmniVoice was investigated but not integrated |
| [docs/api.md](docs/api.md) | Full API reference, auto-generated from the app's real FastAPI OpenAPI schema (`scripts/generate_api_docs.py`) — also live at `/docs` while the app is running |
| [docs/report/final-report.md](docs/report/final-report.md) | Final project report: scope, timeline, results, quality, audit and open items |
| [docs/presentation/](docs/presentation/) | ChatGPT prompt for the judges' presentation |
| [docs/implementation/](docs/implementation/) | Per-phase implementation plans (Phase 19 onward) |
| [docs/operations/](docs/operations/) | Operation guides and gate reports (local AI, sprites, Activity Library prompt packs, gates B-2 to B-24) |
| [.viepilot/ARCHITECTURE.md](.viepilot/ARCHITECTURE.md) | System design, services, data models |
| [.viepilot/ROADMAP.md](.viepilot/ROADMAP.md) | Phase/task plan with acceptance criteria |
| [.viepilot/TRACKER.md](.viepilot/TRACKER.md) | Full progress and decision log |

## Project Structure

Where-is-what map: [docs/structure/STRUCTURE.md](docs/structure/STRUCTURE.md) (Phase 38 layout, D115).

```
Daily_Intel_English/
├── backend/                 # FastAPI package — run with `uvicorn backend.main:app`
│   ├── api/                 # HTTP routes (one module per area)
│   ├── core/                # config, paths, constants, errors, settings
│   ├── db/                  # SQLite access + migrations/
│   ├── schemas/             # Pydantic request/response models
│   ├── ai/                  # every AI part
│   │   ├── llm/             #   cloud-first gateway, providers, AI jobs, prompt loader
│   │   ├── image/           #   local GPU images: engine, worker, pipelines, recipes, GPU arbiter
│   │   ├── tts/             #   Edge TTS
│   │   ├── prompts/         #   prompt templates
│   │   └── models/          #   local model weights (gitignored)
│   ├── content/             # projects, scripts, learning packs, YouTube, Shorts
│   ├── media/               # audio, music, video (Remotion bridge), thumbnails, brand
│   ├── library/             # characters, scenes, shots, sprites, Activity Library, storyboard
│   └── channel/             # channel plan, dashboard
├── frontend/                # pages/ + static/ (vanilla HTML/CSS/JS)
├── renderer/                # Remotion (React/TypeScript) video renderer
├── scripts/                 # maintenance CLIs and benchmarks (nothing the app imports)
├── tests/                   # pytest suite
├── docs/                    # user/, operations/, implementation/, report/, structure/ ...
├── data/                    # runtime data (gitignored)
└── .venv/  .venv-image/     # Python environments (gitignored)
```

## License

MIT License — see [LICENSE](LICENSE)

---

*Built with ViePilot | Crystallized: 2026-09-10*
