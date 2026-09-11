# 🚀 Daily Intel English Studio — Claude Code Kickoff Prompt

## Dự án
**Daily Intel English Studio** — AI-powered podcast production tool cho YouTube (local web app)

**GitHub:** https://github.com/danghoangsqtt-sys/dailyintelenglish  
**Local path:** `d:\DataAdmin\Daily_Intel_English\`  
**GPU:** NVIDIA RTX 3060 12GB VRAM

---

## Đọc ngay trước khi làm bất cứ điều gì

Đọc các file sau theo thứ tự này:

1. `.viepilot/AI-GUIDE.md` — file map & context loading strategy
2. `.viepilot/ARCHITECTURE.md` — toàn bộ kiến trúc, services, API endpoints, data models
3. `.viepilot/PROJECT-CONTEXT.md` — business rules, CEFR rules, conventions
4. `.viepilot/SYSTEM-RULES.md` — coding standards, async rules, do/don't
5. `.viepilot/ROADMAP.md` — danh sách task đầy đủ theo phase
6. `.viepilot/schemas/database-schema.sql` — SQLite schema

---

## Tech Stack đã được chốt

| Layer | Technology |
|-------|-----------|
| Backend | Python 3.11+ / FastAPI / Uvicorn |
| Frontend | Vanilla HTML5 + CSS3 + JavaScript (NO framework) |
| AI | Google Gemini API (`gemini-3.8-flash`) |
| TTS Primary | OmniVoice (k2-fsa) — local GPU RTX 3060 |
| TTS Backup | Edge TTS (free, online) |
| TTS Offline | Piper TTS |
| Audio | pydub + ffmpeg |
| Video | ffmpeg + LivePortrait (lips-sync) |
| Thumbnail | Pillow + Gemini Vision |
| Database | SQLite (aiosqlite) |
| Storage | Local filesystem |

---

## Nhiệm vụ ngay bây giờ: Phase 1 — Task 1.1

Implement **Project Setup & Infrastructure** (Day 1):

### 1. `requirements.txt`

```
fastapi>=0.115.0
uvicorn[standard]>=0.30.0
aiosqlite>=0.20.0
python-dotenv>=1.0.0
pydantic>=2.7.0
pydantic-settings>=2.3.0
httpx>=0.27.0
jinja2>=3.1.0
pydub>=0.25.1
Pillow>=10.4.0
google-generativeai>=0.7.0
edge-tts>=6.1.0
aiofiles>=24.1.0
python-multipart>=0.0.9
```

### 2. `app/main.py` — FastAPI skeleton

- CORS cho `http://localhost:*`
- Lifespan: init DB + load OmniVoice model (lazy) + check ffmpeg
- Mount static files cho `frontend/static/`
- Mount routers: `/api/projects`, `/api/tts`, `/api/music`
- Root route `/` → serve `frontend/pages/dashboard.html`
- `GET /health` → 200 + status dict (ffmpeg OK, db OK, gpu info)

### 3. `app/core/config.py` — Settings (pydantic-settings)

```python
class Settings(BaseSettings):
    GEMINI_API_KEY: str
    APP_HOST: str = "localhost"
    APP_PORT: int = 8000
    DATA_DIR: Path = Path("data")
    OMNIVOICE_MODEL_PATH: Path = Path("models/omnivoice")
    OMNIVOICE_DEVICE: str = "cuda"
    OMNIVOICE_MAX_CONCURRENT: int = 2
    FFMPEG_PATH: str = "ffmpeg"
    DEBUG: bool = True
    
    model_config = SettingsConfig(env_file=".env")
```

### 4. `app/core/constants.py`

```python
SILENCE_SAME_SPEAKER_MS = 300
SILENCE_DIFFERENT_SPEAKER_MS = 500
TARGET_LOUDNESS_LUFS = -16
MP3_BITRATE = "192k"
VIDEO_FPS = 30
VIDEO_WIDTH_STANDARD = 1280
VIDEO_HEIGHT_STANDARD = 720
VIDEO_WIDTH_SHORTS = 720
VIDEO_HEIGHT_SHORTS = 1280
MAX_CONCURRENT_TTS = 2
GEMINI_MAX_RETRIES = 4
GEMINI_RETRY_BASE_DELAY = 1.0  # seconds, exponential backoff
CEFR_LEVELS = ["A1", "A2", "B1", "B2", "C1", "C2"]
GENRES = ["instructions", "directions", "debate", "informational", "interview", "opinion", "storytelling", "small_talk", "negotiation", "news"]
ACCENTS = ["american", "british", "australian", "canadian", "irish", "scottish", "indian", "singaporean", "new_zealand", "south_african"]
```

### 5. `app/db/database.py` — aiosqlite connection

- Singleton `Database` class
- `async def init_db()` — chạy `migrations/001_init.sql`
- `async def get_db()` — FastAPI Depends() provider

### 6. `app/db/migrations/001_init.sql`

Copy từ `.viepilot/schemas/database-schema.sql` (đã có sẵn)

### 7. `scripts/check_dependencies.py`

Script kiểm tra:
- Python version >= 3.11 ✅/❌
- ffmpeg available in PATH ✅/❌  
- NVIDIA GPU available + VRAM size ✅/❌
- `.env` file exists + `GEMINI_API_KEY` set ✅/❌
- `data/` directories exist ✅/❌

### 8. `frontend/pages/dashboard.html` — Dashboard UI

**Design:** Dark mode mặc định, professional podcast studio aesthetic
- Header: Logo "🎙️ Daily Intel English Studio" + Dark/Light toggle
- Hero section: "Tạo podcast tiếng Anh chuẩn với AI"
- Nút "➕ Tạo Dự Án Mới" nổi bật
- Grid project cards (empty state nếu chưa có project)
- Each card: tên project, CEFR badge, genre badge, status badge, ngày tạo, nút Continue/Delete
- Filter bar: All | Draft | In Progress | Complete
- Search box

**Style yêu cầu:**
- Dark background: `#0d1117`, accent: `#7c3aed` (violet), text: `#e6edf3`
- Google Font: Inter
- Glassmorphism cards với border `rgba(124,58,237,0.3)`
- Smooth hover animations
- Responsive, min-width 1024px

---

## Quy tắc coding bắt buộc (từ SYSTEM-RULES.md)

1. **Tất cả routes phải `async def`**
2. **Tất cả I/O phải dùng `await` hoặc threadpool** (không blocking)
3. **Type hints MANDATORY** cho tất cả function signatures
4. **Docstrings MANDATORY** cho tất cả public service methods
5. **Paths dùng `pathlib.Path`** — không hardcode string paths
6. **Magic numbers → `constants.py`** — không inline
7. **API keys → `.env`** — không hardcode
8. **Error handling:** Services raise typed exceptions → global handler → JSON response

---

## API Response format chuẩn

```json
{
  "success": true,
  "data": { ... },
  "error": null,
  "meta": {
    "processing_time_ms": 123
  }
}
```

---

## Sau khi xong Task 1.1

Test với:
```bash
cd d:\DataAdmin\Daily_Intel_English
venv\Scripts\activate
pip install -r requirements.txt
python scripts/check_dependencies.py
uvicorn app.main:app --reload --port 8000
# Mở http://localhost:8000 → phải thấy Dashboard
```

Sau đó tiếp tục với **Task 1.3 — Script Config Wizard** (Step 1 UI + API) theo ROADMAP.md.

---

## Git workflow & PM Delivery Control

> [!IMPORTANT]
> **PM Approval Required**: Không dùng `git add .` bừa bãi. PM là người duy nhất quyết định commit, push và release. AI Implementer chỉ stage các file thuộc `allowed_files` khi được PM yêu cầu.

```bash
# Sau khi toàn bộ quality gates pass và được PM phê duyệt:
git add <file1> <file2> ...
git commit -m "feat(scope): conventional commit message"
# git push chỉ do PM thực hiện hoặc khi PM chỉ định
```

Commit message theo Conventional Commits (từ SYSTEM-RULES.md):
`feat|fix|perf|docs|refactor|test|chore(scope): description`

---

## Context bổ sung quan trọng

- **OmniVoice** chưa được cài — Task 1.1 chỉ cần VERIFY GPU available, không cần load model ngay
- **LivePortrait** cũng chưa cần — sẽ integrate ở Task 1.7
- **Gemini API key** sẽ do user cung cấp vào `.env` sau
- Ứng dụng chạy **offline-first** — mọi feature cơ bản phải hoạt động không cần internet (trừ Gemini và Edge TTS)
- **Không dùng TailwindCSS**, không dùng React/Vue — chỉ Vanilla CSS + JS

---

*Session brainstorm: `docs/brainstorm/session-2026-09-10.md`*  
*Crystallize artifacts: `.viepilot/` folder*  
*Repo: https://github.com/danghoangsqtt-sys/dailyintelenglish*
