# Task 33.3 — Asset slots, direct upload, validation, and prompt packs

## Objective

Make profile assets manageable through explicit canonical slots with safe direct upload, review states, versioned storage, and provider-neutral instructions.

## Paths

- `app/models/visuals.py`
- `app/api/visuals.py`
- `app/services/visuals/character_asset_service.py`
- `app/services/visuals/image_upload.py`
- `app/services/visuals/sprite_service.py`
- `tests/test_character_asset_upload.py`
- `tests/test_character_asset_slots.py`

## File-Level Plan

1. Define core, Tier 1, Tier 2, and Tier 3 slot metadata in one server-side registry.
2. Add bounded multipart single/batch upload, Pillow verification/reopen, pixel and format limits, alpha/canvas checks, staged writes, and rollback cleanup.
3. Persist original filenames as metadata while deriving storage paths only from character ID, identity version, and canonical slot key.
4. Add review/remove/replace behavior, identity-version conflict checks, stale propagation, content delivery, and prompt-pack export.

## Verification

`venv\Scripts\python.exe -m pytest tests/test_character_asset_upload.py tests/test_character_asset_slots.py -q`

## Acceptance Criteria

- [ ] Uploading into a slot always assigns that slot's canonical key.
- [ ] A corrupt, oversized, or invalid replacement cannot damage the current approved asset.
- [ ] Technically valid uploads start as `needs_review`.
- [ ] Changing an identity base marks dependent assets stale while retaining prior version files.

