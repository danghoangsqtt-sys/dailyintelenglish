# Task 49.5 — Explainer plan: đoạn, minh họa, locks và approval

- **Status:** implemented_verified (technical) · 2026-10-16; owner acceptance separate, no V49 acceptance implied.
- **Dependencies:** 49.2, 49.4
- **Requirements:** R04, R06, R07, R12.
- **Contract:** [SPEC tổng](../../../SPEC.md), [PLAN tổng](../../../PLAN.md), [phase SPEC](../SPEC.md), [phase PLAN](../PLAN.md).
- **Scope:**49.5a/b foundation and proposal/review integration technically verified. Real geometry success belongs49.6; owner acceptance is separate.

## Objective

Explainer plan: đoạn, minh họa, locks và approval. Hoàn thành contract tương ứng trong SPEC, giữ khả năng dùng project classic và dữ liệu đã xuất.

## Paths

- backend/schemas/explainer.py
- backend/core/constants.py
- backend/schemas/ai_job.py
- backend/main.py
- backend/ai/llm/ai_worker.py
- backend/ai/llm/prompt_loader.py
- backend/library/storyboard_service.py
- frontend/static/js/api.js
- backend/library/explainer_service.py
- backend/api/explainer.py
- backend/ai/prompts/storyboard/explainer.txt
- tests/test_explainer_plan.py
- tests/test_explainer_api.py
- backend/db/migrations/028_explainer_jobs_assets.sql
- tests/test_explainer_jobs_migration.py
- backend/library/explainer_assets.py
- backend/library/explainer_timing.py
- tests/test_explainer_timing.py
- tests/test_explainer_assets.py
- backend/content/project_service.py
- backend/api/ai_jobs.py
- backend/ai/llm/ai_job_service.py
- .viepilot/phases/49-solo-explainer/PHASE-STATE.md
- .viepilot/TRACKER.md
- .viepilot/ROADMAP.md
- .viepilot/HANDOFF.json
- .viepilot/PLAN.md
- docs/api.md
- docs/operations/task49-5b-recovery-20261016.md
- .viepilot/requests/BUG-043.md
- CHANGELOG.md
- .viepilot/phases/49-solo-explainer/tasks/task-49.5.md

## File-Level Plan / allowed_files

1. Đăng ký durable AI operation propose_explainer, validate hai tầng, chụp source fingerprint trước/sau LLM; không giữ DB transaction khi gọi mạng.
2. Segment có stable ID, token anchors end-exclusive, bao phủ toàn bộ lời nói; thời gian suy ra từ audio thật. Chưa có audio chỉ lưu draft.
3. Photo dùng asset ref/prompt ngoài; diagram steps/comparison/cause_effect có nodes/edges giới hạn; text cards plain text; có important rectangles và ghi chú nguồn khi có.
4. GET/PATCH/propose/approve API theo SPEC: lock trường owner sửa, regenerate chỉ unlocked, expected_revision và 409.
5. Approval snapshot pin presenter, assets, voice/audio và layout rules. Script/audio/pack/asset thay đổi làm stale; locked segment mất anchor phải báo issue.
6. Delegate geometry validation cho 49.6; không approve bằng placeholder luôn true. Classic storyboard giữ scene/insert contract.

**File mới dự kiến:** `backend/library/explainer_service.py`, `backend/api/explainer.py`, `backend/ai/prompts/storyboard/explainer.txt`, `tests/test_explainer_plan.py`, `tests/test_explainer_api.py`.

### Execution refinement (isolated exploration during49.4 gate)

- Inventory found the existing jobs table CHECK accepts only script/learning. New028 (never rewrite applied027) must preserve jobs and checkpoint child rows while adding propose_explainer. Rebuild/copy child and parent together under runner transaction, drop old child before parent, rename replacements and recreate indexes. No foreign-key PRAGMA toggles. Test populated DB copy, injected failure rollback, FK and restart.
- Add immutable project illustration registry in028 and a focused explainer_assets service; do not store knowledge photos in character sprite slots. Stage verified bounded image/hash outside DB lock, publish guarded metadata, expose multipart upload/versioned content APIs, and keep old image versions. Add the explainer artifact category to explicit project deletion; no unsolicited owner-data cleanup.
- Separate token/time mapping into explainer_timing. End-exclusive anchors refer to script token order; match actual aggregated word events including punctuation/contractions. Missing/ambiguous timings are approval issues, never invented seconds from word count. Coverage must be contiguous, exact and unique.
- Job snapshots pin source FP, previous draft/locks and expected plan revision. Existing segment IDs/locked fields survive regeneration; missing locked anchors produce explicit issues. Generic AI job entry must construct the same safe explainer snapshot rather than enqueue an incomplete project-only payload. Commit plan/history/job completion atomically after source/revision recheck; resume a validated checkpoint after interruption.
- Approval stores immutable reviewed snapshot and version refs; source changes are recomputed on read/render to surface stale. Until49.6's real geometry checker is available, production approval must refuse unresolved layouts. Test pin/CAS logic against a labeled validator double, retaining API refusal when geometry is unavailable; do not ship an always-true geometry placeholder.
- Front21 real owner art remains pending; fixtures only validate mechanics. Existing script/learning jobs and classic storyboard remain unchanged.

### Bounded execution slices

**49.5a — persistence, illustrations and real token timing:**028 migration, explainer_assets/timing services, their focused tests, named image/timing limits in core/constants, and the explainer artifact category in project_service deletion. No new AI operation is exposed until49.5b registers its complete handler/API. Verify migration copy/rollback/restart, immutable image decode/hash/path/CAS/cleanup, token coverage and real prior Edge mapping, full regression/Ruff before a durable subtask checkpoint. Task49.5 remains in_progress.

**49.5b — proposal, draft/history, locks and approval:** bounded plan/wire schemas, service/API/prompt, safe AI operation dispatch + worker registration, source fingerprints and revision CAS. Verify job/cancel/resume/error races and locked fields, missing real geometry/timing/assets/factual-review refusal, then full regression before task completion. Geometry success is verified with actual49.6; no permissive placeholder approval.

49.5b implementation detail: proposal wire data excludes server approval/revision/fingerprint/locks/geometry; existing segment IDs/order must survive regeneration. Owner PATCH carries expected source fingerprint as well as revision, automatically locks edited groups, and has an explicit bounded unlock map. A new proposal always requires factual review for changed content/visuals. Approval creates another immutable history revision and pins validated file hashes/timings; the production geometry resolver raises an actionable refusal until49.6 implements it. Generic AI-job creation must route through the same snapshot builder as the dedicated propose endpoint. Keep scripts/learning behavior unchanged and keep image processing/file verification outside DB locks.

Chỉ sửa các Paths trên và cập nhật tiến độ card/phase. Nếu phát hiện cần file khác, ghi lý do và mở rộng bounded scope trước code. Các file đã tạo bởi task trước trong Paths được tiếp tục sử dụng; không tự viết lại hệ thống lân cận.

## Risks / guardrails

### Recovery amendment2026-10-16 — owner evolve+auto authorization

Owner explicitly requested implementing BUG-042/043/044 and reviewing/completing49.5b after recovery audit. Existing49.5 Paths remain the bounded product scope; add `docs/operations/task49-5b-recovery-20261016.md` and `.viepilot/requests/BUG-043.md` for evidence/request updates. BUG-042/shared helper and BUG-044 docs have separate Phase50 cards, approved by the same instruction.

Master `.viepilot/PLAN.md` is included for synchronizing verified counts and next task after actual gates; do not change target scope15 or pending owner acceptance.

`docs/api.md` is included for regeneration with existing `scripts/generate_api_docs.py` after the new explainer routes/schema; generated route documentation must reflect the actual source OpenAPI without starting lifespan or opening the owner DB. Generator code is read-only.

- `backend/schemas/explainer.py`: move segment/aspect uniqueness checks to PATCH request semantic validation while keeping persisted plan validation; malformed owner input must be422 envelope.
- `tests/test_explainer_api.py`, `tests/test_explainer_plan.py`: regression for both original500s, history unchanged on failure, good PATCH afterwards; extend uncovered cancel/recovery/approval/race cases found in review.
- `backend/library/explainer_service.py`, prompt/API/job registration Paths above: review whole49.5b; fix only contract gaps, preserve source/CAS/locks/history and typed errors. Align future geometry import with49.6 card naming; continue refusing missing real geometry.
- Verification: red/green targeted bugs; focused plan/API/timing/assets/jobs/front suites; full `pytest tests/ -x -q`; Ruff, modifiedJS syntax, renderer Vitest/TypeScript; record real commands/results. No Player/layout implementation, owner DB migration, EXE replacement or release.

Risks: shared async cancellation, schema validation error translation, late provider publication and checkpoint recovery. Avoid permissive approval, guessed timing, blanket exception masking and unrelated refactoring. User instruction supplies execution approval; formal owner visual/factual acceptance stays distinct.

Timestamp AI tự đoán sẽ lệch audio. Revision guard phải bao gồm thay đổi source, không chỉ form edits.

Dùng constants/path helpers hiện có, service layer async, validation API + semantic. Không giữ shared DB lock trong network/render/copy nặng. Không sửa dữ liệu production khi có thể dùng sandbox. Không thay đổi gate cũ hoặc phát hành chỉ vì task kỹ thuật chạy qua.

## Verification / expected results

1. Mọi token có đúng một lần; anchors tồn tại, đúng thứ tự, không overlap, timings thật; reject code/diagram quá lớn/malformed AI.
2. Save/reload/history, locks giữ nguyên; regenerate chỉ unlocked; concurrent PATCH/propose không ghi đè bản mới.
3. Thiếu audio/asset/pack hoặc layout chưa resolve thì không approve; input changes làm approved plan stale.
4. Durable job restart/cancel/error theo worker hiện có, không ghi đè draft mới.
5. `git diff --check`; review diff đúng Paths. Chạy quality gates theo SYSTEM-RULES và PLAN trước commit; explicit staging, tuân thủ PM/owner authorization.

## Acceptance / handoff

- [ ] Các bước trên có evidence thực, test commands và kết quả ghi vào card.
- [ ] Error/race/compatibility cases liên quan được kiểm tra, không chỉ happy path.
- [ ] Không ghi “done/pass” cho test hoặc owner gate chưa chạy.
- [ ] PM/owner nhận kết quả theo AR-06; ghi technical verification và owner acceptance riêng.

## Progress

- Recovery2026-10-16: red regressions **4 failed as expected** on old code (cancel during body/commit, duplicate aspects/IDs PATCH500). Shared helper now waits for shielded rollback before releasing its lock even under repeated cancellation; explainer uses this helper. PATCH validates uniqueness and generic proposal revisions reject bool/string coercion; duplicate AI IDs trigger bounded repair. Geometry import matches future `explainer_layout_service`; real checker still required.
- Focused recovery verification: **175 passed in28.42s** across transactions/plan/API/worker/jobs/assets/timing/migration. Renderer **104 passed**, TypeScript/Ruff/modifiedJS/diff clean. Full suite started, result pending. Independent sandbox process smoke: **2 fresh process restarts**, revision history1/2 and edited visual lock retained, idempotent replay same job without provider call, stale PATCH409, approval422, FK/integrity clean. Evidence `data/tmp/task49-5b-smoke-9bffce74861b4f5894b0d71cba91bdf3/verification.json`.
- First full run:1626 passed before the live Edge TTS test failed on sandbox network denial (`speech.platform.bing.com:443`, Access is denied),678.36s. Isolated required retry outside sandbox passed1/1 in1.53s,6 words with real3.312s audio. Full suite restarted outside sandbox on identical source; no test skipped/mocked to bypass the failure. Final result pending; logs retain both attempts.

- 2026-10-16,49.5a technical verification:028 extends the durable operation CHECK and creates a separate immutable project illustration registry. Populated copy preserved17 jobs/43 checkpoints/13 projects/290 script lines; fault injection after table replacement fully rolled back schema/rows/tracking, FK/integrity and2 restarts verified. Owner DB was never opened for writing.
- Illustration service verifies format/size/pixels, EXIF and alpha, stages/normalizes/hashes outside DB transactions, checks the live Solo project before metadata publication and cleans cancelled attempts. Explicit project deletion includes its explainer files; prior image IDs/versions remain immutable. API upload/serving is49.5b, not exposed yet.
- Token index validates exact end-exclusive script coverage and in-segment gesture anchors. Timeline uses measured word events, handles split contractions and preserves actual pauses/lead/tail; rejects stale/missing/ambiguous/overlapping events instead of estimating seconds. Real prior Edge fixture resolved25/25 words over11.54s (mapping evidence only, not a Solo render).
- Verification:34 new focused tests,143 related migration/jobs/projects/timing/image tests passed; `ruff check .` and `git diff --check` clean. Full `pytest tests/ -x -q`: **1809 passed**,1 existing Starlette warning,740.11s. No frontend JS/UI change in49.5a. Evidence:`data/tmp/evolve-20261016/task49_5a-full.log`, `drafts/explainer-migration-copy-1b30664a180b4a6fafd5ffacd9d597b4/verification.json`, `voice-media-dbc2312672/explainer-timing-verification.json` under the same run folder.
-49.5 remains **in_progress**. Next49.5b: source/revision CAS, proposal/locks/history/approval APIs and worker integration. Approval remains unavailable until actual timing/front/assets/factual review and49.6 geometry validation succeed. Real Hoang front21 and V49 owner acceptance still pending; installed EXE/release unchanged.

- Final recovery gate2026-10-16: **1848 passed in741.01s**,1 existing Starlette warning, full suite outside sandbox; no test deselected or mocked to bypass the live Edge case.175 focused,104 renderer,TypeScript/Ruff/JS and generated180-route API parity pass. 49.5b technically verified: full pytest 1848 passed in741.01s;175 focused in28.42s;104 renderer tests and TypeScript/Ruff/JS/diff clean. BUG-042 cancellation-safe shared rollback and BUG-043 PATCH422 fixed;BUG-044 docs reconciled. Two fresh process restarts preserved history/locks/idempotency;integrity/FK clean. Next49.6 geometry/layout; production approval refuses missing real geometry. Owner DB/EXE/release and V49/older gates unchanged. Full report:`docs/operations/task49-5b-recovery-20261016.md`. Git checkpoint follows actual persistence gate; no owner gate self-approved.
