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


## Implementation Notes (2026-10-12, before coding; includes Amendment A D79)

- **Separate prefix `/api/visuals/profiles`** for the new profile API, so the legacy `/api/visuals/characters` routes and
  the current `/characters` page keep working unchanged during the phase (File-Level Plan step 4). The selector (33.7) and
  the new library UI (33.4) use the new routes.
- Migration `019_character_quick_profile.sql` (additive): `characters.appearance TEXT NOT NULL DEFAULT ''` and
  `characters.outfit TEXT NOT NULL DEFAULT ''` — the free-text Quick create fields (D79); the structured legacy columns
  (hair, eyes, colours, items) stay for the local generator and are left empty for Quick create profiles.
- Models: `ProfileQuickCreate` (name, gender, accent ∈ `EDGE_TTS_VOICE_MAP`, optional nationality one word, appearance
  ≤ 400 chars, outfit ≤ 200 chars) and `ProfilePatch` (every profile field optional; voice speed/pitch/volume bounded like
  speakers; personality ≤ 8 short traits; `wizard_step` 0–10).
- `character_profile_service.py`: `create_quick` (voice = `EDGE_TTS_VOICE_MAP[accent][gender]`, facing from gender,
  unique name), `get_profile` / `list_profiles(q, state=active|archived|all)`, `patch_profile` (autosave; gender change
  updates the default facing), `duplicate` (new ID, "Name copy" / "Name copy 2", profile fields only, no assets),
  `archive` / `restore` (restore re-checks the name), `dependencies` (project casts, shot library, activity pictures,
  sprite assets), `delete` (refuses seeds and profiles with dependencies; otherwise removes rows and files).
- **Readiness is computed, never stored:** `profile` (name, gender, accent, appearance, outfit), `voice`
  (voice id + accent), `core_visuals` (approved current full_body, portrait_calm/smile/surprised), `talking_starter`
  (7 Tier 1 sprites), `full_expressions` (15), `full_sprite_pack` (29), `activities` (count, informative). Each part lists
  exactly what is missing. Sprites come from approved `kind='sprite'` asset rows, falling back to the legacy
  `sprite_set.json` when a character has none yet (Lina/Alex before `register-sprites`). `video_ready` = profile + voice +
  core visuals; `talking_ready` = video_ready + Tier 1.
