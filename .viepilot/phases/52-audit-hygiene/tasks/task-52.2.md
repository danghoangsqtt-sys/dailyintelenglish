# Task 52.2 — ENH-036 Solo explainer and launcher cleanups

Status: planned 2026-10-19.

## Objective

Fix three small correctness/feedback issues found by the 2026-10-19 audit without changing APIs or schemas.

## Paths

- frontend/static/js/explainer_editor.js
- backend/library/explainer_service.py
- backend/desktop_launcher.py
- tests/ (new or extended regression tests for the service and launcher; browser test for the editor if an existing Solo editor browser test is present)
- .viepilot/requests/ENH-036.md

## File-Level Plan

1. **Diagram node IDs** (`explainer_editor.js`, `field==="nodes"` branch): reuse an existing node ID by matching the trimmed label first (each old node used at most once), then fall back to a fresh unique `node-N` that does not collide with existing IDs. Edges are kept only when both ends still exist (current filter). Deleting a middle line therefore drops only that node's edges instead of reconnecting others.
2. **Direct layout import** (`explainer_service.py` `_validate_geometry`): import `validate_plan` from `backend.library.explainer_layout_service` directly and remove the `ModuleNotFoundError` fallback and the stale "arrives in 49.6" comment. Behaviour when the checker raises is unchanged.
3. **Launcher timeout** (`desktop_launcher.py` `_open_browser_when_ready`): when the 60 s deadline passes without readiness, write one line to stderr (which is `data/logs/desktop.log` in the windowed EXE) and open the URL anyway, so a slow first start still reaches the app.

## Risks / best practices

Keep the editor's compact style. Do not alter save/CAS flow. Launcher must still never open a different build on an occupied port (`_reuse_existing_instance` unchanged).

## Verification

Focused tests for the explainer service and launcher; Solo editor browser test if present; `node --check` for the JS; Ruff; full pytest before marking verified.
