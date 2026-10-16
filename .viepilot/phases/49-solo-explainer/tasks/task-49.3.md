# Task 49.3 — Nhập, duyệt và quản lý bộ front trong UI

- **Status:** planned · 2026-10-16.
- **Dependencies:** 49.2
- **Requirements:** R02, R08, R09.
- **Contract:** [SPEC tổng](../../../SPEC.md), [PLAN tổng](../../../PLAN.md), [phase SPEC](../SPEC.md), [phase PLAN](../PLAN.md).
- **Scope:** card này là kế hoạch, chưa có kết quả triển khai hay acceptance.

## Objective

Nhập, duyệt và quản lý bộ front trong UI. Hoàn thành contract tương ứng trong SPEC, giữ khả năng dùng project classic và dữ liệu đã xuất.

## Paths

- backend/api/profiles.py
- backend/library/character_asset_service.py
- backend/library/sprite_upload.py
- frontend/pages/characters.html
- frontend/static/js/character_profiles.js
- frontend/static/js/character_selector.js
- frontend/static/js/api.js
- frontend/static/css/style.css
- tests/test_character_profiles_browser.py
- tests/test_presenter_assets_api.py
- tests/test_presenter_assets_browser.py
- .viepilot/phases/49-solo-explainer/PHASE-STATE.md
- .viepilot/TRACKER.md
- .viepilot/ROADMAP.md
- .viepilot/HANDOFF.json
- CHANGELOG.md
- .viepilot/phases/49-solo-explainer/tasks/task-49.3.md

## File-Level Plan / allowed_files

1. Thêm tab Đối thoại/Thuyết trình, 21 slot cards, copy prompt/download reference, import đơn/batch theo manifest, review/approve và tiến độ 21/21.
2. Reuse MIME/size/green key/alpha pipeline hiện có; align với front base, kiểm tra tay/chân/crop. Owner duyệt độ nhất quán nhận diện/trang phục.
3. Readiness trả thiếu slot, ảnh pending và sai version chính xác; không dùng native lấp slot thiếu. Front pack dùng lại giữa các tập.
4. Batch import validate từng file, báo thành công/thất bại riêng; double-submit lock, request race guards, trailing save và dirty navigation.
5. Selector Solo cho biết front pack sẵn sàng; chưa đủ ảnh vẫn được viết script.

**File mới dự kiến:** `tests/test_presenter_assets_api.py`, `tests/test_presenter_assets_browser.py`.

Chỉ sửa các Paths trên và cập nhật tiến độ card/phase. Nếu phát hiện cần file khác, ghi lý do và mở rộng bounded scope trước code. Các file đã tạo bởi task trước trong Paths được tiếp tục sử dụng; không tự viết lại hệ thống lân cận.

## Risks / guardrails

Pixel checks không chứng minh được cùng khuôn mặt/trang phục; owner review là gate chất lượng ảnh.

Dùng constants/path helpers hiện có, service layer async, validation API + semantic. Không giữ shared DB lock trong network/render/copy nặng. Không sửa dữ liệu production khi có thể dùng sandbox. Không thay đổi gate cũ hoặc phát hành chỉ vì task kỹ thuật chạy qua.

## Verification / expected results

1. Import 21 fixtures đúng → approve → ready. Thiếu miệng/blink, pending hoặc sai identity version → not ready.
2. Ảnh green key/transparent được align với front neutral; native asset hashes không đổi.
3. Browser prompt → reference → import → review → reload; batch partial failure hiển thị đúng.
4. Ghi rõ fixture chỉ kiểm tra logic; pack thật của owner mới dùng cho visual Gate V49.
5. `git diff --check`; review diff đúng Paths. Chạy quality gates theo SYSTEM-RULES và PLAN trước commit; explicit staging, tuân thủ PM/owner authorization.

## Acceptance / handoff

- [ ] Các bước trên có evidence thực, test commands và kết quả ghi vào card.
- [ ] Error/race/compatibility cases liên quan được kiểm tra, không chỉ happy path.
- [ ] Không ghi “done/pass” cho test hoặc owner gate chưa chạy.
- [ ] PM/owner nhận kết quả theo AR-06; ghi technical verification và owner acceptance riêng.

## Progress

- 2026-10-16: planned; shipping code chưa sửa, tests triển khai chưa chạy.
