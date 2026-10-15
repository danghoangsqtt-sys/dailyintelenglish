"""Centralized project-root resolution (Task 12.2).

5 places used to independently walk `Path(__file__)` up to the project root
(`backend/main.py`, `backend/media/thumbnail_service.py`,
`backend/media/video_service.py`, `backend/ai/llm/prompt_loader.py`,
`backend/db/database.py`) to find `frontend/`, `prompts/`, and migration files. None
of that is reliable once frozen into a PyInstaller build -- pure-Python modules
get compiled into an internal archive, so `Path(__file__)` no longer points at a
real directory on disk the way it does running from source.
"""

import os
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


def get_runtime_root() -> Path:
    """Locate external Node/image runtimes while keeping bundled UI resources separate."""
    configured = os.environ.get("DIE_WORKSPACE_DIR")
    if configured:
        root = Path(configured).expanduser().resolve()
        if not (root / "renderer/package.json").is_file() or not (root / "backend/ai/image/image_worker.py").is_file():
            raise RuntimeError("DIE_WORKSPACE_DIR must point to the Studio repository containing renderer and the image worker")
        return root
    return get_project_root()


# Phase 38 (D115): bundled resources and external compute runtimes have separate roots.
PROJECT_ROOT = get_project_root()
RUNTIME_ROOT = get_runtime_root()
BACKEND_DIR = PROJECT_ROOT / "backend"
AI_DIR = BACKEND_DIR / "ai"
PROMPTS_DIR = AI_DIR / "prompts"
MIGRATIONS_DIR = BACKEND_DIR / "db" / "migrations"
RENDERER_DIR = RUNTIME_ROOT / "renderer"
MODELS_DIR = RUNTIME_ROOT / "backend/ai/models"  # local model weights (gitignored)
IMAGE_VENV_DIR = RUNTIME_ROOT / ".venv-image"  # the image worker's own Python (torch, diffusers)
