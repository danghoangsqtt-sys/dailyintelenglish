# Task 28.4a: Scene plates in the new look (the 55 built-in scenes)

## Owner request (2026-10-06)

"Recreate the scene picture library" (while the full test suite runs). The plates are the empty
backgrounds of the scene library and the scene reference of every shot, so they must match the new look
(crisp editorial photographs from RealVisXL V5.0).

## Facts

- 55 built-in scenes, each with a plate at `data/library/scenes/<id>/preview.png` (85 MB), all in the
  cel-anime look; `scenes.preview_path` is already set for all 55.
- The app's own job (`pipelines.scene_preview`) loads the model once **per plate**; for 55 plates that is
  slow. The script loads it once.
- 2 characters exist in the library (the old ones); 28.4 redoes them, not this task.
- Standing rule: back up `data/app.db` before any write to the real database.

## Paths

- `scripts/regenerate_scene_plates.py` (new; uses the app's recipes and engine, outside the web app)
- `docs/operations/phase28-scene-plates.md` (report) and `docs/operations/phase28-scene-plates/` (contact sheets)

## File-Level Plan

1. Back up `data/app.db` to `data/backups/app-before-plates-<date>.db` and the old plates to
   `data/tmp/plates-cel-anime-backup/` (outside git, 85 MB).
2. The script loads RealVisXL once through `WorkerImageEngine.session("text2img")` and, for each of the 55
   scenes, renders `recipes.scene_preview_prompt(scene)` with `PLATE_NEGATIVE`, the scene's own seed,
   1344 x 768, 30 steps, CFG 6 (the same call as the app's job). It writes the new plate to the same
   `preview.png` path, so no DB change is needed; scenes without a plate would get `preview_path` set.
3. **Check for people:** every plate is cut out by the worker's `remove_background`; a plate whose
   foreground fraction is above 0.05 is flagged and re-rendered at most twice with a different seed
   (the same idea as the app's extra-person check). The scene's seed in the DB is updated only when a
   re-render replaces it.
4. Build contact sheets (14 plates per sheet) for the owner and Claude to look at.
5. Resume support: a plate already rendered in this run (a `done.json` list) is skipped on restart.

## Verification

- 55 new plates exist, each 1344 x 768, none flagged (or flagged ones listed in the report).
- Claude looks at every contact sheet; any plate with a person, text, or a clearly wrong place is redone.
- The owner sees the sheets and can ask for specific scenes to be redone.
- Tests: the existing suite is untouched by this task (data and one script only).

## Task 28.4a closed (2026-10-06)

55 plates redone and verified (`docs/operations/phase28-scene-plates.md`); the market was redone with a
plate-only wording. Finding recorded: anime-seg is unreliable on photographs, so the extra-person check on
shots is verified in Task 28.4. No application code changed, so no new test run is needed beyond the
27.1 full suite (1466 passed) that ran on the same code.
