# Task 27.4: Studio steps 1-7 share one frame

## Finding

Steps 2 to 7 already ran in the studio frame (the app sidebar, a steps panel on the left, the stage in the middle, an inspector on
the right, the timeline below in steps 2, 4 and 5). Only Step 1 (project configuration) was a centred form with a pill bar on top.

## Plan

- `frontend/pages/step1_config.html`: the form moves into the same shell (`shell-flex` > `shell-row` with `pane-sidebar`,
  `pane-main`, `pane-inspector`); the step list sits in the left panel (workflow variant), the right panel says what happens next.
- `frontend/static/js/step1_config.js`: step list as the workflow variant and `WorkspaceShell.init` (resizers, collapse).
- Tests: `tests/test_studio_frame_browser.py` (all seven steps: the three panels in order, seven step pills, one active, no sideways
  scroll); the Step 1 sidebar test now expects the step list in the left panel.

## Paths

- `frontend/pages/step1_config.html`
- `frontend/static/js/step1_config.js`
- `tests/test_studio_frame_browser.py`
- `tests/test_app_sidebar_browser.py`

## Verification

Step 1 tests (12), the sidebar suite (15), the frame test (7) green; a screenshot of Step 1 in the frame.
