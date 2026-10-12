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

## Amendment C (2026-10-12, owner D85 — activity slots) — **WITHDRAWN by D86, not implemented**

The character's picture library also has **activity slots** (e.g. working out, cooking): the default list is the 25 activities
the Alex/Lina packs use today (`activity_library` character scope), and the owner can add a slot by typing an activity name.
Each activity slot shows a prompt built from the profile (identity, appearance, outfit, the activity, 16:9 scene picture) and
a drop zone. A picture dropped there is stored through `activity_library_service` with `character_id` = the profile and
`activity` = the slot's name (renamed on disk like every upload), and waits for review as Activity Library pictures do today.
Activity slots never block readiness (Phase 33 rule 8).

## Amendment D (2026-10-12, owner D86 — supersedes D85)

"Actions" means the **gestures and mouth shapes** of the talking-sprite pack, as in `data/library/sprites_inbox` (`alex__gesture-wave__open.png` ...). The character picture library therefore has the core pictures plus exactly the 29 sprite slots: 7 expressions x closed/open mouth (14) + `blink` + 7 gestures x closed/open mouth (14). Each slot card shows its prompt and drop zone; a dropped file is renamed to the slot name (`<slot>.png`, the same names as `sprites_inbox` without the character prefix). No activity slots on the character page: activity pictures stay in the Activity Library as today.

## Implementation Notes (2026-10-12, before coding; follows D84 + D86)

- **Slot registry** (`character_asset_service.SLOTS`, one server-side list, 29 sprite slots in the `sprites_inbox` names):
  each slot has `key` (`calm__closed`, …, `gesture-wave__open`), `group` (expression / mouth / blink / gesture),
  `tier` (1/2/3), `parent` (the picture the owner attaches in the outside AI: `calm__closed` for faces and gestures, the
  closed-mouth twin for every `__open`), `region` (face / mouth / eyes / arms-and-hands) and a prompt template. This is the
  proven Phase 32 ChatGPT-web recipe (`docs/operations/Prompt_ChatGPT_Web_Alex.txt`): one base picture, every other picture a
  small region edit of its parent.
- **Base prompt** (`calm__closed`) is written from the profile: full-length adult, gender, nationality, appearance, outfit,
  calm friendly face, lips closed, a slight turn toward the right of the picture for male / left for female (D82), feet on the
  bottom edge, portrait format, flat pure green background `#00B140`, no shadow, no props, no text.
- **Core pictures** (`full_body`, `portrait_calm/smile/surprised`) are **derived automatically** from the approved sprites
  (calm__closed / smile__closed / surprised__closed: full figure and a head-and-shoulders crop on a neutral background), so
  the owner uploads only the 29 sprite pictures. Re-derived when a source sprite is approved again.
- **Upload** `POST /api/visuals/profiles/{id}/slots/{slot}/upload` (multipart, one file): the slot comes from the URL, never
  the filename. Checks: real image bytes (Pillow verify + reopen), PNG/JPEG/WebP, ≤ 20 MB, ≤ 40 MP, ≥ 512 px tall. Then:
  green key-out (`key_out_green` logic of `scripts/sprite_web_import.py`) unless the picture already has transparency;
  base → scaled so the figure fills the canvas height like the existing packs, feet on the floor, centred; other slots →
  registered on the approved base (phase correlation / silhouette, the same logic as the web import); then the
  `sprite_service` checks against the base (head offset, kept body share for gestures, edge contact) → `validation_json`.
- **Storage**: `data/library/characters/<id>/v<identity_version>/<facing>/<slot>.png` (always renamed); the original
  filename only in `original_filename`. Written to a temp file first; the DB row is inserted and the previous current row of
  the slot set `is_current = 0` in one transaction; then the temp file is moved into place; any failure removes the temp file
  and leaves the previous asset untouched.
- **Review**: every upload is `needs_review`; `PUT …/assets/{asset_id}/review` (approve / reject) and
  `POST …/assets/approve` (Approve all for a list of IDs). Approving a new `calm__closed` when one was already approved bumps
  `identity_version` and marks the other current sprites stale (Phase 33 rule 10).
- **Prompt pack**: `GET …/slots` returns every slot with its prompt, parent, region, current asset, state and validation;
  `GET …/prompt-pack.txt` returns the whole pack as one Vietnamese/English text file like the Phase 32 ones.
- **Optional bulk** (D83 kept as a shortcut): `POST …/slots/upload-batch` maps files whose names are canonical slot names
  (with or without a `<name>__` prefix); other files are returned as "drop this on its slot".

## Results (2026-10-12)

- 13 tests (`tests/test_character_asset_slots.py`): 29 slots with prompts/parents/regions, renamed upload, base fit on the canvas,
  parent-first rule, region edit at another size, redrawn fallback, bad files never replace the current picture, non-green
  base refused, Approve all + derived core pictures + readiness, new base → identity version 2, prompt pack text, bulk drop.
- **Real pictures:** the 28 Alex ChatGPT-web edits from Phase 32 (`data/assets_sprites/web_raw/Alex`, 1145 x 1374) put
  through the same functions as the upload route against a base made from `INPUT_alex__calm__closed.png`: 28/28 pass the
  sprite checks; 27 registered as region edits (difference 1.3–8.8, changed share 0.003–0.185), `gesture-think` took the
  redrawn fallback and still passes.
- Found while testing: a mean grey difference alone lets a redrawn picture pass as an edit (the green dominates); the
  changed share of the figure itself, in RGB, is now required too (≤ 0.30).
