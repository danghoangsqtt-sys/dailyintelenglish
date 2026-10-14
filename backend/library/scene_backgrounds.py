"""Scene plates imported from `assets_background/` (named by scene key: cafe.png, city-street.png...). Moved out of the
two-person shot library when that was removed (Phase 44, D123); the behaviour is unchanged."""

from __future__ import annotations

import asyncio
import hashlib
import re
from pathlib import Path
from typing import Any

import aiosqlite
from PIL import Image

from backend.core.config import settings
from backend.library import library_service as library

IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp"}
TARGET_ASPECT = 16 / 9
ASPECT_TOLERANCE = 0.06  # a picture within 6% of 16:9 is kept as it is
CROP_TOP_ANCHOR = 0.15  # a taller picture loses most of its bottom


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _slug(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")


async def _resolve_scene(db: aiosqlite.Connection, token: str) -> str | None:
    wanted = _slug(token)
    cursor = await db.execute("SELECT id, name FROM scenes")
    for row in await cursor.fetchall():
        if wanted in (_slug(row["id"]), _slug(row["id"]).removeprefix("builtin-"), _slug(row["name"])):
            return row["id"]
    return None


def _fit_16_9(path: Path, target: Path) -> bool:
    """Save the picture as a PNG; a picture that is not about 16:9 is cropped to it (the top is kept). True if cropped."""
    with Image.open(path) as source:
        image = source.convert("RGB")
    width, height = image.size
    cropped = False
    if abs(width / height - TARGET_ASPECT) / TARGET_ASPECT > ASPECT_TOLERANCE:
        cropped = True
        if width / height < TARGET_ASPECT:  # too tall: cut height
            new_height = round(width / TARGET_ASPECT)
            top = round((height - new_height) * CROP_TOP_ANCHOR)
            image = image.crop((0, top, width, top + new_height))
        else:  # too wide: cut width, centred
            new_width = round(height * TARGET_ASPECT)
            left = (width - new_width) // 2
            image = image.crop((left, 0, left + new_width, height))
    target.parent.mkdir(parents=True, exist_ok=True)
    image.save(target, format="PNG")
    return cropped


def backgrounds_dir() -> Path:
    return settings.DATA_DIR / "assets_background"


def backgrounds_status() -> dict[str, Any]:
    folder = backgrounds_dir()
    images = sorted(p.name for p in (folder / "assets").iterdir() if p.suffix.lower() in IMAGE_EXTENSIONS) \
        if (folder / "assets").is_dir() else []
    return {"folder": str(folder), "images": len(images)}


async def import_backgrounds(db: aiosqlite.Connection) -> dict[str, list]:
    """Make the pictures of `assets_background/assets` the plates of their scenes, and keep the prompt of
    `assets_background/prompts/<key>.txt` next to the plate. A picture that is not 16:9 is cropped to it. Importing again
    is safe: an unchanged picture is reported as unchanged. Caller holds the write transaction."""
    folder = backgrounds_dir()
    assets = folder / "assets"
    imported, unchanged, skipped = [], [], []
    if not assets.is_dir():
        return {"imported": imported, "unchanged": unchanged, "skipped": skipped}
    for image in sorted(p for p in assets.iterdir() if p.is_file() and p.suffix.lower() in IMAGE_EXTENSIONS):
        scene_id = await _resolve_scene(db, image.stem)
        if scene_id is None:
            skipped.append({"file": image.name, "reason": f"unknown scene '{image.stem}' (use a scene key)"})
            continue
        target = settings.DATA_DIR / "library" / "scenes" / scene_id / "preview.png"
        staged = target.with_suffix(".new.png")
        try:
            cropped = await asyncio.to_thread(_fit_16_9, image, staged)
        except OSError as error:
            skipped.append({"file": image.name, "reason": f"not a readable picture ({error})"})
            continue
        same = target.is_file() and await asyncio.to_thread(_sha, staged) == await asyncio.to_thread(_sha, target)
        if same:
            await asyncio.to_thread(staged.unlink, True)
            unchanged.append(image.name)
        else:
            await asyncio.to_thread(staged.replace, target)
            await db.execute("UPDATE scenes SET preview_path = ?, updated_at = ? WHERE id = ?",
                             (str(target.resolve()), library._now(), scene_id))
            imported.append({"file": image.name, "scene_id": scene_id, "cropped": cropped})
        prompt = folder / "prompts" / f"{image.stem}.txt"
        if prompt.is_file():
            text = await asyncio.to_thread(prompt.read_text, "utf-8-sig")
            await asyncio.to_thread((target.parent / "prompt.txt").write_text, text, "utf-8")
    return {"imported": imported, "unchanged": unchanged, "skipped": skipped}
