"""Phase 71 (ENH-053): the Full and Lite editions, and whether this computer shows the local AI picture features.

Four features draw pictures with Qwen on this computer's GPU: a scene picture (Character Library -> Scenes), the missing
activity illustrations (Step 5), the topic picture and the AI scenes (Step 6). They are shown or hidden together:

- the setting `local_image_ai` is `on` (show), `off` (hide) or `auto` (the default);
- `auto` hides them in the Lite edition, and in the Full edition when this computer has no NVIDIA GPU with at least
  8 GB of memory (the picture lease's own threshold) or no picture environment (`.venv-image`).

Nothing is removed: a hidden feature comes back with the switch, and pictures already in the library are used as before.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import aiosqlite

from backend.core.config import settings
from backend.core.paths import IMAGE_VENV_DIR

SETTING_KEY = "local_image_ai"
CHOICES = ("auto", "on", "off")
MIN_VRAM_MB = 8192  # the same as the image engine's GPU lease


def edition() -> str:
    """`lite` or `full`: a packaged app's build-info.json, else the configured one."""
    if getattr(sys, "frozen", False):
        info = Path(sys.executable).resolve().parent / "build-info.json"
        try:
            value = json.loads(info.read_text(encoding="utf-8")).get("edition")
        except (OSError, ValueError):
            value = None
        if value in ("full", "lite"):
            return value
    return settings.EDITION


async def get_choice(db: aiosqlite.Connection) -> str:
    cursor = await db.execute("SELECT value FROM app_settings WHERE key = ?", (SETTING_KEY,))
    row = await cursor.fetchone()
    return row[0] if row and row[0] in CHOICES else "auto"


async def set_choice(db: aiosqlite.Connection, choice: str) -> None:
    from datetime import datetime, timezone

    await db.execute(
        "INSERT INTO app_settings (key, value, updated_at) VALUES (?, ?, ?) "
        "ON CONFLICT(key) DO UPDATE SET value = excluded.value, updated_at = excluded.updated_at",
        (SETTING_KEY, choice, datetime.now(timezone.utc).isoformat()))


def _image_python() -> Path:
    return IMAGE_VENV_DIR / ("Scripts/python.exe" if sys.platform == "win32" else "bin/python")


async def detect() -> dict:
    """What this computer has: the GPU memory and whether the picture environment is installed."""
    from backend.core.system_checks import get_gpu_memory

    memory = await get_gpu_memory()
    total = memory["total_mb"] if memory else None
    return {"gpu_total_mb": total, "gpu_ok": bool(total and total >= MIN_VRAM_MB), "image_env": _image_python().is_file()}


def decide(edition_name: str, choice: str, found: dict) -> tuple[bool, str]:
    """(shown, reason) -- pure, for the tests."""
    if choice == "on":
        return True, "shown by the setting"
    if choice == "off":
        return False, "hidden by the setting"
    if edition_name == "lite":
        return False, "the Lite edition hides them"
    if not found.get("gpu_ok"):
        total = found.get("gpu_total_mb")
        return False, (f"this computer's GPU has {round(total / 1024)} GB (8 GB needed)" if total else "no NVIDIA GPU was found")
    if not found.get("image_env"):
        return False, "the picture environment (.venv-image) is not installed"
    return True, "this computer can draw them"

