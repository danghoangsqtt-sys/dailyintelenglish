# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller spec for the standalone Windows build (Task 12.2).

onedir, not onefile: faster startup (no self-extraction on every launch) and
easier to diagnose if a resource is missing -- see task-12.2.md for the reasoning.

`frontend/`, `prompts/`, and `app/db/migrations/` are staged as plain data at the
same relative paths app.core.paths.get_project_root() expects to find them under
sys._MEIPASS at runtime.
"""

from PyInstaller.utils.hooks import collect_all

datas = [
    ("frontend", "frontend"),
    ("prompts", "prompts"),
    ("app/db/migrations", "app/db/migrations"),
]
binaries = []
hiddenimports = []

# uvicorn resolves several of its own submodules dynamically (protocol/loop
# implementations) -- collect_all avoids guessing which ones PyInstaller's static
# analysis would otherwise miss.
for package in ("uvicorn",):
    pkg_datas, pkg_binaries, pkg_hiddenimports = collect_all(package)
    datas += pkg_datas
    binaries += pkg_binaries
    hiddenimports += pkg_hiddenimports

# This app's real requirements.txt needs none of these -- they were pulled in
# purely because the dev venv also has leftover packages installed from the
# abandoned OmniVoice GPU experimentation (Phase 1; _synthesize_omnivoice() is a
# hardcoded stub today, see app/services/tts_service.py). Confirmed via a repo-wide
# grep that no file under app/ imports any of them. Without this list, PyInstaller's
# static analysis still finds them importable in site-packages and balloons the
# build to ~4.5GB (torch alone, with bundled CUDA kernels, is ~4GB) for a plain
# FastAPI + SQLite + Pillow + pydub app.
excludes = [
    "torch",
    "torchaudio",
    "transformers",
    "tensorflow",
    "sklearn",
    "librosa",
    "numba",
    "llvmlite",
    "grpc",
    "hf_xet",
    "tokenizers",
    "pandas",
]

a = Analysis(
    ["app/desktop_launcher.py"],
    pathex=[],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=excludes,
    noarchive=False,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="DailyIntelEnglishStudio",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    # Keeps a visible console window so uvicorn's own startup log (and any
    # ffmpeg/GPU-missing warning) is visible on first run -- a silent windowed
    # exe would hide exactly the errors a trial user most needs to see.
    console=True,
    disable_windowed_traceback=False,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    name="DailyIntelEnglishStudio",
)
