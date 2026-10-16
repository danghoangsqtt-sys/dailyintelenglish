# PLAN — Phase 49: Solo Explainer và bộ presenter chính diện

- Status: **executing49.5**, ngày2026-10-16;4/10 verified, Solo foundation/front21/script technical gates verified; content owner review remains. Owner demo:Hoang — Why do we build habits?.
- Đọc [SPEC](SPEC.md) và [PLAN tổng](../../PLAN.md) trước thực thi.
- Độ lớn: XL. Không cam kết deadline trước khi có input/owner review.

## Thứ tự và dependency

| Task | Depends on | Scope chi tiết |
|---|---|---|
| 49.1 | 48.5 | [Mode Solo, schema nền và migration an toàn](tasks/task-49.1.md) |
| 49.2 | 49.1 | [Front21 registry, prompt và version manifest](tasks/task-49.2.md) |
| 49.3 | 49.2 | [Nhập, duyệt và quản lý bộ front trong UI](tasks/task-49.3.md) |
| 49.4 | 49.1 | [Kịch bản độc thoại Why / How / List theo CEFR](tasks/task-49.4.md) |
| 49.5 | 49.2, 49.4 | [Explainer plan: đoạn, minh họa, locks và approval](tasks/task-49.5.md) |
| 49.6 | 49.5 | [Bố cục hai tỷ lệ, vùng quan trọng và đường motion](tasks/task-49.6.md) |
| 49.7 | 49.3, 49.6 | [Player preview và editor duyệt bố cục trong Step 5](tasks/task-49.7.md) |
| 49.8 | 49.7 | [Render production, cử chỉ và motion theo approved plan](tasks/task-49.8.md) |
| 49.9 | 49.8 | [Shorts, thumbnail, series/copy và export cho Solo](tasks/task-49.9.md) |
| 49.10 | 49.9 | [Gate V49: demo thật, hồi quy, đóng gói và bàn giao](tasks/task-49.10.md) |

## Điều kiện bắt đầu

Phase 48 / Gate V48; schema → front assets và script → explainer plan → layout → preview → render → integrations → demo.
Mỗi card có repo-relative Paths và file-level plan. Scope mở rộng phải ghi vào card trước code. Không tự giao agent; mặc định thực hiện tuần tự.

## Cách kiểm tra

- Task 49.1: new/old DB, fault injection migration, restart hai lần, default classic.
- Task 49.2/49.3: native29/front21, versioned manifests, reference DAG, import/review/browser.
- Task 49.4: script Why/How/List, CEFR/budget, classic prompt/repair.
- Task 49.5/49.6: anchors/tiling/revision/locks/stale; geometry/path constraints cả hai aspect.
- Task 49.7: Player bundle, shared scene, editor/browser, no dev server.
- Task 49.8: production props, deterministic gestures/timeline, Player/final parity, short difficult clips.
- Task 49.9: thumbnail/Shorts/copy/channel/export và series/Episode folder.
- Task 49.10: pack thật + full demo hai aspect + Short, full suite và staged EXE, owner Gate V49.

Chạy tests tập trung trong từng task; quality gates đầy đủ theo SYSTEM-RULES trước commit/release. Chưa có test triển khai nào được chạy trong lượt chỉ lập kế hoạch.

## Evidence và handoff

- Báo cáo dự kiến: `docs/operations/phase49-solo-explainer.md`.
- Artifact tạm dự kiến: `data/tmp/phase49-solo/`.
- Card/PHASE-STATE cập nhật kết quả thật; technical verification không thay owner acceptance.
- Không tự đè EXE đang dùng, thay MP4/audio dự án thật hoặc phát hành chỉ để chứng minh task.
- Gate V49 chưa chạy. Bản đang phát hành giữ1.4.0-rc.1, target 1.5.0 là kế hoạch.
