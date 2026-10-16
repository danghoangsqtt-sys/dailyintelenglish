# Task 49.9 — Shorts, thumbnail, series/copy và export cho Solo

- **Status:** planned · 2026-10-16.
- **Dependencies:** 49.8
- **Requirements:** R11, R12, R13.
- **Contract:** [SPEC tổng](../../../SPEC.md), [PLAN tổng](../../../PLAN.md), [phase SPEC](../SPEC.md), [phase PLAN](../PLAN.md).
- **Scope:** card này là kế hoạch, chưa có kết quả triển khai hay acceptance.

## Objective

Shorts, thumbnail, series/copy và export cho Solo. Hoàn thành contract tương ứng trong SPEC, giữ khả năng dùng project classic và dữ liệu đã xuất.

## Paths

- backend/content/shorts_service.py
- backend/content/export_service.py
- backend/content/youtube_service.py
- backend/content/project_service.py
- backend/channel/channel_service.py
- backend/media/thumbnail_service.py
- backend/schemas/channel.py
- backend/api/channel.py
- frontend/static/js/channel.js
- frontend/static/js/step5_shorts.js
- frontend/static/js/step6_thumbnail.js
- tests/test_phase41_export.py
- tests/test_thumbnail_character_slots.py
- tests/test_youtube_export_api.py
- tests/test_channel_api.py
- tests/test_explainer_integrations.py
- .viepilot/phases/49-solo-explainer/PHASE-STATE.md
- .viepilot/TRACKER.md
- .viepilot/ROADMAP.md
- .viepilot/HANDOFF.json
- CHANGELOG.md
- .viepilot/phases/49-solo-explainer/tasks/task-49.9.md

## File-Level Plan / allowed_files

1. Carry mode/structure/voice IDs/front pack refs qua copy và series episode creation; project mới có approval draft và fingerprint riêng.
2. Shorts retime token anchors, clamp segments theo window, validate bố cục9:16, presenter/hook vẫn trong safe area.
3. Thumbnail Solo có một front presenter và topic/illustration; không ép layout hai người. Giữ compositor9:16 safe area.
4. Export chứa mode/revision metadata và assets theo convention hiện có; giữ series/Episode folder tách biệt, title không chia Ep.2.
5. YouTube copy phản ánh độc thoại kiến thức, không giới thiệu hai người không tồn tại. Không tự upload/publish.

**File mới dự kiến:** `tests/test_explainer_integrations.py`.

Chỉ sửa các Paths trên và cập nhật tiến độ card/phase. Nếu phát hiện cần file khác, ghi lý do và mở rộng bounded scope trước code. Các file đã tạo bởi task trước trong Paths được tiếp tục sử dụng; không tự viết lại hệ thống lân cận.

## Risks / guardrails

Full portrait và Short có cửa sổ thời gian/hook khác nhau; phải test retiming riêng. Không copy nguyên approval giữa project IDs.

Dùng constants/path helpers hiện có, service layer async, validation API + semantic. Không giữ shared DB lock trong network/render/copy nặng. Không sửa dữ liệu production khi có thể dùng sandbox. Không thay đổi gate cũ hoặc phát hành chỉ vì task kỹ thuật chạy qua.

## Verification / expected results

1. Series/copy round-trip mode/voices/front pins, approval draft; channel classic không đổi.
2. Short cắt giữa segment/word có anchors hợp lệ, không âm thời gian/nhân đôi audio; presenter/caption fit9:16.
3. Solo/classic thumbnail và export tests; hai Episode liên tiếp xuất hai folder, không ghi đè.
4. Export copy ngoài DB lock còn hoạt động; lỗi giữ package tốt cũ.
5. `git diff --check`; review diff đúng Paths. Chạy quality gates theo SYSTEM-RULES và PLAN trước commit; explicit staging, tuân thủ PM/owner authorization.

## Acceptance / handoff

- [ ] Các bước trên có evidence thực, test commands và kết quả ghi vào card.
- [ ] Error/race/compatibility cases liên quan được kiểm tra, không chỉ happy path.
- [ ] Không ghi “done/pass” cho test hoặc owner gate chưa chạy.
- [ ] PM/owner nhận kết quả theo AR-06; ghi technical verification và owner acceptance riêng.

## Progress

- 2026-10-16: planned; shipping code chưa sửa, tests triển khai chưa chạy.
