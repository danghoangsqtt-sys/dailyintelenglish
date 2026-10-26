# Phase 79 state

Status: implemented_verified (2026-10-26). Not pushed; not rebuilt/installed (owner decides).

| Task | Scope | Status |
|---|---|---|
| 79.1 | BUG-053 image worker errors | done — typed ImageWorkerError, 502 with a plain reason; 3 new tests, Qwen thumbnail suites 22 passed |
| 79.2 | BUG-054 superseded render attempts | done — replaced attempt folder removed after commit (episode, vertical, clip); 5 new tests; existing orphans: 3 folders, 0.63 GB, not deleted (owner decides) |
| 79.3 | ENH-056 local API exposure, BUG-055 log noise, aria helper | done — own-origin CORS, local Host check (automation client moved to localhost), reset traceback filtered, aria attributes; 15 new tests |
| 79.4 | ENH-055 ROADMAP drift, records, full tests | done — ROADMAP reconciled; full pytest 2165 passed (19:27) |

Full pytest: first run 2162 passed / 3 failed (test base URL `http://test` refused by the new Host check, fixed; 2 activity-library browser tests passed 3/3 alone); second run **2165 passed, 0 failed**.
