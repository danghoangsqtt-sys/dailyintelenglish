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

## Amendment A (2026-10-12, D79, D82, D83)

- The prompt pack is generated from the Quick create fields: identity, appearance and outfit text, the canonical file name of
  every slot (`{slot}.png`) and the facing rule (male looks to the right of the picture, female to the left).
- Bulk upload: files named as in the prompt pack are mapped to their slots automatically; other names need a manual slot.
- Automatic alignment before review: shared scale against the identity full body, feet on the canvas floor, face region
  checked; the same checks as `sprite_service` imports today.
- One review grid per upload with **Approve all** and per-picture reject; approval makes the pack usable at once.
- Verification adds: a canonical-name pack maps with no manual step; a misaligned picture is reported, not silently fixed
  beyond the shared alignment; nothing is approved before the grid action.

## Amendment B (2026-10-12, owner D84 — supersedes the auto-mapping emphasis of D83)

The owner's flow is **slot by slot**: the character library shows every picture slot of a profile (core pictures, Tier 1–3
expressions and gestures) as a card with **its own prompt** and **its own upload drop zone**. The owner makes the picture with
an outside AI from that card's prompt and drops it into the same card. The server stores it under the slot's canonical name
(`<character_id>/v<identity_version>/<slot_key>.png`), whatever the uploaded file was called; the original filename is kept
only as metadata. Alignment and technical checks run on upload; the card shows the result; approval stays with the owner
(per card, or **Approve all** for the cards filled in this session).

- Primary path: single-slot upload (`POST …/assets/{slot_key}/upload`); the slot comes from the card, never from the filename.
- Secondary path (kept from D83, optional): dropping several files at once onto the library maps files whose names are
  canonical slot names; any other file must be dropped on its card.
- The prompt pack is shown per card (copy button) and is also downloadable as one text file for the whole profile.
