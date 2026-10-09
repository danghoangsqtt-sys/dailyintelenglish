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

