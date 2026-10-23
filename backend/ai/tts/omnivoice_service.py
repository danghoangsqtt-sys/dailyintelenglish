"""Run one local OmniVoice synthesis in an isolated environment and GPU lease."""

from __future__ import annotations

import asyncio
import json
import logging
import os
import subprocess
import tempfile
from pathlib import Path

from backend.ai.image.gpu_model_manager import get_gpu_manager
from backend.core.config import settings
from backend.core.constants import OMNIVOICE_MIN_FREE_MB, OMNIVOICE_REQUEST_TIMEOUT_SECONDS
from backend.core.exceptions import TTSError
from backend.core.paths import get_project_root, get_runtime_root

logger = logging.getLogger(__name__)


def _python_path() -> Path:
    configured = settings.OMNIVOICE_PYTHON
    if configured:
        return configured
    return get_runtime_root() / ".venv-omnivoice" / ("Scripts/python.exe" if os.name == "nt" else "bin/python")


def _worker_path() -> Path:
    """Resolve the plain worker script from source or PyInstaller's bundled resources."""
    return get_project_root() / "backend" / "ai" / "tts" / "omnivoice_worker.py"


def _model_path() -> Path:
    return settings.OMNIVOICE_MODEL_PATH or settings.DATA_DIR / "models" / "omnivoice"


def is_available() -> bool:
    """Whether the dedicated interpreter and complete local model directory exist."""
    model = _model_path()
    if not _python_path().is_file() or not model.is_dir() or not (model / "config.json").is_file():
        return False
    try:
        return any(
            path.stat().st_size >= 128 * 1024 * 1024
            for suffix in ("*.safetensors", "*.bin")
            for path in model.glob(suffix)
        )
    except OSError:
        return False


def _voice_instruction(speaker: dict) -> str:
    gender = speaker.get("gender")
    accent = (speaker.get("accent") or "american").replace("_", " ")
    pitch_value = float(speaker.get("pitch") or 0.0)
    pitch = "low" if pitch_value < -0.35 else "high" if pitch_value > 0.35 else "moderate"
    attributes = ([gender] if gender in {"male", "female"} else []) + [f"{pitch} pitch", f"{accent} accent"]
    description = (speaker.get("voice_description") or "").strip()
    if description:
        attributes.append(description)
    return ", ".join(attributes)


def _run_worker_sync(payload: dict) -> bytes:
    python = _python_path()
    model = _model_path()
    if not python.is_file():
        raise TTSError(f"OmniVoice environment is not installed: {python}")
    if not is_available():
        raise TTSError(f"OmniVoice local model is missing: {model}. Run scripts/setup_omnivoice.ps1 first.")

    with tempfile.TemporaryDirectory(prefix="omnivoice-") as temp_dir:
        output_path = Path(temp_dir) / "speech.wav"
        request = {**payload, "model_path": str(model), "output_path": str(output_path)}
        try:
            result = subprocess.run(
                [str(python), str(_worker_path())],
                input=json.dumps(request, ensure_ascii=False),
                capture_output=True,
                text=True,
                encoding="utf-8",
                timeout=settings.OMNIVOICE_TIMEOUT_SECONDS or OMNIVOICE_REQUEST_TIMEOUT_SECONDS,
                env={**os.environ, "HF_HUB_OFFLINE": "1", "TRANSFORMERS_OFFLINE": "1", "PYTHONUTF8": "1"},
                check=False,
                cwd=str(get_runtime_root()),
            )
        except subprocess.TimeoutExpired as exc:
            raise TTSError("OmniVoice synthesis timed out. Check the model and GPU setup.") from exc
        if result.returncode != 0:
            # Worker stderr is intentionally omitted: third-party errors can include input text.
            logger.error("OmniVoice worker failed exit_code=%s", result.returncode)
            try:
                error = json.loads(result.stdout).get("error")
            except (json.JSONDecodeError, AttributeError):
                error = None
            raise TTSError(f"OmniVoice synthesis failed: {error or 'worker error'}")
        if not output_path.is_file() or output_path.stat().st_size < 44:
            raise TTSError("OmniVoice worker produced no valid WAV audio.")
        return output_path.read_bytes()


async def synthesize(text: str, speaker: dict) -> bytes:
    """Generate a complete line in Voice Design mode under the shared exclusive GPU lease."""
    if not is_available():
        raise TTSError(
            "OmniVoice is selected but its local environment/model is not ready. "
            "Run scripts/setup_omnivoice.ps1; no other TTS engine was used."
        )
    payload = {
        "text": text,
        "instruct": _voice_instruction(speaker),
        "speed": float(speaker.get("speed") if speaker.get("speed") is not None else 1.0),
    }
    manager = get_gpu_manager()
    try:
        async with manager.lease("omnivoice", settings.OMNIVOICE_MIN_FREE_MB or OMNIVOICE_MIN_FREE_MB):
            worker = asyncio.create_task(asyncio.to_thread(_run_worker_sync, payload))
            try:
                return await asyncio.shield(worker)
            except asyncio.CancelledError:
                # Keep the exclusive lease until the subprocess exits; cancelling
                # to_thread alone cannot stop its CUDA process.
                try:
                    await asyncio.shield(worker)
                except Exception:
                    pass
                raise
    except TTSError:
        raise
    except Exception as exc:
        raise TTSError(f"OmniVoice could not acquire GPU or synthesize the line: {exc}") from exc
