# Task49.5b và BUG-042/043/044 — recovery implementation

Ngày2026-10-16, Asia/Bangkok. Owner yêu cầu `vp-evolve` xử lý các BUG và `vp-auto` triển khai, rà soát hoàn tất49.5b. Phạm vi được ghi trước mã trong task49.5 recovery amendment và Phase50 cards. Final technical quality gate: **1848 passed in741.01s**, plus175 focused tests,104 renderer tests and2 fresh process restarts. Owner acceptance and Git persistence are separate from those technical results.

## Thay đổi

- **BUG-042 /50.1:** shared write transaction rollback cả cancellation/BaseException. Cleanup chạy trong task được shield; giữ lock tới khi rollback hoàn thành, kể cả caller bị cancel thêm. Propagate cancellation sau cleanup; lỗi rollback vẫn nổi lên. Explainer bỏ workaround riêng và dùng helper chung.
- **BUG-043 /49.5b:** PATCH schema kiểm tra aspects/segment IDs unique ngay tại request boundary, trả422 error envelope. Bad edit không đổi current plan/history. Proposal schema cũng kiểm tra duplicate IDs để một lỗi model đi qua bounded repair thay vì lỗi publication. Generic entry yêu cầu strict integer revision, cùng semantics với dedicated entry.
- **49.5b integration:** `propose_explainer` đăng ký worker và prompt, hai API entry dùng cùng guarded snapshot builder, source/revision/lease/cancel recheck trước publication; checkpoint hợp lệ được dùng lại, checkpoint hỏng được regenerate. Plan/history/job completion commit atomically. Owner edits tự khóa nhóm; explicit unlock, stale conflicts, immutable history và approved snapshots pin media/front/illustrations.
- **BUG-044 /50.2:** architecture/meta tách verified source với planned49.6+ và EXErc.1. Renderer README/package description mô tả production backend subprocess, hai compositions Episode/StillFrame, install/dev checks; không đổi dependencies/version.
- Geometry import thống nhất với file dự kiến `backend/library/explainer_layout_service.py`. Production approval từ chối nếu checker chưa tồn tại hoặc proof thiếu/version/aspects sai; fixture validator không chứng minh layout thật.
- `docs/api.md` regenerated from source OpenAPI with180 routes, including the8 explainer endpoints; generator imports the app without running lifespan or migrating the owner DB.

## Verification đã có

| Kiểm tra | Kết quả |
|---|---|
| New failure regressions on old code |4 failed as expected:2 cancellation transaction leaks,2 PATCH500 |
| Focused transactions/plan/API/worker/jobs/assets/timing/migration |175 passed,28.42s |
| Renderer Vitest |104 passed,14 files |
| Renderer TypeScript |Passed |
| Ruff toàn repo; modifiedJS syntax; diff whitespace |Passed |
| First full pytest in sandbox |1626 passed, then live Edge TTS failed because sandbox denied outbound speech.platform.bing.com;678.36s. Not declared a full PASS |
| Isolated real Edge TTS retry outside sandbox |1 passed,1.53s;6 words,3.312s audio,last word ends2.450s |
| Full pytest outside sandbox |**1848 passed in741.01s**,1 existing Starlette warning;all tests selected |
| Disposable app persistence |2 fresh process restarts; history1/2, owner visual lock, same completed idempotent job, stale PATCH409, refusal422; integrity/FK clean |

Full command:

```powershell
.\.venv\Scripts\python.exe -m pytest tests/ -x -q -p no:cacheprovider --basetemp data/tmp/task49-5b-full-network-20261016
```

First log: `data/tmp/task49-5b-full-20261016.log`. Network-enabled full retry uses basetemp `data/tmp/task49-5b-full-network-20261016` and log `data/tmp/task49-5b-full-network-20261016.log`; it does not deselect or weaken the live test. Focused command covers `test_transactions`, `test_explainer_plan`, `test_explainer_api`, `test_ai_worker`, `test_ai_job_service`, `test_ai_jobs_api`, `test_explainer_assets`, `test_explainer_timing`, `test_explainer_jobs_migration` with separate basetemp.

Persistence script: `data/tmp/task49-5b-restart-smoke-20261016.py`. Evidence: `data/tmp/task49-5b-smoke-9bffce74861b4f5894b0d71cba91bdf3/verification.json`. Each restart runs a new Python process against one disposable DB. Provider and catalog are synthetic/offline; no real speech/listening or factual/CEFR acceptance is claimed. Initial harness attempts required explicit offline voice fixture and separate processes instead of reusing a loop-bound lock; no production code change was needed for the harness.

## Delivery boundary

Owner DB, installed EXE, existing project media and published1.4.0-rc.1/stable1.3.0 stay unchanged. This scope completes plan infrastructure, not the layout/Player/render planned in49.6–49.10. Hoang front21 real art and V49 owner review remain pending; Phase47 and B-25/B-26/B-27/B-28 remain pending.

Technical verification is recorded separately from PM/owner acceptance. Git checkpoint/push status will be recorded after final gates and actual persistence; no release/tag acceptance is implied by tests.

## Next step and checkpoint

49.5a/b are technically verified; Phase49 has5/10 verified tasks, next49.6 geometry/layout. Phase50.1/50.2 and BUG-042/043/044 are technically fixed pending PM review. Save explicit Git checkpoints and verify upstream persistence before declaring workflow PASS; no build or release is part of this delivery. The original audit reproducer asserts the old defect and is historical; use committed `test_transactions`, `test_explainer_api` and `test_explainer_plan` regressions to verify the corrected behavior.
