# Task 33.8 — Activity, storyboard, and shot integration

## Objective

Make downstream visual systems work with arbitrary profiles and meaningful speaker pairs in projects with three to six cast members while preserving the two-visible-per-beat rule.

## Paths

- `app/services/visuals/activity_library_service.py`
- `app/services/visuals/activity_matcher.py`
- `app/services/visuals/storyboard_service.py`
- `app/services/visuals/project_visuals_service.py`
- `app/services/visuals/shot_library_service.py`
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


## Implementation Notes (2026-10-12, before coding)

- Already general (checked): the Activity Library character filters and targets are built from the character list
  (`shot_library.js`); the storyboard keeps at most two speakers per beat from the speakers of its lines
  (`storyboard_service.py:168,201`, `BeatInput.speakers max_length=2`); the activity matcher uses the beat's speaker (32.8a).
- **The gap — talking sprites:** `_build_sprite_props` shows only speakers 0 and 1, so a third speaker talks off screen.
  New pure `sprite_segments(line_speakers)` in `video_renderer_remotion.py`: each line's on-screen pair = its speaker + the
  last other speaker before it (else the next one); consecutive lines with the same pair form a segment. Each segment is
  placed with `sprite_placement` (D81) and mirrored (D82) on its own; its characters carry a window `fromSec`/`toSec`
  (segment boundaries; the first starts at 0, the last has no end) and enter/leave with the existing slide-and-fade. The
  plan (`sprite_plan.build_plan`) runs per segment with that segment's slots. Pictures are copied per character
  (`sprites/<project>/<character_id>/`), so one character can stand in different slots in different segments.
- Renderer: `spriteCharacterSchema` gains `fromSec` (default 0) and `toSec` (nullable); `spriteFrame` uses the window for
  presence; a character outside its window is not drawn. Two-speaker projects produce one segment: same video as before.
- Tests: segment table (2 speakers, 3 speakers rotating, a lone speaker, unknown speakers), props for a 3-speaker project
  (who is on screen per line, windows, placement per segment), Vitest for windowed presence, the existing 2-speaker props.
