# Task 49.10 — Gate V49: demo thật, hồi quy, đóng gói và bàn giao

- **Status:** planned · 2026-10-16.
- **Dependencies:** 49.9
- **Requirements:** R01, R02, R03, R04, R05, R06, R07, R08, R09, R10, R11, R12, R13.
- **Contract:** [SPEC tổng](../../../SPEC.md), [PLAN tổng](../../../PLAN.md), [phase SPEC](../SPEC.md), [phase PLAN](../PLAN.md).
- **Scope:** card này là kế hoạch, chưa có kết quả triển khai hay acceptance.

## Objective

Gate V49: demo thật, hồi quy, đóng gói và bàn giao. Hoàn thành contract tương ứng trong SPEC, giữ khả năng dùng project classic và dữ liệu đã xuất.

## Paths

- scripts/build_exe.ps1
- daily_intel_english_studio.spec
- scripts/check_dependencies.py
- README.md
- docs/user/windows-installation.md
- scripts/generate_api_docs.py
- docs/api.md
- renderer/package.json
- docs/user/solo-explainer.md
- docs/operations/phase49-solo-explainer.md
- .viepilot/phases/49-solo-explainer/PHASE-STATE.md
- .viepilot/TRACKER.md
- .viepilot/ROADMAP.md
- .viepilot/HANDOFF.json
- CHANGELOG.md
- .viepilot/phases/49-solo-explainer/tasks/task-49.10.md

## File-Level Plan / allowed_files

1. Thêm preview build có thể lặp lại trước PyInstaller, fail nếu thiếu bundle; frozen resources có widget. Cập nhật hướng dẫn cài source và user guide.
2. Owner chọn topic/profile và chuẩn bị pack thật21/21; dựng một tập có ảnh, sơ đồ, thẻ chữ, nhiều vị trí/size/gesture và manual locks.
3. Render đầy đủ16:9,9:16 và một Short trong staging; probe/decode/xem các đoạn khó, kiểm tra voice IDs, A/V và caption/safe area.
4. Đo elapsed/props/frame count/hardware cùng baseline, ghi giới hạn performance và2D motion; không suy diễn phần trăm chưa đo.
5. Full quality gates và EXE trial mở từ icon logo; Player/media chạy không cần dev server. Chưa ghi đè EXE owner hay publish nếu chưa có lệnh phát hành.
6. Evidence gồm commands/logs/results/limits, tách technical và owner acceptance. Target1.5.0 chỉ thành candidate khi triển khai/duyệt; bản hiện tại vẫn1.4.0-rc.1.

**File mới dự kiến:** `docs/user/solo-explainer.md`, `docs/operations/phase49-solo-explainer.md`.

Chỉ sửa các Paths trên và cập nhật tiến độ card/phase. Nếu phát hiện cần file khác, ghi lý do và mở rộng bounded scope trước code. Các file đã tạo bởi task trước trong Paths được tiếp tục sử dụng; không tự viết lại hệ thống lân cận.

## Risks / guardrails

Ảnh thật và owner review là đầu vào bên ngoài cho nghiệm thu; fixtures cho phép làm code trước, không cho phép claim feature/release accepted.

Dùng constants/path helpers hiện có, service layer async, validation API + semantic. Không giữ shared DB lock trong network/render/copy nặng. Không sửa dữ liệu production khi có thể dùng sandbox. Không thay đổi gate cũ hoặc phát hành chỉ vì task kỹ thuật chạy qua.

## Verification / expected results

1. Full pytest/Ruff, renderer Vitest/typecheck, JS syntax/browser regression; migration failure/restart, native29 và caption Phase 47 còn đúng.
2. Pack21 ảnh thật approved, presenter mọi spoken frame, đủ ba visual types rõ; manual edits giữ sau reload và được render dùng.
3. A/V drift và duration lệch tối đa0.10s theo SPEC, decode đầy đủ, safe area cả hai aspect/Short; concurrent edits không publish stale output.
4. EXE trial trong folder mới mở từ branded icon, Player bundle/audio URL hoạt động; network errors rõ.
5. Owner V49 visual/content sign-off explicit. B-25/B-26/B-27/B-28 và Phase 47 review ghi riêng, không tự đóng.
6. `git diff --check`; review diff đúng Paths. Chạy quality gates theo SYSTEM-RULES và PLAN trước commit; explicit staging, tuân thủ PM/owner authorization.

## Acceptance / handoff

- [ ] Các bước trên có evidence thực, test commands và kết quả ghi vào card.
- [ ] Error/race/compatibility cases liên quan được kiểm tra, không chỉ happy path.
- [ ] Không ghi “done/pass” cho test hoặc owner gate chưa chạy.
- [ ] PM/owner nhận kết quả theo AR-06; ghi technical verification và owner acceptance riêng.

## Progress

- 2026-10-16: planned; shipping code chưa sửa, tests triển khai chưa chạy.
