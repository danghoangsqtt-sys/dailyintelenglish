# Task 49.2 — Front21 registry, prompt và version manifest

- **Status:** implemented_verified · 2026-10-16; front backend verified, real-art owner gate pending.
- **Dependencies:** 49.1
- **Requirements:** R02, R08, R09, R12.
- **Contract:** [SPEC tổng](../../../SPEC.md), [PLAN tổng](../../../PLAN.md), [phase SPEC](../SPEC.md), [phase PLAN](../PLAN.md).
- **Scope:** front21 backend technically verified; UI import tab follows 49.3. Synthetic fixtures do not replace real owner art acceptance.

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
- .viepilot/phases/49-solo-explainer/tasks/task-49.3.md
- .viepilot/phases/49-solo-explainer/PLAN.md
- .viepilot/phases/49-solo-explainer/SPEC.md
- .viepilot/PLAN.md
- .viepilot/SPEC.md
- tests/test_music_upload_multi_browser.py

## File-Level Plan / allowed_files

1. Định nghĩa đúng 21 front slots theo SPEC: 10 cặp miệng + blink. Registry, readiness và filename mapping có view native/front; mặc định giữ native 29.
2. Prompt chính diện, đứng nhìn camera, giữ nhận diện/trang phục profile; hướng chỉ theo màn hình. Reference graph theo base-first, không có vòng lặp.
3. Duyệt neutral front trước khi tạo prompt 9 pose đóng; ảnh mở dùng ảnh đóng tương ứng, blink dùng neutral. App tạo prompt/reference, không gọi local AI tạo presenter.
4. API slots/input/review có view param; manifest pin identity_version, pack_revision và asset IDs. Path có version, không đè native sprite_dir.
5. Thay front base làm các ảnh front phụ thuộc cần review lại. Giữ asset revisions cần cho kế hoạch/job cũ để import ảnh mới không đổi kết quả đang render.

**File mới dự kiến:** `backend/library/presenter_asset_plan.py`, `tests/test_presenter_asset_plan.py`.

### Execution refinement (isolated candidate preparation only, before dependencies finish)

- Keep native 29 constants, processing, materialization and readiness unchanged. A separate presenter_asset_plan module owns front21 prompts, immutable per-asset storage, dependency review and versioned manifests. Add optional Literal native/front view to existing slot/input/upload/batch/review/approve/prompt routes; native remains default and cross-view review is rejected.
- Front base is full-body standing and keeps head/hands/feet inside canvas. Existing native prepare_base cuts full-length images at mid-thigh, so add a front-only base preparation helper without that crop; compare front edits only against the approved front base. Screen-left/right prompts explicitly name the viewer's screen direction, never gender mirroring.
- Store front files by full asset UUID, never move or overwrite an older approved file. Validation metadata pins front base/parent IDs; approving a replacement base invalidates front descendants only, replacement gesture invalidates its mouth descendant. Re-review requires a current approved reference chain; stale images made from another base must be imported again.
- Front manifests pin profile/identity, all 21 asset IDs and content hashes, addressed by revision hash. Old manifests remain resolvable after imports. Native sprite_dir is never rewritten by front imports. Add front readiness separately to profile response; front pending never lowers native readiness.
- Owner chose **Hoang — Why do we build habits?** for final demo. Prepare front prompts using that existing identity/outfit after implementation; no owner DB writes or synthetic-art acceptance.
- Upload uses read snapshot → image staging outside shared lock → guarded write publication (identity/base/parent/current slot CAS), removes unpublished files on conflict. Manifest snapshots release DB lock before immutable JSON write; resolver verifies every file content hash and confined path. Front base rejects visibly clipped source edges before fitting; native crop remains default.
- Full gate again exposed the preexisting music browser fixture race (699 passed; Windows 32 while deleting the previous test's MP3). Bound the correction to test isolation: use a fresh live-server/data directory per test, make browser depend on that server so browser closes first, and remove cross-test file deletion. Keep all 7 behavior assertions and music production code unchanged. Run the 7 tests and full regression again; do not hide errors or add arbitrary cleanup sleeps.

Chỉ sửa các Paths trên và cập nhật tiến độ card/phase. Nếu phát hiện cần file khác, ghi lý do và mở rộng bounded scope trước code. Các file đã tạo bởi task trước trong Paths được tiếp tục sử dụng; không tự viết lại hệ thống lân cận.

## Risks / guardrails

Tên slot có thể trùng giữa hai view; upload/manifest phải chọn view rõ ràng. Không gộp front21 vào assert native 29.

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

- 2026-10-16:49.1 checkpoint e5b2893 persisted/pushed with clean tree/upstream/ahead0; six bounded front21 source/test files applied afterward.
- Front registry 21, full-body prompt/reference graph, optional native/front API views, separate readiness, immutable asset/manifests and reference invalidation implemented. Screen directions are viewer-relative. Native 29/materialization unchanged; cross-view review rejected.
- Isolated candidate **32 passed in 144.55s**, including 21 synthetic asset uploads/review, DAG, legacy native 29, idempotent base approval, targeted gesture/base invalidation, old-manifest resolution after new imports, corruption/traversal rejection and staging lock/CAS cleanup. Native slots/profiles/voice browser regression **28 passed in 74.15s**. Fixed two test-helper Ruff shadowing findings before application.
- Current source focused **12 passed in 126.22s**, including added cropped-source rejection. Ruff/diff clean. Full suite required before checkpoint; not PASS yet. No real owner assets/DB or installed EXE changed.
- Full run stopped 699 passed on the music fixture's previous-case file deletion (same Windows 32 class as 49.1). Fresh per-test server/library and ordered browser teardown retain all 7 behavior checks; focused module **7 passed in 12.45s**. Full retry now running after this bounded test-only isolation fix; no music production behavior changed.

- Final full retry **1740 passed in 710.71s**, one existing Starlette warning. Ruff/diff clean; source snapshot unchanged through this gate. Native 28 regressions and focused 12 front tests passed; old front manifests remain readable after new imports and detect file corruption. Test music isolation 7/7 retained all behavior assertions; no music production changes. Log `data/tmp/evolve-20261016/task49.2-pytest-r2.log`.
- Isolated UI candidate for 49.3 separately reached 25 API/browser passes and was visually inspected, not yet applied/accepted in this task. Real owner front21 still pending; no owner DB/EXE/release change.
