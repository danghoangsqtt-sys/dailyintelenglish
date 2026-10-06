# Phase 28 Task 28.4: Lan and Minh replace the old characters (2026-10-06)

**Owner decision:** "remove all the old characters and replace them with the 2 new characters".

- **Script:** `scripts/replace_library_characters.py` (dry run first, then `--apply`). It uses the library's own
  service functions in one transaction: create, add the picked candidate, `pick_reference` (the app crops
  `face.png`), add and approve the four sheet views, lock; then move the cast, delete the old characters.
- **Result (checked in the real database):** exactly 2 characters, both `locked`: **Lan** (female, young,
  "English teacher", long straight black hair, white blouse and trousers) and **Minh** (male, young,
  "university student", tousled black hair, black slim-fit shirt and slim trousers). Each has a candidate, a
  512 x 512 `face.png`, and four approved sheet views (`full_body`, `portrait_calm`, `portrait_smile`,
  `portrait_surprised`); 0 asset files missing; the old folders are gone.
- **The surprised view** did not exist on the 28.2 sheets and was made for this task. The first try kept the
  calm or smiling face of the identity reference; a lower reference strength (0.3), a stronger expression
  prompt and a "no smile" negative fixed it.
- **The one project that used the old characters** (Demo Episode) kept its cast: speaker 0 is now the new
  Minh and speaker 1 the new Lan. Its 12 stored shots still show the old drawings until they are regenerated.
- **Backups (outside git):** `data/backups/app_before_new_characters_28_4_20261006.db` and
  `data/tmp/characters-old-backup/` (the two old character folders).
- **Library data made here:** the sheets in `docs/operations/phase28-characters/` (the surprised views are
  `woman_face_surprised.png` and `man_face_surprised.png`).
