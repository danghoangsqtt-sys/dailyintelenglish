# Task 33.7 — Character Selector and explicit project assignment

## Objective

Replace dropdown/name matching with a game-style roster and profile panel that explicitly assigns distinct profile IDs and copies voice defaults with user-visible control.

## Paths

- `frontend/pages/step1_config.html`
- `frontend/static/js/step1_config.js`
- `frontend/pages/step5_video.html`
- `frontend/static/js/step5_video.js`
- `frontend/static/js/api.js`
- `app/api/visuals.py`
- `app/models/visuals.py`
- `app/services/visuals/project_visuals_service.py`
- `tests/test_character_selector_browser.py`
- `tests/test_visuals_project_api.py`

## File-Level Plan

1. Build a shared selector with speaker slots, profile roster, and large profile panel; previewing never mutates cast.
2. Require **Choose for {speaker}**, prevent duplicate assignment, and show why a profile is incompatible with the selected renderer.
3. Copy profile name/voice defaults on first assignment; when data already exists, show the fields that will change and allow preserving project overrides.
4. Remove `castByName()` and every automatic name-based binding path; persist character ID and profile version.

## Verification

`venv\Scripts\python.exe -m pytest tests/test_character_selector_browser.py tests/test_visuals_project_api.py -q`

## Acceptance Criteria

- [ ] Clicking a roster card only previews it.
- [ ] Choosing saves the expected ID/version and never assigns the same profile twice.
- [ ] Existing custom project voice settings are not silently overwritten.
- [ ] No cast path searches by display name.

## Implementation Notes

- Keep roster-card clicks read-only; only the explicit speaker assignment action may persist cast data.
- Send the copy-defaults decision with each assignment and update project speaker fields only when it is true.
- Treat profile IDs and pinned identity versions as the cast identity. Speaker display names remain editable dialogue labels.
- Explain renderer readiness from profile capability data before assignment and keep duplicate-profile prevention in both the browser and service layer.

