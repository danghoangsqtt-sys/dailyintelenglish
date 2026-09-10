"""TTS engine discovery routes. Line generation lands in Task 1.6."""

import shutil
import time

from fastapi import APIRouter

from app.core.config import settings
from app.core.responses import ok

router = APIRouter(prefix="/api/tts", tags=["tts"])


@router.get("/engines")
async def list_engines() -> dict:
    """Report which TTS engines are currently usable on this machine.

    OmniVoice availability is based on the model directory existing —
    actual model loading and GPU checks happen at startup / in
    scripts/check_dependencies.py, not on every request here.
    """
    started_at = time.perf_counter()
    engines = [
        {
            "id": "omnivoice",
            "available": settings.OMNIVOICE_MODEL_PATH.exists(),
            "kind": "local_gpu",
        },
        {"id": "edge_tts", "available": True, "kind": "online_free"},
        {
            "id": "piper",
            "available": shutil.which("piper") is not None,
            "kind": "local_offline",
        },
    ]
    return ok(engines, started_at=started_at)
