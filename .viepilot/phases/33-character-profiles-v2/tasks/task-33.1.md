# Task 33.1 — Profile schema and migration rehearsal

## Objective

Create additive migration 018, extend existing character records in place, pin project casts to an identity version, and prove that Lina/Alex survive migration on a copy of the real database and asset directories.

## Paths

- `app/db/migrations/018_character_profiles_v2.sql`
- `app/models/visuals.py`
- `app/services/visuals/library_service.py`
- `app/services/visuals/project_visuals_service.py`
- `scripts/migrate_character_profiles_v2.py`
- `tests/test_character_profiles_migration.py`

## File-Level Plan

1. Implement the reviewed form of `.viepilot/schemas/phase33-character-profiles.sql`, rebuilding `project_cast` transactionally where SQLite requires it.
2. Backfill normalized names, review states, version 1, timestamps, and protected seed flags for Lina/Alex without changing IDs or paths.
3. Register current Lina/Alex sprite files as version 1 asset rows through an idempotent post-migration command; retain `sprite_set.json` as a derived compatibility manifest.
4. Add child-key indexes, foreign-key checks, migration rollback cleanup, and a rehearsal command that accepts copied DB/data roots only.

## Verification

- Apply all migrations to an empty temporary DB.
- Apply migration 018 twice through the application's normal migration runner.
- Rehearse on a copy of `data/app.db` and copied Lina/Alex asset roots; compare IDs, row counts, cast rows, approved paths, and foreign-key check output.

## Acceptance Criteria

- [ ] Lina/Alex IDs, files, and project cast assignments are unchanged.
- [ ] Existing speaker voice settings are unchanged.
- [ ] Active normalized names are unique and project casts cannot duplicate a character.
- [ ] No migration or rehearsal writes to the real database or real asset directory.

## Amendment A (2026-10-12, D81–D82)

- `characters.gender` is required for every profile (`male` / `female`); the migration keeps Alex `male`, Lina `female`
  and refuses a profile without gender instead of guessing.
- Add `characters.sprite_facing` (`right` / `left`; default `right` for male, `left` for female) and track whether an
  approved opposite-facing pack exists (slot set or flag, decided in the migration design).
- Paths add: `app/db/migrations/018_character_profiles_v2.sql` (same migration, extra columns).

## Implementation Notes (2026-10-12, before coding)

- Migration `018_character_profiles_v2.sql`, wrapped in one `BEGIN … COMMIT`:
  - `characters`: the columns of `.viepilot/schemas/phase33-character-profiles.sql` plus `sprite_facing TEXT NOT NULL DEFAULT ''`
    backfilled `right` for male, `left` for female; `normalized_name = lower(trim(name))`; unique active-name index;
    `is_seed = 1` for the real Lina/Alex IDs (`e961d07c-…`, `0383161f-…`), no effect on other databases.
  - `character_assets`: schema columns plus `facing TEXT NOT NULL DEFAULT 'native'` (`native` / `opposite` — decides D82:
    an opposite-facing pack is a set of asset rows with `facing='opposite'`, no separate flag). Backfill: `slot_key = kind`
    for the sheet kinds (full_body, portrait_calm/smile/surprised), `review_state` from `approved`, `updated_at = created_at`.
    One-current-slot unique index includes `facing`.
  - `project_cast` rebuilt (create new, copy, drop, rename): `profile_version` from the character's `identity_version`,
    `UNIQUE (project_id, character_id)`, character FK `ON DELETE RESTRICT` (`delete_character` already removes cast rows
    first, so its behaviour is unchanged).
- Gender is already `NOT NULL` and validated `female`/`male` by `CharacterInput`; no extra constraint needed.
- `library_service`: create/edit write `normalized_name` and default `sprite_facing`; a duplicate active name raises
  `ConflictError` instead of an IntegrityError.
- `project_visuals_service.set_cast`: refuses the same character twice (ValidationError) and stores `profile_version`.
- `scripts/migrate_character_profiles_v2.py`: `register_legacy_sprites` (idempotent) adds each sprite in
  `sprite_set.json` as an approved `character_assets` row (`kind='sprite'`, `slot_key='sprite/<name>'`,
  `source='legacy_migration'`, path unchanged); `rehearse` copies a DB + library folders to a temp dir, runs `init_db` and the
  registration there, and prints a before/after comparison (IDs, counts, cast, approved paths, `PRAGMA foreign_key_check`).
  It refuses a target under the real `data/`.
- The real database gets migration 018 the normal way at the next app start (after a backup); the rehearsal never writes it.
