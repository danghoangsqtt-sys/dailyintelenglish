# Task 49.1 — Mode Solo, schema nền và migration an toàn

- **Status:** implemented_verified · 2026-10-16; foundation only, V49 visual/render gate remains pending.
- **Dependencies:** 48.5
- **Requirements:** R01, R11, R12.
- **Contract:** [SPEC tổng](../../../SPEC.md), [PLAN tổng](../../../PLAN.md), [phase SPEC](../SPEC.md), [phase PLAN](../PLAN.md).
- **Scope:** mode/schema/migration foundation implemented and technically verified. Solo script/render/editor arrive in later tasks, no feature-complete or release claim.

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
- tests/test_explainer_config_browser.py
- backend/library/project_visuals_service.py
- frontend/static/js/character_selector.js
- backend/core/voice.py
- .viepilot/phases/49-solo-explainer/PHASE-STATE.md
- .viepilot/TRACKER.md
- .viepilot/ROADMAP.md
- .viepilot/HANDOFF.json
- CHANGELOG.md
- .viepilot/phases/49-solo-explainer/tasks/task-49.1.md
- .viepilot/phases/49-solo-explainer/tasks/task-49.2.md
- .viepilot/phases/49-solo-explainer/PLAN.md
- .viepilot/phases/49-solo-explainer/SPEC.md
- .viepilot/PLAN.md
- .viepilot/SPEC.md

## File-Level Plan / allowed_files

1. Thêm presentation_mode classic/solo_explainer, explainer_structure why/how/list ở create/get/update; defaultclassic cho mọi project cũ, kể cả num_speakers1.
2. Solo validation đúng một speaker/cast, Step 1 khóa số người và giữ CEFR/thời lượng/accent controls. Cho viết script trước khi đủ front assets.
3. Định nghĩa Pydantic contract plan/revision/segments/token anchors/visuals/layout/locks theo SPEC, giới hạn payload và không nhận code tùy ý.
4. Migration dự kiến 027 thêm mode/structure và project_explainer_plans current+history/snapshot, FK project. Kiểm tra số migration mới nhất ngay trước code.
5. Kiểm tra runner rollback + schema_migrations tracking trên lỗi giữa file; sửa transactional handling bounded tại database.py trước multi-ALTER, hoặc tách migration thành số kế tiếp và cập nhật card/docs.
6. Backup/restore và chạy trên DB mới + bản sao cũ trước khi áp thật; không chạy migration vào instance đang render.

**File mới dự kiến:** `backend/db/migrations/027_solo_explainer.sql`, `backend/schemas/explainer.py`, `tests/test_explainer_migration.py`, `tests/test_explainer_project.py`.

### Execution refinement (planning while Phase 48 gate runs; no shipping Solo edits yet)

- Inventory confirms 026 is latest.027 adds explicit mode/structure and current/history plan tables with FK/checks. Migration runner must execute complete SQL statements within a per-file transaction, incorporating schema_migrations insertion in the same commit; avoid executescript's implicit commit. Normalize legacy 018's BEGIN/COMMIT wrappers under runner ownership. Historical pre 027 duplicate ADD COLUMN can be skipped statement-by-statement only after verifying the named column exists, so remaining statements still run; 027+ is strict. Test middle-file failure rollback, restart twice and an old partially applied migration.
- `schemas/explainer.py` defines strict bounded photo/diagram/text-card payloads, token anchors, stable segment IDs, normalized rectangles/layout, locks, presenter asset/version references and plan status/revision. Code/HTML payloads and unexpected keys are rejected; source/timing validation requiring DB context belongs to 49.5.
- Project service persists mode/structure in INSERT/get/config snapshots and validates merged updates, rejects two-speaker Solo or mode changes once a script exists. Mode/structure changes invalidate relevant in-flight snapshots. No migration runs against owner DB in this task.
- `core/voice.py` includes presentation mode/structure in the existing media-input revision so a configuration change while a job runs cannot publish work for an old mode. Mode/structure edits after a script exists are rejected under the same Step 1 read-only policy, rather than silently converting an existing episode.
- Step 1 exposes mode/Why/How/List, forces one speaker for Solo and preserves classic controls. New Solo profiles may be selected/cast once basic identity/voice are configured, before front assets exist; actual front readiness is enforced before render in later tasks. Add an optional Solo eligibility parameter to CharacterSelector and scoped set_cast validation; classic video readiness unchanged.
- New isolated config browser tests cover mode toggle, count lock, save/reload and classic defaults. Migration tests include a SQLite online-backup copy of the current DB using read-only source access; compare legacy rows/FKs and schema restart without writing owner source.

Chỉ sửa các Paths trên và cập nhật tiến độ card/phase. Nếu phát hiện cần file khác, ghi lý do và mở rộng bounded scope trước code. Các file đã tạo bởi task trước trong Paths được tiếp tục sử dụng; không tự viết lại hệ thống lân cận.

## Risks / guardrails

Runner cũ có duplicate-column fallback theo file; migration phải chứng minh atomicity/resume, không dựa vào việc lỗi giả định hiếm gặp.

Dùng constants/path helpers hiện có, service layer async, validation API + semantic. Không giữ shared DB lock trong network/render/copy nặng. Không sửa dữ liệu production khi có thể dùng sandbox. Không thay đổi gate cũ hoặc phát hành chỉ vì task kỹ thuật chạy qua.

## Verification / expected results

1. Migration new DB + legacy DB, rowcounts/FK, app restart 2lần, defaultclassic và old APIs không đổi.
2. Fault injection giữa ALTER/CREATE không để partial state bị đánh dấu complete; restart/resume được theo contract đã chọn.
3. Solo reject 2speakers, unsupported mode, malformed diagram/code; round-trip config có structure.
4. Step 1 browser classic vẫn hoạt động; kế hoạch file migration đánh số đúng inventory tại execution.
5. `git diff --check`; review diff đúng Paths. Chạy quality gates theo SYSTEM-RULES và PLAN trước commit; explicit staging, tuân thủ PM/owner authorization.

## Acceptance / handoff

- [ ] Các bước trên có evidence thực, test commands và kết quả ghi vào card.
- [ ] Error/race/compatibility cases liên quan được kiểm tra, không chỉ happy path.
- [ ] Không ghi “done/pass” cho test hoặc owner gate chưa chạy.
- [ ] PM/owner nhận kết quả theo AR-06; ghi technical verification và owner acceptance riêng.

## Progress

- 2026-10-16: V48 durable checkpoint 881ffce pushed with clean tree/upstream/ahead0; task 49.1 plan/state/tag opened before 13 bounded source/test files applied.
- Strict plan contracts, explicit mode/Why/How/List, one-presenter config/cast, merged update validation and read-only-after-script policy implemented. Profile/voice can be cast without front art for Solo; classic readiness unchanged. Mode/structure included in media revision.
- Migration 027 adds explicit defaults and current/history plan tables. Per-file transaction includes schema_migrations; historical 018 wrappers normalized; verified pre 027 duplicate-column skips only its individual statement, 027+ strict. Rollback/restart/partial legacy/trigger-semicolon tests pass.
- Isolated candidate **70 passed** after correcting a Pydantic discriminator-validator incompatibility and closing the character chooser in the browser test; current shipping-source focused suite **70 passed in 16.21s**, final Step 1 browser modules **10 passed in 11.22s** after matching existing section/field styling. Ruff, both JS syntax and diff checks clean. Full workspace regression running; no task PASS yet.
- Read-only online-backup copy verification: 13 projects/25 speakers/290 script lines and every original table/column unchanged, all old projects defaultclassic, FK/integrity pass, 2 restarts and backup restore verified. Evidence `data/tmp/evolve-20261016/drafts/solo-db-copy-0d6a95d18e87411384487c8f8fad3b4c/verification.json`. Source owner DB never opened for writes.
- Owner chose Hoang — Why do we build habits?; preparatory front21 prompts/reference sent, real 21-image pack and V49 still pending. Front registry, script, layout/editor and production rendering are later tasks.
- Actual isolated source UI inspected at 1280px; no JS page errors, mode Solo/Why and one-presenter lock correct. Screenshots/report `data/tmp/evolve-20261016/solo-ui-fbee3fdad0/`. Narrow 390px check exposes existing desktop shell overflow; no mobile-support claim or unrelated shell refactor in this task.
- First full gate stopped at 697 passed because existing `test_music_upload_multi_browser.py` cleanup attempted to unlink `two.mp3` while its background analyser held a Windows handle. The unchanged module passed 7/7 in 7.38s when isolated. Retry the full gate on the same source snapshot; do not mark PASS from a partial run or alter unrelated music behavior merely to get green.

- Final full retry **1728 passed in 581.51s**, one existing Starlette warning. No music source/test changed: existing module's transient Windows file-handle failure 7/7 isolated and full retry passed on the same source. Full log `data/tmp/evolve-20261016/task49.1-pytest-r2.log`. Ruff/both modified JS syntax/diff clean. No owner DB migration, EXE update or new release.
