# Audit: phụ đề bị chia rời giữa cụm nghĩa

**Ngày:** 2026-10-15 · **Skill:** vp-audit · **Kết quả:** 1 lỗi xác nhận, BUG-041.

## Phạm vi

Owner cung cấp bốn ảnh và xác nhận vấn đề là **chữ phụ đề bị chia rời**, không yêu cầu điều tra thêm giọng đọc. Audit tập trung vào phân trang karaoke của video ngang/dọc; không phải một lần đánh giá lại toàn bộ repository.

- Tier 1 — đọc bối cảnh Phase 46/current trial; không thực hiện lại kiểm tra toàn bộ phase/tag.
- Tier 2 — README đã công bố motion 16:9/9:16; không chứng nhận toàn bộ tài liệu qua audit này.
- Tier 3 — đã truy nguyên code, tái hiện bằng dữ liệu thật, kiểm tra bộ test liên quan và tham khảo hướng dẫn biên tập phụ đề chính thức.

## Finding: BUG-041 — phân trang cắt giữa cụm nghĩa

**Mức độ:** high về chất lượng video học tiếng Anh; không phải mất dữ liệu hoặc crash.

### Dữ liệu thật

Project **The Dinner Party Challenge · Ep. 3: Cooking the Final Dish**, id `6b8c5068-5c52-4bd5-9203-8953bec7b197`, script lines 0/1. SQLite được mở `mode=ro`, `total_changes = 0`.

Reproducer gọi trực tiếp `captionPage`, `buildKaraokeTokens`, `withScriptPunctuation` từ mã nguồn hiện tại với word timings của audio job hoàn tất. Các giới hạn lấy từ cấu hình đang dùng, không giả lập thuật toán phân trang.

| Nhân vật / layout | Cuối trang trước | Đầu trang sau | Khoảng giữa word timestamps |
|---|---|---|---:|
| Alex / 16:9 | `…culinary skills in the` | `kitchen under pressure.` | 29 ms |
| Lina / 16:9 | `…being a total piece` | `of cake for such a talented team like us.` | 15 ms |
| Alex / 9:16 | `…culinary skills in the` | `kitchen under pressure.` | 29 ms |
| Lina / 9:16 | `…being a total` | `piece of cake for such a talented team like us.` | 15 ms |

Alex có một trang ngang 16 từ kéo dài 5.927 ms rồi một trang 3 từ chỉ 1.309 ms. Nội dung không mất nhưng câu bị ngắt ở điểm không tự nhiên. Với bản dọc, một trang còn ghép `Alex. This will be…`: phần cuối câu trước bị đẩy sang trang sau và gộp cùng câu mới.

Các số 29/15 ms là khoảng giữa metadata word timings, **không phải phép đo khoảng lặng từ waveform**. Chưa nghe/đánh giá chất lượng giọng đọc trong audit này.

### Nguyên nhân

1. `renderer/src/motionLayout.ts:5`: bản ngang giới hạn 16 từ / 96 ký tự; bản dọc lấy 10 từ / 54 ký tự từ `safeZone.ts`.
2. `renderer/src/karaoke.ts:93`: `captionPage` xếp từ tuần tự. Chạm trần từ/ký tự là cắt ngay; dấu câu chỉ giúp trong một số trường hợp đủ số từ. Không đánh giá cụm giới từ, thành ngữ, điểm kết thúc câu bị đẩy sang trang sau hoặc cân bằng trang cuối.
3. `renderer/src/Episode.tsx:158`: cả hai layout sử dụng hàm này. Trang đổi theo thời điểm từ đầu tiên của trang mới; CSS không tự gây ra chỗ cắt `piece | of cake`.
4. `renderer/src/Episode.tsx:161`: hiệu ứng vào trang khởi động lại mỗi lần đổi trang. Điều này có thể làm người xem cảm thấy cú cắt rõ hơn; chưa đo độc lập tác động của motion, nên không coi đây là nguyên nhân gốc thứ hai.
5. `renderer/src/captionPaging.test.ts`: 4 test hiện có kiểm tra dấu câu, giới hạn số từ, thứ tự và câu ngắn. Không có kiểm tra giữ cụm nghĩa hoặc cân bằng phần đuôi. **4/4 vẫn pass khi lỗi tái hiện được.**

### Phân biệt với audio

`backend/ai/tts/tts_service.py:89` gửi cả script line vào một lần synthesize. `backend/media/audio_service.py:160` ghép từng audio line và chèn khoảng nghỉ giữa các line (300 ms cùng speaker / 500 ms khác speaker), không sử dụng kết quả phân trang renderer. Chưa có bằng chứng cần tạo lại TTS để sửa lỗi phụ đề này.

## Hướng sửa đề xuất

- Tính các điểm ngắt ứng viên trong giới hạn trước khi chọn trang; ưu tiên hết câu, mệnh đề hoặc trước cụm giới từ/liên từ phù hợp.
- Giữ liền các cụm học và thành ngữ nếu chúng nằm gọn trong khung; có thể truyền danh sách idiom hiện có từ `learning` đến `CaptionBand`. Hiện `EpisodeLine` không chứa `language_notes`, không nên giả định renderer đã có field này.
- Tránh kết thúc trang bằng mạo từ hoặc giới từ đang chờ bổ ngữ; cân bằng phần đuôi để không tạo trang rất ngắn chỉ vì trang trước đã nhồi đầy.
- Dùng cùng một chính sách cho 16:9 và 9:16 với giới hạn hình học riêng; không chữa bằng cách phóng khung hoặc giảm chữ toàn bộ video.
- Giữ nguyên thứ tự token, dấu câu và word timings; bảo đảm phân trang ổn định khi seek/render song song.

Ví dụ bố cục ngang mục tiêu để duyệt (chưa triển khai):

```text
Today, we are attempting a notoriously difficult recipe
→ to truly test our culinary skills in the kitchen under pressure.

but if we stay organized, I am confident that it ends up being
→ a total piece of cake for such a talented team like us.
```

Đây là ví dụ chọn trang, không phải thay đổi nội dung thoại hoặc bắt buộc chia thành nhiều trang ngắn.

### Tài liệu tham khảo

[Netflix — English (USA) Timed Text Style Guide, I.10 Line Treatment](https://partnerhelp.netflixstudios.com/hc/en-us/articles/217350977-English-USA-Timed-Text-Style-Guide) khuyến nghị ưu tiên dấu câu/cấu trúc ngữ pháp khi xuống dòng và tránh tách các thành phần gắn với nhau. Audit áp dụng nguyên tắc dễ đọc này cho **chuyển trang** như một đề xuất thiết kế; không tuyên bố thông số Netflix là yêu cầu bắt buộc cho video karaoke YouTube.

## Bounded implementation proposal

Candidate `allowed_files` cho lượt sửa sau: `renderer/src/karaoke.ts`, `renderer/src/Episode.tsx`, `renderer/src/captionPaging.test.ts`, request BUG-041 và biên bản xác minh. Chỉ thêm helper/test chuyên biệt khi kế hoạch được cập nhật trước.

Kiểm tra cần chạy: regression từ hai câu thật và cả hai layout; giữ token/timing/punctuation, câu ngắn, idiom dài quá khung, thiếu learning, câu không có dấu câu, số/chữ Edge không khớp; Vitest liên quan + TypeScript; preview các điểm chuyển trang bằng renderer thật để kiểm tra safe area và số dòng.

Không cần render lại toàn bộ tập để chẩn đoán. Sau khi bản sửa qua preview mới tái tạo video và đóng gói nếu owner yêu cầu. Theo scope của vp-audit, lượt này lưu finding và tiêu chí; chưa sửa source hoặc thay EXE.

## Guardrails cho vp-auto

```yaml
stack: react-typescript-remotion-captions
summary_used: research-and-local-source
must_follow:
  - Preserve every token exactly once, in order, with its original timings.
  - Keep fitting learning phrases together and prefer grammatical page boundaries.
  - Keep per-layout safe-area and readable font limits.
  - Use deterministic segmentation independent of current frame.
avoid:
  - Fixing only the two screenshot phrases with hardcoded special cases.
  - Increasing page limits or shrinking all text to conceal poor segmentation.
  - Re-synthesizing speech as a workaround for renderer pagination.
preflight_checklist:
  - Reproduce Episode 3 lines 0 and 1 with stored word timings.
  - Cover both 16:9 and 9:16, without dropped or duplicated words.
  - Verify rendered boundary previews, not only token counts.
needs_detail_lookup: false
```

## Evidence

- `data/tmp/caption-audit-20261015/inspect_db.py`, `matched-lines.json` — đọc DB và dữ liệu đối chiếu; 0 DB changes.
- `data/tmp/caption-audit-20261015/repro.mjs`, `real-pages.json` — tái hiện trực tiếp source, word timings thật.
- `npm.cmd test -- src/captionPaging.test.ts` tại `renderer`: **4 passed**, 456 ms.
- Không chạy lại full suite; không đổi script/audio/video gốc, config hoặc runtime đang sử dụng.
