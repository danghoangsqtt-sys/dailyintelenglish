# Task 28.4: Redo the character library: Lan and Minh replace the two old characters

## Owner decision (2026-10-06)

"Remove all the old characters and replace them with the 2 new characters." The new characters are the two
approved on the Task 28.2 sheets: **Lan** (woman) and **Minh** (man). Real data is deleted, so a backup comes
first.

## Facts (read from the real database, 2026-10-06)

- 2 old characters, both `locked` and in the old cel-anime look: Lan (yellow sweater / navy jeans) and Minh
  (light-blue shirt / black trousers); 18 assets, each with a `face.png` reference.
- One project uses them: **Demo Episode** (`project_cast`: speaker 0 = old Minh, speaker 1 = old Lan);
  12 `project_shots` exist for it.
- The library locks a character only when it has a picked candidate (it becomes `face.png`, cropped at a fixed
  box 20-80 % x 2-62 %) and **four approved sheet assets**: `full_body`, `portrait_calm`, `portrait_smile`,
  `portrait_surprised`. The 28.2 sheets have no "surprised" view.
- Form limits: hair is at most 4 words; tops and bottoms come from fixed lists (blouse, slim-fit shirt,
  trousers, slim trousers); the same colour for both garments is allowed since Task 28.3.

## Plan

1. **Surprised view:** add a `face_surprised` panel to `scripts/character_sheet_realvis.py` (the same pipeline:
   RealVisXL + face IP-Adapter + a front skeleton, "surprised face, open mouth"), render 2 seeds per character,
   pick by eye.
2. **Backup first:** `data/backups/app_before_new_characters_28_4_20261006.db` and the two old character
   folders to `data/tmp/characters-old-backup/` (outside git).
3. **Script** `scripts/replace_library_characters.py` (uses the app's own service functions inside
   `write_transaction`, so the rules of the library apply):
   - create **Lan**: female, young, Vietnamese, "English teacher", hair "long straight black hair", eyes
     "dark eyes", top white blouse, bottom white trousers; **Minh**: male, young, Vietnamese, "university
     student", hair "tousled black hair", eyes "dark eyes", top black slim-fit shirt, bottom black slim
     trousers;
   - add the approved images as assets: `candidate` = the 28.2 face_front (1024 x 1024), then
     `pick_reference` (the app makes `face.png`); the four sheet kinds from the approved panels
     (`full_body` <- full_front, `portrait_calm` <- face_front, `portrait_smile` <- face_smile,
     `portrait_surprised` <- the new panel), each approved; then lock;
   - re-point the Demo Episode cast to the new characters (speaker 0 -> Minh, speaker 1 -> Lan), delete the
     old characters with their cast rows and files.
   - one transaction for the database part: either everything changes or nothing.
4. **Check:** `GET /api/visuals/characters` shows exactly Lan and Minh, locked, with images served; the
   Character Library page is looked at in the browser; the file sizes of `face.png` are checked.
5. **Real pipeline smoke (Task 28.4b):** on a **copy** of the data folder, run the app's own shot job (Demo
   Episode: singles and duos, with the face references, the duo refine, the colour retry and the extra-person
   check) and look at the shots; the results decide whether the duo needs more tuning before the Gate.

## Paths

- `scripts/character_sheet_realvis.py`
- `scripts/replace_library_characters.py` (new)
- `docs/operations/phase28-characters/` (the surprised panels and the final sheets)
- `docs/operations/phase28-characters-replaced.md` (the report)

## Verification

- The script is dry-run first (prints what it would do, writes nothing), then run for real.
- After the run: 2 characters, 8 sheet assets approved (4 each), 2 `face` assets, both locked; the old
  folders are gone; the Demo Episode cast points at the new ids; the app serves the images.
- The full test suite is unaffected (data change only), but is rerun after any application code change.

## Result (2026-10-06)

Lan and Minh replace the old characters in the real library (`docs/operations/phase28-characters-replaced.md`).
Next, Task 28.4b: the app's own shot job on a copy of the data (`scripts/make_smoke_copy.py`, a second app on
port 8001 with `DIE_DATA_DIR`): the Demo Episode's 12 shots, to check the duo refine, the colour retry and the
extra-person check on photographs with the real faces.

## Task 28.4 closed (2026-10-06)

Lan and Minh are in the real library; the real shot job was run on a copy (`docs/operations/phase28-shots-real-pipeline.md`)
and the black rule and the per-outfit negatives were fixed from its findings (full suite: 1498 passed). Two findings
are carried to Task 28.5 with the owner's approval: counting faces on photographs and a "check this shot" mark.
