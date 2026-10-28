"""Bootstrap a linked local desktop build before application settings are imported."""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path


SEM_FAILCRITICALERRORS, SEM_NOGPFAULTERRORBOX, SEM_NOOPENFILEERRORBOX = 0x0001, 0x0002, 0x8000


def quiet_child_processes(popen: type | None = None, kernel32: object | None = None) -> bool:
    """Phase 84 (real run 2026-10-28): an ffmpeg that could not start (0xC0000142, "the application was unable to start
    correctly") showed a Windows dialog that held an automatic video for 55 minutes until the owner clicked it.

    The error mode makes such a child fail at once (children inherit it), so the Producer's second try follows within
    seconds; and child programs (ffmpeg, node) start without a console of their own (CREATE_NO_WINDOW) unless the caller
    chose flags -- a windowed app gave each of them a hidden console, the usual cause of that start failure. Windows
    only; True when applied."""
    if os.name != "nt":
        return False
    import subprocess

    popen = popen or subprocess.Popen
    if getattr(popen, "_studio_quiet", False):
        return True
    if kernel32 is None:
        import ctypes

        kernel32 = ctypes.windll.kernel32
    kernel32.SetErrorMode(SEM_FAILCRITICALERRORS | SEM_NOGPFAULTERRORBOX | SEM_NOOPENFILEERRORBOX)
    original = popen.__init__
    no_window = getattr(subprocess, "CREATE_NO_WINDOW", 0x08000000)

    def __init__(self, *args, **kwargs):
        if not kwargs.get("creationflags"):
            kwargs["creationflags"] = no_window
        original(self, *args, **kwargs)

    popen.__init__ = __init__
    popen._studio_quiet = True
    return True


def configure_desktop_runtime() -> None:
    """Load the EXE's relative workspace/data locator, preserving explicit env overrides."""
    if not getattr(sys, "frozen", False):
        return
    quiet_child_processes()
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
