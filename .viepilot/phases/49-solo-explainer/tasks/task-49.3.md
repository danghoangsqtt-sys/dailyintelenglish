# Task 49.3 — Nhập, duyệt và quản lý bộ front trong UI

- **Status:** implemented_verified · 2026-10-16; source front21 UI verified, real-art V49 remains pending.
- **Dependencies:** 49.2
- **Requirements:** R02, R08, R09.
- **Contract:** [SPEC tổng](../../../SPEC.md), [PLAN tổng](../../../PLAN.md), [phase SPEC](../SPEC.md), [phase PLAN](../PLAN.md).
- **Scope:** front21 profile UI implemented and technically verified. Real front art and Solo script/layout/render remain separate tasks/gates.

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
- .viepilot/phases/49-solo-explainer/tasks/task-49.4.md
- .viepilot/phases/49-solo-explainer/PLAN.md
- .viepilot/phases/49-solo-explainer/SPEC.md
- .viepilot/PLAN.md
- .viepilot/SPEC.md

## File-Level Plan / allowed_files

1. Thêm tab Đối thoại/Thuyết trình, 21 slot cards, copy prompt/download reference, import đơn/batch theo manifest, review/approve và tiến độ 21/21.
2. Reuse MIME/size/green key/alpha pipeline hiện có; align với front base, kiểm tra tay/chân/crop. Owner duyệt độ nhất quán nhận diện/trang phục.
3. Readiness trả thiếu slot, ảnh pending và sai version chính xác; không dùng native lấp slot thiếu. Front pack dùng lại giữa các tập.
4. Batch import validate từng file, báo thành công/thất bại riêng; double-submit lock, request race guards, trailing save và dirty navigation.
5. Selector Solo cho biết front pack sẵn sàng; chưa đủ ảnh vẫn được viết script.

**File mới dự kiến:** `tests/test_presenter_assets_api.py`, `tests/test_presenter_assets_browser.py`.

### Execution refinement (isolated UI preparation during 49.2 regression)

- Add native/front tabs within the current profile, native default. Existing card groups, drops, keyboard/file input, copy prompt and approve actions are reused with an explicit captured view/profile ID. All view-sensitive API helpers remain in api.js; default native URLs unchanged for compatibility.
- Separate approved progress 29/native and 21/front. Front neutral card exposes the existing identity reference when available; instructions require neutral → closed gestures → open mouths/blink with each parent approved first. A fully approved synthetic pack is logic evidence only, never real-face/gesture acceptance.
- Lock asset operations and profile/view switching while upload/review/batch is active, prevent double submits and warn on unload. Clear/disable old slot cards while a new profile/view loads; request tokens must ignore late responses. Preserve same-profile unsaved voice edits across tab/asset refresh; optional details flush to their captured profile IDs.
- Capture operation context before asynchronous work, keep the lock through refreshing its result, revoke local preview object URLs and show each batch result/error without delayed notices writing another profile. Quick-create and profile actions share navigation guards while operations are pending.
- Solo selector shows front progress/readiness and that writing can start without art; classic eligibility unchanged. Add actual browser prompt/reference/import/review/reload/error/race checks plus backend batch/readiness/view checks. No global shell refactor or mobile-support claim.

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

- 2026-10-16:49.2 checkpoint 8d77b82 persisted/pushed and clean/upstream/ahead0 verified; 6 bounded UI/test files applied afterward. Three modified JS syntax/Ruff/diff clean.
- Native/front tabs near profile heading, 29/21 progress, identity download, prompt copy/pack, single/batch upload, parent-first approval, targeted failure/status and Solo selector progress implemented. Front neutral has a wider prompt/reference card; front groups follow neutral→closed gestures→mouths→blink.
- Profile/view/loading locks, captured async context, late response tokens, same-profile voice draft retention, beforeunload pending guard, local preview URL cleanup, create double-submit guard and disabled old fields during profile loading implemented. Native default API URLs unchanged.
- Isolated candidate 25 API/browser passes; initial harness relative download URL corrected, then voice-save wait message kept explicit for existing regression. Current source **26 passed in 27.63s**: 5 API +6 front browser +4 profile +9 voice +2 Solo config cases. Includes native row/file hashes unchanged after front upload, wrong identity/ownership, pending upload/create and late responses. Fixtures certify logic, not actual Hoang image/gesture quality.
- Visual source smoke uses a separate copied Hoang profile/native reference; no owner data writes or real front generation. Reports/screenshots under `data/tmp/evolve-20261016/front-ui-visual-dd96763238/`; source voice catalog in that screenshot explicitly fixture-only. Full regression running before checkpoint; no task PASS yet.

- Final full **1751 passed in 715.41s**, one existing Starlette warning. Ruff/all3 modified JS syntax/diff clean. Source UI visually inspected in isolated copied Hoang profile, no JS errors, identity reference link verified; actual report at `data/tmp/evolve-20261016/front-ui-visual-dd96763238/`. Source profile/voice data and EXE unchanged. Next 49.4, no real front pack or Solo render acceptance claimed.
- Final visual capture explicitly waited for both view controls and local fonts to be ready: `data/tmp/evolve-20261016/front-ui-visual-8f0b37b451/`, zero JS errors, 21 cards and native identity reference confirmed. Earlier images include the brief loading/disabled state.
