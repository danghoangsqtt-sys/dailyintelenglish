# Audit — project folder layout and clean-up (2026-11-04)

Owner: "bố cục cây thư mục của dự án khá rối rắm … chia ra làm 2 thư mục lớn là backend và frontend … thư mục chứa
file cài đặt đưa ra bên ngoài … xóa bản cài đặt cũ, các tệp chạy thử cũ, tệp mã nguồn cũ, xử lý rác".
Measured on commit 72f7b5b0. Acted on in [Phase 95](phases/95-project-layout/SUMMARY.md): the renderer went into `backend/`, not `frontend/`, by the owner's choice.

## What is at the top level today

| Entry | Size | Tracked files | What it is |
| --- | ---: | ---: | --- |
| `backend/` | 54 GB | 239 | Python app; 53 GB of it is `backend/ai/models` (Qwen image + VieNeu weights, gitignored) |
| `frontend/` | small | 141 | pages, JS, CSS |
| `renderer/` | 540 MB | 97 | Remotion (React/TS) video renderer, run by the backend through Node; also builds `frontend/static/solo-preview` |
| `tests/` | small | 224 | pytest (unit + browser) |
| `scripts/` | small | 27 | build/install scripts mixed with one-off maintenance scripts |
| `assets/` | 156 KB | 1 | `app.ico` only (used by the PyInstaller spec) |
| `daily_intel_english_studio.spec`, `requirements.txt`, `pytest.ini` | | 3 | build spec, Python deps, test config |
| `data/` | 8.4 GB | 62 | live app data (DB, videos, audio, library) |
| `dist/` | 6.8 GB | 0 | package outputs **and the installed app** (`dist/DailyIntelEnglishStudio`) |
| `build/` | 92 MB | 0 | PyInstaller work folder (rebuilt every package run) |
| `docs/`, `.viepilot/`, `CHANGELOG.md`, `README.md`, `LICENSE` | 25 MB | | documentation and project state |
| `.venv`, `.venv-image`, `.venv-vieneu`, `.remotion` | | 0 | Python envs for the app / image worker / VieNeu; Remotion's headless Chrome |
| `.pytest_cache`, `.ruff_cache`, `.cache` | ~0 | 0 | tool caches |

## Hard constraints found (these decide what may move)

1. **`data/` cannot move.** The DB stores absolute paths `D:\DataAdmin\Daily_Intel_English\data\…` in 1,800+ rows
   (script line audio 550, thumbnails 264, character assets 226, activity library 188, video jobs 88, …).
2. **The installed app runs from this repo.** `dist/DailyIntelEnglishStudio/studio-runtime.json` sets
   `workspace_dir = ..\..` and `data_dir = ..\..\data`; at start it checks for `renderer/package.json` and
   `backend/ai/image/image_worker.py` and uses `.venv-image`, `.venv-vieneu` and `backend/ai/models` (`backend/core/paths.py`).
   Any move of `renderer/` or of the installed folder needs a rebuild and reinstall in the same step, or the app breaks.
3. **`backend/ai/models` (53 GB) stays where it is.** It is already inside `backend/`; moving it is a 53 GB copy for nothing.
4. Hard-coded path references outside docs: `renderer/` 20 files, `tests/` 37, `scripts/` 27, `frontend/` 21,
   `.venv-image` 13, spec 4, `requirements.txt` 4. All fixable with `git mv` + edits, then the full test run.
5. No orphaned project output: every folder in `data/video`, `audio`, `thumbnails`, `explainer` belongs to a project in the DB.

## Proposed layout

```
Daily_Intel_English/
├── backend/            Python app (as today)
│   ├── tests/          ← tests/            (pytest.ini follows)
│   ├── scripts/        ← maintenance scripts from scripts/ (cleanup, library_package, check_dependencies, …)
│   └── requirements.txt ← requirements.txt
├── frontend/           pages, JS, CSS (as today)
│   └── renderer/       ← renderer/  (the video renderer and the Solo preview player; RENDERER_DIR, spec, runtime check updated)
├── installer/          ← everything that builds and installs the desktop app:
│   │                     daily_intel_english_studio.spec, assets/app.ico, package_desktop.ps1, install_desktop.ps1,
│   │                     build_exe.ps1, create_setup_zip.py, desktop_upgrade.py, verify_desktop_upgrade.py, setup_vieneu.ps1
├── dist/               package outputs + the installed app (outside backend/frontend, as asked)
├── data/               live data — cannot move (constraint 1)
├── docs/  .viepilot/  README.md  CHANGELOG.md  LICENSE  .env.example  .gitignore
└── .venv  .venv-image  .venv-vieneu  .remotion   (environments, gitignored; stay at the root)
```

## Clean-up candidates (each needs the owner's yes)

| Item | Size | Why it is junk | Proposed |
| --- | ---: | --- | --- |
| `dist/2.0-phase86d-20261029`, `2.0-phase87-20261103`, `2.0-phase88-20261103`, `2.0-phase94-20261104` | 4.97 GB | old package builds; the installed app is 72f7b5b0 | delete |
| `dist/2.0-library-20261104` | 0 | empty folder from today's failed package run | delete |
| `build/` | 92 MB | PyInstaller work folder, recreated by every package run | delete (and gitignore stays) |
| `data/backups/desktop-*` (6 folders) | 1.95 GB | copies of earlier installs; keep the newest (`desktop-20261104-083008-440`) | delete 5, keep 1 |
| `data/backups/old-branches-20261022.bundle` | 589 MB | git bundle of branches deleted on 2026-10-22 | owner decides |
| `data/backups/library-characters-sprites-before-phase33-…tgz`, `app-before-cleanup-…db`, `edge-*`, `automation` | 105 MB | backups from before Phases 33/41 (October) | owner decides |
| `.pytest_cache`, `.ruff_cache`, `.cache` | ~0 | tool caches | delete |
| `scripts/archive_old_shots.py`, `scripts/benchmarks/image_models/bench_realvisxl.py` | | shots and SDXL were removed (D123) | delete with their tests if any |
| `scripts/migrate_character_profiles_v2.py`, `generate_cefr_review_samples.py`, `verify_ai_baseline.py`, `qualify_local_ai.py`, `generate_api_docs.py`, `verify_solo_media.py` | | one-off scripts nothing calls (Sept–Oct) | delete after a reference check |
| `.viepilot/ui-direction/session-2026-11-03-ia` (v2–v6) and the rejected A–D pages | ~2 MB | rejected UI prototypes; E is the accepted one | owner decides (they are history) |

Not junk: `data/video` 2.9 GB, `data/audio` 1.0 GB, `data/library` 1.4 GB (all belong to live projects),
`renderer/node_modules`, `.remotion`, the three `.venv*`, `backend/ai/models`.

## Found but outside this clean-up (follow-ups)

- **SDXL leftovers in code** after D123: `backend/ai/image/pipelines.py`, `image_worker.py`, `core/config.py`,
  `main.py`, `schemas/video.py`, `frontend/static/js/step5_video.js`, `shot_library.js`, and tests that mention it.
  Removing dead code is a code change of its own.
- **`models--Qwen--Qwen-Image-2512`** in the model cache is not named anywhere in the code (the app uses
  Qwen-Image-2.1-Turbo and Qwen-Image-Edit-2511); its blobs may be several GB. Check before deleting.

## How it would run (if approved)

1. A phase plan with the exact move list, committed before any move.
2. `git mv` for every tracked move (history kept); path edits in code, spec, scripts, tests, `.gitignore`, docs.
3. Full pytest, then package + reinstall in the same step (constraint 2), then check the running app.
4. Deletions only from the list the owner approves; the Recycle Bin for anything not in git.
