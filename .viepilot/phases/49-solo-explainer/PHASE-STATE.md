# PHASE-STATE — Phase 49: Solo Explainer và bộ presenter chính diện

- **Status:** implementation_verified_owner_art_pending;49.1–49.9 technically verified,49.10 code/package checks verified, real-art V49 demonstration pending.
- **Planned at:** 2026-10-16, Asia/Bangkok.
- **Tasks:**9/10 technically verified;49.10 implementation verified but its real-art/owner gate remains pending. No implementation task is left planned.
- **Gate V49:** fixture technical checks passed; real-art demonstration and explicit owner acceptance pending.
- **Dependencies:** Phase 48 / Gate V48; schema → front assets và script → explainer plan → layout → preview → render → integrations → demo.
- **Release:** published1.4.0-rc.1 unchanged; local staged source EXE verified; target1.5.0 unreleased.
- **Source:** [SPEC](SPEC.md), [PLAN](PLAN.md), [master PLAN](../../PLAN.md).

| Task | Nội dung | Status |
|---|---|---|
| [49.1](tasks/task-49.1.md) | Mode Solo, schema nền và migration an toàn | implemented_verified |
| [49.2](tasks/task-49.2.md) | Front21 registry, prompt và version manifest | implemented_verified |
| [49.3](tasks/task-49.3.md) | Nhập, duyệt và quản lý bộ front trong UI | implemented_verified |
| [49.4](tasks/task-49.4.md) | Kịch bản độc thoại Why / How / List theo CEFR | implemented_verified |
| [49.5](tasks/task-49.5.md) | Explainer plan: đoạn, minh họa, locks và approval | implemented_verified |
| [49.6](tasks/task-49.6.md) | Bố cục hai tỷ lệ, vùng quan trọng và đường motion | implemented_verified |
| [49.7](tasks/task-49.7.md) | Player preview và editor duyệt bố cục trong Step 5 | implemented_verified |
| [49.8](tasks/task-49.8.md) | Render production, cử chỉ và motion theo approved plan | implemented_verified |
| [49.9](tasks/task-49.9.md) | Shorts, thumbnail, series/copy và export cho Solo | implemented_verified |
| [49.10](tasks/task-49.10.md) | Gate V49: demo thật, hồi quy, đóng gói và bàn giao | implementation_verified_owner_art_pending |

**49.5a checkpoint (2026-10-16):** 49.5a foundation verified: immutable project illustrations, exact token/real-audio timing and atomic028 job/asset migration. Full1809 passed in740.11s,143 related tests (34 new), Ruff/diff clean. Populated disposable copy preserved17 jobs/43 checkpoints and passed injected rollback/FK/integrity/2 restarts; actual Edge mapping25/25 tokens over11.54s.49.5 remains in_progress for proposal/locks/history/approval; owner DB/EXE/release unchanged.

**49.5b recovery verification (2026-10-16):** 49.5b technically verified: full pytest 1848 passed in741.01s;175 focused in28.42s;104 renderer tests and TypeScript/Ruff/JS/diff clean. BUG-042 cancellation-safe shared rollback and BUG-043 PATCH422 fixed;BUG-044 docs reconciled. Two fresh process restarts preserved history/locks/idempotency;integrity/FK clean. Next49.6 geometry/layout; production approval refuses missing real geometry. Owner DB/EXE/release and V49/older gates unchanged. [Report](../../../docs/operations/task49-5b-recovery-20261016.md). Git persistence is assessed separately before formal task PASS.

## Planning verification

SPEC/PLAN đã được viết từ yêu cầu owner và code inventory. Validation tài liệu ghi ở master handoff; không dùng planning validation để đánh dấu implementation pass.

## Owner inputs

Owner đã chọn **Hoang — “Why do we build habits?”** ngày16/10/2026. Dùng profile Hoang hiện có làm identity/outfit reference, cấu trúc Why. Bộ21 ảnh front sẽ do owner tạo bằng AI ngoài rồi nhập/duyệt; vẫn cần trước GateV49. Fixture dùng để kiểm tra logic trước, không thay nghiệm thu hình thật.

Bản chuẩn bị prompt21 và ảnh tham chiếu đã được gửi owner tại `data/tmp/evolve-20261016/hoang-front21/`. Đọc từ bản sao DB đã kiểm chứng, không sửa profile/assets thật. Neutral front vẫn chờ owner tạo/duyệt; backend và UI front import/review đã verified; real owner art chưa nhập/duyệt. Solo script đã qua technical gate; layout/render vẫn đang triển khai. Hai real LLM drafts chưa owner/factual/CEFR accepted.

Phase 47 vẫn chờ visual review. Gate B-25/B-26/B-27/B-28 giữ pending.

## Final implementation checkpoint —2026-10-16

Feature full pytest 1867 passed in779.20s. Post-Windows-UTF8 full run:1862 passed,5 legacy subprocess mock-signature failures; all40 video/bridge checks passed in7.95s after updating those5 mocks, with no further application-code change.124 renderer tests, TypeScript/Ruff/JS/diff clean. Actual Player/StillFrame6 comparisons, four decoded fixture MP4s, two frozen restarts and production landscape/portrait/SRT verified. Real owner art/V49 acceptance pending.

[Report](../../../docs/operations/phase49-solo-explainer.md) · [Summary](SUMMARY.md). Start with Character Library → Presenter21 to create/import/review real owner pictures; then complete49.10 real demo/V49.
