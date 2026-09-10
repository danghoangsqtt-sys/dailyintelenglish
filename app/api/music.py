"""Music library listing routes. Upload/delete UI lands in Task 1.10."""

import asyncio
import time

from fastapi import APIRouter

from app.core.config import settings
from app.core.responses import ok

router = APIRouter(prefix="/api/music", tags=["music"])

AUDIO_EXTENSIONS = {".mp3", ".wav", ".ogg", ".m4a"}


def _list_music_files() -> list[dict]:
    music_dir = settings.DATA_DIR / "music_library"
    music_dir.mkdir(parents=True, exist_ok=True)
    return [
        {"filename": f.name, "size_bytes": f.stat().st_size}
        for f in sorted(music_dir.iterdir())
        if f.is_file() and f.suffix.lower() in AUDIO_EXTENSIONS
    ]


@router.get("")
async def list_music() -> dict:
    """List background music tracks available in the local music library."""
    started_at = time.perf_counter()
    tracks = await asyncio.to_thread(_list_music_files)
    return ok(tracks, started_at=started_at)
