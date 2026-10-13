# Prompt tạo bài thuyết trình — Daily Beyond English Studio

**Cách dùng:**
1. Mở ChatGPT (bản có tạo slide / tải file).
2. Đính kèm video demo `demo_output/daily_beyond_english_demo.mp4` (hoặc đưa link nếu ChatGPT không nhận video lớn) và các ảnh trong
   `docs/presentation/screenshots/` (20 ảnh, tên file đã đánh số theo đúng quy trình).
3. Dán toàn bộ phần **PROMPT** bên dưới.

---

## PROMPT

Bạn là chuyên gia thiết kế bài thuyết trình sản phẩm công nghệ cho hội đồng giám khảo. Hãy tạo một bài thuyết trình
**15–18 slide, tiếng Việt**, phong cách hiện đại, chuyên nghiệp, dùng bảng màu của thương hiệu: **xanh lá đậm #14301F,
xanh lá tươi #2BB673, vàng nắng #FFD23F, nền sáng**, font tiêu đề đậm kiểu Montserrat. Mỗi slide: tiêu đề ngắn, tối đa
4–5 ý, ưu tiên hình ảnh tôi đính kèm (đặt đúng ảnh vào đúng slide theo gợi ý), có ghi chú thuyết trình (speaker notes)
khoảng 60–90 giây mỗi slide. Xuất file PowerPoint (.pptx).

### Thông tin sản phẩm

**Tên:** Daily Beyond English Studio — ứng dụng "xưởng sản xuất" video học tiếng Anh cho kênh YouTube *Daily Beyond English*.

**Vấn đề:** Một kênh YouTube dạy tiếng Anh cần đăng đều đặn video chất lượng (hội thoại tự nhiên, giọng đọc chuẩn, phụ đề,
minh họa, từ vựng, thumbnail, mô tả SEO). Làm thủ công một tập mất nhiều giờ với nhiều công cụ rời rạc; khó giữ nhân vật
nhất quán, khó lên kế hoạch nhiều chủ đề/series, kênh dễ đơn điệu.

**Giải pháp:** Một ứng dụng chạy trên máy cá nhân, gom toàn bộ quy trình từ ý tưởng đến gói đăng YouTube trong 7 bước,
có AI hỗ trợ ở mỗi bước, và bảng điều khiển để quản lý cả kênh.

**Đối tượng:** người làm nội dung học tiếng Anh cho người Việt (trình độ A1–C2, mặc định B1).

**Quy trình 7 bước (mỗi bước một màn hình):**
1. **Cấu hình tập** — chủ đề, trình độ CEFR, thể loại (hội thoại, phỏng vấn, kể chuyện, tranh luận…), chọn nhân vật kiểu game.
2. **Kịch bản AI** — hội thoại tự nhiên theo trình độ, sửa từng câu, ghi chú ngôn ngữ (collocation, ngữ pháp).
3. **Học liệu AI** — từ vựng có IPA và nghĩa tiếng Việt, idiom, collocation, phrasal verb, mẫu câu, ngữ pháp, câu hỏi luyện nghe;
   mọi ví dụ đều lấy đúng câu trong bài (hệ thống tự kiểm tra, loại mục AI bịa).
4. **Giọng đọc & nhạc nền** — giọng Edge TTS tự nhiên theo nhân vật, thời gian từng từ để làm phụ đề karaoke, nhạc nền tự chọn
   theo chủ đề, chuẩn hóa âm lượng theo chuẩn phát sóng (ITU-R BS.1770).
5. **Video** — AI dựng storyboard; video dựng bằng Remotion: hai nhân vật "biết nói" (khẩu hình theo giọng, biểu cảm, cử chỉ,
   chớp mắt), nam bên trái – nữ bên phải nhìn nhau, ảnh minh họa hoạt động phía sau, phụ đề karaoke, thẻ từ vựng hiện đúng lúc,
   intro/outro thương hiệu.
6. **Thumbnail** — ghép tự động nhân vật + ảnh minh họa của tập + tiêu đề lớn + nhãn trình độ, số tập, logo; 3 phiên bản;
   hoặc dùng ảnh tự tạo bằng AI bên ngoài theo prompt hệ thống soạn sẵn.
7. **Gói YouTube** — 3 tiêu đề, mô tả chuẩn SEO dưới 5.000 ký tự (chapters, học liệu kèm nghĩa tiếng Việt, câu hỏi luyện nghe,
   hashtag, liên kết tập trước/sau của series), transcript làm bình luận ghim, tải gói zip.

**Quản lý kênh:**
- **Kế hoạch kênh:** Chủ đề (danh sách phát) → Series → Tập; AI đề xuất cả bản đồ kênh đa dạng thể loại và trình độ; tạo hàng
  loạt project đánh số tập; lịch đăng tự xoay vòng chủ đề để kênh không đơn điệu.
- **Dashboard kênh:** số liệu, tập đăng kế tiếp, "việc cần làm hôm nay", **lộ trình xây kênh 5 giai đoạn** tự tính từ dữ liệu
  thật (Bản sắc → Kế hoạch → 10 tập đầu → Đăng đều hằng tuần → Mở rộng), **bảng sản xuất Kanban** theo 7 bước.
- **Thư viện:** Character Library (hồ sơ nhân vật, 29 ô ảnh sprite, prompt cho từng ô để tạo bằng AI ngoài, tự căn chỉnh ảnh),
  Activity Library (ảnh minh họa hoạt động dùng lại; thiếu thì GPU máy vẽ hoặc tạo bằng AI ngoài, duyệt một lần), Scene Library
  (55 bối cảnh), Music Library.

**Công nghệ:**
- Backend Python 3 · FastAPI · SQLite (aiosqlite, 23 migration); frontend HTML/CSS/JavaScript thuần.
- AI: cổng AI "cloud trước, máy cục bộ dự phòng" (Gemini 3.1 Flash-Lite → OpenRouter → Ollama qwen chạy trên GPU RTX 3060),
  ngắt mạch theo nhà cung cấp, kiểm tra JSON schema, tự sửa một lần, tự chuẩn hóa khi AI đặt sai tên trường.
- Giọng nói: Edge TTS có mốc thời gian từng từ. Âm thanh: pydub + ffmpeg + pyloudnorm.
- Video: Remotion 4 + React 19 + TypeScript (render cục bộ). Ảnh: diffusers + RealVisXL trên GPU cục bộ; Pillow cho thumbnail.
- Chất lượng: **1.678 bài kiểm thử tự động** (unit, API, trình duyệt thật với Playwright), quy trình phát triển theo phase có
  kế hoạch – kiểm thử – nghiệm thu chủ sản phẩm ("Gate").

**Số liệu dự án:** bắt đầu 10/09/2026; 715 commit; 37 giai đoạn phát triển (phase); khoảng 21.500 dòng Python, 9.200 dòng
JavaScript, 2.500 dòng TypeScript; 141 file kiểm thử.

**Kết quả thực tế (nghiệm thu Gate B-24):** từ một dòng định hướng, AI lập series "The Dinner Party Challenge" (3 tập); tập 1
làm trọn: kịch bản 20 câu trong 30 giây, học liệu 9 giây, audio 4 phút 19 giây có nhạc trong 38 giây, video dựng trong khoảng
3 phút, 3 thumbnail, gói YouTube với mô tả 2.846 ký tự — toàn bộ chưa đến 10 phút máy chạy cho một tập hoàn chỉnh.

**Điểm khác biệt:**
- Một quy trình liền mạch thay cho 6–8 công cụ rời rạc; mọi bước có thể sửa tay.
- Nhân vật nhất quán xuyên suốt video, thumbnail và cả kênh.
- Học liệu "bám bài" — không bịa ví dụ; phù hợp người học Việt (nghĩa tiếng Việt).
- Quản lý kênh như một sản phẩm: lộ trình, lịch đăng, bảng sản xuất.
- Chạy trên máy cá nhân, dữ liệu tập không rời máy (trừ lời gọi AI văn bản), chi phí thấp.

**Hướng phát triển:** video dọc cho YouTube Shorts và TikTok (clip nổi bật 30–90 giây do AI chọn, cả tập dạng dọc, gói đăng
riêng từng nền tảng); đăng YouTube tự động qua API; phân tích số liệu kênh.

### Cấu trúc slide gợi ý (dùng ảnh theo tên file)

1. **Trang bìa** — tên sản phẩm, slogan "Từ một ý tưởng đến tập YouTube hoàn chỉnh", logo. Ảnh: `19_episode_video_frames.png` (làm nền mờ).
2. **Vấn đề** — làm kênh học tiếng Anh thủ công tốn thời gian, rời rạc, khó đều đặn.
3. **Giải pháp tổng quan** — sơ đồ 7 bước + quản lý kênh. Ảnh: `01_dashboard_top.png`.
4. **Video demo** — chèn video demo (hoặc ảnh `13_step5_video.png` + đường dẫn video).
5. **Kế hoạch kênh bằng AI** — chủ đề → series → tập, lịch xoay vòng. Ảnh: `04_channel_plan.png`, `05_channel_calendar.png`.
6. **Dashboard & lộ trình xây kênh** — Ảnh: `02_dashboard_roadmap.png`, `03_dashboard_board.png`.
7. **Nhân vật nhất quán** — Character Library, chọn nhân vật kiểu game. Ảnh: `06_characters.png`, `07_step1_config.png`.
8. **Kịch bản AI** — Ảnh: `08_step2_script.png`.
9. **Học liệu bám bài** — Ảnh: `09_step3_learning.png`, `10_step3_collocations.png`.
10. **Giọng đọc & nhạc** — Ảnh: `11_step4_audio.png`.
11. **Storyboard & video nhân vật biết nói** — Ảnh: `12_step5_storyboard.png`, `19_episode_video_frames.png`.
12. **Thumbnail tự động** — Ảnh: `14_step6_thumbnails.png`, `20_episode_thumbnails.png`.
13. **Gói YouTube chuẩn SEO** — Ảnh: `15_step7_youtube.png`, `16_step7_pinned.png`.
14. **Thư viện tái sử dụng** — Ảnh: `17_shot_activity_library.png`, `18_music_library.png`.
15. **Kiến trúc & công nghệ** — sơ đồ khối: Giao diện → FastAPI → (Cổng AI cloud/local · TTS · Remotion · GPU ảnh) → SQLite/thư mục dữ liệu.
16. **Chất lượng & quy trình phát triển** — 1.678 test, phase + Gate nghiệm thu, số liệu dự án.
17. **Kết quả thực tế** — số liệu Gate B-24 (thời gian từng bước), so sánh "thủ công nhiều giờ" và "dưới 10 phút máy chạy".
18. **Hướng phát triển & cảm ơn** — Shorts/TikTok, đăng tự động, phân tích kênh; lời cảm ơn và hỏi đáp.

Yêu cầu thêm: biểu đồ đơn giản cho slide 17 (cột thời gian từng bước), sơ đồ cho slide 3 và 15 vẽ bằng hình khối của
PowerPoint (không dùng ảnh chụp), mỗi slide có số trang và logo nhỏ góc dưới.
