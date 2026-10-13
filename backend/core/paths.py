"""Centralized project-root resolution (Task 12.2).

5 places used to independently walk `Path(__file__)` up to the project root
(`backend/main.py`, `backend/media/thumbnail_service.py`,
`backend/media/video_service.py`, `backend/ai/llm/prompt_loader.py`,
`backend/db/database.py`) to find `frontend/`, `prompts/`, and migration files. None
of that is reliable once frozen into a PyInstaller build -- pure-Python modules
get compiled into an internal archive, so `Path(__file__)` no longer points at a
real directory on disk the way it does running from source.
"""

import sys
from pathlib import Path


def get_project_root() -> Path:
    """Return the directory containing `backend/` and `frontend/`.

    A frozen PyInstaller build (onedir or onefile) stages every `--add-data`
    resource under `sys._MEIPASS` -- that's the project-root equivalent at
    runtime. Running from source, it's 3 levels up from this file
    (backend/core/paths.py -> app -> project root), same depth every one of the 5
    former call sites already computed independently.
    """
    if getattr(sys, "frozen", False):
        return Path(sys._MEIPASS)  # type: ignore[attr-defined]
    return Path(__file__).resolve().parent.parent.parent


# Phase 38 (D115): the homes of the folders the app reads at runtime.
PROJECT_ROOT = get_project_root()
BACKEND_DIR = PROJECT_ROOT / "backend"
AI_DIR = BACKEND_DIR / "ai"
PROMPTS_DIR = AI_DIR / "prompts"
MIGRATIONS_DIR = BACKEND_DIR / "db" / "migrations"
RENDERER_DIR = PROJECT_ROOT / "renderer"
MODELS_DIR = AI_DIR / "models"  # local model weights (gitignored)
IMAGE_VENV_DIR = PROJECT_ROOT / ".venv-image"  # the image worker's own Python (torch, diffusers)
