# SPEC — Phase 49: Solo Explainer và bộ presenter chính diện

- Ngày: 2026-10-16 · Trạng thái: **executing 49.5** (49.1–49.4 verified; V49 still pending).
- Mục tiêu: Video kiến thức tiếng Anh một người, front21, minh họa đa dạng, bố cục tự đề xuất và owner duyệt.
- Dependency: Phase 48 / Gate V48; schema → front assets và script → explainer plan → layout → preview → render → integrations → demo.
- Quy mô: XL ·10 task ·49.1–49.4 implemented_verified, 49.5 in_progress, 5 planned.
- Nguồn chuẩn: [SPEC tổng](../../SPEC.md), phần 5–8; [brainstorm](../../../docs/brainstorm/session-2026-10-16.md).
- Thực thi: [phase PLAN](PLAN.md), [state](PHASE-STATE.md).

## Yêu cầu và task

| Task | Kết quả | Requirements |
|---|---|---|
| [49.1](tasks/task-49.1.md) | Mode Solo, schema nền và migration an toàn | R01, R11, R12 |
| [49.2](tasks/task-49.2.md) | Front21 registry, prompt và version manifest | R02, R08, R09, R12 |
| [49.3](tasks/task-49.3.md) | Nhập, duyệt và quản lý bộ front trong UI | R02, R08, R09 |
| [49.4](tasks/task-49.4.md) | Kịch bản độc thoại Why / How / List theo CEFR | R01, R12 |
| [49.5](tasks/task-49.5.md) | Explainer plan: đoạn, minh họa, locks và approval | R04, R06, R07, R12 |
| [49.6](tasks/task-49.6.md) | Bố cục hai tỷ lệ, vùng quan trọng và đường motion | R03, R04, R05, R06, R11 |
| [49.7](tasks/task-49.7.md) | Player preview và editor duyệt bố cục trong Step 5 | R03, R04, R05, R06, R07, R11 |
| [49.8](tasks/task-49.8.md) | Render production, cử chỉ và motion theo approved plan | R02, R03, R04, R05, R06, R07, R11, R13 |
| [49.9](tasks/task-49.9.md) | Shorts, thumbnail, series/copy và export cho Solo | R11, R12, R13 |
| [49.10](tasks/task-49.10.md) | Gate V49: demo thật, hồi quy, đóng gói và bàn giao | R01, R02, R03, R04, R05, R06, R07, R08, R09, R10, R11, R12, R13 |

## Contract bắt buộc

- Presentation mode explicit, default classic cho project cũ; Solo đúng một speaker nhưng viết script trước khi đủ ảnh được.
- Front21 độc lập native 29; 10 cặp miệng + blink; prompt → AI ngoài → owner import/review. Giữ identity/outfit và nhìn camera.
- Why/How/List theo CEFR; ảnh/sơ đồ/thẻ chữ là schema hữu hạn, không executable code từ AI.
- Segment token anchors từ script; timestamp từ audio thật. Revision, source fingerprint, locks và approval snapshot là bắt buộc.
- Presenter luôn hiện, trái/phải/giữa, scale linh hoạt. Hai aspect có layout riêng; xét important regions, caption, brand và cả đường motion.
- Owner preview/chỉnh/duyệt; regenerate giữ fields khóa. Invalid/stale plan không render; sửa concurrent không publish bản cũ.
- Preview dùng cùng component/frame logic với Remotion production. Font/asset URLs/build phải hoạt động trong EXE, không cần dev server.
- Thumbnail một người, Shorts retiming, series/Episode folders, export và classic behavior giữ đúng.

## Gate V49

1. Pack thật 21/21 approved, một tập kiến thức owner chọn có đủ ảnh + diagram + card.
2. Presenter chính diện luôn hiện, cử chỉ/miệng/blink phù hợp, vị trí/scale linh hoạt không che nội dung.
3. Preview sửa/khóa/tải lại/regenerate và production dùng đúng approved revision.
4. Full 16:9, full 9:16 và một Short decode đầy đủ; drift/duration theo SPEC≤0.10s, caption/safe area hợp lệ.
5. Migration/legacy/classic regression, Player bundle/frozen EXE one-click được kiểm tra.
6. Owner duyệt hình/nội dung; technical pass và owner acceptance ghi riêng.

## Không nằm trong phase

Rig3D/LivePortrait, tự sinh bộ presenter bằng Qwen local, arbitrary diagram/HTML từ AI, fact-check tự động toàn bộ kiến thức, tự publish YouTube.

Gate B-25/B-26/B-27/B-28 và Phase 47 owner review vẫn giữ nguyên. Bản phát hành hiện tại 1.4.0-rc.1; target 1.5.0 chưa được build/phát hành.
