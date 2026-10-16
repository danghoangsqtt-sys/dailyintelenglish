# SPEC — Phase 48: Giọng nói riêng cho nhân vật

- Ngày: 2026-10-16 · Trạng thái: **implemented_verified**.
- Mục tiêu: Chọn, nghe thử và lưu concrete voice ID cho từng profile/speaker, không dùng lại cache giọng cũ.
- Dependency: Không cần migration hoặc owner gate cũ đóng để bắt đầu. Không thay trạng thái Phase 47; V48 đã có technical evidence và owner listening acceptance.
- Quy mô: L · 5 task · 5 technically verified, V48 evidence complete.
- Nguồn chuẩn: [SPEC tổng](../../SPEC.md), phần 4.1–4.3; [brainstorm](../../../docs/brainstorm/session-2026-10-16.md).
- Thực thi: [phase PLAN](PLAN.md), [state](PHASE-STATE.md).

## Yêu cầu và task

| Task | Kết quả | Requirements |
|---|---|---|
| [48.1](tasks/task-48.1.md) | Catalog giọng Edge TTS và nghe thử độc lập | R10, R13, R14, R15 |
| [48.2](tasks/task-48.2.md) | Lưu giọng theo profile và speaker project | R10, R12, R13 |
| [48.3](tasks/task-48.3.md) | Fingerprint TTS, invalidation và bảo vệ media tốt cũ | R12, R13 |
| [48.4](tasks/task-48.4.md) | Voice picker trong hồ sơ nhân vật và Audio Studio | R10, R13, R14, R15 |
| [48.5](tasks/task-48.5.md) | Gate V48: giọng thật, hồi quy và hướng dẫn | R10, R12, R13, R14, R15 |

## Contract bắt buộc

- Edge TTS hiện có; danh sách giọng English lấy metadata thật, cache có trạng thái stale, không hứa voice/style không tồn tại.
- Audition riêng khỏi cache script; concrete voice ID và effective parameters hiển thị rõ.
- Profile default cho lần cast mới; project đã cast có snapshot riêng. Apply phải chủ động và giữ speed/pitch/volume theo project.
- Speaker update theo ID, không thay cả speaker list; revision guard chống request cũ.
- Fingerprint TTS và targeted invalidation, word timings/karaoke/nhạc không mất. Voice unavailable không fallback sai giọng trong im lặng.
- Legacy project/default map còn dùng được, không tự mass regenerate.

## Gate V48

1. Hai profile cùng giới tính/locale chọn hai voice ID khác nhau, lưu/tải lại/cast đúng.
2. Audition không đổi project/cache; profile edit không tự đổi project đã cast.
3. Voice change không reuse line giọng cũ; chỉ speaker liên quan synth lại, media tổng stale đúng.
4. Provider/network/race lỗi được báo rõ; audio decode/word timings/mix/render ngắn có evidence.
5. Owner nghe và duyệt; automated ID checks không thay nhận xét chất giọng. Owner accepted Brian/Christopher/Roger/Ryan on2026-10-16, requesting about20 selectable voices. Show the full real English catalog (47 observed), with search/filter/audition/save, rather than restricting selection to four samples. Phase technical gate verified; source evidence in SUMMARY, installed EXE unchanged.

## Không nằm trong phase

Engine TTS mới, cloning giọng, tự tạo lại hàng loạt episode đã xuất, ép tất cả nhân vật khác voice.

Gate B-25/B-26/B-27/B-28 và Phase 47 owner review vẫn giữ nguyên. Bản phát hành hiện tại1.4.0-rc.1; target 1.5.0 chưa được build/phát hành.
