# Phase 79 state

Status: implemented_verified (2026-10-26). Not pushed; not rebuilt/installed (owner decides).

| Task | Scope | Status |
|---|---|---|
| 79.1 | BUG-053 image worker errors | done — typed ImageWorkerError, 502 with a plain reason; 3 new tests, Qwen thumbnail suites 22 passed |
| 79.2 | BUG-054 superseded render attempts | done — replaced attempt folder removed after commit (episode, vertical, clip); 5 new tests; existing orphans: 3 folders, 0.63 GB, not deleted (owner decides) |
| 79.3 | ENH-056 local API exposure, BUG-055 log noise, aria helper | done — own-origin CORS, local Host check (automation client moved to localhost), reset traceback filtered, aria attributes; 15 new tests |
| 79.4 | ENH-055 ROADMAP drift, records, full tests | done — ROADMAP reconciled; full pytest 2165 passed (19:27) |

Full pytest: first run 2162 passed / 3 failed (test base URL `http://test` refused by the new Host check, fixed; 2 activity-library browser tests passed 3/3 alone); second run **2165 passed, 0 failed**.

Install 2026-10-27 (owner: "Build the new Full edition with Phases 79 and 80 and install it into the app, keeping backups like last time"): Full 2.0.0 built from a00322a (clean) into `dist/2.0-phase80-20261027/` (ZIP SHA-256 8eb5cfcc307489c72f0a698c9ae5f7c30a6c7385aa00bdd98436beaa6ca6420c); installed with `scripts/install_desktop.ps1` (idle-job preflight passed; `app.before-upgrade.db`, `app.at-exit.db`, previous app and Desktop shortcut in `data/backups/desktop-20261027-153256-221/`). Restarted PID 27316: dashboard 200, main-folder and Shorts-batch APIs, new batch page, renderer ready, foreign Host refused (400), SQLite integrity ok, 66 projects, 0 FK issues. Main save folder not chosen yet (owner). Lite not rebuilt. Not pushed.
