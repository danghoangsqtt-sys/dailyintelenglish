# Task 32.6a — Activity Library backend

## Objective

Create the database-backed, review-gated Activity Library for reusable 16:9 activity cutaways. An item is character-specific or generic, starts pending after inbox import, and records every render use. No item may enter matching before approval.

## Paths

- `app/db/migrations/017_activity_library.sql` — additive SQLite tables and indexes.
- `app/services/visuals/activity_library_service.py` — validation, inbox parsing/import, asset lifecycle, deterministic metadata handling and usage persistence.
- `app/models/visuals.py` — Pydantic request models for activity metadata and review state.
- `app/api/visuals.py` — library list, content, import, metadata, review and history routes.
- `tests/test_activity_library.py` — migration/service/API contract tests.

## File-Level Plan

1. Add `activity_library` and `activity_library_usage` tables. Store content hash, path, nullable `character_id`, canonical activity, context tags JSON, normalized aliases JSON, review state, variant, timestamps, counters and last-use timestamp. Index approved items by character/activity and usage by item.
2. Parse `generic|<character>__<activity>__[context]__[variant].png` from `data/library/activities_inbox`; allow PNG/JPEG/WebP only, verify decodability and an image aspect suitable for 16:9 cutaways, resolve character name without accepting an unknown name, copy by generated ID, hash-deduplicate and retain rejected inbox files.
3. Keep the taxonomy open but normalize lower-case ASCII tokens and aliases; require a non-empty canonical activity; permit only known `pending|approved|rejected` review states. Metadata edits revalidate all fields.
4. Provide owner-facing list/filter, content, import, metadata update, approve/reject and usage-history endpoints. File content endpoints must enforce the activity-library root.
5. Record a usage row atomically only after an activity image is selected for a render; usage counts are derived/updated transactionally and are never incremented by preview or coverage.

## Best Practices / Risks

- Use `aiosqlite`, `Path`, `asyncio.to_thread` for PIL/file work, typed exceptions and service-layer routes.
- Never trust a filename, database path or user-supplied character ID as a filesystem path.
- Do not create visual content, call an AI model or match images in this task.

## Verification

`venv\Scripts\python.exe -m pytest tests/test_activity_library.py -q`

Expected: tests cover migration, filename parsing, unknown character, duplicate hash, invalid image, validation, review transitions, safe content lookup, metadata updates and usage history.

## Acceptance Criteria

- [ ] Pending imported items are invisible to matching by default.
- [ ] Generic and character-specific images are both representable.
- [ ] Invalid/import-failed files report a reason and remain recoverable in inbox.
- [ ] Approved/rejected state, metadata and usage history survive a DB reopen.
