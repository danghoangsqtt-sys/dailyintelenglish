# Task 78.1 — Beat preview API

## Objective
`POST /api/projects/{project_id}/storyboard/preview` returns, for each beat in the request (unsaved draft beats allowed; empty body = the saved storyboard), what the talking-characters render shows during it, so Step 5 can draw a per-beat thumbnail before any render.

## Paths
- `backend/library/storyboard_preview.py` (new): `preview(db, project_id, beats) -> dict`.
- `backend/api/storyboard.py`: the route.
- `backend/schemas/storyboard.py`: `PreviewInput` (beats with the BeatInput fields, validated loosely: ranges and kind only).
- `tests/test_storyboard_preview.py` (new).

## File-Level Plan
- `storyboard_preview.py`
  - Load script line speakers (`speaker_index` per line, same join as the renderer), cast rows, the scenes referenced by the beats (`library_service.get_scene_row`, `_scene_view` for `preview_url`), approved activity candidates.
  - Scene per line: `video_renderer_remotion._beat_scene_per_line(beats, line_count)`; a beat's background = the scene of its first line (insert beats carry the previous place, as rendered). Report `{scene_id, name, preview_url | null}`; `null` plate → note "no picture yet".
  - Characters: `sprite_segments(line_speakers)` → the pair of the beat's first line; `sprite_placement` with cast genders; `sprite_mirrored`; sprite picture `"{expression}__closed"` if present in the set, else `calm__closed`; URL `/api/visuals/library/sprites/{character_id}/{name}/content`; `top_fraction` via `_figure_top` (cached per character within the call). Missing cast / unusable set → `{name, missing: "cast" | "sprites"}`.
  - Insert: `activity_matcher.beat_speaker_index` + `match_activity` → `{status: character|generic, url}`; else the pending picture (`activity_illustrations` helper data) or `{status: "missing"}`; plus `seconds_cap` 6 (cutaways last at most 6 s).
  - Beats with an out-of-range line span come back as `{error: "..."}` for that beat only.
- `storyboard.py`: `@router.post("/preview")` inside `read_transaction()`.
- Tests: scene beat with plate → preview_url and two characters with slot/mirror; insert beat → carried-over scene + illustration status; unsaved draft beats accepted; bad range → per-beat error; unknown project → 404.

## Best practices
Read-only (no writes, no file copies); reuse renderer helpers instead of copying logic; small JSON (URLs, not images).

## Verification
`pytest tests/test_storyboard_preview.py tests/test_storyboard_api.py -q`; `ruff check` on the changed files.
