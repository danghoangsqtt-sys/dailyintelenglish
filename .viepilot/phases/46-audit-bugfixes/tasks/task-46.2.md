# Task 46.2 — BUG-040: deterministic local browser load

## Objective
Local studio pages load with their existing Inter typeface when Internet/font CDNs are unavailable.

## Paths
- frontend/pages/
- frontend/static/css/style.css
- frontend/static/js/app_sidebar.js
- frontend/static/fonts/Inter-Variable.ttf
- frontend/static/fonts/Inter-OFL.txt
- tests/test_offline_fonts_browser.py
- tests/conftest.py
- tests/browser_navigation.py
- tests/test_browser_navigation.py
- tests/test_app_sidebar_browser.py
- .viepilot/requests/BUG-040.md
- .viepilot/phases/46-audit-bugfixes/
- .viepilot/TRACKER.md
- .viepilot/ROADMAP.md
- .viepilot/HANDOFF.json
- CHANGELOG.md

## File-Level Plan
- Regression test: record non-loopback requests and simulate an unavailable external font stylesheet; keep load-event checks and prove the pre-fix failure.
- Download Inter variable font and OFL license from the official Google Fonts source, add local @font-face; remove Google Fonts links from all eleven pages currently using them. Preserve family, weights and layout.
- Run the four affected browser modules together and the new offline regression; retain screenshots/network evidence in disposable test output if needed.

## Risk and conventions
Font license shipped beside asset; no change to browser timing thresholds or application behavior. Use real isolated uvicorn helper; tests never touch production DB/cloud.

## Verified scope refinement before implementation (2026-10-15)
The full run passed 1,614 tests but Chromium returned ERR_NO_BUFFER_SPACE on one local Learning navigation. That entire module passed alone (5/5). Windows System event 4231 also records ephemeral TCP port allocation failure during the earlier audit; it supports resource pressure as a failure class, without proving the current cause. Extend the shared test fixture with one logged retry for this exact infrastructure error on loopback GET navigation only. Do not retry timeouts, assertions, unrelated network errors or external URLs. Test the classification and retry bound; rerun the full suite afterward.

The fail-fast rerun then exposed initial sidebar animation: the Step 2 rail measured 103.796875 px during its initial 232 -> 64 px transition. This was reproduced twice after fonts became local. Keep transitions disabled until the initial stored/default sidebar state has been applied and layout resolved; enable normal user-triggered transitions afterward. The existing initial-width and toggle/drawer browser assertions verify this behavior; do not relax their geometry thresholds.

## Verification
- python -m pytest -q tests/test_offline_fonts_browser.py
- python -m pytest -q tests/test_music_upload_multi_browser.py tests/test_step1_config_edit_browser.py tests/test_step_nav_browser.py tests/test_studio_frame_browser.py
- Ruff and full suite after all phase changes.

## Verification result
Pre-fix stalled-CDN test failed at load in 5 s. After bundling Inter: 38/38 affected-browser and offline tests passed in 34.57 s. Font source: https://github.com/google/fonts/tree/main/ofl/inter, SIL OFL included. No load-state assertion was weakened. Implemented/verified; acceptance/persistence pending.

## Final regression gate
2026-10-15: 1,621 pytest passed in 871.13 s; 72 Vitest passed; Ruff, TypeScript, JS syntax and diff checks clean. Technical implementation/verification complete; formal acceptance and persistence await the owner/PM under AR-06.
