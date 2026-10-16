# Task 49.4 — Kịch bản độc thoại Why / How / List theo CEFR

- **Status:** planned · 2026-10-16.
- **Dependencies:** 49.1
- **Requirements:** R01, R12.
- **Contract:** [SPEC tổng](../../../SPEC.md), [PLAN tổng](../../../PLAN.md), [phase SPEC](../SPEC.md), [phase PLAN](../PLAN.md).
- **Scope:** card này là kế hoạch, chưa có kết quả triển khai hay acceptance.

## Objective

Kịch bản độc thoại Why / How / List theo CEFR. Hoàn thành contract tương ứng trong SPEC, giữ khả năng dùng project classic và dữ liệu đã xuất.

## Paths

- backend/content/script_pipeline.py
- backend/content/script_service.py
- backend/ai/llm/prompt_loader.py
- backend/ai/prompts/script/script_base.txt
- backend/ai/prompts/script/outline.txt
- backend/ai/prompts/script/section.txt
- backend/schemas/script.py
- backend/ai/prompts/script/solo_explainer.txt
- tests/test_explainer_script.py
- .viepilot/phases/49-solo-explainer/PHASE-STATE.md
- .viepilot/TRACKER.md
- .viepilot/ROADMAP.md
- .viepilot/HANDOFF.json
- CHANGELOG.md
- .viepilot/phases/49-solo-explainer/tasks/task-49.4.md

## File-Level Plan / allowed_files

1. Thêm prompt riêng Why/How/List bằng tiếng Anh, một người nói với người xem; inject qua prompt_loader, không hardcode trong service.
2. Reuse outline/sections/word budget/CEFR/global repair; điều chỉnh turn-taking checks chỉ ở Solo, giữ validator chung.
3. Truyền presentation mode, structure và speaker ID duy nhất xuyên generation/retry/regenerate.
4. Chủ đề đời sống/kiến thức có ví dụ và tóm tắt, tránh lặp; không mặc định biến thành hội thoại giả hoặc bài ngữ pháp.
5. Ghi chú nguồn khi đầu vào có, không bịa URL/trích dẫn. Owner vẫn duyệt thông tin.

**File mới dự kiến:** `backend/ai/prompts/script/solo_explainer.txt`, `tests/test_explainer_script.py`.

Chỉ sửa các Paths trên và cập nhật tiến độ card/phase. Nếu phát hiện cần file khác, ghi lý do và mở rộng bounded scope trước code. Các file đã tạo bởi task trước trong Paths được tiếp tục sử dụng; không tự viết lại hệ thống lân cận.

## Risks / guardrails

Prompt một speaker hiện có chưa bảo đảm mọi validator hội thoại thích hợp cho độc thoại; kiểm tra cả generation và repair.

Dùng constants/path helpers hiện có, service layer async, validation API + semantic. Không giữ shared DB lock trong network/render/copy nặng. Không sửa dữ liệu production khi có thể dùng sandbox. Không thay đổi gate cũ hoặc phát hành chỉ vì task kỹ thuật chạy qua.

## Verification / expected results

1. Fixtures/prompt/schema cho ba structure và A2/B1/C1; đúng một speaker/cast và word budget hiện có.
2. Classic prompt/repair không đổi; regenerate một đoạn không thêm người thứ hai.
3. Một smoke LLM thật theo policy hiện có; ghi CEFR, độ dài, giới hạn, không coi output là đã fact-check.
4. Structure sai hoặc malformed output bị validate/repair có giới hạn, không lưu script chưa hợp lệ.
5. `git diff --check`; review diff đúng Paths. Chạy quality gates theo SYSTEM-RULES và PLAN trước commit; explicit staging, tuân thủ PM/owner authorization.

## Acceptance / handoff

- [ ] Các bước trên có evidence thực, test commands và kết quả ghi vào card.
- [ ] Error/race/compatibility cases liên quan được kiểm tra, không chỉ happy path.
- [ ] Không ghi “done/pass” cho test hoặc owner gate chưa chạy.
- [ ] PM/owner nhận kết quả theo AR-06; ghi technical verification và owner acceptance riêng.

## Progress

- 2026-10-16: planned; shipping code chưa sửa, tests triển khai chưa chạy.
