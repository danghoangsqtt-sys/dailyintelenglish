# Task 49.2 — Front21 registry, prompt và version manifest

- **Status:** planned · 2026-10-16.
- **Dependencies:** 49.1
- **Requirements:** R02, R08, R09, R12.
- **Contract:** [SPEC tổng](../../../SPEC.md), [PLAN tổng](../../../PLAN.md), [phase SPEC](../SPEC.md), [phase PLAN](../PLAN.md).
- **Scope:** card này là kế hoạch, chưa có kết quả triển khai hay acceptance.

## Objective

Front21 registry, prompt và version manifest. Hoàn thành contract tương ứng trong SPEC, giữ khả năng dùng project classic và dữ liệu đã xuất.

## Paths

- backend/library/character_asset_service.py
- backend/library/sprite_service.py
- backend/library/character_profile_service.py
- backend/library/sprite_upload.py
- backend/schemas/visuals.py
- backend/api/profiles.py
- tests/test_sprite_service.py
- tests/test_character_profiles_api.py
- backend/library/presenter_asset_plan.py
- tests/test_presenter_asset_plan.py
- .viepilot/phases/49-solo-explainer/PHASE-STATE.md
- .viepilot/TRACKER.md
- .viepilot/ROADMAP.md
- .viepilot/HANDOFF.json
- CHANGELOG.md
- .viepilot/phases/49-solo-explainer/tasks/task-49.2.md

## File-Level Plan / allowed_files

1. Định nghĩa đúng 21 front slots theo SPEC: 10 cặp miệng + blink. Registry, readiness và filename mapping có view native/front; mặc định giữ native 29.
2. Prompt chính diện, đứng nhìn camera, giữ nhận diện/trang phục profile; hướng chỉ theo màn hình. Reference graph theo base-first, không có vòng lặp.
3. Duyệt neutral front trước khi tạo prompt 9 pose đóng; ảnh mở dùng ảnh đóng tương ứng, blink dùng neutral. App tạo prompt/reference, không gọi local AI tạo presenter.
4. API slots/input/review có view param; manifest pin identity_version, pack_revision và asset IDs. Path có version, không đè native sprite_dir.
5. Thay front base làm các ảnh front phụ thuộc cần review lại. Giữ asset revisions cần cho kế hoạch/job cũ để import ảnh mới không đổi kết quả đang render.

**File mới dự kiến:** `backend/library/presenter_asset_plan.py`, `tests/test_presenter_asset_plan.py`.

### Execution refinement (isolated candidate preparation only, before dependencies finish)

- Keep native29 constants, processing, materialization and readiness unchanged. A separate presenter_asset_plan module owns front21 prompts, immutable per-asset storage, dependency review and versioned manifests. Add optional Literal native/front view to existing slot/input/upload/batch/review/approve/prompt routes; native remains default and cross-view review is rejected.
- Front base is full-body standing and keeps head/hands/feet inside canvas. Existing native prepare_base cuts full-length images at mid-thigh, so add a front-only base preparation helper without that crop; compare front edits only against the approved front base. Screen-left/right prompts explicitly name the viewer's screen direction, never gender mirroring.
- Store front files by full asset UUID, never move or overwrite an older approved file. Validation metadata pins front base/parent IDs; approving a replacement base invalidates front descendants only, replacement gesture invalidates its mouth descendant. Re-review requires a current approved reference chain; stale images made from another base must be imported again.
- Front manifests pin profile/identity, all21 asset IDs and content hashes, addressed by revision hash. Old manifests remain resolvable after imports. Native sprite_dir is never rewritten by front imports. Add front readiness separately to profile response; front pending never lowers native readiness.
- Owner chose **Hoang — Why do we build habits?** for final demo. Prepare front prompts using that existing identity/outfit after implementation; no owner DB writes or synthetic-art acceptance.

Chỉ sửa các Paths trên và cập nhật tiến độ card/phase. Nếu phát hiện cần file khác, ghi lý do và mở rộng bounded scope trước code. Các file đã tạo bởi task trước trong Paths được tiếp tục sử dụng; không tự viết lại hệ thống lân cận.

## Risks / guardrails

Tên slot có thể trùng giữa hai view; upload/manifest phải chọn view rõ ràng. Không gộp front21 vào assert native29.

Dùng constants/path helpers hiện có, service layer async, validation API + semantic. Không giữ shared DB lock trong network/render/copy nặng. Không sửa dữ liệu production khi có thể dùng sandbox. Không thay đổi gate cũ hoặc phát hành chỉ vì task kỹ thuật chạy qua.

## Verification / expected results

1. 21 key duy nhất, 10 cặp + blink; mọi parent reference tồn tại và DAG hợp lệ; hướng chỉ theo màn hình.
2. Native registry 29, readiness, load_set và API default không đổi.
3. Profile có hai view; front pending không làm native unready. Thay base chỉ invalidates front descendants.
4. Old manifest vẫn resolve sau import revision mới; reject view/slot sai và filename/path traversal.
5. `git diff --check`; review diff đúng Paths. Chạy quality gates theo SYSTEM-RULES và PLAN trước commit; explicit staging, tuân thủ PM/owner authorization.

## Acceptance / handoff

- [ ] Các bước trên có evidence thực, test commands và kết quả ghi vào card.
- [ ] Error/race/compatibility cases liên quan được kiểm tra, không chỉ happy path.
- [ ] Không ghi “done/pass” cho test hoặc owner gate chưa chạy.
- [ ] PM/owner nhận kết quả theo AR-06; ghi technical verification và owner acceptance riêng.

## Progress

- 2026-10-16: planned; shipping code chưa sửa, tests triển khai chưa chạy.
