# Task 49.6 — Bố cục hai tỷ lệ, vùng quan trọng và đường motion

- **Status:** planned · 2026-10-16.
- **Dependencies:** 49.5
- **Requirements:** R03, R04, R05, R06, R11.
- **Contract:** [SPEC tổng](../../../SPEC.md), [PLAN tổng](../../../PLAN.md), [phase SPEC](../SPEC.md), [phase PLAN](../PLAN.md).
- **Scope:** card này là kế hoạch, chưa có kết quả triển khai hay acceptance.

## Objective

Bố cục hai tỷ lệ, vùng quan trọng và đường motion. Hoàn thành contract tương ứng trong SPEC, giữ khả năng dùng project classic và dữ liệu đã xuất.

## Paths

- backend/library/explainer_service.py
- backend/schemas/explainer.py
- backend/core/constants.py
- renderer/src/safeZone.ts
- renderer/src/types.ts
- backend/library/explainer_layout_service.py
- tests/test_explainer_layout.py
- renderer/src/explainerLayout.ts
- renderer/src/explainerLayout.test.ts
- .viepilot/phases/49-solo-explainer/PHASE-STATE.md
- .viepilot/TRACKER.md
- .viepilot/ROADMAP.md
- .viepilot/HANDOFF.json
- CHANGELOG.md
- .viepilot/phases/49-solo-explainer/tasks/task-49.6.md

## File-Level Plan / allowed_files

1. Pure layout solver cho left/right/center và uniform scale, normalized coordinates, hai variant riêng 16:9 và 9:16.
2. Default height22%, khoảng12–38% thêm giới hạn width/safe area; xét important bounds, caption/logo, hợp nhất alpha bounds của pose và motion margin.
3. Ảnh chưa annotation được contain vào panel riêng; owner sửa important rectangles, không dựa vào AI đoán góc trống.
4. Đề xuất reflow/contain/scale khác; không fit thì có issues và không approve. Không ẩn presenter hoặc chồng lên chữ.
5. Giữ vị trí khoảng2.5s khi phù hợp; kiểm tra đường easing, không có hành lang an toàn thì cut tại ranh giới đoạn và luôn có presenter.
6. Backend validation và renderer helper dùng cùng versioned geometry fixtures; backend là nguồn quyết định hợp lệ, preview phản hồi nhanh.

**File mới dự kiến:** `backend/library/explainer_layout_service.py`, `tests/test_explainer_layout.py`, `renderer/src/explainerLayout.ts`, `renderer/src/explainerLayout.test.ts`.

Chỉ sửa các Paths trên và cập nhật tiến độ card/phase. Nếu phát hiện cần file khác, ghi lý do và mở rộng bounded scope trước code. Các file đã tạo bởi task trước trong Paths được tiếp tục sử dụng; không tự viết lại hệ thống lân cận.

## Risks / guardrails

Easing overshoot có thể vượt box; xét envelope hoặc dùng easing không overshoot. Safe-area centering khác tâm frame.

Dùng constants/path helpers hiện có, service layer async, validation API + semantic. Không giữ shared DB lock trong network/render/copy nặng. Không sửa dữ liệu production khi có thể dùng sandbox. Không thay đổi gate cũ hoặc phát hành chỉ vì task kỹ thuật chạy qua.

## Verification / expected results

1. Ảnh rộng/dọc/nội dung giữa, tay lớn, diagram/text quá khổ, mọi anchor, min/max scale và safe zone từng aspect.
2. Kiểm tra union bounds và continuous path/envelope, không chỉ đầu/cuối; trường hợp không thể fit phải fail rõ.
3. Backend/TS geometry fixtures khớp; seek/frame order cho cùng kết quả; approved layouts không che vùng bảo vệ.
4. Locked layout không bị solver ghi đè; issue chỉ đúng segment và gợi ý cách sửa.
5. `git diff --check`; review diff đúng Paths. Chạy quality gates theo SYSTEM-RULES và PLAN trước commit; explicit staging, tuân thủ PM/owner authorization.

## Acceptance / handoff

- [ ] Các bước trên có evidence thực, test commands và kết quả ghi vào card.
- [ ] Error/race/compatibility cases liên quan được kiểm tra, không chỉ happy path.
- [ ] Không ghi “done/pass” cho test hoặc owner gate chưa chạy.
- [ ] PM/owner nhận kết quả theo AR-06; ghi technical verification và owner acceptance riêng.

## Progress

- 2026-10-16: planned; shipping code chưa sửa, tests triển khai chưa chạy.
