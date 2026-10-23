# PLAN - Phase 73

Execution authorized by owner 2026-10-23: vp-crystallize + vp-auto, reiterated "continue". Source: docs/brainstorm/session-2026-10-23.md (D1-D4).

Activity Library has Activity pictures and Scenes tabs, distinct entities. Scenes supports metadata creation/edit, duplication, AI background generation, search/category/plate filters and archive/restore. Preserve built-in deletion protection. Keep existing advanced folder import. Step 5 chooses scenes per beat from the active library; remove project shortlist chips. AI and deterministic fallback consume active scenes. Archive retains IDs, previews and historical project/storyboard/render references; existing beats can retain archived choices. Preserve still-picture mode selector and historical project_scenes data/API for compatibility.

Acceptance: create scene and generate AI background in library; newly added scene immediately available on entering/reloading storyboard; >3 distinct library scenes can be chosen across beats subject to existing image budget; archive hides new choices and preserves old references; restore returns choice; Activity workflows continue working. No release/build required.

Risks: archived choices leaking through direct SQL or fallback; invalidating old storyboard saves; UI initialization races. Verify through targeted API/service/browser checks and JS/Python static checks. Real paid/GPU generation need not run; exercise queued generation and terminal states with controlled fixtures.

## Tasks and bounded allowed_files

### 73.1 - Scene lifecycle and proposal compatibility

Add archived_at; active list by default, include_archived option and project-scoped historical scene visibility. POST archive/restore; DELETE archives custom scenes, protects built-ins. Count project usage across shortlist, beats and explainer references. Active-only AI/fallback and automatic plate selection; direct ID resolution retained. Validate archived storyboard choices only when already referenced by project. Use active library fallback, no fixed cafe dependency. Test archive/restore, old refs and fallback.

- `backend/db/migrations/037_scene_archive.sql`
- `backend/library/library_service.py`
- `backend/api/visuals.py`
- `backend/library/storyboard_service.py`
- `backend/library/explainer_stage.py`
- `backend/library/project_visuals_service.py`
- `backend/media/video_renderer_remotion.py`
- `tests/test_scene_archive.py`
- `tests/test_storyboard_propose.py`
- `tests/test_visuals_scenes_v2.py`

### 73.2 - Activity Library scene management

Reuse scene editor/preview/job workflow in Activity Library Scenes tab. Search/category/plate/archive filters; create/edit/duplicate/archive/restore and AI generation progress/cancel. Keep bulk background import as advanced. Legacy Character Library scene entry links to Activity Library; preserve character profile initialization. API helpers match backend 73.1. Preserve existing uncommitted i18n content; append only related translations.

- `frontend/pages/shot_library.html`
- `frontend/static/js/shot_library.js`
- `frontend/static/js/scene_library.js`
- `frontend/pages/characters.html`
- `frontend/static/js/characters.js`
- `frontend/static/js/api.js`
- `frontend/static/js/i18n_vi.js`
- `tests/test_scene_library_browser.py`

### 73.3 - Storyboard scene choices and Step 5

Remove project shortlist chip UI/state and writes. Keep still-scene mode. Per beat scene selector has search over all active scenes, grouped categories, and only current archived scene retained as labelled choice. Refresh library when returning to page without replacing unsaved beat edits. Link to Activity Library Scenes tab. Verify existing storyboard UI and static checks.

- `frontend/static/js/step5_video.js`
- `frontend/static/js/storyboard.js`
- `frontend/pages/step5_video.html`
- `tests/test_storyboard_browser.py`
- `tests/test_visuals_project_browser.py`

## Delivery metadata allowed_files

- `.viepilot/phases/73-scene-library/SPEC.md`, `PLAN.md`, `PHASE-STATE.md`, `SUMMARY.md` and three task cards: execution scope and evidence.
- `.viepilot/ROADMAP.md`, `.viepilot/TRACKER.md`, `.viepilot/HANDOFF.json`: incremental Phase 73 checkpoint; preserve older pending owner gates.
- `CHANGELOG.md`: user-visible feature under Unreleased.
- `docs/brainstorm/session-2026-10-23.md`: record crystallized decisions and implementation link.

UI reference: owner screenshot and current Activity Library/Character Library components; retain existing shell and tokens. Prototype inventory (2026-09-14 and 2026-10-06) reviewed during planning; no new page or stack introduced.

## Amendment 73.4 - brief to prompt and external AI workflow

Owner requested simple Vietnamese/English input that becomes a professional scene image prompt for local Qwen GPU or external web AI. Added task card [73.4](tasks/73.4.md) records bounded implementation files, upload completion flow, risk and checks. Implemented and technically verified; owner review pending.
