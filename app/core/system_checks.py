"""Non-blocking checks for external tooling (ffmpeg, GPU) used at startup and /health."""

import asyncio
import shutil

from app.core.config import settings


async def check_ffmpeg() -> bool:
    """Return True if the configured ffmpeg binary is runnable."""
    ffmpeg_path = shutil.which(settings.FFMPEG_PATH) or settings.FFMPEG_PATH
    try:
        process = await asyncio.create_subprocess_exec(
            ffmpeg_path,
            "-version",
            stdout=asyncio.subprocess.DEVNULL,
            stderr=asyncio.subprocess.DEVNULL,
        )
        await process.wait()
        return process.returncode == 0
    except (FileNotFoundError, OSError):
        return False


async def get_gpu_info() -> dict | None:
    """Return NVIDIA GPU name + total VRAM via nvidia-smi, or None if unavailable."""
    nvidia_smi = shutil.which("nvidia-smi")
    if nvidia_smi is None:
        return None
    try:
        process = await asyncio.create_subprocess_exec(
            nvidia_smi,
            "--query-gpu=name,memory.total",
            "--format=csv,noheader",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.DEVNULL,
        )
        stdout, _ = await process.communicate()
        if process.returncode != 0:
            return None
        first_line = stdout.decode("utf-8", errors="ignore").strip().splitlines()[0]
        name, memory_total = (part.strip() for part in first_line.split(","))
        return {"name": name, "memory_total": memory_total}
    except (FileNotFoundError, OSError, IndexError, ValueError):
        return None


async def get_gpu_memory() -> dict | None:
    """Return live VRAM use in MiB (`used_mb`/`free_mb`/`total_mb`), or None.

    Task 20.1 (D20.1-d): the GPU model manager's one source of truth for "is there
    room". Same `nvidia-smi` instrument every recorded Phase 19/21 measurement used
    (e.g. the 3916 MiB free with qwen loaded behind the StyleTTS 2 threshold), so the
    runtime check and the thresholds agree -- and no new dependency in the packaged
    .exe (pynvml) and no torch in the main venv. None on a machine with no NVIDIA
    driver, which every caller treats as "no usable GPU".
    """
    nvidia_smi = shutil.which("nvidia-smi")
    if nvidia_smi is None:
        return None
    try:
        process = await asyncio.create_subprocess_exec(
            nvidia_smi,
            "--query-gpu=memory.used,memory.free,memory.total",
            "--format=csv,noheader,nounits",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.DEVNULL,
        )
        stdout, _ = await process.communicate()
        if process.returncode != 0:
            return None
        first_line = stdout.decode("utf-8", errors="ignore").strip().splitlines()[0]
        used_mb, free_mb, total_mb = (int(part.strip()) for part in first_line.split(","))
        return {"used_mb": used_mb, "free_mb": free_mb, "total_mb": total_mb}
    except (FileNotFoundError, OSError, IndexError, ValueError):
        return None
