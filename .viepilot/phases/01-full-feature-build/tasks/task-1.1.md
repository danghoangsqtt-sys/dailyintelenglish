# Task 1.1: Project Setup & Infrastructure

## Meta
- **ID**: 1.1
- **Phase**: 1
- **Status**: in_progress
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
- [ ] Dependency check reports all GREEN on target environment

## Forbidden Scope
- No frontend business logic in backend routes
- No hardcoded secrets or paths

## Verification Commands
- `venv\Scripts\python -m pytest tests/`
- `venv\Scripts\ruff check app/`
