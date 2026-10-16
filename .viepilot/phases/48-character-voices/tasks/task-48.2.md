# Task 48.2 — Lưu giọng theo profile và speaker project

- **Status:** implemented_verified · 2026-10-16; technical evidence below, owner phase gate separate.
- **Dependencies:** 48.1
- **Requirements:** R10, R12, R13.
- **Contract:** [SPEC tổng](../../../SPEC.md), [PLAN tổng](../../../PLAN.md), [phase SPEC](../SPEC.md), [phase PLAN](../PLAN.md).
- **Scope:** persistence implemented and technically verified; Phase48 UI/E2E gate remains pending.

## Objective

Lưu giọng theo profile và speaker project. Hoàn thành contract tương ứng trong SPEC, giữ khả năng dùng project classic và dữ liệu đã xuất.

## Paths

- backend/schemas/project.py
- backend/schemas/visuals.py
- backend/library/character_profile_service.py
- backend/library/project_visuals_service.py
- backend/content/project_service.py
- backend/api/projects.py
- backend/api/profiles.py
- tests/test_character_profiles_api.py
- tests/test_phase40_character_names.py
- tests/test_character_voice_selection.py
- backend/core/voice.py
- tests/conftest.py
- tests/test_channel_api.py
- backend/channel/channel_service.py
- frontend/static/js/step1_config.js
- tests/test_step1_config_edit_browser.py
- tests/test_video_visual_modes_browser.py
- .viepilot/phases/48-character-voices/PHASE-STATE.md
- .viepilot/TRACKER.md
- .viepilot/ROADMAP.md
- .viepilot/HANDOFF.json
- CHANGELOG.md
- .viepilot/phases/48-character-voices/tasks/task-48.2.md

## File-Level Plan / allowed_files

1. Thêm optional voice_id vào SpeakerConfig/SpeakerUpdate, sửa INSERT _replace_speakers và get/update/copy round-trip. Update speaker có script tại chỗ, giữ speaker/line IDs.
2. Profile lưu default_voice_id được validate catalog; không reset explicit selection vô tình khi đổi accent/gender. Legacy unset voice vẫn default map.
3. Giữ nguyên snapshot giọng của project đã cast khi sửa profile. apply_profile_voice là thao tác rõ ràng; giữ project speed/pitch/volume.
4. Computed voice_revision từ fields giọng hiện hành; endpoint PATCH mang expected revision, validate provider ngoài write lock rồi recheck revision trong transaction, 409 khi stale.
5. Áp dụng validation hai tầng, trả resolved voice metadata cho UI; không tạo migration thừa vì voice columns đã tồn tại.

**File mới dự kiến:** `tests/test_character_voice_selection.py`.

### Execution refinement (2026-10-16, before code)

- Add pure `backend/core/voice.py`: resolve concrete/default voice and compute effective voice revisions without provider or DB I/O. Reuse from profile/project/TTS to avoid divergent rules.
- `schemas/project.py`, `schemas/visuals.py`: typed voice ID and expected revision, explicit apply-profile action; metadata fields must never become SQL column names.
- `project_service.py`: voice_id in INSERT/config snapshot/get/update; speaker rows stay in place. `character_profile_service.py`: computed revision and preserve stored concrete voice on accent/gender edits (there is no historical explicit/default flag, so treating stored IDs as pinned avoids silently replacing owner choices).
- `api/projects.py` / `api/profiles.py`: snapshot under read lock, validate catalog outside lock, compare revision again under write lock, then update. Profile apply also checks the referenced profile snapshot.
- `project_visuals_service.py`: same cast member must not reapply changed profile voice when another member is swapped. Newly selected character applies its voice normally.
- `channel_service.py`: copy concrete profile voice into SpeakerConfig/config snapshot for future series projects, not merely into the later cast row.
- Tests/conftest.py adds a deterministic fake voice catalog to the existing provider-isolation policy; tests that exercise failure paths override it locally. Update the former accent-change test to the intentionally new pinned-voice rule, retain facing behavior assertions. No DB migration is needed.
- Step1 currently drops voice_id in load/build payloads: preserve it on draft edit/save and set it for a newly chosen character. Verify existing config browser regression plus JS syntax; no second picker in Step1. New core file is `backend/core/voice.py`.
- Commands: focused profile/project/channel/voice pytest; Ruff; full pytest before persistence checkpoint. Expected: all tests pass with no real catalog calls from the suite.
- Full-suite run exposed an existing browser timing race in `test_video_visual_modes_browser.py`: workspace becomes visible before async visual loading and mode initialization finish. The isolated module passes5/5. Use Playwright's retrying expectation for remembered aria-pressed values, preserving the same required result; no Step5 product-code change. Rerun full suite before checkpoint.

Chỉ sửa các Paths trên và cập nhật tiến độ card/phase. Nếu phát hiện cần file khác, ghi lý do và mở rộng bounded scope trước code. Các file đã tạo bởi task trước trong Paths được tiếp tục sử dụng; không tự viết lại hệ thống lân cận.

## Risks / guardrails

Full replace speaker có cascade script; chỉ dùng update theo ID cho project hiện hữu. Catalog validation không được giữ DB lock chờ mạng.

Dùng constants/path helpers hiện có, service layer async, validation API + semantic. Không giữ shared DB lock trong network/render/copy nặng. Không sửa dữ liệu production khi có thể dùng sandbox. Không thay đổi gate cũ hoặc phát hành chỉ vì task kỹ thuật chạy qua.

## Verification / expected results

1. Create/patch/get/cast/copy hai profile cùng locale/gender khác IDs; reopen DB không mất.
2. Sửa profile không sửa project đã cast, apply rõ ràng đổi đúng ID và giữ CEFR speed/pitch/volume. Legacy default path còn hoạt động.
3. Patch speaker không đổi speaker ID/script_lines; request race trả409, network validation không giữ shared lock. Profile accent/gender update không âm thầm thay explicit voice.
4. `git diff --check`; review diff đúng Paths. Chạy quality gates theo SYSTEM-RULES và PLAN trước commit; explicit staging, tuân thủ PM/owner authorization.

## Acceptance / handoff

- [ ] Các bước trên có evidence thực, test commands và kết quả ghi vào card.
- [ ] Error/race/compatibility cases liên quan được kiểm tra, không chỉ happy path.
- [ ] Không ghi “done/pass” cho test hoặc owner gate chưa chạy.
- [ ] PM/owner nhận kết quả theo AR-06; ghi technical verification và owner acceptance riêng.

## Progress

- Implemented concrete voice_id round-trip in schema/INSERT/config snapshots, computed voice revisions, out-of-lock catalog validation, guarded speaker/profile writes and explicit apply-profile operation. Same cast retains pinned project voice; series and Step1 edit carry the ID. No migration.
- Focused tests **45 passed**: new persistence/race tests, profile APIs, character-name/cast regressions, channel APIs and real Step1 browser edit/reload tests. Legacy profiles with empty voice IDs exposed a channel validation issue; normalized to None and rerun passed. Ruff and JS syntax clean. Full suite running before checkpoint.
- Owner accepted all four new sample voices and wants about20 choices; full live English catalog currently47. Phase owner listening examples accepted; final technical/UI gate still pending.

- Full retry **1675 passed**, one existing Starlette warning, **951.38s**. Evidence: `data/tmp/evolve-20261016/task48.2-pytest-r2.log`. Initial full run stopped at1557 pass/1 browser timing failure; isolated5/5 passed, retrying Playwright expectations fixed premature reads without changing Step5 behavior. Ruff/JS/diff checks clean before checkpoint. No real DB/EXE/release changes.
