# Task 33.5 — Visual Asset Studio and bulk mapping

## Objective

Let users complete every picture requirement inside the wizard using external uploads or the existing local generation pipeline, with clear image-to-slot mapping and review.

## Paths

- `frontend/pages/characters.html`
- `frontend/static/js/characters.js`
- `frontend/static/js/api.js`
- `frontend/static/css/style.css`
- `app/api/visuals.py`
- `app/services/visuals/jobs.py`
- `app/services/visuals/pipelines.py`
- `app/services/visuals/character_asset_service.py`
- `app/main.py`
- `tests/test_character_asset_studio_browser.py`
- `tests/test_visuals_library_api.py` (local generation job regression)

## File-Level Plan

1. Render each slot with its example, dimensions, transparency/framing rules, prompt, current picture, validation, and review actions.
2. Add single-slot upload with immediate local preview and persisted-result replacement after the API response.
3. Add multi-file mapping with numbered thumbnails, per-image slot dropdown, duplicate/unmapped checks, replacement choice, and ordered result summary.
4. Route **Generate locally** through existing image jobs and GPU coordination; keep output pending and surface quality limitations.

## Verification

`venv\Scripts\python.exe -m pytest tests/test_character_asset_studio_browser.py tests/test_visuals_library_api.py -q`

## Acceptance Criteria

- [x] Every selected image stays visible while it is mapped and named.
- [x] The user can correct every proposed slot before import.
- [x] Upload and generation errors identify the affected picture and preserve other work.
- [x] Normal use requires no folder copy or manual filename change.

## Implementation Notes

- Reuse the canonical slot registry and upload endpoints from Task 33.3; the browser never derives a slot from a filename.
- Keep selected `File` objects in browser memory so a failed item can be remapped or retried without selecting the batch again.
- Open the studio from wizard Steps 5–9 and return to the same step after review.
- Treat local generation as an explicit per-slot job request with the same pending-review result contract as uploaded images.
- Keep GPU work inside the existing image job runner and cancellation/progress UI.

## Completion Evidence

- Single-slot uploads show an immediate preview, preserve explicit slot assignment, and return to the persisted reviewed asset.
- Bulk mapping keeps numbered previews and original names visible, rejects missing/duplicate slot choices, and reports failures per slot while retaining the selected batch.
- Core visual slots can use the existing cancellable local image queue; generated results enter `needs_review`. Sprite generation is explicitly refused because the local engine cannot reliably make the required aligned transparent canvas.
- Targeted studio, API, upload and slot regression: 13 passed; prior wizard/legacy browser regression: 4 passed; Ruff, JavaScript syntax and diff checks pass.

