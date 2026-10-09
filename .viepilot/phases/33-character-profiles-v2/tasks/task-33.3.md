# Task 33.3 — Asset slots, direct upload, validation, and prompt packs

## Objective

Make profile assets manageable through explicit canonical slots with safe direct upload, review states, versioned storage, and provider-neutral instructions.

## Paths

- `app/models/visuals.py`
- `app/api/visuals.py`
- `app/services/visuals/character_asset_service.py`
- `app/services/visuals/character_profile_service.py`
- `app/services/visuals/image_upload.py`
- `app/services/visuals/sprite_service.py`
- `tests/test_character_asset_upload.py`
- `tests/test_character_asset_slots.py`

## File-Level Plan

1. Define core, Tier 1, Tier 2, and Tier 3 slot metadata in one server-side registry.
2. Add bounded multipart single/batch upload, Pillow verification/reopen, pixel and format limits, alpha/canvas checks, staged writes, and rollback cleanup.
3. Persist original filenames as metadata while deriving storage paths only from character ID, identity version, and canonical slot key.
4. Add review/remove/replace behavior, identity-version conflict checks, stale propagation, content delivery, and prompt-pack export.

## Implementation Notes

- **Files touched:** the seven paths listed above plus ViePilot state/changelog files.
- **Upload limits:** 20 MB per file, 40 files per batch, bounded 1 MB reads, actual Pillow format verification, and a 24 megapixel decode ceiling.
- **Slot contract:** core visuals accept PNG/JPEG/WebP; sprite slots require exact 1280×1536 RGBA PNG with clear corners and no opaque canvas edge.
- **Storage:** stage under the version directory, normalize to PNG, then atomically replace; database current-slot changes occur only after validation and file persistence.
- **Review:** all uploaded/local-generated assets start `needs_review`; renderer readiness only counts approved current assets.
- **Identity version:** replacing `face`, `full_body`, or `calm__closed` increments the profile version after explicit confirmation and marks old-version dependents stale without deleting files.
- **Expected verification:** corruption, size, alpha, dimension, replacement rollback, review, stale propagation, batch mapping, and prompt archive tests.

## Verification

`venv\Scripts\python.exe -m pytest tests/test_character_asset_upload.py tests/test_character_asset_slots.py -q`

## Acceptance Criteria

- [x] Uploading into a slot always assigns that slot's canonical key.
- [x] A corrupt, oversized, or invalid replacement cannot damage the current approved asset.
- [x] Technically valid uploads start as `needs_review`.
- [x] Changing an identity base marks dependent assets stale while retaining prior version files.

## Verification Result — PASS (2026-10-10)

- Asset upload/slot/profile regression: **24 passed**.
- Ruff on changed Python and `git diff --check`: PASS.
- Verified single and explicit batch mapping, PNG/JPEG/WebP normalization, exact transparent sprite canvas, current-slot review/remove, failed replacement preservation, prompt ZIP and identity-version stale propagation.

