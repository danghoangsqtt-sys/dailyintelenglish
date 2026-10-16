# Task 49.5 — Explainer plan: đoạn, minh họa, locks và approval

- **Status:** planned · 2026-10-16.
- **Dependencies:** 49.2, 49.4
- **Requirements:** R04, R06, R07, R12.
- **Contract:** [SPEC tổng](../../../SPEC.md), [PLAN tổng](../../../PLAN.md), [phase SPEC](../SPEC.md), [phase PLAN](../PLAN.md).
- **Scope:** card này là kế hoạch, chưa có kết quả triển khai hay acceptance.

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
- .viepilot/phases/49-solo-explainer/PHASE-STATE.md
- .viepilot/TRACKER.md
- .viepilot/ROADMAP.md
- .viepilot/HANDOFF.json
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

Chỉ sửa các Paths trên và cập nhật tiến độ card/phase. Nếu phát hiện cần file khác, ghi lý do và mở rộng bounded scope trước code. Các file đã tạo bởi task trước trong Paths được tiếp tục sử dụng; không tự viết lại hệ thống lân cận.

## Risks / guardrails

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

- 2026-10-16: planned; shipping code chưa sửa, tests triển khai chưa chạy.
