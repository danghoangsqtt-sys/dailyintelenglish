"""Phase 62 (ENH-044): "Open with Windows" -- a shortcut to the installed app in the user's Startup folder. The app it
opens starts with `--autostart` (no browser window) and waits for the night window."""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

from backend.core.exceptions import ValidationError

SHORTCUT_NAME = "Daily Beyond English (automatic production).lnk"


def startup_folder() -> Path:
    return Path(os.environ.get("APPDATA", "")) / "Microsoft" / "Windows" / "Start Menu" / "Programs" / "Startup"


def shortcut_path() -> Path:
    return startup_folder() / SHORTCUT_NAME


def available() -> bool:
    """Only the installed (packaged) app on Windows can open itself with Windows."""
    return sys.platform == "win32" and bool(getattr(sys, "frozen", False))


def is_enabled() -> bool:
    return sys.platform == "win32" and shortcut_path().is_file()


def apply(enabled: bool) -> None:
    """Create or remove the Startup shortcut (raises ValidationError when this app cannot do it)."""
    path = shortcut_path()
    if not enabled:
        path.unlink(missing_ok=True)
        return
    if not available():
        raise ValidationError("Open with Windows works in the installed app only (the desktop version).")
    target = Path(sys.executable)
    command = (
        "$s = (New-Object -ComObject WScript.Shell).CreateShortcut($env:DBE_LINK);"
        "$s.TargetPath = $env:DBE_TARGET; $s.Arguments = '--autostart'; $s.WorkingDirectory = $env:DBE_DIR;"
        "$s.WindowStyle = 7; $s.Description = 'Daily Beyond English: automatic production'; $s.Save()"
    )
    env = dict(os.environ, DBE_LINK=str(path), DBE_TARGET=str(target), DBE_DIR=str(target.parent))
    path.parent.mkdir(parents=True, exist_ok=True)
    result = subprocess.run(["powershell", "-NoProfile", "-NonInteractive", "-Command", command], env=env,
                            capture_output=True, text=True, timeout=30,
                            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
    if result.returncode != 0 or not path.is_file():
        raise ValidationError(f"The Startup shortcut could not be created: {result.stderr.strip()[:300]}")
