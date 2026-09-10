"""Verify the local machine is ready to run Daily Intel English Studio.

Usage:
    python scripts/check_dependencies.py
"""

import shutil
import subprocess
import sys
from pathlib import Path

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
    """Verify ffmpeg is installed and runnable from PATH."""
    ffmpeg_path = shutil.which("ffmpeg")
    if ffmpeg_path is None:
        return False, "ffmpeg not found in PATH"
    try:
        result = subprocess.run(
            [ffmpeg_path, "-version"], capture_output=True, text=True, timeout=10
        )
        version_line = result.stdout.splitlines()[0] if result.stdout else ffmpeg_path
        return result.returncode == 0, version_line
    except (subprocess.SubprocessError, OSError) as exc:
        return False, f"ffmpeg found but failed to run: {exc}"


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


def check_env_file() -> tuple[bool, str]:
    """Verify .env exists and GEMINI_API_KEY is set to a non-placeholder value."""
    env_path = PROJECT_ROOT / ".env"
    if not env_path.exists():
        return False, ".env file not found (copy .env.example to .env)"
    content = env_path.read_text(encoding="utf-8")
    for line in content.splitlines():
        if line.strip().startswith("GEMINI_API_KEY="):
            value = line.split("=", 1)[1].strip()
            if value and value != "your_gemini_api_key_here":
                return True, "GEMINI_API_KEY is set"
            return False, "GEMINI_API_KEY is empty or still a placeholder"
    return False, "GEMINI_API_KEY not found in .env"


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
