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
- `tests/test_character_asset_studio_browser.py`

## File-Level Plan

1. Render each slot with its example, dimensions, transparency/framing rules, prompt, current picture, validation, and review actions.
2. Add single-slot upload with immediate local preview and persisted-result replacement after the API response.
3. Add multi-file mapping with numbered thumbnails, per-image slot dropdown, duplicate/unmapped checks, replacement choice, and ordered result summary.
4. Route **Generate locally** through existing image jobs and GPU coordination; keep output pending and surface quality limitations.

## Verification

`venv\Scripts\python.exe -m pytest tests/test_character_asset_studio_browser.py tests/test_visuals_library_api.py -q`

## Acceptance Criteria

- [ ] Every selected image stays visible while it is mapped and named.
- [ ] The user can correct every proposed slot before import.
- [ ] Upload and generation errors identify the affected picture and preserve other work.
- [ ] Normal use requires no folder copy or manual filename change.

