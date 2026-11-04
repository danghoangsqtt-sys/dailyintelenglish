# Phase 95 — project layout and clean-up (plan, written before any move)

Owner (2026-11-04, /vp-audit): split the tree into backend and frontend, packaging outside them, delete old builds,
old test runs, old source and junk. Findings and constraints: `.viepilot/audit-report.md`.

## Owner decisions

- Layout: as proposed, **but the renderer goes into `backend/`** (it is Node, run by the backend to render video).
- Delete: old package builds (~5 GB), old install backups + `build/` + tool caches (~1.6 GB), unused scripts,
  October backups (~700 MB, incl. `old-branches-20261022.bundle`).
- Rejected UI prototypes (v2–v6, A–D): delete, keep direction E only.

## Target layout

- `backend/tests/` <- `tests/` (pytest.ini `testpaths`; `parent.parent`/`parents[1]` roots in tests become one level deeper)
- `backend/scripts/` <- maintenance scripts (`check_dependencies`, `cleanup_*`, `library_package`, `build_lineart_icons`,
  `run_ai_operational_trial`, `live_provider_contract_check`, `start_studio.ps1`); their ROOT gets one more `parent`
- `backend/requirements.txt` <- `requirements.txt`
- `backend/renderer/` <- `renderer/` (whole folder incl. untracked node_modules): `core/paths.py` RENDERER_DIR and the
  runtime check, `dashboard_service.py` / `thumbnail_compose.py` logo paths, spec `datas`, `build_exe.ps1`,
  `renderer/scripts/*.mjs` (`../frontend` -> `../../frontend`), `build_lineart_icons.py`, `cleanup_workspace.py`,
  `start_studio.ps1`, the safe-zone test
- `installer/` <- spec, `assets/app.ico`, `package_desktop.ps1`, `install_desktop.ps1`, `build_exe.ps1`,
  `create_setup_zip.py`, `desktop_upgrade.py`, `verify_desktop_upgrade.py`, `setup_vieneu.ps1`
- Stay: `data/` (absolute paths in the DB), `dist/`, `docs/`, `.viepilot/`, `.venv*`, `.remotion`, `backend/ai/models`

## Deletions (git rm for tracked, Recycle Bin for the rest)

- `dist/2.0-phase86d-20261029`, `2.0-phase87-20261103`, `2.0-phase88-20261103`, `2.0-phase94-20261104`, `2.0-library-20261104`
- `build/`, `.pytest_cache`, `.ruff_cache`, `.cache`
- `data/backups/desktop-*` except `desktop-20261104-083008-440`; `old-branches-20261022.bundle`,
  `library-characters-sprites-before-phase33-*.tgz`, `app-before-cleanup-*.db`, `edge-*`, `automation`
- `scripts/archive_old_shots.py`, `scripts/benchmarks/`, `migrate_character_profiles_v2.py`,
  `generate_cefr_review_samples.py`, `verify_ai_baseline.py`, `qualify_local_ai.py`, `generate_api_docs.py`,
  `verify_solo_media.py` (and any test that only covers them)
- `.viepilot/ui-direction/session-2026-11-03-ia/`, and `a-board.html`, `b-studio.html`, `c-bento.html`, `d-friendly.html`
  in `session-2026-11-03-alt/`

## Order and verification

1. This plan committed. 2. Moves (git mv / folder move) and path edits. 3. Deletions. 4. Full pytest.
5. Package + reinstall in the same step (the installed app checks `renderer/package.json` in the workspace), then
`/api/system/build` and a render check. 6. Docs (README tree, ARCHITECTURE, HANDOFF, TRACKER, CHANGELOG).
