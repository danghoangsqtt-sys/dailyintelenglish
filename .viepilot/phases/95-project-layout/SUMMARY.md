# Phase 95 summary — project layout and clean-up (2026-11-04)

## New layout

`backend/` (app, `tests/`, `scripts/`, `renderer/`, `requirements.txt`), `frontend/`, `installer/` (spec, icon, package and
install scripts, `HUONG-DAN-SU-DUNG.txt`), `dist/` (packages + the installed app), `data/` (live data, cannot move: the DB
holds absolute paths), `docs/`, `.viepilot/`. `pytest.ini` stays at the root so tests run from the repository root.

Moved with `git mv` so history follows. `tests` is now the package `backend.tests`. The spec resolves from `SPECPATH`.

## Removed

To the Recycle Bin (owner can restore; the disk space returns when it is emptied): old package builds, old install backups,
`build/`, tool caches, October backups, rejected UI prototypes' untracked files; from `data/` (1.44 GB + 86 MB):
- inbox pictures byte-identical to their library copies (`library/activities_inbox`, `library/sprites_inbox`);
- 3 old renders and 4 old audio mixes of one project that no DB row names (its current video stays);
- render and worker logs, old run evidence (`quality_reviews`);
- `library/front21-male-20261020` (an abandoned generation folder no DB row names; approved pictures are in the library);
- `assets_sprites` (no code uses it; also leaves git).

Kept on purpose: `library/sprites` and `library/characters` (both read by the code), project `explainer/` copies of activity
pictures (a project's snapshot), `assets_background` (the source of the Import backgrounds button), `tts_cache`.

Git: 8 unused scripts, their tests (`test_generate_cefr_review_samples`, `test_phase44_remove_sdxl_shots`, one migration test).
Prototype E keeps its icons and Lina frames in its own folder.

## Package

`installer/package_desktop.ps1` now also makes `DailyBeyondEnglishStudio-<version>-Source.zip` (the workspace both editions
need) and puts `HUONG-DAN-SU-DUNG.txt` in the output folder and in each ZIP; the stale SETUP.txt text is gone.

## Installed

Full 2.0.0 from 70f97200 runs on port 8000 (data counts unchanged: 118 projects, 5 characters, 226 character assets). The
renderer's bundle and one rendered still frame were checked after the move; the typecheck in the build caught two imports
of `frontend/` that the path script had missed (70f97200). No full video was rendered through the app.

## Not done

- `data/tmp`: 7 folders from 2026-10-16 refuse access (even reading their permissions); left in place.
- Follow-ups from the audit: SDXL leftovers in code; the Qwen-Image-2512 model cache may be unused; root `.remotion` (269 MB)
  looks unused because Remotion keeps its browser in `backend/renderer/node_modules/.remotion`.
