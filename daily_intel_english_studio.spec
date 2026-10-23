# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller spec for the standalone Windows build (Task 12.2).

onedir, not onefile: faster startup (no self-extraction on every launch) and
easier to diagnose if a resource is missing -- see task-12.2.md for the reasoning.

`frontend/`, `prompts/`, and `backend/db/migrations/` are staged as plain data at the
same relative paths backend.core.paths.get_project_root() expects to find them under
sys._MEIPASS at runtime.
"""

from PyInstaller.utils.hooks import collect_all
from pathlib import Path

if not Path("frontend/static/solo-preview/player.js").is_file():
    raise RuntimeError("Build the Solo preview first: npm --prefix renderer run build:preview")

datas = [
    ("frontend", "frontend"),
    ("backend/ai/prompts", "backend/ai/prompts"),
    ("backend/db/migrations", "backend/db/migrations"),
    # The separate CUDA interpreter needs a real script file outside PyInstaller's archive.
    ("backend/ai/tts/omnivoice_worker.py", "backend/ai/tts"),
    ("renderer/public/brand", "renderer/public/brand"),
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

# Keep model stacks in the separate image environment. Librosa and its CPU
# dependencies are needed by music analysis and must remain in the desktop build.
excludes = [
    "torch",
    "torchaudio",
    "transformers",
    "tensorflow",
    "grpc",
    "hf_xet",
    "tokenizers",
    "pandas",
]

a = Analysis(
    ["backend/desktop_launcher.py"],
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
    # Desktop bootstrap retains diagnostics in data/logs/desktop.log.
    console=False,
    icon="assets/app.ico",
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
