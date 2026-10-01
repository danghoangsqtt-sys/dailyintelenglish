# Task 20.7 — Remotion visuals and AI scene thumbnail

## Handover

### Files added/changed

- `app/services/visuals/project_visuals_service.py` — pure chapter/scene/speaker shot assignment with the required fallbacks (§8).
- `app/services/video_renderer_remotion.py` — copy complete shot files into Remotion public assets, attach visual props and use a cast face for a chip without an uploaded avatar (§8).
- `video-renderer/src/types.ts`, `video-renderer/src/Root.tsx`, `video-renderer/src/StillFrame.tsx`, `video-renderer/src/Episode.tsx`, `video-renderer/src/visuals.ts` — optional visual props, full-bleed shot backgrounds with ten-frame crossfades and line-scale motion, and duo-aware vocabulary placement (§8).
- `app/services/thumbnail_service.py`, `app/api/thumbnail.py`, `app/models/thumbnail.py` — project-only `ai_scene` discovery, safe source selection, 16:9 and 9:16 scene crops, left dark scrim and white outlined headline (§9). The route and request-model changes are necessary wiring for the new pseudo-template.
- `frontend/static/js/api.js`, `frontend/static/js/step6_thumbnail.js` — Step 6 project-specific picker and fallback to the five existing templates (§7.3).
- `video-renderer/src/visuals.test.ts`, `tests/test_visuals_remotion.py`, `tests/test_visuals_thumbnail.py`, `tests/test_visuals_step6_browser.py` — spec §10 coverage.
- `.viepilot/phases/20-ai-visuals/tasks/task-20.7.md` — this handover.

### Tests added

- `test_assign_line_shots_chapters_position_speaker_and_fallbacks`
- `test_remotion_props_copy_complete_shot_and_cast_face`
- `test_remotion_props_without_shots_keep_visuals_optional`
- `test_ai_scene_template_requires_shot_renders_both_aspects_and_falls_back`
- `test_step6_ai_scene_option_appears_with_shot`
- Vitest: optional prop default, vocabulary placement, shot selection/crossfade/scale.

### Verification

- Focused Remotion props and existing Remotion tests: `22 passed, 2 warnings in 2.87s`.
- TypeScript (`npx tsc --noEmit`): clean (exit 0).
- Vitest (`npx vitest run`): `Tests  37 passed (37)`.
- `node --check frontend/static/js/api.js` and `node --check frontend/static/js/step6_thumbnail.js`: clean (exit 0).
- Ruff (`ruff check` on touched Python paths): `All checks passed!`
- Full suite (`python -m pytest -q`): `1268 passed, 2 warnings in 516.25s (0:08:36)`.

### Deviations from spec

- None.

### Open questions for the PM

- None.
