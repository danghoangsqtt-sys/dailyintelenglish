"""Phase 93 (Task 93.3, D144 start): the assistant character's half-body frames for Home's band.

The assistant is a library character with talking sprites (default Lina). A frame is cut from the character's front
sprite set (falling back to its usual set): the top half of the figure, kept at the same size for every frame so mouth
and blink swaps line up, and cached as WebP. Phase 94 adds the three-quarter view and the assistant's lines.
"""

from __future__ import annotations

import time
from pathlib import Path

import aiosqlite
from fastapi import APIRouter, Depends
from fastapi.responses import FileResponse

from backend.core.config import settings
from backend.core.exceptions import NotFoundError, ValidationError
from backend.core.responses import ok
from backend.db.database import get_db
from backend.library.library_service import data_path

router = APIRouter(prefix="/api/assistant", tags=["assistant"])

DEFAULT_NAME = "Lina"
FRAMES = {"calm__closed", "calm__open", "blink", "gesture-wave", "gesture-wave__open", "gesture-talk", "gesture-talk__open",
          "gesture-point-left", "gesture-point-left__open", "gesture-think", "gesture-think__open"}
SIZE = (680, 760)  # the half-body frame, portrait


async def _assistant(db: aiosqlite.Connection) -> dict | None:
    cursor = await db.execute("SELECT id, name FROM characters WHERE name = ? COLLATE NOCASE LIMIT 1", (DEFAULT_NAME,))
    row = await cursor.fetchone()
    return dict(row) if row else None


async def _sprite(db: aiosqlite.Connection, character_id: str, name: str) -> Path | None:
    """The current approved sprite picture: the front set first, then the character's usual set."""
    for facing in ("front", "native"):
        cursor = await db.execute(
            "SELECT path FROM character_assets WHERE character_id = ? AND slot_key = ? AND facing = ? AND is_current = 1 "
            "ORDER BY updated_at DESC LIMIT 1", (character_id, f"sprite/{name}", facing))
        row = await cursor.fetchone()
        if row and row["path"]:
            path = data_path(row["path"])
            if path.is_file():
                return path
    fallback = settings.DATA_DIR / "library" / "sprites" / character_id / f"{name}.png"
    return fallback if fallback.is_file() else None


def half_body(source: Path, target: Path, box_from: Path) -> None:
    """Cut the top half of the figure; the crop box comes from `box_from` (the calm picture) so every frame lines up."""
    from PIL import Image

    with Image.open(box_from) as ref:
        x0, y0, x1, y1 = ref.convert("RGBA").getbbox() or (0, 0, ref.width, ref.height)
    height = (y1 - y0) * 0.52
    width = height * SIZE[0] / SIZE[1]
    top = y0 - (y1 - y0) * 0.02
    left = (x0 + x1) / 2 - width / 2
    with Image.open(source) as image:
        rgba = image.convert("RGBA")
        canvas = Image.new("RGBA", (round(width), round(height)), (0, 0, 0, 0))
        canvas.alpha_composite(rgba, (round(-left), round(-top)))  # transparent where the box leaves the picture
        target.parent.mkdir(parents=True, exist_ok=True)
        canvas.resize(SIZE, Image.LANCZOS).save(target, "WEBP", quality=88, method=6)


@router.get("")
async def get_assistant(db: aiosqlite.Connection = Depends(get_db)) -> dict:
    started_at = time.perf_counter()
    found = await _assistant(db)
    return ok({"name": found["name"] if found else None, "available": bool(found)}, started_at=started_at)


@router.get("/frames/{name}.webp")
async def get_frame(name: str, db: aiosqlite.Connection = Depends(get_db)) -> FileResponse:
    if name not in FRAMES:
        raise ValidationError(f"Unknown frame '{name}'")
    found = await _assistant(db)
    if not found:
        raise NotFoundError("The assistant character is not in the library")
    source = await _sprite(db, found["id"], name)
    calm = await _sprite(db, found["id"], "calm__closed")
    if not source or not calm:
        raise NotFoundError(f"The assistant has no '{name}' picture")
    target = settings.DATA_DIR / "cache" / "assistant" / found["id"] / f"{name}.webp"
    if not target.is_file() or target.stat().st_mtime < max(source.stat().st_mtime, calm.stat().st_mtime):
        half_body(source, target, calm)
    return FileResponse(target, media_type="image/webp", headers={"Cache-Control": "max-age=3600"})
