# PLAN — Phase 70: library package, clean-up and release 1.5.0 (ENH-052)

Status: execution_authorized 2026-10-22 — the owner chose: delete all 15 test projects, a library package, 1.5.0, USB hand-over.

| Task | Scope |
|---|---|
| 70.1 | `backend/library/library_package.py`: `summary()`, `export_package(dest)` (manifest + table rows + files: `library/characters`, `library/sprites`, `library/activities`, `library/scenes`, `assets_background/assets`, `music_library`, `brand_voice`), `import_package(zip)` (DB backup first; refuse while a job runs; merge by primary key, newer `updated_at` wins; files copied when missing or newer; safe paths only — no `..`, no absolute paths; channel episodes lose project links the target does not have). Never exported: `app_settings` (API keys), projects and their media |
| 70.2 | API `/api/library-package` (GET summary, POST export → file in `data/exports`, GET download, POST import upload streamed to disk) and `scripts/library_package.py export|import` for USB; Settings → **Data & sync** section with the counts, Export, Import and the result |
| 70.3 | Clean-up: `scripts/cleanup_test_projects.py --all-projects` (dry-run by default, DB backup, service-layer deletes, migrations applied first) and `scripts/cleanup_workspace.py` (dry-run list with sizes; `--apply` deletes `data/tmp`, older desktop backups, `build`, `dist/*.next-*`, `renderer/public/remotion-render`, `demo_output`, `debug.log`) |
| 70.4 | Tests: package round trip into an empty data dir (rows, files, no API key), merge rules (newer wins, older kept, nothing deleted), path safety, refusal while a job runs, API and Settings browser test, clean-up dry-run; full pytest + Vitest |
| 70.5 | Release: CHANGELOG `[1.5.0]`, version 1.5.0 in the build, install guide updated (laptop, library package, low-VRAM notes), run the clean-up on the real data, build + verify + install, hand-over folder `data/exports/handoff-1.5.0`, tag `v1.5.0`, push |

Kept: every feature; nothing in the package can overwrite a newer row or delete anything.
