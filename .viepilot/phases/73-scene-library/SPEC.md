# Phase 73 - Scene Library and storyboard selection

Execution authorized by owner 2026-10-23: vp-crystallize + vp-auto, reiterated "continue". Source: docs/brainstorm/session-2026-10-23.md (D1-D4).

Activity Library has Activity pictures and Scenes tabs, distinct entities. Scenes supports metadata creation/edit, duplication, AI background generation, search/category/plate filters and archive/restore. Preserve built-in deletion protection. Keep existing advanced folder import. Step 5 chooses scenes per beat from the active library; remove project shortlist chips. AI and deterministic fallback consume active scenes. Archive retains IDs, previews and historical project/storyboard/render references; existing beats can retain archived choices. Preserve still-picture mode selector and historical project_scenes data/API for compatibility.

Acceptance: create scene and generate AI background in library; newly added scene immediately available on entering/reloading storyboard; >3 distinct library scenes can be chosen across beats subject to existing image budget; archive hides new choices and preserves old references; restore returns choice; Activity workflows continue working. No release/build required.

Risks: archived choices leaking through direct SQL or fallback; invalidating old storyboard saves; UI initialization races. Verify through targeted API/service/browser checks and JS/Python static checks. Real paid/GPU generation need not run; exercise queued generation and terminal states with controlled fixtures.
