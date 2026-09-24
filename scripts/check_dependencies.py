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


def check_ollama() -> tuple[bool, str]:
    """Verify Ollama is reachable and the configured model is pulled.

    Task 14.7 (Amendment D): local-only release path -- Ollama is now a hard
    requirement to *generate* (not to *start*, Phase 13 invariant 9 stays).
    Mirrors app/api/ai_jobs.py's own /api/ai/health probe rather than
    importing it, matching this script's existing "checks the same source of
    truth the app itself uses, independently" style (see check_ffmpeg).
    """
    import httpx

    base_url = settings.OLLAMA_BASE_URL
    try:
        with httpx.Client(base_url=base_url, timeout=5.0) as client:
            version_response = client.get("/api/version")
            if version_response.status_code != 200:
                return False, f"Ollama not reachable at {base_url} — install: https://ollama.com/download"
            tags_response = client.get("/api/tags")
            tags_response.raise_for_status()
            for model in tags_response.json().get("models", []):
                if settings.OLLAMA_MODEL in (model.get("name"), model.get("model")):
                    digest = (model.get("digest") or "")[:12]
                    return True, f"{settings.OLLAMA_MODEL} present (digest {digest})"
            return False, f"model not pulled — run: ollama pull {settings.OLLAMA_MODEL}"
    except (httpx.HTTPError, OSError) as exc:
        return False, f"Ollama not reachable at {base_url}: {exc} — install: https://ollama.com/download"


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


def check_cloud_provider() -> tuple[bool, str]:
    """Report whether the OpenAI-compatible cloud provider (Task 18.3, ENH-011)
    is configured -- informational only, same as the Gemini check it replaces:
    a fresh install runs local-only by default (AI_MODE=local), so this is
    never required, only useful to know before switching Settings to cloud_first.

    settings.OPENAI_COMPAT_API_KEY/_MODEL already reflect the process
    environment first, falling back to `.env` then any DB-stored Settings-page
    value (see app.core.config.Settings / app.services.settings_service), so
    this checks the same source of truth the app itself uses instead of
    re-parsing `.env`.
    """
    if settings.OPENAI_COMPAT_API_KEY and settings.OPENAI_COMPAT_MODEL:
        return True, f"configured (model: {settings.OPENAI_COMPAT_MODEL})"
    return False, "not configured -- set via the Settings page, or DIE_OPENAI_COMPAT_API_KEY/_MODEL in .env"


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
    """Run all checks and print a GREEN/RED report; exit 1 if any required check fails.

    Task 14.7 (Amendment D): Ollama + the configured model are required
    (local-only is always the fallback and default AI_MODE). The cloud
    provider (Task 18.3, ENH-011) is informational only -- still reported,
    never failing the overall check -- since AI_MODE defaults to "local"
    regardless of whether it's configured.
    """
    required_checks = [
        ("Python >= 3.11", check_python_version),
        ("ffmpeg", check_ffmpeg),
        ("NVIDIA GPU", check_gpu),
        ("Ollama + model", check_ollama),
        ("OmniVoice model", check_omnivoice_model),
        ("data/ directories", check_data_dirs),
    ]
    informational_checks = [
        ("Cloud provider (optional — see Settings page)", check_cloud_provider),
    ]

    all_passed = True
    print("Daily Intel English Studio - Dependency Check\n" + "-" * 48)
    for label, check_fn in required_checks:
        passed, detail = check_fn()
        status = "GREEN" if passed else "RED"
        print(f"[{status}] {label}: {detail}")
        all_passed = all_passed and passed

    for label, check_fn in informational_checks:
        passed, detail = check_fn()
        status = "GREEN" if passed else "YELLOW"
        print(f"[{status}] {label}: {detail}")

    print("-" * 48)
    print("All checks passed." if all_passed else "Some checks failed - see RED lines above.")
    return 0 if all_passed else 1


if __name__ == "__main__":
    sys.exit(main())
