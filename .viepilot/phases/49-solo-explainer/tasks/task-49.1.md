# Task 49.1 — Mode Solo, schema nền và migration an toàn

- **Status:** planned · 2026-10-16.
- **Dependencies:** 48.5
- **Requirements:** R01, R11, R12.
- **Contract:** [SPEC tổng](../../../SPEC.md), [PLAN tổng](../../../PLAN.md), [phase SPEC](../SPEC.md), [phase PLAN](../PLAN.md).
- **Scope:** card này là kế hoạch, chưa có kết quả triển khai hay acceptance.

## Objective

Mode Solo, schema nền và migration an toàn. Hoàn thành contract tương ứng trong SPEC, giữ khả năng dùng project classic và dữ liệu đã xuất.

## Paths

- backend/db/database.py
- backend/schemas/project.py
- backend/content/project_service.py
- backend/api/projects.py
- backend/core/constants.py
- frontend/pages/step1_config.html
- frontend/static/js/step1_config.js
- frontend/static/js/api.js
- backend/db/migrations/027_solo_explainer.sql
- backend/schemas/explainer.py
- tests/test_explainer_migration.py
- tests/test_explainer_project.py
- .viepilot/phases/49-solo-explainer/PHASE-STATE.md
- .viepilot/TRACKER.md
- .viepilot/ROADMAP.md
- .viepilot/HANDOFF.json
- CHANGELOG.md
- .viepilot/phases/49-solo-explainer/tasks/task-49.1.md

## File-Level Plan / allowed_files

1. Thêm presentation_mode classic/solo_explainer, explainer_structure why/how/list ở create/get/update; defaultclassic cho mọi project cũ, kể cả num_speakers1.
2. Solo validation đúng một speaker/cast, Step 1 khóa số người và giữ CEFR/thời lượng/accent controls. Cho viết script trước khi đủ front assets.
3. Định nghĩa Pydantic contract plan/revision/segments/token anchors/visuals/layout/locks theo SPEC, giới hạn payload và không nhận code tùy ý.
4. Migration dự kiến027 thêm mode/structure và project_explainer_plans current+history/snapshot, FK project. Kiểm tra số migration mới nhất ngay trước code.
5. Kiểm tra runner rollback + schema_migrations tracking trên lỗi giữa file; sửa transactional handling bounded tại database.py trước multi-ALTER, hoặc tách migration thành số kế tiếp và cập nhật card/docs.
6. Backup/restore và chạy trên DB mới + bản sao cũ trước khi áp thật; không chạy migration vào instance đang render.

**File mới dự kiến:** `backend/db/migrations/027_solo_explainer.sql`, `backend/schemas/explainer.py`, `tests/test_explainer_migration.py`, `tests/test_explainer_project.py`.

Chỉ sửa các Paths trên và cập nhật tiến độ card/phase. Nếu phát hiện cần file khác, ghi lý do và mở rộng bounded scope trước code. Các file đã tạo bởi task trước trong Paths được tiếp tục sử dụng; không tự viết lại hệ thống lân cận.

## Risks / guardrails

Runner cũ có duplicate-column fallback theo file; migration phải chứng minh atomicity/resume, không dựa vào việc lỗi giả định hiếm gặp.

Dùng constants/path helpers hiện có, service layer async, validation API + semantic. Không giữ shared DB lock trong network/render/copy nặng. Không sửa dữ liệu production khi có thể dùng sandbox. Không thay đổi gate cũ hoặc phát hành chỉ vì task kỹ thuật chạy qua.

## Verification / expected results

1. Migration new DB + legacy DB, rowcounts/FK, app restart2lần, defaultclassic và old APIs không đổi.
2. Fault injection giữa ALTER/CREATE không để partial state bị đánh dấu complete; restart/resume được theo contract đã chọn.
3. Solo reject2speakers, unsupported mode, malformed diagram/code; round-trip config có structure.
4. Step 1 browser classic vẫn hoạt động; kế hoạch file migration đánh số đúng inventory tại execution.
5. `git diff --check`; review diff đúng Paths. Chạy quality gates theo SYSTEM-RULES và PLAN trước commit; explicit staging, tuân thủ PM/owner authorization.

## Acceptance / handoff

- [ ] Các bước trên có evidence thực, test commands và kết quả ghi vào card.
- [ ] Error/race/compatibility cases liên quan được kiểm tra, không chỉ happy path.
- [ ] Không ghi “done/pass” cho test hoặc owner gate chưa chạy.
- [ ] PM/owner nhận kết quả theo AR-06; ghi technical verification và owner acceptance riêng.

## Progress

- 2026-10-16: planned; shipping code chưa sửa, tests triển khai chưa chạy.
