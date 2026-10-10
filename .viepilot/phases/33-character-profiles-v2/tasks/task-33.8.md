# Task 33.8 — Activity, storyboard, and shot integration

## Objective

Make downstream visual systems work with arbitrary profiles and meaningful speaker pairs in projects with three to six cast members while preserving the two-visible-per-beat rule.

## Paths

- `app/services/visuals/activity_library_service.py`
- `app/services/visuals/activity_matcher.py`
- `app/services/visuals/storyboard_service.py`
- `app/services/visuals/project_visuals_service.py`
- `app/services/visuals/shot_library_service.py`
- `frontend/pages/shot_library.html`
- `frontend/static/js/shot_library.js`
- `frontend/static/js/storyboard.js`
- `tests/test_character_profile_integration.py`
- `tests/test_storyboard_shots.py`

## File-Level Plan

1. Build Activity Library profile filters dynamically and show per-profile approved/pending/rejected counts plus generic coverage.
2. Keep activity fallback `character > generic > sprite` and ensure an empty character-specific library never blocks rendering.
3. Derive each beat's single or duo speakers from script participation and reviewed beat speakers instead of reusing the first cast pair.
4. Generate or select shot-library pairs on demand for the actual ordered pair; keep the maximum of two visible characters explicit in API and UI.

## Verification

`venv\Scripts\python.exe -m pytest tests/test_character_profile_integration.py tests/test_activity_matcher.py tests/test_storyboard_shots.py -q`

## Acceptance Criteria

- [ ] A new profile appears in sprite/activity filters without hardcoded frontend changes.
- [ ] A three-speaker storyboard rotates singles/pairs according to the active dialogue.
- [ ] No beat persists more than two visible speakers.
- [ ] Missing profile-specific activities fall back without blocking the render.

## Implementation Notes

- Populate Activity Library profile filters and count summaries from the profile API; do not encode profile names in HTML or JavaScript.
- Preserve the matcher priority of profile-specific activity, generic activity, then sprite fallback.
- Normalize every beat to zero, one, or two valid cast speaker indexes and derive duo shots from that beat's ordered participants.
- Keep shot-library identity based on ordered character IDs resolved from speaker indexes; never substitute the first cast pair for a reviewed pair.

