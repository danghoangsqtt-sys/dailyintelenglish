# Brainstorm — Phim tài liệu doodle giải thích (video dài, ảnh tĩnh AI, phụ đề từng từ)

## Session Info

- **Date:** 2026-11-05, Asia/Bangkok
- **Status:** Phạm vi đã chốt với owner; kế hoạch: [Phase 98](../../.viepilot/phases/98-doodle-story/PLAN.md).
- **workflow_version:** 2.19.0
- **Skill:** vp-brainstorm 1.1.0
- **Language:** vi (theo owner)
- **Nguồn:** owner đính kèm video tham khảo "The Nepal Disaster: Why the Mountain Turned Into a Tsunami" (YouTube `IUQvhmXyvwk`). Chỉ học công thức, không dùng lại lời, ảnh hay logo của video đó (cùng nguyên tắc Phase 96).

## 1. Phân tích video tham khảo (số đo thật)

| Yếu tố | Kết quả | Cách đo |
|---|---|---|
| Định dạng | 10:24, 1920x1080, 30 fps, H.264/AAC | ffprobe |
| Số shot | 112; trung bình 5,6 s, trung vị 4,9 s | Lệch khung hình 5 fps, bỏ dải phụ đề |
| Nhịp cắt | 18 lần ở phút đầu, sau đó khoảng 9–12 lần/phút | Như trên |
| Chuyển động trong shot | Không có (lệch < 1/255 trên 6 shot) | So đầu và cuối shot |
| Chuyển cảnh | Crossfade 12 khung = 0,4 s (6 chỗ đo) | Lệch từng khung 30 fps |
| Lời | 1.818 từ, 175 từ/phút, 124 câu, trung vị 13 từ/câu | faster-whisper small (tên riêng có thể nghe sai) |
| Hình/lời | 16 từ/ảnh, 1,1 câu/ảnh | Tính từ hai số trên |
| Âm thanh | Một giọng, không nhạc nền (khoảng nghỉ tụt dưới -60 dB, 193 lần) | silencedetect |
| Phụ đề | IN HOA đậm, trắng, không viền, 3–5 từ, ở giữa phía dưới, từ đang đọc nằm trong ô đen bo góc | Xem khung hình |

**Lỗi của mẫu, không chép:** một ảnh giữ 59 s (3:57–4:57); chữ của prompt lọt vào ảnh ("HISTORICAL DOODLE MAP OF VALLEY."); phụ đề trắng khó đọc trên nền kem.

### Công thức kịch bản

| Đoạn | Mốc | Vai trò |
|---|---|---|
| Mở lạnh | 0:00–0:50 | Hình ảnh gây sốc, 3 điều vô lý, một câu hỏi; không chào |
| Dữ kiện | 0:50–1:20 | Ở đâu, khi nào, thiệt hại |
| Giải thích sai, lật lại | 1:20–2:05 | Giả thuyết đầu tiên sụp đổ |
| Điều tra | 2:05–3:20 | Tìm ra nguồn, số liệu kèm so sánh |
| Khái niệm then chốt | 3:20–4:57 | Gọi tên một thuật ngữ và giải thích bằng ẩn dụ |
| Phá hiểu lầm | 4:57–6:07 | Vì sao cách gọi phổ biến là sai |
| Điều chưa chắc | 6:07–6:50 | Nói rõ "chưa được xác nhận" |
| Vì sao không ai được báo | 6:50–7:50 | Góc hệ thống |
| Nguyên nhân sâu xa, lịch sử lặp lại | 7:50–9:10 | Mở rộng ý nghĩa |
| Tóm tắt nhân quả | 9:10–9:47 | Nối cả chuỗi |
| Tôn trọng nạn nhân, cảm ơn | 9:47–10:24 | Kết thúc |

Thủ pháp: câu móc mỗi 30–60 s, số liệu luôn có so sánh dễ hình dung và hai đơn vị đo, một ẩn dụ dễ nhớ cho mỗi khái niệm.

### Kiểu hình lặp lại

Bản đồ ghim đỏ · thước đo kích thước · mặt cắt có nhãn · trước/sau · thẻ thuật ngữ · gạch chéo đỏ · lịch · đường thời gian · ẩn dụ nhân hóa · nến tưởng niệm. Phong cách: nét mực tay, giấy cũ, màu đất (ochre, cát, olive, xanh bụi, nâu gỉ), người que đầu tròn trắng.

## 2. Thử kỹ thuật (2026-11-05)

Qwen-Image-2.1-Turbo trên RTX 3060, 6 cảnh do tôi tự nghĩ (chủ đề khác video gốc): [ảnh lưới](assets/2026-11-05-doodle/qwen-test-grid.jpg).

- Phong cách đồng nhất trên 6/6 ảnh; mọi nhãn chữ yêu cầu đúng chính tả.
- Khoảng 30 s/ảnh, thêm 85 s nạp model, VRAM đỉnh 9,3 GB. Ước tính 112 ảnh gần 1 giờ.
- Yếu: nét giống bút chì hơn mẫu, giấy có vệt mờ nhỏ, hình dáng vật có thể sai (bồn chứa bị vẽ tròn).
- Chưa thử: một video hoàn chỉnh; độ ổn định qua hơn 100 ảnh; chất lượng kịch bản 1.800 từ.

## 3. Đối chiếu hệ thống

| Cần | Trạng thái | Nơi liên quan |
|---|---|---|
| Video một giọng, kế hoạch hình theo đoạn | Có | `solo_explainer`, `backend/library/explainer_service.py` |
| Vẽ Qwen theo đoạn | Có, cần thêm công thức doodle | `backend/ai/image/pipelines.py`, `recipes.py` |
| Đọc link/bài báo | Có | `backend/content/link_reader.py`, `source_service.py` |
| Kiểm tra sự thật | Có | `vox_fact_issues`, `prompts/explainer/fact_check.txt` |
| Sửa, vẽ lại ảnh | Có cho các kiểu vẽ theo dòng | `backend/content/beats_service.py`, Step 5 |
| Phụ đề theo từ | Có; thiếu kiểu ô đen | `backend/renderer/src/karaoke.ts`, `captionStyle.ts` |
| Tự động qua đêm, gói YouTube | Có | `backend/automation/`, `youtube_service.py` |
| Ảnh tràn khung, crossfade 0,4 s | Thiếu | Scene Remotion mới |
| Kịch bản dài 1.800 từ theo công thức trên | Thiếu | VOX tối đa 8 khối x 70 từ, khoảng 560 từ (`script_pipeline.py`) |
| Kiểm tra: không giữ ảnh quá lâu, không có chữ prompt trong ảnh | Thiếu | Kiểm tra kế hoạch hình |

VOX giữ nguyên; thêm một kiểu video mới, không thay thế kiểu cũ.

## 4. Quyết định

Owner chốt 2026-11-05:

| # | Câu hỏi | Owner chọn |
|---|---|---|
| D1 | Lớp học tiếng Anh | **Phim + thẻ từ khóa:** phim liền mạch, 5-8 thẻ thuật ngữ đúng lúc nhắc đến (IPA, nghĩa tiếng Việt theo cài đặt khán giả), danh sách từ trong mô tả YouTube |
| D2 | Nguồn nội dung | **Cả chủ đề và bài báo:** nhập chủ đề, hoặc dán link để AI viết lại bằng lời mới; có kiểm tra sự thật, cờ cảnh báo số liệu, owner duyệt trước khi xuất |
| D3 | Độ dài, khung hình | **16:9, chọn 3-12 phút,** mặc định khoảng 8 phút; bản Shorts để sau |
| D4 | Phong cách hình | **Giấy cũ + điểm nhấn xanh:** nét mực, màu đất, thêm chút xanh lá và vàng của Daily Beyond English |
| D5 | Quy tắc D123 | **Ngoại lệ cho riêng kiểu video này:** vẽ người que mặt chấm chung chung; vẫn không vẽ nhân vật của kênh. Các kiểu video khác giữ nguyên D123 |
| D6 | Loại nội dung | Owner bổ sung khi lập phase: "kết hợp giữa một chủ đề lịch sử, thần thoại, chuyên môn, hay một nội dung truyện ngắn tự tạo kết hợp với tiếng anh thay vì chỉ là nội dung không đầu không đuôi". Mỗi video là **một câu chuyện trọn vẹn** thuộc một trong bốn loại, tiếng Anh dệt vào chính câu chuyện. Làm rõ D2: bài báo hoặc tài liệu dán vào là tư liệu cho bốn loại này, không phải một loại tin thời sự riêng |

### Mặc định đề xuất (owner chưa hỏi riêng, đổi được khi lập kế hoạch)

- Kiểu video mới trong Solo; VOX và các kiểu cũ giữ nguyên hành vi.
- Không nhạc nền theo mẫu; nhạc nền hiện có vẫn bật được.
- Giọng đọc chọn như các kiểu Solo hiện có.
- Không giữ một ảnh quá 12 s (mẫu có 3 shot 12-13 s, loại trừ lỗi 59 s).
- Phụ đề IN HOA, ô đen ở từ đang đọc, thêm viền chữ để dễ đọc hơn mẫu.
- Thông tin về nạn nhân phải có nguồn; điều chưa xác nhận phải nói rõ; kết bằng giọng tôn trọng.

## 5. Câu hỏi mở

- Local AI có viết nổi kịch bản khoảng 1.800 từ theo công thức không (VOX từng ngắn hơn 30 % và lặp lại công thức khi chia đoạn, Phase 86)?
- Qwen có giữ được phong cách và nhãn chữ qua hơn 100 ảnh không?

Cả hai được trả lời bằng video thử hoàn chỉnh ở Phase 1.

## Phases

- **Phase 1:** công thức hình doodle có điểm nhấn xanh; cảnh ảnh tràn khung, crossfade 0,4 s; phụ đề ô đen; kịch bản dài 3-12 phút từ chủ đề hoặc bài báo; kiểm tra sự thật; sửa và vẽ lại ảnh ở Step 5; thẻ thuật ngữ và danh sách từ; một video thử hoàn chỉnh để owner duyệt.
- **Phase 2:** đưa vào Tự động, Channel, Shorts batch nếu Phase 1 đạt.
- **Phase 3:** cắt Shorts 9:16 từ video dài.

## Project meta intake (FEAT-009)

Bỏ qua: dự án đã có `.viepilot/PROJECT-META.md` và hồ sơ thương hiệu Daily Beyond English từ các phiên trước. Không đổi.

## Next

`/vp-evolve` để lập phase (mô hình làm việc gần đây: PLAN.md commit riêng trước khi cài đặt).
