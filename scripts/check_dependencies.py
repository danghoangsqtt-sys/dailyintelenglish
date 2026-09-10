"""Verify the local machine is ready to run Daily Intel English Studio.

Usage:
    python scripts/check_dependencies.py
"""

import shutil
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.core.config import settings  # noqa: E402

PROJECT_ROOT = Path(__file__).resolve().parent.parent
MIN_PYTHON = (3, 11)
REQUIRED_DATA_DIRS = [
    "data/audio",
    "data/music_library",
    "data/projects",
    "data/thumbnails",
    "data/tts_cache",
    "data/video",
]


def check_python_version() -> tuple[bool, str]:
    """Verify the running interpreter is Python 3.11+."""
    ok = sys.version_info[:2] >= MIN_PYTHON
    return ok, f"Python {sys.version.split()[0]}"


def check_ffmpeg() -> tuple[bool, str]:
    """Verify the configured ffmpeg binary (settings.FFMPEG_PATH) is installed and runnable.

    Mirrors the resolution logic in app.core.system_checks.check_ffmpeg so both
    the startup check and this CLI script agree on which binary is actually used.
    """
    configured = settings.FFMPEG_PATH
    ffmpeg_path = shutil.which(configured) or configured
    try:
        result = subprocess.run(
            [ffmpeg_path, "-version"], capture_output=True, text=True, timeout=10
        )
        version_line = result.stdout.splitlines()[0] if result.stdout else ffmpeg_path
        return result.returncode == 0, version_line
    except (subprocess.SubprocessError, OSError):
        return False, f"'{configured}' not found in PATH (DIE_FFMPEG_PATH)"


def check_gpu() -> tuple[bool, str]:
    """Verify an NVIDIA GPU is visible via nvidia-smi and report VRAM size."""
    nvidia_smi = shutil.which("nvidia-smi")
    if nvidia_smi is None:
        return False, "nvidia-smi not found — GPU features (OmniVoice, LivePortrait) unavailable"
    try:
        result = subprocess.run(
            [nvidia_smi, "--query-gpu=name,memory.total", "--format=csv,noheader"],
            capture_output=True,
            text=True,
            timeout=10,
        )
        if result.returncode != 0 or not result.stdout.strip():
            return False, "nvidia-smi ran but reported no GPU"
        name, memory_total = (part.strip() for part in result.stdout.strip().splitlines()[0].split(","))
        return True, f"{name} ({memory_total})"
    except (subprocess.SubprocessError, OSError, ValueError) as exc:
        return False, f"nvidia-smi found but failed to run: {exc}"


PLACEHOLDER_API_KEY = "your_gemini_api_key_here"


def check_env_file() -> tuple[bool, str]:
    """Verify DIE_GEMINI_API_KEY resolves to a real value via settings.

    settings.GEMINI_API_KEY already reflects the process environment first,
    falling back to `.env` (see app.core.config.Settings), so this checks the
    same source of truth the app itself uses instead of re-parsing `.env`.
    """
    api_key = settings.GEMINI_API_KEY
    if api_key and api_key != PLACEHOLDER_API_KEY:
        return True, "DIE_GEMINI_API_KEY is set"
    if not (PROJECT_ROOT / ".env").exists():
        return False, "DIE_GEMINI_API_KEY not set (no env var, and .env not found — copy .env.example to .env)"
    return False, "DIE_GEMINI_API_KEY is empty or still a placeholder"


def check_omnivoice_model() -> tuple[bool, str]:
    """Verify the OmniVoice model directory exists and is non-empty."""
    model_path = settings.OMNIVOICE_MODEL_PATH
    if not model_path.is_absolute():
        model_path = PROJECT_ROOT / model_path
    if not model_path.exists():
        return False, f"model path not found: {model_path}"
    if not any(model_path.iterdir()):
        return False, f"model path is empty: {model_path}"
    return True, f"model files present at {model_path}"


def check_data_dirs() -> tuple[bool, str]:
    """Verify (and create) the runtime data directories."""
    missing = []
    for rel_dir in REQUIRED_DATA_DIRS:
        path = PROJECT_ROOT / rel_dir
        if not path.exists():
            path.mkdir(parents=True, exist_ok=True)
            missing.append(rel_dir)
    if missing:
        return True, f"created missing dirs: {', '.join(missing)}"
    return True, "all data directories present"


def main() -> int:
    """Run all checks and print a GREEN/RED report; exit 1 if any check fails."""
    checks = [
        ("Python >= 3.11", check_python_version),
        ("ffmpeg", check_ffmpeg),
        ("NVIDIA GPU", check_gpu),
        (".env / GEMINI_API_KEY", check_env_file),
        ("OmniVoice model", check_omnivoice_model),
        ("data/ directories", check_data_dirs),
    ]

    all_passed = True
    print("Daily Intel English Studio - Dependency Check\n" + "-" * 48)
    for label, check_fn in checks:
        passed, detail = check_fn()
        status = "GREEN" if passed else "RED"
        print(f"[{status}] {label}: {detail}")
        all_passed = all_passed and passed

    print("-" * 48)
    print("All checks passed." if all_passed else "Some checks failed - see RED lines above.")
    return 0 if all_passed else 1


if __name__ == "__main__":
    sys.exit(main())
