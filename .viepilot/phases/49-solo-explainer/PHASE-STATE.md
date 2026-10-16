# PHASE-STATE — Phase 49: Solo Explainer và bộ presenter chính diện

- **Status:** in_progress;49.1–49.2 verified,49.3 front21 UI active.
- **Planned at:** 2026-10-16, Asia/Bangkok.
- **Tasks:** 2/10 verified, 1 in progress, 7 planned.
- **Gate V49:** not_started; technical verification và owner acceptance đều chưa có.
- **Dependencies:** Phase 48 / Gate V48; schema → front assets và script → explainer plan → layout → preview → render → integrations → demo.
- **Release:** current 1.4.0-rc.1; target 1.5.0 planned, chưa build.
- **Source:** [SPEC](SPEC.md), [PLAN](PLAN.md), [master PLAN](../../PLAN.md).

| Task | Nội dung | Status |
|---|---|---|
| [49.1](tasks/task-49.1.md) | Mode Solo, schema nền và migration an toàn | implemented_verified |
| [49.2](tasks/task-49.2.md) | Front21 registry, prompt và version manifest | implemented_verified |
| [49.3](tasks/task-49.3.md) | Nhập, duyệt và quản lý bộ front trong UI | in_progress |
| [49.4](tasks/task-49.4.md) | Kịch bản độc thoại Why / How / List theo CEFR | planned |
| [49.5](tasks/task-49.5.md) | Explainer plan: đoạn, minh họa, locks và approval | planned |
| [49.6](tasks/task-49.6.md) | Bố cục hai tỷ lệ, vùng quan trọng và đường motion | planned |
| [49.7](tasks/task-49.7.md) | Player preview và editor duyệt bố cục trong Step 5 | planned |
| [49.8](tasks/task-49.8.md) | Render production, cử chỉ và motion theo approved plan | planned |
| [49.9](tasks/task-49.9.md) | Shorts, thumbnail, series/copy và export cho Solo | planned |
| [49.10](tasks/task-49.10.md) | Gate V49: demo thật, hồi quy, đóng gói và bàn giao | planned |

## Planning verification

SPEC/PLAN đã được viết từ yêu cầu owner và code inventory. Validation tài liệu ghi ở master handoff; không dùng planning validation để đánh dấu implementation pass.

## Owner inputs

Owner đã chọn **Hoang — “Why do we build habits?”** ngày16/10/2026. Dùng profile Hoang hiện có làm identity/outfit reference, cấu trúc Why. Bộ21 ảnh front sẽ do owner tạo bằng AI ngoài rồi nhập/duyệt; vẫn cần trước GateV49. Fixture dùng để kiểm tra logic trước, không thay nghiệm thu hình thật.

Bản chuẩn bị prompt21 và ảnh tham chiếu đã được gửi owner tại `data/tmp/evolve-20261016/hoang-front21/`. Đọc từ bản sao DB đã kiểm chứng, không sửa profile/assets thật. Neutral front vẫn chờ owner tạo/duyệt; backend front import/review đã verified; UI tab đang49.3, real art chưa nhập/duyệt.

Phase 47 vẫn chờ visual review. Gate B-25/B-26/B-27/B-28 giữ pending.
