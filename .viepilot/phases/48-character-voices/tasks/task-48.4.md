# Task 48.4 — Voice picker trong hồ sơ nhân vật và Audio Studio

- **Status:** planned · 2026-10-16.
- **Dependencies:** 48.1, 48.2, 48.3
- **Requirements:** R10, R13.
- **Contract:** [SPEC tổng](../../../SPEC.md), [PLAN tổng](../../../PLAN.md), [phase SPEC](../SPEC.md), [phase PLAN](../PLAN.md).
- **Scope:** card này là kế hoạch, chưa có kết quả triển khai hay acceptance.

## Objective

Voice picker trong hồ sơ nhân vật và Audio Studio. Hoàn thành contract tương ứng trong SPEC, giữ khả năng dùng project classic và dữ liệu đã xuất.

## Paths

- frontend/pages/characters.html
- frontend/pages/step4_tts.html
- frontend/static/js/character_profiles.js
- frontend/static/js/character_selector.js
- frontend/static/js/step4_tts.js
- frontend/static/js/api.js
- frontend/static/css/style.css
- tests/test_character_profiles_browser.py
- tests/test_tts_audio_browser.py
- frontend/static/js/voice_picker.js
- tests/test_voice_picker_browser.py
- .viepilot/phases/48-character-voices/PHASE-STATE.md
- .viepilot/TRACKER.md
- .viepilot/ROADMAP.md
- .viepilot/HANDOFF.json
- CHANGELOG.md
- .viepilot/phases/48-character-voices/tasks/task-48.4.md

## File-Level Plan / allowed_files

1. Picker component vanilla dùng chung: search, locale/gender filters, tên+ID, stale indicator, nghe câu mẫu/câu nhập và save.
2. Profile hiển thị default; Step 4 hiển thị actual project voice và nút áp dụng default profile. Character selector cho biết voice snapshot khi cast.
3. Cảnh báo trùng ID giữa speaker nhưng không cấm. Thông báo rõ đổi giọng sẽ cần tạo lại audio/video phụ thuộc.
4. Disable/double-submit lock khi save/preview, bỏ response cũ bằng request token, stop playback cũ, serialize/trailing save và dirty navigation guards.
5. Xử lý offline/voice unavailable/409 bằng thông báo cụ thể và thao tác retry/reload; không hiển thị saved khi request chưa thành công.

**File mới dự kiến:** `frontend/static/js/voice_picker.js`, `tests/test_voice_picker_browser.py`.

Chỉ sửa các Paths trên và cập nhật tiến độ card/phase. Nếu phát hiện cần file khác, ghi lý do và mở rộng bounded scope trước code. Các file đã tạo bởi task trước trong Paths được tiếp tục sử dụng; không tự viết lại hệ thống lân cận.

## Risks / guardrails

Giao diện summary có thể hiển thị default trong khi project dùng override; luôn label rõ hai cấp và dùng resolved project data.

Dùng constants/path helpers hiện có, service layer async, validation API + semantic. Không giữ shared DB lock trong network/render/copy nặng. Không sửa dữ liệu production khi có thể dùng sandbox. Không thay đổi gate cũ hoặc phát hành chỉ vì task kỹ thuật chạy qua.

## Verification / expected results

1. Browser chọn hai giọng, nghe thử, save/reload profile/project; tên/ID displayed khớp response.
2. Race preview A chậm/B nhanh không phát A, save lỗi/409 không mất edit; keyboard/focus/loading hợp lý.
3. Sửa profile không tự đổi Step 4 project; apply profile có tác dụng và cho thấy stale; duplicate warning dismiss được.
4. Node JS syntax cho file sửa và regression browser characters/Audio Studio.
5. `git diff --check`; review diff đúng Paths. Chạy quality gates theo SYSTEM-RULES và PLAN trước commit; explicit staging, tuân thủ PM/owner authorization.

## Acceptance / handoff

- [ ] Các bước trên có evidence thực, test commands và kết quả ghi vào card.
- [ ] Error/race/compatibility cases liên quan được kiểm tra, không chỉ happy path.
- [ ] Không ghi “done/pass” cho test hoặc owner gate chưa chạy.
- [ ] PM/owner nhận kết quả theo AR-06; ghi technical verification và owner acceptance riêng.

## Progress

- 2026-10-16: planned; shipping code chưa sửa, tests triển khai chưa chạy.
