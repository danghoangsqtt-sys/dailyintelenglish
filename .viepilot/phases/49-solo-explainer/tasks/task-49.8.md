# Task 49.8 — Render production, cử chỉ và motion theo approved plan

- **Status:** planned · 2026-10-16.
- **Dependencies:** 49.7
- **Requirements:** R02, R03, R04, R05, R06, R07, R11, R13.
- **Contract:** [SPEC tổng](../../../SPEC.md), [PLAN tổng](../../../PLAN.md), [phase SPEC](../SPEC.md), [phase PLAN](../PLAN.md).
- **Scope:** card này là kế hoạch, chưa có kết quả triển khai hay acceptance.

## Objective

Render production, cử chỉ và motion theo approved plan. Hoàn thành contract tương ứng trong SPEC, giữ khả năng dùng project classic và dữ liệu đã xuất.

## Paths

- backend/media/video_renderer_remotion.py
- backend/media/video_service.py
- backend/api/video.py
- backend/schemas/video.py
- backend/library/explainer_service.py
- renderer/src/Root.tsx
- renderer/src/Episode.tsx
- renderer/src/types.ts
- renderer/src/SoloScene.tsx
- renderer/src/Presenter.tsx
- renderer/src/ExplainerVisual.tsx
- renderer/src/CaptionBand.tsx
- renderer/src/spriteTimeline.ts
- renderer/src/conversationMotion.ts
- tests/test_video_service_remotion.py
- renderer/src/presenterTimeline.ts
- renderer/src/presenterTimeline.test.ts
- tests/test_explainer_video_props.py
- .viepilot/phases/49-solo-explainer/PHASE-STATE.md
- .viepilot/TRACKER.md
- .viepilot/ROADMAP.md
- .viepilot/HANDOFF.json
- CHANGELOG.md
- .viepilot/phases/49-solo-explainer/tasks/task-49.8.md

## File-Level Plan / allowed_files

1. Dispatch presentation mode classic/solo; props pin approved revision, front manifest, visual refs và timings thật. Stage assets qua bridge hiện có.
2. Shared SoloScene dựng ảnh, diagram nodes và card reveal theo token anchors; giới hạn text, reuse caption Phase 47/font/brand.
3. 10 pose cues theo ý: talk/point đúng phía/count/emphasize/think/wave/neutral, có rests. Mouth theo audio, blink và breathing nhẹ, seed/frame xác định.
4. Uniform scale và trajectory đã validate; không dùng quarter-turn mirroring cho front. Presenter luôn hiện, không mất hình giữa mouth poses.
5. Precompute/memo anchors/layout/timeline; không solver/provider/file I/O mỗi frame. Reuse ANGLE/timeout/retry và fingerprint check trước atomic publish.
6. Giữ full portrait API flow hiện tại trừ khi có cập nhật scope được ghi rõ; hai aspect dùng bố cục riêng, không crop output16:9.

**File mới dự kiến:** `renderer/src/presenterTimeline.ts`, `renderer/src/presenterTimeline.test.ts`, `tests/test_explainer_video_props.py`.

Chỉ sửa các Paths trên và cập nhật tiến độ card/phase. Nếu phát hiện cần file khác, ghi lý do và mở rộng bounded scope trước code. Các file đã tạo bởi task trước trong Paths được tiếp tục sử dụng; không tự viết lại hệ thống lân cận.

## Risks / guardrails

Cử chỉ vẫn là ảnh2D, không hứa skeletal animation. Mouth pair alignment và blink chỉ dùng pose tương thích để tránh bật khuôn mặt.

Dùng constants/path helpers hiện có, service layer async, validation API + semantic. Không giữ shared DB lock trong network/render/copy nặng. Không sửa dữ liệu production khi có thể dùng sandbox. Không thay đổi gate cũ hoặc phát hành chỉ vì task kỹ thuật chạy qua.

## Verification / expected results

1. Classic props giữ nguyên; Solo chỉ render khi approved và đủ pack/timing/current fingerprint, kiểm tra trước render tốn tài nguyên.
2. Vitest determinism theo seek/seed, mouth/blink/gesture coverage, presenter luôn có và trajectory không che nội dung.
3. Player và final still tại cùng thời điểm khớp geometry/caption/visual; boundary clips cả hai aspect decode được.
4. Đổi voice/layout/asset lúc render không publish stale result; MP4/SRT tốt cũ giữ hash. Đo cost baseline và mới.
5. `git diff --check`; review diff đúng Paths. Chạy quality gates theo SYSTEM-RULES và PLAN trước commit; explicit staging, tuân thủ PM/owner authorization.

## Acceptance / handoff

- [ ] Các bước trên có evidence thực, test commands và kết quả ghi vào card.
- [ ] Error/race/compatibility cases liên quan được kiểm tra, không chỉ happy path.
- [ ] Không ghi “done/pass” cho test hoặc owner gate chưa chạy.
- [ ] PM/owner nhận kết quả theo AR-06; ghi technical verification và owner acceptance riêng.

## Progress

- 2026-10-16: planned; shipping code chưa sửa, tests triển khai chưa chạy.
