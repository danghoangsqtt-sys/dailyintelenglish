# Task 49.4 — Kịch bản độc thoại Why / How / List theo CEFR

- **Status:** implemented_verified · 2026-10-16; structure/transport verified, content/CEFR owner review remains V49.
- **Dependencies:** 49.1
- **Requirements:** R01, R12.
- **Contract:** [SPEC tổng](../../../SPEC.md), [PLAN tổng](../../../PLAN.md), [phase SPEC](../SPEC.md), [phase PLAN](../PLAN.md).
- **Scope:** Solo script/prompt/repair paths implemented and technically verified. Real LLM smoke recorded separately from owner content/CEFR acceptance.

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
- backend/ai/prompts/script/repair.txt
- backend/ai/prompts/script/regenerate_line.txt
- tests/test_explainer_script.py
- .viepilot/phases/49-solo-explainer/PHASE-STATE.md
- .viepilot/TRACKER.md
- .viepilot/ROADMAP.md
- .viepilot/HANDOFF.json
- CHANGELOG.md
- .viepilot/phases/49-solo-explainer/tasks/task-49.4.md
- .viepilot/phases/49-solo-explainer/tasks/task-49.5.md
- .viepilot/phases/49-solo-explainer/PLAN.md
- .viepilot/phases/49-solo-explainer/SPEC.md
- .viepilot/PLAN.md
- .viepilot/SPEC.md

## File-Level Plan / allowed_files

1. Thêm prompt riêng Why/How/List bằng tiếng Anh, một người nói với người xem; inject qua prompt_loader, không hardcode trong service.
2. Reuse outline/sections/word budget/CEFR/global repair; điều chỉnh turn-taking checks chỉ ở Solo, giữ validator chung.
3. Truyền presentation mode, structure và speaker ID duy nhất xuyên generation/retry/regenerate.
4. Chủ đề đời sống/kiến thức có ví dụ và tóm tắt, tránh lặp; không mặc định biến thành hội thoại giả hoặc bài ngữ pháp.
5. Ghi chú nguồn khi đầu vào có, không bịa URL/trích dẫn. Owner vẫn duyệt thông tin.

**File mới dự kiến:** `backend/ai/prompts/script/solo_explainer.txt`, `tests/test_explainer_script.py`.

### Execution refinement (isolated preparation during 49.3 full gate)

- Existing section/global validators already exempt a one-speaker script from turn-taking/balance, so keep those checks and classic behavior. Explicit Solo mode must reject a malformed multi-speaker configuration before a provider call; old single-speaker classic remains supported.
- Add one bounded Jinja Solo block for Why/How/List, viewer-directed English knowledge explanation, everyday examples and a takeaway. Existing genre's dialogue instructions must not override Solo. Preserve CEFR ceiling, language-feature toggles, actual word budgets and one UUID/alias across direct generation, outline, sections, all repair purposes and single-line regeneration.
- Add optional mode/structure context to prompt loader and template conditions with classic defaults. Repair and regeneration templates are within scope because otherwise rewritten text can lose the Solo purpose/structure. Do not rewrite transport, worker checkpoints or budget algorithms. Current config hashes already include full project mode/structure; verify this rather than adding another hash.
- Tests cover Why/How/List ×A2/B1/C1 prompt constraints, one-speaker validation, bounded semantic/length repairs, regeneration ID preservation, classic prompt compatibility and section/global checks. Run a real LLM smoke in an isolated DB through current provider policy and record actual word counts/IDs/content limits; do not write owner scripts or certify facts/CEFR from model success alone.

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

- 2026-10-16:49.3 checkpoint 9a74aba persisted/pushed with clean/upstream/ahead0;10 bounded Solo script/test files applied afterward. Ruff/diff clean, no modified frontend JS in this task.
- Solo Why/How/List Jinja block, explicit one-presenter guard and context through legacy full generation, pipeline outline/section/semantic-length-global repairs, and single-line regeneration implemented. Classic mode keeps its prompt defaults; Solo generated line identity stays server-owned. Existing one-speaker exemptions and checkpoint/budget algorithms retained.
- Candidate/source focused **238 passed** (source 2.85s), including 24 new cases for structure×A2/B1/C1, malformed mode/count/structure, one-presenter persistence over 10 lines, bounded unknown-speaker repair/failure preserving prior script, classic default equality and regeneration. A draft test expected `failed`; corrected to the actual durable status enum`error` without changing production job states.
- Real source pipeline smoke in new sandbox `data/tmp/evolve-20261016/solo-llm-18d6918f5b/`: B1 Why, 125-word/1min target; actual 114 words, one presenter, one repair, complete in 124.594s. Gemini 3.1 Flash-Lite unavailable; configured chain succeeded with `gemini-flash-lite-latest`. No provider policy override. Read current owner settings via read-only DB connection, wrote only sandbox. Full source regression running; no task PASS yet, no owner content/CEFR/factual certification or real project overwrite.
- First full gate **1775 passed in 707.45s**. Review found the first real draft too abstract with an over-simple brain explanation. Refined Solo-only instructions for concrete language, useful examples instead of padding and careful factual claims; classic templates/transport unchanged. Isolated refined prompt still 238 pass; second real pipeline completed 117 words in 180.706s, one presenter/one repair, last response `gemini-3.1-flash-lite` after transient cloud failures. Its driving/brain-rest wording also needs editorial review, so neither sample is owner-approved or demo-ready; model success is not factual/CEFR acceptance. Refined prompt applied only after first full finished; rerun focused/full gates before checkpoint.

- Final refined source **1775 passed in 709.21s**, one existing Starlette warning; 238 focused in 3.01s, Ruff/diff clean. Separate comparison against pre-Solo committed templates: 6 classic full prompts +3 regeneration prompts unchanged, ignoring only trailing whitespace. No frontend JS changed. Real 114/117-word smokes are structural evidence only, not approved demo content; editorial/factual limits above retained. No owner script/media/EXE replaced.
- Next 49.5: ignored 028 migration copy preserved 17 AI jobs/43 checkpoints/13 projects/290 script lines, injected middle-file rollback/schema/tracking and 2 restarts/FK/integrity verified. Draft timing 13 checks pass and resolves 25/25 real Edge tokens, 11.54s presentation with source word start/end retained. These are preparation only until 49.5 source/task gates.
