# PLAN — Phase 48: Giọng nói riêng cho nhân vật

- Status: **executing**, ngày2026-10-16;48.1–48.3 implemented_verified,48.4 in_progress. Owner accepted four listening examples and wants about20 choices; technical/UI/E2E still pending.
- Đọc [SPEC](SPEC.md) và [PLAN tổng](../../PLAN.md) trước thực thi.
- Độ lớn: L. Không cam kết deadline trước khi có input/owner review.

## Thứ tự và dependency

| Task | Depends on | Scope chi tiết |
|---|---|---|
| 48.1 | SPEC/PLAN hiện tại | [Catalog giọng Edge TTS và nghe thử độc lập](tasks/task-48.1.md) |
| 48.2 | 48.1 | [Lưu giọng theo profile và speaker project](tasks/task-48.2.md) |
| 48.3 | 48.2 | [Fingerprint TTS, invalidation và bảo vệ media tốt cũ](tasks/task-48.3.md) |
| 48.4 | 48.1, 48.2, 48.3 | [Voice picker trong hồ sơ nhân vật và Audio Studio](tasks/task-48.4.md) |
| 48.5 | 48.4 | [Gate V48: giọng thật, hồi quy và hướng dẫn](tasks/task-48.5.md) |

## Điều kiện bắt đầu

Không cần migration hoặc owner gate cũ đóng để bắt đầu. Không thay trạng thái Phase 47; V48 mới chờ nghe thật.
Mỗi card có repo-relative Paths và file-level plan. Scope mở rộng phải ghi vào card trước code. Không tự giao agent; mặc định thực hiện tuần tự.

## Cách kiểm tra

- Task 48.1: catalog/cache/provider failures + isolated audition.
- Task 48.2: profile/project persistence, apply semantics và optimistic revision.
- Task 48.3: voice fingerprint, targeted stale, atomic publication, word timings.
- Task 48.4: browser thao tác thật, save/reload, request races và dirty state.
- Task 48.5: full regression theo rules, audio thật hai voice, owner Gate V48.

Chạy tests tập trung trong từng task; quality gates đầy đủ theo SYSTEM-RULES trước commit/release. Chưa có test triển khai nào được chạy trong lượt chỉ lập kế hoạch.

## Evidence và handoff

- Báo cáo dự kiến: `docs/operations/phase48-character-voices.md`.
- Artifact tạm dự kiến: `data/tmp/phase48-voices/`.
- Card/PHASE-STATE cập nhật kết quả thật; technical verification không thay owner acceptance.
- Không tự đè EXE đang dùng, thay MP4/audio dự án thật hoặc phát hành chỉ để chứng minh task.
- Gate V48 chưa chạy. Bản đang phát hành giữ1.4.0-rc.1, target 1.5.0 là kế hoạch.
