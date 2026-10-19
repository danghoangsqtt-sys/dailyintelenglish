# Task 52.2 — ENH-036 Solo explainer and launcher cleanups

Status: implemented_verified 2026-10-19.

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
3. **Launcher timeout** (`desktop_launcher.py` `_open_browser_when_ready`): when the 60 s deadline passes without readiness, write one line to stderr (which is `data/logs/desktop.log` in the windowed EXE) naming the URL so the owner can open it manually. **Plan amended during implementation:** the browser is still *not* opened on timeout — `tests/test_desktop_runtime.py::test_readiness_timeout_does_not_open_competing_process` records the Phase 51 decision that an unverified port may belong to a competing process.

## Risks / best practices

Keep the editor's compact style. Do not alter save/CAS flow. Launcher must still never open a different build on an occupied port (`_reuse_existing_instance` unchanged).

## Verification

Focused tests for the explainer service and launcher; Solo editor browser test if present; `node --check` for the JS; Ruff; full pytest before marking verified.

## Verification result 2026-10-19

Focused 60 passed (desktop runtime, Solo editor browser, explainer plan/API/layout), including two new tests: `test_diagram_node_ids_follow_labels_so_edges_never_reconnect` (real Chromium) and `test_readiness_timeout_leaves_a_manual_open_hint`. The existing `test_missing_production_geometry_is_a_refusal_not_a_permissive_placeholder` still passes after the direct import. `node --check` and Ruff clean. Full suite runs at phase end.
