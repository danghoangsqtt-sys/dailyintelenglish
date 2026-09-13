# Task 1.1: Project Setup & Infrastructure

## Meta
- **ID**: 1.1
- **Phase**: 1
- **Status**: done (2026-09-13)
- **Priority**: high
- **Assignee**: AI

## Paths
- `app/main.py`
- `app/core/config.py`
- `app/core/constants.py`
- `app/db/database.py`
- `scripts/check_dependencies.py`
- `requirements.txt`

## Acceptance Criteria
- [x] Virtual environment created and core packages installed
- [x] Directory structure created
- [x] FastAPI skeleton running with CORS, lifespan, router mounts
- [x] SQLite database initialization functional
- [x] Dependency check reports all GREEN on target environment — confirmed 2026-09-13
  after ffmpeg/`.env`/Gemini key/OmniVoice model were all resolved this session:
  ```
  [GREEN] Python >= 3.11: Python 3.14.7
  [GREEN] ffmpeg: ffmpeg version 9.0.1-full_build-www.gyan.dev
  [GREEN] NVIDIA GPU: NVIDIA GeForce RTX 3060 (12288 MiB)
  [GREEN] .env / GEMINI_API_KEY: DIE_GEMINI_API_KEY is set
  [GREEN] OmniVoice model: model files present at models/omnivoice
  [GREEN] data/ directories: all data directories present
  All checks passed.
  ```

## Forbidden Scope
- No frontend business logic in backend routes
- No hardcoded secrets or paths

## Verification Commands
- `venv\Scripts\python -m pytest tests/`
- `venv\Scripts\ruff check app/`
