# PLAN — Phase 76: Topic / Series / Video project folders

**Status:** implemented, packaged and installed in local 2.0.0 after a later owner request; not publicly released. Source: [SPEC](SPEC.md), [brainstorm](../../../docs/brainstorm/session-2026-10-23-project-folders.md).

## Architecture and order

Keep `project_exports` as the per-project list of selected output components. Add a `layout_mode` that defaults existing rows to `legacy`, a stored relative path for stable collision handling, and a topic-root table keyed by the Channel Plan topic ID or a normalized freeform project topic. A hierarchical save updates the shared topic parent and this project's mode/items/path. Preserve the existing destination resolver for legacy rows.

The existing API remains the single source for settings, preview, save, sync, open and stop. `project_folder.js` shows the user's selected parent separately from the resolved project folder and communicates an explicit mode on save. New panels default to the hierarchical mode; a legacy project stays legacy until its user switches its folder setting. Reuse the panel in Step 1 and Step 7.

## Tasks and dependencies

| Task | Outcome | Depends on | Card |
|---|---|---|---|
| 76.1 | Additive persistence, safe path resolver, hierarchical API behavior and focused service/API tests | Phase 41 export service | [76.1](tasks/76.1.md) |
| 76.2 | Update shared Step 1 / Step 7 folder panel to choose mode, show destination and reuse Topic root | 76.1 | [76.2](tasks/76.2.md) |
| 76.3 | Regression coverage, user/architecture docs and phase state handoff | 76.1–76.2 | [76.3](tasks/76.3.md) |

## Bounded paths

- Task 76.1: `backend/db/migrations/039_topic_export_roots.sql`, `backend/content/export_service.py`, `backend/api/export.py`, `tests/test_phase41_export.py`, `tests/test_phase76_topic_export.py`.
- Task 76.2: `frontend/static/js/project_folder.js`, `frontend/static/css/style.css`, `frontend/static/js/i18n_vi.js`, `tests/test_project_folder_browser.py`.
- Task 76.3: `docs/operations/topic-project-folders.md`, `.viepilot/ARCHITECTURE.md`, `.viepilot/PROJECT-CONTEXT.md`, `.viepilot/ROADMAP.md`, `.viepilot/TRACKER.md`, `.viepilot/HANDOFF.json`, `.viepilot/phases/76-topic-project-folders/{PHASE-STATE.md,tasks/*.md}`, `docs/brainstorm/session-2026-10-23-project-folders.md`, `CHANGELOG.md`.

Original execution preserved the existing local package outputs and prior Phase 73–75 work. A later explicit owner request authorized a coherent 2.0.0 rebuild, local Full installation, commit and push on the current branch; no version bump, tag or public release was requested.

## Risks and verification

- **Legacy compatibility:** migration must default all pre-existing project exports to legacy resolution. Cover both reading and resaving those rows.
- **Shared-root semantics:** only the root suggestion is shared; per-project items and opt-in state stay separate so an existing project is not silently redirected.
- **Path collisions:** use stable identity suffixes only for colliding sibling labels; sanitize Windows reserved names and trailing periods/spaces.
- **Topic edits:** existing outputs remain at their original location. The latest Topic name is used for subsequent hierarchical sync; show the resolved location before saving.
- **Checks:** focused Phase 41/76 export tests, relevant browser tests, Ruff on changed Python, JS syntax, migration from a legacy-shaped DB, JSON/diff checks. Do not run the entire suite unless focused results indicate a regression.
