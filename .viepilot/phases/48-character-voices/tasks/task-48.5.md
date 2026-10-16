# Task 48.5 — Gate V48: giọng thật, hồi quy và hướng dẫn

- **Status:** planned · 2026-10-16.
- **Dependencies:** 48.4
- **Requirements:** R10, R12, R13.
- **Contract:** [SPEC tổng](../../../SPEC.md), [PLAN tổng](../../../PLAN.md), [phase SPEC](../SPEC.md), [phase PLAN](../PLAN.md).
- **Scope:** card này là kế hoạch, chưa có kết quả triển khai hay acceptance.

## Objective

Gate V48: giọng thật, hồi quy và hướng dẫn. Hoàn thành contract tương ứng trong SPEC, giữ khả năng dùng project classic và dữ liệu đã xuất.

## Paths

- README.md
- docs/user/windows-installation.md
- scripts/generate_api_docs.py
- docs/api.md
- tests/test_tts_service.py
- tests/test_character_profiles_browser.py
- docs/user/character-voices.md
- docs/operations/phase48-character-voices.md
- .viepilot/phases/48-character-voices/PHASE-STATE.md
- .viepilot/TRACKER.md
- .viepilot/ROADMAP.md
- .viepilot/HANDOFF.json
- CHANGELOG.md
- .viepilot/phases/48-character-voices/tasks/task-48.5.md

## File-Level Plan / allowed_files

1. Tạo hai profile thử nghiệm cùng gender/locale nhưng hai voice ID khả dụng khác nhau; dùng project/DB sandbox, không sửa audio dự án thật.
2. Chạy luồng audition → lưu profile → cast → mix → render ngắn; lưu actual resolved voice IDs, timing hashes và ảnh UI.
3. Cập nhật user guide và API docs từ OpenAPI thật, ghi rõ mạng cần cho Edge TTS, profile default vs project override và invalidation.
4. Ghi technical verification và owner listening acceptance riêng. Phase 48 chỉ complete sau owner/PM acceptance, không coi synthesized success là nghe tự nhiên.
5. Không tự publish1.5; Phase 49.1 phụ thuộc V48 theo PLAN.

**File mới dự kiến:** `docs/user/character-voices.md`, `docs/operations/phase48-character-voices.md`.

Chỉ sửa các Paths trên và cập nhật tiến độ card/phase. Nếu phát hiện cần file khác, ghi lý do và mở rộng bounded scope trước code. Các file đã tạo bởi task trước trong Paths được tiếp tục sử dụng; không tự viết lại hệ thống lân cận.

## Risks / guardrails

Không thể dùng checksum khác nhau để kết luận chất giọng đạt yêu cầu; owner nghe quyết định. Không overwrite source audio thật để dựng evidence.

Dùng constants/path helpers hiện có, service layer async, validation API + semantic. Không giữ shared DB lock trong network/render/copy nặng. Không sửa dữ liệu production khi có thể dùng sandbox. Không thay đổi gate cũ hoặc phát hành chỉ vì task kỹ thuật chạy qua.

## Verification / expected results

1. Full pytest/Ruff theo gate dự án; renderer regression/typecheck nếu bridge/freshness sửa liên quan. Không claim pass trước khi có log.
2. Nghe thử hai actual voices để owner nhận ra khác biệt và duyệt; code chỉ xác minh IDs, audio decode/timings.
3. Provider error/stale catalog/no silent fallback demo, save/reload/copy và unchanged classic defaults.
4. Evidence có commands/results/limits; các gate cũ và release1.4.0-rc.1 giữ nguyên.
5. `git diff --check`; review diff đúng Paths. Chạy quality gates theo SYSTEM-RULES và PLAN trước commit; explicit staging, tuân thủ PM/owner authorization.

## Acceptance / handoff

- [ ] Các bước trên có evidence thực, test commands và kết quả ghi vào card.
- [ ] Error/race/compatibility cases liên quan được kiểm tra, không chỉ happy path.
- [ ] Không ghi “done/pass” cho test hoặc owner gate chưa chạy.
- [ ] PM/owner nhận kết quả theo AR-06; ghi technical verification và owner acceptance riêng.

## Progress

- 2026-10-16: planned; shipping code chưa sửa, tests triển khai chưa chạy.
