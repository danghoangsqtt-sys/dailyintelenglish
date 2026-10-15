"""Bootstrap a linked local desktop build before application settings are imported."""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path


def configure_desktop_runtime() -> None:
    """Load the EXE's relative workspace/data locator, preserving explicit env overrides."""
    if not getattr(sys, "frozen", False):
        return
    directory = Path(sys.executable).resolve().parent
    locator = directory / "studio-runtime.json"
    if locator.is_file():
        values = json.loads(locator.read_text(encoding="utf-8"))
        if not isinstance(values, dict) or set(values) - {"workspace_dir", "data_dir"}:
            raise ValueError("Invalid studio-runtime.json: expected workspace_dir and data_dir paths")
        for key, variable in (("workspace_dir", "DIE_WORKSPACE_DIR"), ("data_dir", "DIE_DATA_DIR")):
            value = values.get(key)
            if value is None:
                continue
            if not isinstance(value, str) or not value.strip():
                raise ValueError(f"Invalid {key} in studio-runtime.json")
            os.environ.setdefault(variable, str((directory / value).resolve()))
    if os.environ.get("DIE_WORKSPACE_DIR"):
        # Existing media rows and .env may contain repository-relative paths.
        # Double-clicking from Explorer must resolve them just like source mode.
        os.chdir(Path(os.environ["DIE_WORKSPACE_DIR"]))
    # Windowed PyInstaller executables have no stdout/stderr. Uvicorn and some
    # dependency loggers expect streams; retain diagnostics without a console.
    if sys.stdout is None or sys.stderr is None:
        data = Path(os.environ.get("DIE_DATA_DIR") or Path(os.environ.get("LOCALAPPDATA") or Path.home()) / "DailyIntelEnglishStudio/data")
        logs = data / "logs"
        logs.mkdir(parents=True, exist_ok=True)
        stream = (logs / "desktop.log").open("a", encoding="utf-8", buffering=1)
        if sys.stdout is None:
            sys.stdout = stream
        if sys.stderr is None:
            sys.stderr = stream
