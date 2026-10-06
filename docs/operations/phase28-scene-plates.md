# Phase 28 Task 28.4a: the 55 scene plates in the new look

**Date:** 2026-10-06. **Script:** `scripts/regenerate_scene_plates.py`. **Sheets:** `docs/operations/phase28-scene-plates/plates_1..5.png`
(12 plates per sheet, labelled with the scene name, category and time of day).

- All 55 built-in scenes were redone with RealVisXL V5.0 through the app's own engine and recipes
  (`scene_preview_prompt`, `PLATE_NEGATIVE`, the scene's own seed, 1344 x 768, 30 steps, CFG 6): **27 minutes
  in total, 24 seconds a plate**, one model load.
- The new plates replace the old files at the same paths; the database rows already pointed there. Checked:
  55 rows, 0 missing files, 0 plates identical to the old ones, all 1344 x 768, and the API serves them (200).
- Backups, outside git: `data/tmp/plates-cel-anime-backup/` (the 55 old plates) and
  `data/backups/app_before_plates_28_4a_20261006.db`.
- **Looked at by eye, all five sheets:** photographic, crisp, the right place, no text or logos, no people. Two
  details: Zoo shows two elephants (animals, fine), and the colour grade of a few indoor plates leans a
  little cool and green.
- **The "people" check cannot be trusted on photographs.** The worker's cut-out (anime-seg) is trained on
  anime: it flagged a mountain trail (0.90, no person) and said 0.0 on a market with vendors. The contact
  sheets are the real check. The Market plate always drew vendors, so it has a plate-only wording
  ("an empty open-air street market at dawn ... nobody there"); the library place text is unchanged.
- This also matters for the app's extra-person check on shots: its reliability on photographs must be
  verified in Task 28.4 on real duo shots.
