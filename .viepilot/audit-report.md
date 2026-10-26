# Audit Report - 2026-10-26 (second pass, after Phase 78)

Scope: owner `/vp-audit` "xem dự án còn vị trí nào bất hợp lý và bug tiến hành phân tích và sửa lỗi". Branch `owner-runs/20261001-r9`. Evidence: the installed app's `data/logs/desktop.log`, the data folders, a security review of the local API, Ruff bug rules (`F,E9,B,PLE,ASYNC,S608`). Fixes delivered as [Phase 79](phases/79-audit-fixes/PLAN.md).

## Summary

| Tier | Status | Notes |
|---|---|---|
| 1 State | ⚠️ | Phases 78–79 committed but not pushed (owner has not asked); phases 39–77 untagged by design |
| 2 Docs | ✅ after fix | ENH-055 ROADMAP drift (Phase 49, 76) reconciled; CHANGELOG updated |
| 3 Stack/code | ✅ after fixes | 3 bugs and 1 security gap fixed with tests (below); Ruff bug rules: only harmless hits |
| 4 Framework | skipped | not the ViePilot repo |

## Fixed (Phase 79)

| ID | Severity | Finding | Fix |
|---|---|---|---|
| BUG-053 | high | Step 6 topic picture / AI scenes: any image-worker failure was an unhandled 500. The owner hit it twice (`OSError: The paging file is too small … (os error 1455)`). | `ImageWorkerError` with a plain, actionable message (virtual memory / GPU memory / crash / other); 502 with that message; raw text only in the log; Vietnamese copy. |
| BUG-054 | medium | Every render made a new attempt folder; the replaced one (150–250 MB video + 7–8 MB log) stayed forever. 3 orphan folders, 0.63 GB today. | After a render is committed as current, the previous attempt folder is removed (episode, vertical, clip). Only 32-hex attempt folders in the project/clip folder that hold no current path; a locked file leaves it for later. |
| ENH-056 | medium | CORS allowed any `localhost:<port>` with credentials; no Host check, so DNS rebinding could reach the API (projects, AI keys, file writes). | CORS limited to the studio's own origins; `LocalHostOnly` refuses other Host names (off when the owner sets a network `APP_HOST`). The night automation's in-process client moved from `http://automation` to `http://localhost` (it would have been refused). |
| BUG-055 | low | 211 harmless `ConnectionResetError [WinError 10054]` tracebacks (browser cancelling video range requests) buried real errors in `desktop.log`. | That one asyncio callback error is dropped; every other loop error is still logged. |
| — | low | `dashboard_channel.js` `el()` assigned `aria-*` as DOM properties (silently dropped). | Set as attributes. |
| ENH-055 | low | ROADMAP Phase 49 / 76 status drift. | Reconciled with TRACKER. |

## Reviewed, no change needed

- All 17 file-serving endpoints validate names or resolve paths inside their data folders.
- Settings API returns masked keys only.
- The one audio 500 in the log was a handled error that succeeded on retry.

## Left for the owner

- Existing orphan renders (3 folders, 0.63 GB) are not deleted; they can be removed once the owner agrees.
- Installed app (Phase 78 build) does not include Phase 79 until it is rebuilt and installed.

## Tests

- New: `test_local_api_exposure.py` (15), `test_render_attempt_cleanup.py` (4), BUG-053 tests in the Qwen thumbnail suites (3), `test_video_api` render-replacement test (1).
- Full suite first run: 2162 passed, 3 failed — `test_script_api` used `base_url="http://test"` (now refused by the Host check; test moved to `http://localhost`, 15/15 repeat passes); 2 activity-library browser tests passed 3/3 in isolation. Second full run: **2165 passed, 0 failed** (19:27).

## Stack guardrails (for vp-auto preflight)

- In-process clients (`httpx.ASGITransport`) and tests use `http://localhost` as base URL.
- Image-worker failures surface as `ImageWorkerError`; endpoints map it to a friendly 4xx/5xx, never let it escape.
- A render that replaces another removes the previous attempt folder only after the database commit.
- Previous guardrails stay: migration functions registered by every runner; full suite before packaging; commit new modules with their importers; UI errors show friendly text.
