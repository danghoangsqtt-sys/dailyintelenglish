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

## Amendment A (2026-10-12, D80)

- The selector replaces the free-text speaker name fields in Step 1 (`frontend/static/js/step1_config.js`,
  `frontend/pages/step1_config.html`): each speaker slot opens the selector; the speaker name becomes the character name and
  voice defaults are copied in. New projects cannot be created with an unassigned speaker.
- Old projects keep their speaker names; Step 5 shows **Use character name** where the name and the cast character differ
  (e.g. Demo Episode "Maya" → Lina).
- Paths add: `frontend/static/js/step1_config.js`, `frontend/pages/step1_config.html`, `tests/test_step1_config_edit_browser.py`.

## Implementation Notes (2026-10-12, before coding; D80)

- **Shared selector** `frontend/static/js/character_selector.js` (`CharacterSelector.open({slots, profiles, onChoose})`): an
  overlay with the speaker slots on top, a searchable roster of active profiles (picture, name, gender, badges) and a large
  preview panel (picture, gender, accent, voice, intro, personality, readiness). Clicking a card only previews it; **Choose for
  {speaker}** assigns. A profile already used by another speaker is disabled and names that speaker; a profile that is not
  video ready is disabled with what it still needs.
- **Step 1:** each speaker card shows the chosen character (picture, name, gender, accent) and **Choose character**; the
  free-text name, gender and accent inputs are gone for new projects. Choosing copies name, gender, accent and voice
  (speed/pitch/volume) into the speaker; when a speaker already has different voice settings (edit mode) a confirm shows
  what changes and lets the owner keep them. Save requires every speaker to have a character; after create/update the cast is
  saved with `PUT /api/projects/{id}/visuals/cast` (IDs + profile version). Edit mode reads the existing cast.
- **Step 5:** the cast dropdown lists video-ready profiles (not only legacy `locked` ones) and a **Use character name** button
  appears when a speaker's name differs from its character's (Demo Episode "Maya" → Lina). `castByName()` is removed: no
  cast is ever inferred from a display name.
- **Backend:** `set_cast` accepts a legacy `locked` character or a profile whose readiness is `video_ready`; the refusal names
  what is missing. Duplicate assignment stays refused (33.1).
