# Task 33.2 — Profile domain, readiness, lifecycle, and API

## Objective

Provide one domain service and API for complete reusable profiles, independent readiness, autosaved drafts, duplication, archive/restore, and safe deletion.

## Paths

- `app/models/visuals.py`
- `app/api/visuals.py`
- `app/services/visuals/character_profile_service.py`
- `app/services/visuals/library_service.py`
- `tests/test_character_profiles.py`
- `tests/test_character_profiles_api.py`

## File-Level Plan

1. Add profile input/patch/response models with explicit field bounds and normalized-name validation.
2. Compute readiness from fields and approved current assets; do not store one aggregate lifecycle status.
3. Add filtered list/detail, autosave PATCH, duplicate, archive, restore, dependency report, and dependency-aware delete routes.
4. Keep legacy character routes compatible during the phase and map old `locked` semantics to computed readiness where needed.

## Verification

`venv\Scripts\python.exe -m pytest tests/test_character_profiles.py tests/test_character_profiles_api.py -q`

## Acceptance Criteria

- [ ] A draft can be created, patched by step, refreshed, and resumed.
- [ ] Readiness explains every missing requirement.
- [ ] Archive preserves dependencies; seed/dependent profiles cannot be permanently deleted.
- [ ] Duplicate creates a new ID and a conflict-free active name.

