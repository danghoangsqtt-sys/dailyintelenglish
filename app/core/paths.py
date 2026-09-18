"""Centralized project-root resolution (Task 12.2).

5 places used to independently walk `Path(__file__)` up to the project root
(`app/main.py`, `app/services/thumbnail_service.py`,
`app/services/video_service.py`, `app/core/prompt_loader.py`,
`app/db/database.py`) to find `frontend/`, `prompts/`, and migration files. None
of that is reliable once frozen into a PyInstaller build -- pure-Python modules
get compiled into an internal archive, so `Path(__file__)` no longer points at a
real directory on disk the way it does running from source.
"""

import sys
from pathlib import Path


def get_project_root() -> Path:
    """Return the directory containing `app/`, `frontend/`, and `prompts/`.

    A frozen PyInstaller build (onedir or onefile) stages every `--add-data`
    resource under `sys._MEIPASS` -- that's the project-root equivalent at
    runtime. Running from source, it's 3 levels up from this file
    (app/core/paths.py -> app -> project root), same depth every one of the 5
    former call sites already computed independently.
    """
    if getattr(sys, "frozen", False):
        return Path(sys._MEIPASS)  # type: ignore[attr-defined]
    return Path(__file__).resolve().parent.parent.parent
